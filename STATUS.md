# Liquidity Sweep Strategy - STATUS.md

## Current State (v0.58.0 — 🏆 ATH)

| Metric | Value | Status |
|--------|-------|--------|
| Version | 0.58.0 | 🏆 ATH |
| Trades | 43 | ✅ |
| Win Rate | 48.8% | ✅ (target: 40-55%) |
| Profit | 3.80% | ✅ |
| Profit Factor | 1.97 | ✅ |
| SQN | 1.60 | ✅ |
| Drawdown | 0.85% | ✅ (target: <15%) |
| DD Duration | 21 days | ✅ |

**Key Changes (v0.58.0):**
- Disabled ChoCH exits entirely — exit_signal was -35.87 USDT on 17 trades (11.8% WR)
- All mechanical exits (early_profit, ROI, trailing_stop) are 100% WR
- Only drag: time_exit_6h (6 trades, -17.05 USDT)

---

## Target Goals

| Goal | Target | Current | Status |
|------|--------|---------|--------|
| Win Rate | 40-55% | 48.8% | ✅ |
| Profit/Trade | 1-5% | 0.26% avg | ⚠️ |
| Trade Frequency | 50-200/yr | ~22/yr | ⚠️ Low |
| Max Drawdown | <15% | 0.85% | ✅ |
| Profit Factor | >1.5 | 1.97 | ✅ |

---

## In Progress

- **Hyperopt (run 23319892426):** 200 epochs on v0.58.0 code, SharpeHyperOptLoss
  - Searching: buy, ROI, trailing, stoploss parameter spaces
  - Expected: globally optimal params that manual tuning can't reach

---

## Recent Iteration Log (v0.57-v0.61)

| Version | Profit | PF | Change | Result |
|---------|--------|-----|--------|--------|
| v0.57.0 | 2.93% | 1.75 | Restore 8 pairs + XRP fix | ✅ Improved |
| **v0.58.0** | **3.80%** | **1.97** | **Disable ChoCH exits** | **🏆 ATH** |
| v0.59.0 | 1.67% | 1.63 | Breakeven exit 3h | ❌ Regression |
| v0.60.0 | 3.33% | 1.73 | Time exit 5h | ❌ Regression |
| v0.61.0 | 3.49% | 1.83 | Disable time_exit_2 | ❌ Regression |

**Lesson:** Manual exit tuning hit diminishing returns. ROI exits need 5h+ avg. Any time-based exit ≤5h steals from ROI. Breakeven exits too aggressive at 3h.

---

## Next Steps

1. **Apply hyperopt results** when run completes
2. **Backtest with optimized params** — target 4%+ profit, PF 2.0+
3. **Consider:** rolling 2-year backtest window for robustness check
