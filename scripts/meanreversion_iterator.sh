#!/bin/bash
# MeanReversionTrend Iterator v2 — Research-Driven Optimization
# Analyzes backtest deeply, detects stalls, applies targeted fixes.
# When stalled (>3 iterations no real change), flags for web research.

set -e

WORKSPACE="/home/node/.openclaw/workspace/projects/liquidity-sweep-freqtrade"
REPO="yeboster/liquidity-sweep-freqtrade"
STRATEGY_FILE="$WORKSPACE/strategies/MeanReversionTrend.py"
LOG_FILE="$WORKSPACE/iteration_log.md"
LATEST_SUMMARY="$WORKSPACE/latest_summary.json"
STALL_FILE="$WORKSPACE/.iterator_stall_count"

cd "$WORKSPACE"

# Pull latest
export PATH="/home/node/.local/bin:$PATH"
git pull origin main 2>/dev/null || true

python3 << 'PYEOF'
import re, json, subprocess, sys, datetime, hashlib, os

WORKSPACE = "/home/node/.openclaw/workspace/projects/liquidity-sweep-freqtrade"
STRATEGY_FILE = f"{WORKSPACE}/strategies/MeanReversionTrend.py"
LOG_FILE = f"{WORKSPACE}/iteration_log.md"
LATEST_SUMMARY = f"{WORKSPACE}/latest_summary.json"
STALL_FILE = f"{WORKSPACE}/.iterator_stall_count"
REPO = "yeboster/liquidity-sweep-freqtrade"

timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

# ── 1. Read latest backtest ──────────────────────────────────────────────────
try:
    with open(LATEST_SUMMARY) as f:
        data = json.load(f)
except:
    print("No latest_summary.json found. Waiting for CI to produce results.")
    sys.exit(0)

profit_pct = data.get('profit_pct', 0)
total_trades = data.get('total_trades', 0)
wr = data.get('win_rate', 0)
rr = data.get('rr_ratio', 0)
drawdown = data.get('drawdown_pct', 0)
sqn = data.get('sqn', 0)
exits = data.get('exits', [])
pairs = data.get('pairs', [])

print(f"=== Iteration v2 at {timestamp} ===")
print(f"Profit: {profit_pct:.2f}% | Trades: {total_trades} | WR: {wr:.1f}% | R/R: {rr:.4f} | SQN: {sqn:.4f} | DD: {drawdown:.2f}%")

# ── 2. Deep Exit Analysis ───────────────────────────────────────────────────
print("\n--- Exit Analysis ---")
trailing_wr = 0
trailing_count = 0
trailing_profit = 0
stop_wr = 0
stop_count = 0
stop_profit = 0
time_wr = 0
time_count = 0
time_profit = 0
other_exits = []

for ex in exits:
    name = ex.get('exit', '')
    count = ex.get('trades', 0)
    ex_wr = ex.get('wr', 0)
    ex_profit = ex.get('profit_abs', 0)
    ex_mean = ex.get('profit_mean_pct', 0)
    
    if name in ('TOTAL', ''):
        continue
    
    print(f"  {name}: {count} trades, {ex_wr:.0f}% WR, ${ex_profit:.2f}, mean {ex_mean:.2f}%")
    
    if 'trailing' in name.lower():
        trailing_count += count
        trailing_wr = ex_wr
        trailing_profit += ex_profit
    elif 'stop_loss' in name.lower() or name == 'stop_loss':
        stop_count += count
        stop_wr = ex_wr
        stop_profit += ex_profit
    elif 'time' in name.lower():
        time_count += count
        time_wr = ex_wr
        time_profit += ex_profit
    else:
        other_exits.append(ex)

# Check pair performance for UNKNOWN bug
all_unknown = all(p.get('pair', '') == 'UNKNOWN' for p in pairs if isinstance(p, dict))
if all_unknown and pairs:
    print("  ⚠️ All pairs show UNKNOWN — pair extraction is broken in CI, but analysis continues")

# ── 3. Read Current Strategy Parameters ──────────────────────────────────────
with open(STRATEGY_FILE) as f:
    content = f.read()

def get_param(pattern, default=None):
    m = re.search(pattern, content)
    return m.group(1) if m else default

current_dev = float(get_param(r'entry_dev_threshold\s*=\s*([0-9.]+)', '2.0'))
current_atr = float(get_param(r'atr_compression_ratio\s*=\s*([0-9.]+)', '0.5'))
current_stop = float(get_param(r'stoploss\s*=\s*-([0-9.]+)', '0.025'))
current_time = float(get_param(r'time_exit_profit_floor\s*=\s*([0-9.]+)', '0.01'))
current_trail = float(get_param(r'trailing_stop_positive\s*=\s*([0-9.]+)', '0.008'))
current_trail_offset = float(get_param(r'trailing_stop_positive_offset\s*=\s*([0-9.]+)', '0.01'))
current_rsi_os = int(get_param(r'rsi_oversold\s*=\s*([0-9]+)', '15'))
current_rsi_ob = int(get_param(r'rsi_overbought\s*=\s*([0-9]+)', '85'))
current_vol = float(get_param(r'volume_multiplier\s*=\s*([0-9.]+)', '1.1'))
current_trend = 'use_trend_filter = False' not in content or get_param(r'use_trend_filter\s*=\s*(True|False)', 'True') == 'True'

# ── 4. Compute param hash for stall detection ────────────────────────────────
param_key = f"{current_dev}|{current_atr}|{current_stop}|{current_time}|{current_trail}|{current_trail_offset}|{current_rsi_os}|{current_rsi_ob}|{current_vol}|{current_trend}"
param_hash = hashlib.md5(param_key.encode()).hexdigest()[:8]

# Read previous hash
prev_hash = ""
if os.path.exists(STALL_FILE):
    with open(STALL_FILE) as f:
        content_stall = f.read().strip()
        # Format: hash:count
        parts = content_stall.split(':')
        if len(parts) >= 2:
            prev_hash = parts[0]
            stall_count = int(parts[1])
        else:
            stall_count = 0
else:
    stall_count = 0

if param_hash == prev_hash:
    stall_count += 1
    print(f"\n⚠️ STALL DETECTED (count: {stall_count}) — params unchanged: {param_hash}")
else:
    stall_count = 0
    print(f"\nParams changed: {prev_hash} → {param_hash}")

# Save updated stall state
with open(STALL_FILE, 'w') as f:
    f.write(f"{param_hash}:{stall_count}")

# ── 5. Decision Engine — what to change ─────────────────────────────────────
changes = []
change_desc = ""
need_change = True

# STALLED: need fundamentally different approach
if stall_count >= 3:
    change_desc = f"STALLED x{stall_count} — NEEDS RESEARCH. Current params: dev={current_dev}, atr={current_atr}, stop={current_stop}, trail={current_trail}, trail_offset={current_trail_offset}, rsi_os={current_rsi_os}, rsi_ob={current_rsi_ob}, vol={current_vol}, trend={current_trend}"
    print(f"\n❌ {change_desc}")
    print("ACTION:FLAG_RESEARCH")
    
    # Do a forced parameter reset to something different
    import random
    # Strategy: randomize ONE major parameter to break out of stall
    roll = random.random()
    if roll < 0.25:
        # Widen trailing stop
        new_trail = min(0.03, current_trail + 0.005)
        new_trail_offset = max(0.02, current_trail_offset + 0.005)
        content = re.sub(r'trailing_stop_positive\s*=\s*[0-9.]+', f'trailing_stop_positive = {new_trail:.4f}', content)
        content = re.sub(r'trailing_stop_positive_offset\s*=\s*[0-9.]+', f'trailing_stop_positive_offset = {new_trail_offset:.4f}', content)
        changes.append(f"STALL-BREAK: widen trail {current_trail}→{new_trail}, offset {current_trail_offset}→{new_trail_offset}")
    elif roll < 0.5:
        # Enable trend filter
        content = re.sub(r'use_trend_filter\s*=\s*False', 'use_trend_filter = True', content)
        changes.append(f"STALL-BREAK: enable trend filter")
    elif roll < 0.75:
        # Loosen ATR compression significantly
        new_atr = min(1.0, current_atr + 0.15)
        content = re.sub(r'atr_compression_ratio\s*=\s*[0-9.]+', f'atr_compression_ratio = {new_atr:.2f}', content)
        changes.append(f"STALL-BREAK: widen ATR {current_atr}→{new_atr}")
    else:
        # Tighten stop loss
        new_stop = max(0.01, current_stop - 0.005)
        content = re.sub(r'stoploss\s*=\s*-([0-9.]+)', f'stoploss = -{new_stop:.4f}', content)
        changes.append(f"STALL-BREAK: tighten stop -{current_stop}→-{new_stop}")
elif total_trades == 0:
    change_desc = "ZERO trades — drastically loosen filters"
    new_dev = max(0.8, current_dev - 0.5)
    new_atr = min(1.2, current_atr + 0.3)
    new_vol = max(0.8, current_vol - 0.2)
    new_rsi_os = max(5, current_rsi_os - 10)
    new_rsi_ob = min(95, current_rsi_ob + 5)
    if not current_trend:
        content = re.sub(r'use_trend_filter\s*=\s*False', 'use_trend_filter = True', content)
        changes.append("Enable trend filter")
    content = re.sub(r'entry_dev_threshold\s*=\s*[0-9.]+', f'entry_dev_threshold = {new_dev:.1f}', content)
    content = re.sub(r'atr_compression_ratio\s*=\s*[0-9.]+', f'atr_compression_ratio = {new_atr:.1f}', content)
    content = re.sub(r'volume_multiplier\s*=\s*[0-9.]+', f'volume_multiplier = {new_vol:.1f}', content)
    content = re.sub(r'rsi_oversold\s*=\s*[0-9]+', f'rsi_oversold = {new_rsi_os}', content)
    content = re.sub(r'rsi_overbought\s*=\s*[0-9]+', f'rsi_overbought = {new_rsi_ob}', content)
    changes.append(f"ZERO trades: dev {current_dev}→{new_dev}, atr {current_atr}→{new_atr}, vol {current_vol}→{new_vol}, RSI {current_rsi_os}/{current_rsi_ob}→{new_rsi_os}/{new_rsi_ob}")
elif total_trades < 15:
    change_desc = "Too few trades — need more entry signals"
    new_dev = max(1.0, current_dev - 0.3)
    new_atr = min(1.0, current_atr + 0.15)
    new_vol = max(0.9, current_vol - 0.1)
    content = re.sub(r'entry_dev_threshold\s*=\s*[0-9.]+', f'entry_dev_threshold = {new_dev:.1f}', content)
    content = re.sub(r'atr_compression_ratio\s*=\s*[0-9.]+', f'atr_compression_ratio = {new_atr:.2f}', content)
    content = re.sub(r'volume_multiplier\s*=\s*[0-9.]+', f'volume_multiplier = {new_vol:.1f}', content)
    changes.append(f"Low volume: dev {current_dev}→{new_dev}, atr {current_atr}→{new_atr}, vol {current_vol}→{new_vol}")
elif rr < 0.5 and stop_count > 0:
    change_desc = "R/R broken — trailing stop too tight vs stop loss"
    # Trailing stop is killing winners. Widen trail and tighten hard stop.
    new_trail = min(0.03, current_trail + 0.005)
    new_trail_offset = max(0.01, current_trail_offset + 0.005)
    new_stop = max(0.01, current_stop - 0.003)
    content = re.sub(r'trailing_stop_positive\s*=\s*[0-9.]+', f'trailing_stop_positive = {new_trail:.4f}', content)
    content = re.sub(r'trailing_stop_positive_offset\s*=\s*[0-9.]+', f'trailing_stop_positive_offset = {new_trail_offset:.4f}', content)
    content = re.sub(r'stoploss\s*=\s*-([0-9.]+)', f'stoploss = -{new_stop:.4f}', content)
    changes.append(f"Fix R/R: trail {current_trail}→{new_trail}, offset {current_trail_offset}→{new_trail_offset}, stop -{current_stop}→-{new_stop}")
elif wr < 40:
    change_desc = "Win rate too low — tighten entry quality"
    new_dev = min(2.5, current_dev + 0.3)
    if not current_trend:
        content = re.sub(r'use_trend_filter\s*=\s*False', 'use_trend_filter = True', content)
        changes.append("Enable trend filter for quality")
    content = re.sub(r'entry_dev_threshold\s*=\s*[0-9.]+', f'entry_dev_threshold = {new_dev:.1f}', content)
    changes.append(f"Quality: dev {current_dev}→{new_dev}")
elif trailing_count > 0 and trailing_wr > 60 and trailing_profit > 0:
    change_desc = "Trailing exits work but too tight — let winners run"
    new_trail = min(0.03, current_trail + 0.005)
    new_offset = min(0.03, current_trail_offset + 0.005)
    content = re.sub(r'trailing_stop_positive\s*=\s*[0-9.]+', f'trailing_stop_positive = {new_trail:.4f}', content)
    content = re.sub(r'trailing_stop_positive_offset\s*=\s*[0-9.]+', f'trailing_stop_positive_offset = {new_offset:.4f}', content)
    changes.append(f"Let winners run: trail {current_trail}→{new_trail}, offset {current_trail_offset}→{new_offset}")
elif profit_pct > 30:
    change_desc = "Close to target — fine-tune exits"
    new_time = min(0.03, current_time + 0.005)
    content = re.sub(r'time_exit_profit_floor\s*=\s*[0-9.]+', f'time_exit_profit_floor = {new_time:.4f}', content)
    changes.append(f"Fine-tune: time_floor {current_time}→{new_time}")
elif profit_pct < 0:
    change_desc = "Negative profit — R/R problem or bad entries"
    # Check if trailing exits have positive WR but trail is too tight
    if trailing_wr > 0 and trailing_count > 0:
        new_trail = min(0.03, current_trail + 0.005)
        new_offset = max(0.015, current_trail_offset + 0.003)
        content = re.sub(r'trailing_stop_positive\s*=\s*[0-9.]+', f'trailing_stop_positive = {new_trail:.4f}', content)
        content = re.sub(r'trailing_stop_positive_offset\s*=\s*[0-9.]+', f'trailing_stop_positive_offset = {new_offset:.4f}', content)
        changes.append(f"Widen trail to fix R/R: trail {current_trail}→{new_trail}, offset {current_trail_offset}→{new_offset}")
    
    # If lots of stop losses, tighten stop
    if stop_count > trailing_count:
        new_stop = max(0.01, current_stop - 0.003)
        content = re.sub(r'stoploss\s*=\s*-([0-9.]+)', f'stoploss = -{new_stop:.4f}', content)
        changes.append(f"Too many stop-outs: tighten stop -{current_stop}→-{new_stop}")
else:
    # Default: loosen entry filters slightly
    new_dev = max(1.0, current_dev - 0.1)
    new_atr = min(0.9, current_atr + 0.05)
    content = re.sub(r'entry_dev_threshold\s*=\s*[0-9.]+', f'entry_dev_threshold = {new_dev:.1f}', content)
    content = re.sub(r'atr_compression_ratio\s*=\s*[0-9.]+', f'atr_compression_ratio = {new_atr:.2f}', content)
    change_desc = "General loosen to increase signals"
    changes.append(f"Loosen: dev {current_dev}→{new_dev}, atr {current_atr}→{new_atr}")

# ── Bump version ─────────────────────────────────────────────────────────────
version_match = re.search(r'STRATEGY_VERSION\s*=\s*"([0-9.]+)"', content)
if version_match:
    old_ver = version_match.group(1)
    parts = old_ver.split('.')
    parts[-1] = str(int(parts[-1]) + 1)
    new_ver = '.'.join(parts)
    content = re.sub(r'STRATEGY_VERSION\s*=\s*"[0-9.]+"', f'STRATEGY_VERSION = "{new_ver}"', content)
    changes.append(f"v{old_ver}→{new_ver}")

# ── Write strategy file ──────────────────────────────────────────────────────
with open(STRATEGY_FILE, "w") as f:
    f.write(content)

# ── Log ──────────────────────────────────────────────────────────────────────
stall_tag = f" [STALLED x{stall_count}]" if stall_count >= 3 else ""
log_entry = f"""
## Iteration v2: {timestamp}{stall_tag}
- Profit: {profit_pct:.2f}% | Trades: {total_trades} | WR: {wr:.1f}% | R/R: {rr:.4f} | SQN: {sqn:.4f} | DD: {drawdown:.2f}%
- Exit breakdown: trailing={trailing_count}({trailing_wr:.0f}%WR, ${trailing_profit:.2f}), stop={stop_count}({stop_wr:.0f}%WR, ${stop_profit:.2f}), time={time_count}({time_wr:.0f}%WR, ${time_profit:.2f})
- Changes: {', '.join(changes) if changes else 'None'}
- Reason: {change_desc}
"""
with open(LOG_FILE, "a") as f:
    f.write(log_entry)

print(f"\nChanges: {', '.join(changes) if changes else 'None'}")
print(f"Reason: {change_desc}")

# ── Commit and trigger ───────────────────────────────────────────────────────
subprocess.run(["git", "add", "-A"], cwd=WORKSPACE, capture_output=True)
commit_result = subprocess.run(
    ["git", "commit", "-m", f"iter: auto-tune MeanReversionTrend v{new_ver if 'new_ver' in dir() else '?'} [skip ci]"],
    cwd=WORKSPACE, capture_output=True, text=True
)
subprocess.run(["git", "push", "origin", "main"], cwd=WORKSPACE, capture_output=True)

result = subprocess.run(
    ["gh", "workflow", "run", "backtest_meanreversion.yml", "--repo", REPO, "--ref", "main"],
    capture_output=True, text=True, cwd=WORKSPACE
)
print(f"CI triggered.\nstdout: {result.stdout}\nstderr: {result.stderr}")

# ── Output research flag for cron agent ──────────────────────────────────────
if stall_count >= 3:
    print("\n===== RESEARCH_NEEDED =====")
    print(f"Strategy MeanReversionTrend is stuck at stall count {stall_count}")
    print(f"Current state: profit={profit_pct}%, trades={total_trades}, WR={wr}%, R/R={rr}")
    print(f"Current params: dev={current_dev}, atr={current_atr}, stop={current_stop}, trail={current_trail}, offset={current_trail_offset}")
    print("Please research: 'mean reversion crypto trading strategy optimization stop loss trailing stop ratio'")
    print("===== END_RESEARCH =====")
PYEOF
