# Liquidity Sweep Strategy - Research & Roadmap

> Updated: 2026-03-18
> Version: v0.42.0 (just fixed)

---

## 🚨 CRITICAL FINDING (2026-03-18)

**Root Cause Found:** Trailing stop was completely broken!
- `trailing_stop_positive = 0.277` → **27.7%** trailing (should be 0.5%)
- `trailing_stop_positive_offset = 0.295` → **29.5%** activation (should be 1.5%)

This explains why 46% of trades exited via trailing_stop_loss at -1.61% avg loss — the trailing stop was activating WAY too late and trailing WAY too far.

**Fix Applied (v0.42.0):**
- `trailing_stop_positive = 0.005` (0.5%)
- `trailing_stop_positive_offset = 0.015` (1.5%)

---

## Executive Summary

- **Win Rate:** 19-24% (target: 40-55%)
- **Core Problem:** TSL formula bug (FIXED in v0.42.0)
- **Next:** Run backtest to verify fix

---

## Root Cause Analysis (Updated)

### 1. Trailing Stop Loss Bug ✅ FIXED
- **Symptom:** 46% of trades exit via TSL at avg -1.61%
- **Root Cause Found:** Wrong values in config (27.7% instead of 0.5%)
- **Fix:** v0.42.0 corrects trailing_stop_positive and offset

### 2. Win Rate vs R:R Mismatch
- Avg win: +0.57% (ROI exits)
- Avg loss: -1.61% (TSL)
- Breakeven WR needed: ~74%

### 3. Entry Quality Issues
- No session filtering (NY/London vs Asian)
- Too many trades (600-800/year, target: 50-200)

---

## Debugging Framework

### Quick Debug Commands

```bash
# 1. Run backtest with trade logging
freqtrade backtesting -c config.json -s LiquiditySweep --export-filename trades.csv

# 2. Analyze exit reasons
freqtrade analysis -s LiquiditySweep --breakdown

# 3. Enable debug logging
freqtrade backtesting -c config.json -s LiquiditySweep -l DEBUG

# 4. Inspect specific trade
# Look at trades.csv for entry_reason, exit_reason, profit_abs
```

### Key Metrics to Track

| Metric | Target | Current | Issue |
|--------|--------|---------|-------|
| Win Rate | 40-55% | 19-24% | ❌ |
| Avg Win | 1-3% | 0.57% | ❌ |
| Avg Loss | -1.5% | -1.61% | ✅ |
| TSL Exit % | <30% | 78% | ❌ |
| ROI Exit % | >50% | ~20% | ❌ |
| Trades/Year | 50-200 | ~600-800 | ❌ Too many |

---

## Research Findings

### ICT Best Practices (from web research)

1. **Silver Bullet Setup** (70-80% WR claimed)
   - SSL/BSL sweep + immediate FVG + MSS/ChoCH
   - Entry at FVG boundary, stop at sweep extreme
   - Time window: NY/London sessions only

2. **Session Filtering**
   - NY (13:30-16:00 UTC): Highest volatility
   - London (08:00-11:00 UTC): Second highest
   - Asian: Low volume, avoid

3. **Stop Loss Placement**
   - Place **beyond** sweep high/low (buffer pips)
   - Not directly on the level (stop hunt protection)

4. **Partial Profit Taking**
   - 50% at 1R (breakeven protected)
   - Trail remainder to liquidity pool

5. **Max 2-3 trades/day** (prevent overtrading)

---

## Updated Roadmap

### Phase 0: Critical Bug Fix (DONE ✅)

| Task | Status | Result |
|------|--------|--------|
| **0.1** | ✅ DONE | Fixed trailing stop formula (v0.42.0) |
| **0.2** | ⏳ Next | Widen SL to 3x ATR |
| **0.3** | ⏳ Next | Add session filter (NY/London only) |

**Version:** v0.42.0 - Trailing stop fix

### Phase 1: Risk Management

| Task | Description | Expected Impact |
|------|-------------|-----------------|
| **1.1** | Widen SL to 3x ATR | Fewer premature stops |
| **1.2** | Position sizing: 1-2% risk/trade | Consistent risk |
| **1.3** | Partial profit taking: 50% at 1.5R | Breakeven + rides |
| **1.4** | Add session filter (NY/London) | Quality over quantity |

### Phase 2: Entry Quality

| Task | Description | Expected Impact |
|------|-------------|-----------------|
| **2.1** | Session filter: NY (13:30-16:00 UTC) | Higher volatility |
| **2.2** | Double confirmation: sweep + BOS | Quality gate |
| **2.3** | Weekend filter (no Sat/Sun) | Avoid low volume |

---

## Version History

| Version | Focus | Key Changes |
|---------|-------|-------------|
| v0.42.0 | ✅ DONE | Fixed trailing stop formula (0.277→0.005) |
| v0.43.0 | ⏳ Next | Widen SL to 3x ATR |
| v0.44.0 | ⏳ Next | Session filter NY/London |
| v0.45.0 | ⏳ Next | Entry quality improvements |

### Phase 4: Hyperopt & Fine-Tuning (Ongoing)

- Hyperopt OTE zone (30-70%)
- Per-pair parameter optimization
- Rolling 2-year backtest window

---

## Debugging Checklist

When backtest fails:

- [ ] **Check trade volume:** 0 trades = logic bug, too few = filters too strict
- [ ] **Check exit reasons:** TSL > 50% = SL problem, ROI = entry problem
- [ ] **Check profit distribution:** Many small wins + few big losses = typical
- [ ] **Check pair performance:** Some pairs may need different params
- [ ] **Run local backtest first:** Before CI, catch errors faster

---

## Action Items

1. **Run v0.42.0** backtest to verify trailing stop fix
2. **Analyze** exit reasons - expect fewer trailing_stop_loss exits
3. **Next:** Widen SL to 3x ATR (v0.43.0)

---

*Last Updated: 2026-03-18*
