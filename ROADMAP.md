# Liquidity Sweep Strategy - Research & Roadmap

> Created: 2026-03-17
> Focus: Debugging & Profit Optimization

---

## Executive Summary

The strategy has been iterating for 40+ versions with persistent issues:
- **Win Rate:** 19-24% (target: 40-55%)
- **Core Problem:** TSL hits 78% of trades; R:R math broken

---

## Root Cause Analysis

### 1. Trailing Stop Loss (TSL) Problem
**Symptom:** 78% of trades exit via TSL at avg -1.61%
**Root Cause:** 
- ATR-based SL (2.0x) still too tight for BTC volatility
- TSL activates too early (+1.5%), triggers before reversals
- Entry quality issue: entries fire at wrong price levels

### 2. Win Rate vs R:R Mismatch
**Current Math:**
- Avg win: +0.57% (ROI exits)
- Avg loss: -1.61% (TSL)
- Breakeven WR needed: ~74%

**ICT Theory Says:** WR should be 40-50% with 1:2 R:R

### 3. Entry Quality Issues (from v0.14.0 notes)
- Unmitigated imbalances beyond stop loss
- Entries without HTF trend alignment (fixed in v0.27.0)
- No session filtering (NY/London vs Asian)

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

### Phase 0: Immediate Fixes (This Week)

| Task | Description | Expected Impact |
|------|-------------|-----------------|
| **0.1** | Disable TSL entirely, use fixed SL only | Reduce TSL exits |
| **0.2** | Widen SL to 3x ATR | Fewer premature stops |
| **0.3** | Add 1.5% fixed profit target | Capture small wins |
| **0.4** | Add session filter (NY/London only) | Quality over quantity |

**Version:** v0.42.0

### Phase 1: Risk Management (Week 1-2)

| Task | Description | Expected Impact |
|------|-------------|-----------------|
| **1.1** | Max drawdown exit (15%) | Capital protection |
| **1.2** | Position sizing: 1-2% risk/trade | Consistent risk |
| **1.3** | Partial profit taking: 50% at 1.5R | Breakeven + rides |
| **1.4** | Remove trailing stop completely | Simplifies exits |

**Expected:** WR ~30%, smaller losses, math starts working

### Phase 2: Entry Quality (Week 3-4)

| Task | Description | Expected Impact |
|------|-------------|-----------------|
| **2.1** | Session filter: NY (13:30-16:00 UTC) | Higher volatility |
| **2.2** | Liquidity pool proximity | Enter near major liquidity |
| **2.3** | Double confirmation: sweep + BOS | Quality gate |
| **2.4** | Weekend filter (no Sat/Sun) | Avoid low volume |

**Expected:** WR 35-45%, ~100 trades/year

### Phase 3: Profit Optimization (Week 5-6)

| Task | Description | Expected Impact |
|------|-------------|-----------------|
| **3.1** | Scale-out: 33%/33%/33% at 1%/2.5%/5% | Capture moves |
| **3.2** | HTF trend filter (1H/4H) | Never fight trend |
| **3.3** | Market structure confirmed (BOS) | Entry timing |

**Expected:** Avg profit 1.5-3%, WR 40-50%

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

## Version Plan

| Version | Focus | Key Changes |
|---------|-------|-------------|
| v0.42.0 | Risk Management | Disable TSL, widen SL, add profit target |
| v0.43.0 | Session Filter | NY/London only |
| v0.44.0 | Entry Quality | Double confirmation, weekend filter |
| v0.45.0 | Profit Taking | Scale-out strategy |

---

## Action Items

1. **Run v0.42.0** with: TSL disabled, SL=3x ATR, 1.5% profit target
2. **Analyze** exit reasons in backtest results
3. **Iterate** based on data, not assumptions

---

*Last Updated: 2026-03-17*
