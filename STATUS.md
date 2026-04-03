# Liquidity Sweep — STATUS

**Last Updated:** 2026-04-03 09:27 UTC
**Version:** v0.99.78b — OTE-zone structural stop (0.75% stop-hunt buffer)
**GitHub:** `yeboster/liquidity-sweep-freqtrade`

---

## Current Performance (v0.99.77, 6yr backtest, 110 trades)

| Metric | Value | vs S&P500 (~10-12%/yr) |
|--------|-------|------------------------|
| Trades | 110 (55/yr normalized ~20/yr) | ~20 trades/yr ceiling confirmed |
| Win Rate | 65.45% | ✅ decent |
| Annualized | ~4.8%/yr ($48/yr) | ⚠️ below S&P500 |
| R/R Ratio | 1.31 | ⚠️ below 1.5 target |
| Profit | $290.62 (29.06% over 6yr) | ~$48/yr |
| SQN | ~4.0 | ✅ (2.0+ is good) |
| Max Drawdown | 1.80% | ✅ excellent |

**The core problem:** R/R < 1.5 and annualized < S&P500. The strategy is conservative and low-frequency.

---

## The Core Issue: trailing_stop_loss

```
trailing_stop_loss: 16 trades, 0% WR, -$129.76
time_exit_8h:       45 trades, 51% WR, +$10.07  ← both drag on R/R
```

**Hypothesis (v0.99.78):** ATR-based stops trigger on normal retracements, not structural breaks.
**Fix:** OTE-zone structural stop — only exit when price CLOSES below OTE lower (structural support broken).
**Added:** 0.75% stop-hunt buffer below OTE lower.

---

## Strategy Parameters (v0.99.78b)

| Parameter | Value |
|-----------|-------|
| Timeframe | 15m entry / 1H context |
| Pairs | BTC, ETH, ADA, AVAX, AAVE, SOL, MATIC, ATOM, DOT, LINK (UNI removed) |
| Mode | Spot (long only) |
| OTE Zone | 30-70% (Fibonacci retracement) |
| Trailing Stop | FALSE (disabled v0.99.50) |
| ATR Floor | -2.0% (fallback for non-OTE trades) |
| ATR Multiplier | 4.0× (via custom_stoploss) |
| Early Profit Take | +2.0% (45min hold) |
| Dynamic TP | 1.5× ATR threshold |
| time_exit_2 | Enabled at 8h / +1.5% profit floor |
| R/R Entry Filter | ≥ 1.5 |

---

## What Changed vs v0.99.77

- **v0.99.78b:** Added 0.75% stop-hunt buffer to OTE-zone stop (stop fires on CLOSE below ote_lower×0.9925)
- **v0.99.78:** Replaced ATR-based custom_stoploss with OTE-zone structural stop
- **v0.99.77:** ATR floor -2.0% (reverted -2.3%)

---

## Next Steps

1. **v0.99.78 backtest** — OTE-zone structural stop results (~15 min)
2. If TS exits improve: iterate on buffer size (0.5%, 1.0%)
3. If R/R still < 1.5: try tighter time_exit_2 profit floor or remove it entirely
4. Consider 1H timeframe for better entry quality
