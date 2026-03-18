# Liquidity Sweep Strategy - Research & Roadmap

> Updated: 2026-03-18
> Version: v0.46.0 tested

---

## 🚨 CRITICAL FINDING (2026-03-18)

**Root Cause Found:** Trailing stop was completely broken!
- `trailing_stop_positive = 0.277` → **27.7%** trailing (should be 0.5%)
- `trailing_stop_positive_offset = 0.295` → **29.5%** activation (should be 1.5%)

This explains why 46% of trades exited via trailing_stop_loss at -1.61% avg loss — the trailing stop was activating WAY too late and trailing WAY too far.

---

## v0.46.0 Test Results (2026-03-18)

**Fix Applied:** Early profit exit at +0.8% (after 45min) + wider stoploss floor -8%

| Metric | v0.45.0 | v0.46.0 | Change |
|--------|---------|---------|--------|
| Total Trades | 63 | 63 | — |
| Win Rate | 20.6% | 22.2% | +1.6pp |
| Profit % | -13.04% | -12.94% | +0.1pp |
| TSL exits | 30 (47.6%, -1.27%) | 29 (46.0%, -1.35%) | Slightly worse loss |
| Early profit | 0 | 6 (9.5%, +0.96%) | NEW: working but offset by TSL |
| ROI exits | 9 (14.3%, +0.63%) | 6 (9.5%, +0.46%) | Fewer |

**Analysis:** Early profit exit fires on 6 trades (+0.96% avg) but TSL losses increased slightly (-1.27% → -1.35%). Widen floor to -8% didn't help. Core issue: 9 winning trades averaging +0.79% vs 54 losing trades at -1.35% is mathematically unsustainable without major entry quality overhaul.

**Verdict:** v0.46.0 marginally better (+0.1pp profit). Need fundamentally different approach — entry quality gate or market regime filter.

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
| **0.2** | ✅ DONE | Widen SL to 3x ATR (v0.43.0) |
| **0.3** | ✅ DONE | Add session filter (v0.44.0), disabled (v0.45.0) — too aggressive |

### Phase 1: Risk Management (PARTIAL ✅)

| Task | Status | Result |
|------|--------|--------|
| **1.1** | ✅ DONE | Widen SL to 3x ATR (v0.43.0) |
| **1.2** | ❌ SKIP | Position sizing (freqtrade handles this) |
| **1.3** | ⚠️ TESTED | Partial profit taking at +0.8% (v0.46.0) — marginal gain |
| **1.4** | ✅ DONE | Session filter tested, disabled (too aggressive) |

### Phase 2: Entry Quality (STALEMATE)

| Task | Status | Result |
|------|--------|--------|
| **2.1** | ❌ FAILED | Session filter cut too many trades (19 vs 63, WR 10.5%) |
| **2.2** | ⏳ Next | Double confirmation: sweep + BOS |
| **2.3** | ⏳ Next | Weekend filter (no Sat/Sun) |

### Core Problem (UNSOLVED)

**Win rate too low + avg win too small = mathematically unsalvageable with exits alone**

- Win rate: 20-22% (need 67%+ to break even with current R:R)
- Avg win: +0.63% | Avg loss: -1.35% (ratio 1:2.1)
- TSL exits 46% of trades at avg -1.35% loss
- ROI exits only 9.5% of trades
- Even with TSL fix, exit-based optimization cannot overcome poor entries

**Next recommended action:** Add OTE (Originating Trend Engine) zone filter — only take sweeps in the 38-78% retracement zone. This is the core ICT Silver Bullet concept.

---

## Version History

| Version | Focus | Key Changes |
|---------|-------|-------------|
| v0.46.0 | ⚠️ MARGINAL | Early profit exit + wider floor (-8%) — marginal improvement (+0.1pp). TSL still dominant. |
| v0.45.0 | ✅ DONE | Disable session filter (was too aggressive) |
| v0.44.0 | ✅ DONE | Session filter NY/London (v0.44.0), disabled in v0.45.0 |
| v0.43.0 | ✅ DONE | Widen ATR stoploss to 3x |
| v0.42.0 | ✅ DONE | Fixed trailing stop formula (0.277→0.005) |

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
