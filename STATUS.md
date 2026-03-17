# Liquidity Sweep Strategy - STATUS.md

## Current State (v0.41.0 - FIXED)

| Metric | Value | Status |
|--------|-------|--------|
| Version | 0.41.0 | 🔧 Fixed |
| Status | Backtest error fix deployed | ✅ |
| Issue | CategoricalParameter with single option | ✅ Resolved |

**Latest Fix (2026-03-17):**
- Fixed `require_ote = CategoricalParameter([True], ...)` → `[True, False]`
- Removed duplicate `require_ob` dummy line
- Error: `CategoricalParameter space must be [a, b, ...] (at least two parameters)`

---

## Target Goals

| Goal | Target | Rationale |
|------|--------|-----------|
| **Win Rate** | 40-55% | Realistic for ICT-style |
| **Profit/Trade** | 1-5% | Conservative targets |
| **Trade Frequency** | 50-200/year | ~1-4 per day |
| **Max Drawdown** | <15% | Risk management |
| **Risk:Reward** | Minimum 1:1.5 | Math must work |

---

## Roadmap (Phased Approach)

### Phase 1: Risk Management Foundation (Week 1-2)
**Goal:** Fix the losing math, stabilize drawdown

- [ ] **1.1** Add max drawdown exit - stop trading if DD > 15%
- [ ] **1.2** Implement position sizing: risk 1-2% per trade max
- [ ] **1.3** Add partial profit taking: exit 50% at 1.5R, let 50% ride
- [ ] **1.4** Widen stop loss to 3x ATR (reduce premature TSL hits)
- [ ] **1.5** Remove trailing stop entirely - use fixed SL only

**Expected:** Win rate ~30%, but losses smaller. Math starts working.

### Phase 2: Entry Quality (Week 3-4)
**Goal:** Higher win rate without killing volume

- [ ] **2.1** Add session filter - only trade NY/London sessions (highest volatility)
- [ ] **2.2** Add liquidity pool proximity - enter near major liquidity (within 0.5%)
- [ ] **2.3** Require double confirmation: sweep + BOS on separate candles
- [ ] **2.4** Add weekend filter - no trades Sat/Sun (low volume)

**Expected:** Win rate 35-45%, ~100 trades/year.

### Phase 3: Profit Optimization (Week 5-6)
**Goal:** Capture larger moves, improve R:R

- [ ] **3.1** Implement scale-out strategy:
  - 33% at 1% profit (breakeven protected)
  - 33% at 2.5% profit  
  - 33% let ride to 5%+ or trailing SL at 1.5%
- [ ] **3.2** Add trend continuation filter - enter only with HTF trend alignment
- [ ] **3.3** Add market structure confirmed - only enter after clean BOS

**Expected:** Avg profit 1.5-3% per trade, WR 40-50%.

### Phase 4: Fine-Tuning (Ongoing)
**Goal:** Continuous improvement via hyperopt

- [ ] **4.1** Hyperopt OTE zone (30-70% is core ICT)
- [ ] **4.2** Hyperopt time exits per pair
- [ ] **4.3** Test pair-specific parameters (BTC needs more room than ADA)
- [ ] **4.4** Backtest on rolling 2-year window (not just recent)

---

## Key Principles

1. **Math First** - If WR * avg_win < avg_loss, strategy is broken
2. **Protect Capital** - Max 2% risk per trade, 15% max DD
3. **Let Winners Ride** - Scale out, don't scalp everything
4. **Session Matters** - NY/London = volume, Asian = chop
5. **HTF Trend is King** - Never fight the 1H/4H trend

---

## Quick Wins to Try Now

| Change | Impact |
|--------|--------|
| Disable trailing stop | Immediate TSL reduction |
| Add 1.5% profit target | Captures small wins |
| Widen SL to 3x ATR | Fewer premature exits |
| NY session only | Higher quality setups |

---

## Next Action

Run backtest with:
- TSL disabled
- SL = 3x ATR
- Add 1.5% fixed profit target

Version: **v0.42.0** - Focus on risk management
