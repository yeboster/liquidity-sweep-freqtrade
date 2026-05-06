#!/bin/bash
# MeanReversionTrend Iterator — runs every 2 hours
# Goal: iterate strategy parameters until 40% annual profit target is hit

set -e

WORKSPACE="/home/node/.openclaw/workspace/projects/liquidity-sweep-freqtrade"
REPO="yeboster/liquidity-sweep-freqtrade"
STRATEGY_FILE="$WORKSPACE/strategies/MeanReversionTrend.py"
LOG_FILE="$WORKSPACE/iteration_log.md"
LATEST_SUMMARY="$WORKSPACE/latest_summary.json"

cd "$WORKSPACE"

# Pull latest
export PATH="/home/node/.local/bin:$PATH"
git pull origin main 2>/dev/null || true

python3 << 'PYEOF'
import re, json, subprocess, sys, datetime

WORKSPACE = "/home/node/.openclaw/workspace/projects/liquidity-sweep-freqtrade"
STRATEGY_FILE = f"{WORKSPACE}/strategies/MeanReversionTrend.py"
LOG_FILE = f"{WORKSPACE}/iteration_log.md"
LATEST_SUMMARY = f"{WORKSPACE}/latest_summary.json"
REPO = "yeboster/liquidity-sweep-freqtrade"

# Read latest backtest results
try:
    with open(LATEST_SUMMARY) as f:
        data = json.load(f)
    profit_pct = data.get('profit_pct', 0)
    total_trades = data.get('total_trades', 0)
    wr = data.get('win_rate', 0)
    rr = data.get('rr_ratio', 0)
    drawdown = data.get('drawdown_pct', 0)
except:
    profit_pct = total_trades = wr = rr = drawdown = 0

timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
print(f"=== Iteration check at {timestamp} ===")
print(f"Profit: {profit_pct}% | Trades: {total_trades} | WR: {wr}% | R/R: {rr} | DD: {drawdown}%")

# Decision logic
need_change = False
change_desc = ""
changes = []

if total_trades == 0:
    need_change = True
    change_desc = "ZERO trades — remove RSI confirmation, lower dev threshold to 1.0, disable trend filter"
elif profit_pct < 10:
    need_change = True
    change_desc = "profit < 10% — loosen filters (lower dev threshold, widen ATR compression)"
elif profit_pct < 20:
    need_change = True
    change_desc = "profit < 20% — moderate loosen (lower dev threshold, add more pairs)"
elif profit_pct < 30:
    need_change = True
    change_desc = "profit < 30% — fine-tune exits (raise time_exit_profit_floor, tighten stop)"
elif profit_pct < 40:
    need_change = True
    change_desc = "profit < 40% — add pairs or tighten entry filters for quality"
else:
    change_desc = "profit >= 40% — target hit, no changes"

print(f"Decision: {'NEED CHANGE' if need_change else 'STANDING BY'} — {change_desc}")

if not need_change:
    print("Target hit or no changes needed. Standing by.")
    sys.exit(0)

print(f"Applying: {change_desc}")

with open(STRATEGY_FILE) as f:
    content = f.read()

# Read current values
dev_match = re.search(r'entry_dev_threshold\s*=\s*([0-9.]+)', content)
current_dev = float(dev_match.group(1)) if dev_match else 2.0

atr_match = re.search(r'atr_compression_ratio\s*=\s*([0-9.]+)', content)
current_atr = float(atr_match.group(1)) if atr_match else 0.5

stop_match = re.search(r'stoploss\s*=\s*-([0-9.]+)', content)
current_stop = float(stop_match.group(1)) if stop_match else 0.025

time_match = re.search(r'time_exit_profit_floor\s*=\s*([0-9.]+)', content)
current_time = float(time_match.group(1)) if time_match else 0.01

if total_trades == 0:
    new_dev = max(1.0, current_dev - 0.5)
    new_atr = min(0.9, current_atr + 0.2)
    content = re.sub(r'use_trend_filter\s*=\s*True', 'use_trend_filter = False', content)
    content = re.sub(r'rsi_oversold\s*=\s*[0-9.]+', 'rsi_oversold = 20', content)
    content = re.sub(r'rsi_overbought\s*=\s*[0-9.]+', 'rsi_overbought = 80', content)
    changes.append(f"ZERO trades fix: dev {current_dev}→{new_dev}, atr {current_atr}→{new_atr}, trend filter OFF, RSI relaxed")
elif profit_pct < 10:
    new_dev = max(1.2, current_dev - 0.3)
    new_atr = min(0.8, current_atr + 0.2)
    changes.append(f"Loosen: dev {current_dev}→{new_dev}, atr {current_atr}→{new_atr}")
elif profit_pct < 20:
    new_dev = max(1.4, current_dev - 0.2)
    new_atr = min(0.7, current_atr + 0.1)
    changes.append(f"Moderate loosen: dev {current_dev}→{new_dev}, atr {current_atr}→{new_atr}")
elif profit_pct < 30:
    new_time = min(0.02, current_time + 0.005)
    new_stop = max(0.02, current_stop - 0.005)
    content = re.sub(r'time_exit_profit_floor\s*=\s*[0-9.]+', f'time_exit_profit_floor = {new_time:.4f}', content)
    content = re.sub(r'stoploss\s*=\s*-([0-9.]+)', f'stoploss = -{new_stop:.4f}', content)
    changes.append(f"Tune exits: time_floor {current_time}→{new_time}, stop -{current_stop}→-{new_stop}")
elif profit_pct < 40:
    new_dev = min(2.5, current_dev + 0.1)
    changes.append(f"Tighten quality: dev {current_dev}→{new_dev}")

if 'new_dev' in dir():
    content = re.sub(r'entry_dev_threshold\s*=\s*[0-9.]+', f'entry_dev_threshold = {new_dev:.1f}', content)
if 'new_atr' in dir():
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

with open(STRATEGY_FILE, "w") as f:
    f.write(content)

# Log
log_entry = f"""
## Iteration: {timestamp}
- Profit: {profit_pct:.2f}% | Trades: {total_trades} | WR: {wr}% | R/R: {rr} | DD: {drawdown}%
- Changes: {', '.join(changes) if changes else 'None'}
- Reason: {change_desc}
"""
with open(LOG_FILE, "a") as f:
    f.write(log_entry)

print(f"Changes applied: {', '.join(changes) if changes else 'None'}")

# Commit and push
subprocess.run(["git", "add", "-A"], cwd=WORKSPACE)
subprocess.run(["git", "commit", "-m", "iter: auto-tune MeanReversionTrend [skip ci]"], cwd=WORKSPACE)
subprocess.run(["git", "push", "origin", "main"], cwd=WORKSPACE)

# Trigger CI
result = subprocess.run(
    ["gh", "workflow", "run", "backtest_meanreversion.yml", "--repo", REPO, "--ref", "main"],
    capture_output=True, text=True, cwd=WORKSPACE
)
print(f"CI triggered.\nstdout: {result.stdout}\nstderr: {result.stderr}")
PYEOF