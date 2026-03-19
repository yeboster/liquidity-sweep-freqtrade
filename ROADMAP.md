# Liquidity Sweep Strategy - Research & Roadmap

> Updated: 2026-03-19
> Version: v0.50.1 tested

---

## 🚨 CRITICAL FINDING (2026-03-18)

**Root Cause Found:** Trailing stop was completely broken!
- `trailing_stop_positive = 0.277` → **27.7%** trailing (should be 0.5%)
- `trailing_stop_positive_offset = 0.295` → **29.5%** activation (should be 1.5%)

This explains why 46% of trades exited via trailing_stop_loss at -1.61% avg loss — the trailing stop was activating WAY too late and trailing WAY too far.

---

## v0.47.0 Test Results (2026-03-18)

**Fix Applied:** Double confirmation — replace ChoCh with BOS for entry validation (roadmap 2.2).
- ChoCh can fire on minor structure breaks
- BOS confirms true market structure breakdown — more robust for ICT Silver Bullet entries

| Metric | v0.46.0 | v0.47.0 | Change |
|--------|---------|---------|--------|
| Total Trades | 63 | 52 | -17% |
| Win Rate | 22.2% | **36.5%** | **+14.3pp** 🚀 |
| Profit % | -12.94% | **+0.05%** | **+12.99pp** ✅ |
| TSL exits | 29 (46%, -1.35%) | 3 (5.8%, -1.97%) | Huge reduction |
| Early profit | 6 (9.5%, +0.98%) | 10 (19.2%, +0.98%) | More wins captured |
| ROI exits | 6 (9.5%, +0.46%) | 8 (15.4%, +0.05%) | Slight improvement |
| exit_signal | — | 21 (40.4%, -0.52%) | New dominant exit |
| Drawdown | — | 1.64% | Much improved |

**Analysis:** BOS confirmation dramatically improved win rate (22% → 36.5%) and turned profit positive (+0.05%). TSL exits reduced from 46% to 5.8%. New dominant exit is `exit_signal` (40.4%) at -0.52% avg — this is the HTF trend reversal exit, working as intended.

**Remaining Issues:**
- exit_signal exits (21 trades, -0.52% avg) are cutting winners short via HTF trend reversal
- TSL still problematic on remaining 3 exits (-1.97% avg)
- Profit is barely positive (0.05%) — needs further refinement

**Verdict:** Major breakthrough in win rate. Entry quality improvement via BOS > ChoCh confirmed.

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

### Phase 2: Entry Quality (STALEMATE → IMPROVED → 🎉 BREAKTHROUGH)

| Task | Status | Result |
|------|--------|--------|
| **2.1** | ❌ FAILED | Session filter cut too many trades (19 vs 63, WR 10.5%) |
| **2.2** | ✅ DONE | Double confirmation: sweep + BOS (v0.47.0) — **MAJOR IMPROVEMENT** |
| **2.3** | ✅ DONE | Weekend filter (v0.49.0) — **44.4% WR, +1.87% profit** |

## v0.51.0 Test Results (2026-03-19)

**Fix Applied:** Remove HTF trend exits from `populate_exit_trend` — replaced ChoCH-only exits.
Problem (roadmap Phase 4): exit_signal exits (33.3% of trades, avg -1.71%) were cutting winners short via 1H HTF trend reversal. ChoCH on entry TF (15m) is more responsive and appropriate for local exit decisions.

| Metric | v0.50.1 | v0.51.0 | Change |
|--------|---------|---------|--------|
| Total Trades | 36 | 36 | — |
| Win Rate | 44.4% | 44.4% | — |
| Profit % | 1.87% | **2.02%** | **+0.15pp** ✅ |
| Profit Factor | 1.55 | **1.62** | +0.07 |
| Avg Hold | 2h55m | 3h05m | +10min longer |
| TSL exits | 3 (8.3%, +6.52%) | 3 (8.3%, +1.97%) | TSL still capturing winners |
| exit_signal | 12 (33.3%, -1.71%) | **11 (30.6%, -0.51%)** | **+1.20pp improvement** 🎉 |
| Early profit | 9 (25%, +3.30%) | 9 (25%, +3.30%) | — |
| ROI exits | — | 5 (13.9%, +0.05%) | More ROI exits (trade running longer) |
| Drawdown | 1.58% | 1.58% | Same |

**Analysis:** Removing HTF trend exits improved profit from 1.87% → 2.02% (+0.15pp) with same trade count. The exit_signal avg loss dropped from -1.71% to -0.51% — a massive 1.20pp improvement on those exits. Winners are now running longer (3h05m vs 2h55m). Profit factor improved from 1.55 to 1.62.

**Key Observation:** ChoCH-only exits let winners run. The 1H HTF trend was too slow/aggressive for 15m entry timeframe exits. The strategy now holds trades an extra 10 minutes on average, capturing more of the move.

**Verdict:** HTF trend exit removal = incremental improvement. ChoCH-only exits confirmed. Next target: still reduce remaining exit_signal exits (now 30.6%, avg -0.51%) — could try tightening ChoCH threshold or adding confirmation before exit_signal fires.

---

## v0.50.1 Test Results (2026-03-19)

**Fix Applied:** Tighten OTE zone to 30-70% mandatory + make require_ote non-optimizable.
Problem (roadmap Phase 4): OTE zone was 30-85%, hyperopt could widen to 50-85%. Extreme Fibonacci zones (78.6%, 88.6%) dilute entry quality. Also require_ote optimize=False prevents hyperopt disabling OTE (v0.38.0 disaster).

| Metric | v0.49.0 | v0.50.1 | Change |
|--------|---------|---------|--------|
| Total Trades | 36 | 36 | — |
| Win Rate | 44.4% | 44.4% | — |
| Profit % | 1.87% | 1.87% | — |
| Profit Factor | 1.55 | 1.55 | — |
| Avg Hold | 2h55m | 2h55m | — |
| TSL exits | — | 3 (8.3%, +6.52%) | Good — TSL capturing winners |
| Early profit | — | 9 (25%, +3.30%) | Strong |
| exit_signal | — | 12 (33.3%, -1.71%) | Still dominant (HTF reversal cuts winners) |

**Analysis:** No improvement over v0.49.0 — identical 36 trades, 44.4% WR, 1.87% profit. Tightening OTE bounds within 30-70% had no measurable effect since v0.49.0 was already using a similar range. The OTE filter is now "locked in" which provides stability but no further gains.

**Key Observation:** exit_signal exits (33.3%, avg -1.71%) are cutting winners short via HTF trend reversal. This is the next major target.

**Verdict:** OTE lock-in confirmed. Next focus: reduce exit_signal exits (HTF reversal exit too aggressive). Consider widening or disabling the HTF trend exit signal.

---

## v0.49.0 Test Results (2026-03-19)

**Fix Applied:** Weekend filter — skip Saturday (dayofweek=5) and Sunday (dayofweek=6).

| Metric | v0.47.0 | v0.49.0 | Change |
|--------|---------|---------|--------|
| Total Trades | 52 | **36** | -31% |
| Win Rate | 36.5% | **44.4%** | **+7.9pp** 🎉 |
| Profit % | 0.05% | **1.87%** | **+1.82pp** ✅ |
| Drawdown | 1.64% | 1.58% | -0.06pp |
| Profit Factor | — | **1.55** | Strong |
| Avg Duration | — | 2h55m | |

**Analysis:** Weekend filter dramatically improved quality over quantity:
- 31% fewer trades but 44% win rate vs 36.5%
- Profit nearly quadrupled (1.87% vs 0.05%)
- Filter removes low-liquidity weekend chop — core ICT principle confirmed
- Profit factor 1.55 = solid edge emerging

**Verdict:** Weekend filter is a definitive keeper. Next: OTE zone filter.

---

### Core Problem (IMPROVING)

**Win rate climbing:** 22% → 36.5% → 44.4%
**Profit turning positive:** -12.9% → 0.05% → 1.87%
**Next target:** 50%+ WR, 3%+ profit via OTE zone filter.

---

## Version History

| Version | Focus | Key Changes |
|---------|-------|-------------|
| v0.51.0 | 🎉 IMPROVED | Remove HTF trend exits → profit 1.87%→2.02%, exit_signal avg -1.71%→-0.51% |
| v0.50.1 | ✅ DONE | Tighten OTE to 30-70% mandatory (no change — v0.49.0 already near-optimal) |
| v0.49.0 | 🎉 BREAKTHROUGH | Weekend filter — WR 36.5%→44.4%, profit 0.05%→1.87%, profit factor 1.55 |
| v0.47.0 | 🚀 BREAKTHROUGH | BOS double-confirmation — WR 22%→36.5%, profit -12.9%→+0.05%, drawdown 1.64% |
| v0.46.0 | ⚠️ MARGINAL | Early profit exit + wider floor (-8%) — marginal improvement (+0.1pp). TSL still dominant. |
| v0.45.0 | ✅ DONE | Disable session filter (was too aggressive) |
| v0.44.0 | ✅ DONE | Session filter NY/London (v0.44.0), disabled in v0.45.0 |
| v0.43.0 | ✅ DONE | Widen ATR stoploss to 3x |
| v0.42.0 | ✅ DONE | Fixed trailing stop formula (0.277→0.005) |

### Phase 4: Hyperopt & Fine-Tuning (STALEMATE → NEXT TARGET: exit_signal exits)

- ✅ OTE zone locked to 30-70% mandatory (v0.50.1) — no measurable improvement
- ✅ Remove HTF trend exits (v0.51.0) — exit_signal avg loss -1.71% → -0.51% 🎉
- ⏳ Further reduce exit_signal exits (30.6%, avg -0.51%) — tighten ChoCH or add confirmation
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
