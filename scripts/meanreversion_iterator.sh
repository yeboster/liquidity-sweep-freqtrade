#!/bin/bash
# MeanReversionTrend Iterator — runs every 2 hours
# Goal: iterate strategy parameters until 40% annual profit target is hit

set -e

REPO="yeboster/liquidity-sweep-freqtrade"
STRATEGY_FILE="strategies/MeanReversionTrend.py"
CONFIG_FILE="config_meanreversion.json"
LOG_FILE="iteration_log.md"
WORKSPACE="/home/node/.openclaw/workspace/projects/liquidity-sweep-freqtrade"

cd "$WORKSPACE"

# Pull latest
export PATH="/home/node/.local/bin:$PATH"
git pull origin main 2>/dev/null || true

# Read latest backtest results
LATEST_SUMMARY="latest_summary.json"
if [ -f "$LATEST_SUMMARY" ]; then
    PROFIT_PCT=$(jq -r '.profit_pct // 0' "$LATEST_SUMMARY")
    TOTAL_TRADES=$(jq -r '.total_trades // 0' "$LATEST_SUMMARY")
    WR=$(jq -r '.win_rate // 0' "$LATEST_SUMMARY")
    RR=$(jq -r '.rr_ratio // 0' "$LATEST_SUMMARY")
    DRAWDOWN=$(jq -r '.drawdown_pct // 0' "$LATEST_SUMMARY")
else
    PROFIT_PCT=0
    TOTAL_TRADES=0
    WR=0
    RR=0
    DRAWDOWN=0
fi

TIMESTAMP=$(date -u "+%Y-%m-%d %H:%M:%S")
echo "=== Iteration check at $TIMESTAMP ==="
echo "Profit: ${PROFIT_PCT}% | Trades: $TOTAL_TRADES | WR: ${WR}% | R/R: $RR | DD: ${DRAWDOWN}%"

# Decision logic
NEED_CHANGE=false
CHANGE_DESC=""

if (( $(echo "$PROFIT_PCT < 10" | bc -l) )); then
    NEED_CHANGE=true
    CHANGE_DESC="profit < 10% — loosen filters (lower dev threshold 2.0→1.5, widen ATR compression 0.5→0.7)"
elif (( $(echo "$PROFIT_PCT < 20" | bc -l) )); then
    NEED_CHANGE=true
    CHANGE_DESC="profit < 20% — moderate loosen (lower dev threshold 2.0→1.7, add more pairs)"
elif (( $(echo "$PROFIT_PCT < 30" | bc -l) )); then
    NEED_CHANGE=true
    CHANGE_DESC="profit < 30% — fine-tune exits (raise time_exit_profit_floor 1%→1.5%, tighten stop -2.5%→-2%)"
elif (( $(echo "$PROFIT_PCT < 40" | bc -l) )); then
    NEED_CHANGE=true
    CHANGE_DESC="profit < 40% — add pairs or tighten entry filters for quality"
else
    CHANGE_DESC="profit >= 40% — target hit, no changes"
fi

if [ "$TOTAL_TRADES" -eq 0 ]; then
    NEED_CHANGE=true
    CHANGE_DESC="ZERO trades — remove RSI confirmation, lower dev threshold to 1.0, disable trend filter"
fi

if [ "$NEED_CHANGE" = true ]; then
    echo "Applying: $CHANGE_DESC"
    
    # Use Python to safely modify strategy parameters
    python3 << PYEOF
import re

with open("$STRATEGY_FILE", "r") as f:
    content = f.read()

# Track what we changed
changes = []

# Read current values
import re

dev_match = re.search(r'entry_dev_threshold\s*=\s*([0-9.]+)', content)
current_dev = float(dev_match.group(1)) if dev_match else 2.0

atr_match = re.search(r'atr_compression_ratio\s*=\s*([0-9.]+)', content)
current_atr = float(atr_match.group(1)) if atr_match else 0.5

rsi_match = re.search(r'rsi_oversold\s*=\s*([0-9.]+)', content)
current_rsi_os = float(rsi_match.group(1)) if rsi_match else 30.0

rsi_ob_match = re.search(r'rsi_overbought\s*=\s*([0-9.]+)', content)
current_rsi_ob = float(rsi_ob_match.group(1)) if rsi_ob_match else 70.0

stop_match = re.search(r'stoploss\s*=\s*-([0-9.]+)', content)
current_stop = float(stop_match.group(1)) if stop_match else 0.025

time_match = re.search(r'time_exit_profit_floor\s*=\s*([0-9.]+)', content)
current_time = float(time_match.group(1)) if time_match else 0.01

profit = float("$PROFIT_PCT")
trades = int("$TOTAL_TRADES")

if trades == 0:
    # No trades at all — drastically loosen
    new_dev = max(1.0, current_dev - 0.5)
    new_atr = min(0.9, current_atr + 0.2)
    # Disable trend filter for testing
    content = re.sub(r'use_trend_filter\s*=\s*True', 'use_trend_filter = False', content)
    # Disable RSI strictness
    content = re.sub(r'rsi_oversold\s*=\s*[0-9.]+', f'rsi_oversold = 20', content)
    content = re.sub(r'rsi_overbought\s*=\s*[0-9.]+', f'rsi_overbought = 80', content)
    changes.append(f"ZERO trades fix: dev {current_dev}→{new_dev}, atr {current_atr}→{new_atr}, trend filter OFF, RSI relaxed")

elif profit < 10:
    new_dev = max(1.2, current_dev - 0.3)
    new_atr = min(0.8, current_atr + 0.2)
    changes.append(f"Loosen: dev {current_dev}→{new_dev}, atr {current_atr}→{new_atr}")

elif profit < 20:
    new_dev = max(1.4, current_dev - 0.2)
    new_atr = min(0.7, current_atr + 0.1)
    changes.append(f"Moderate loosen: dev {current_dev}→{new_dev}, atr {current_atr}→{new_atr}")

elif profit < 30:
    new_time = min(0.02, current_time + 0.005)
    new_stop = max(0.02, current_stop - 0.005)
    content = re.sub(r'time_exit_profit_floor\s*=\s*[0-9.]+', f'time_exit_profit_floor = {new_time:.4f}', content)
    content = re.sub(r'stoploss\s*=\s*-([0-9.]+)', f'stoploss = -{new_stop:.4f}', content)
    changes.append(f"Tune exits: time_floor {current_time}→{new_time}, stop -{current_stop}→-{new_stop}")

elif profit < 40:
    # Tighten for quality to push over the edge
    new_dev = min(2.5, current_dev + 0.1)
    changes.append(f"Tighten quality: dev {current_dev}→{new_dev}")

# Apply dev and atr changes if they were set
if 'new_dev' in locals():
    content = re.sub(r'entry_dev_threshold\s*=\s*[0-9.]+', f'entry_dev_threshold = {new_dev:.1f}', content)
if 'new_atr' in locals():
    content = re.sub(r'atr_compression_ratio\s*=\s*[0-9.]+', f'atr_compression_ratio = {new_atr:.1f}', content)

# Update version
version_match = re.search(r'STRATEGY_VERSION\s*=\s*"([0-9.]+)"', content)
if version_match:
    old_ver = version_match.group(1)
    parts = old_ver.split('.')
    if len(parts) >= 2:
        parts[-1] = str(int(parts[-1]) + 1)
        new_ver = '.'.join(parts)
        content = re.sub(r'STRATEGY_VERSION\s*=\s*"[0-9.]+"', f'STRATEGY_VERSION = "{new_ver}"', content)
        changes.append(f"Version: {old_ver}→{new_ver}")

with open("$STRATEGY_FILE", "w") as f:
    f.write(content)

# Log
log_entry = f"""
## Iteration: {TIMESTAMP}
- Profit: {profit:.2f}% | Trades: {trades} | WR: {WR}% | R/R: {RR} | DD: {DRAWDOWN}%
- Changes: {', '.join(changes) if changes else 'None'}
- Reason: {CHANGE_DESC}
"""
with open("$LOG_FILE", "a") as f:
    f.write(log_entry)

print(f"Changes applied: {', '.join(changes) if changes else 'None'}")
PYEOF

    # Commit and push
    git add -A
    git commit -m "iter: auto-tune MeanReversionTrend [skip ci]" || true
    git push origin main || true
    
    # Trigger CI
    gh workflow run backtest_meanreversion.yml --repo "$REPO" --ref main || true
    
    echo "CI triggered. Next check in 2 hours."
else
    echo "Target hit or no changes needed. Standing by."
fi
