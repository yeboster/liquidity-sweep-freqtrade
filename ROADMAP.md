# Liquidity Sweep — Roadmap

> **Last Updated:** 2026-04-03 09:27 UTC
> **Version:** v0.99.78b — OTE-zone structural stop + 0.75% stop-hunt buffer
> **Strategy Type:** Liquidity Sweep / Mean Reversion (ICT SMC)
> **Mode:** Spot, Long only

---

## 🎯 TARGETS

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| R/R Ratio | 1.31 | ≥ 1.5 | ⚠️ below |
| Annualized Profit | ~4.8%/yr | ≥ 10%/yr | ⚠️ below S&P500 |
| Trades/yr | ~20 | 100+ | ❌ hard cap |
| Win Rate | 65% | any | ✅ fine |
| Drawdown | 1.8% | any | ✅ excellent |
| SQN | ~4.0 | ≥ 2.0 | ✅ good |

**Problem:** Strategy is conservative, low-frequency, and R/R < 1.5. The annualized return is below S&P500.

---

## KEY FINDINGS (6yr backtest, 110 trades)

### 1. Trade Frequency Ceiling — CONFIRMED
The ~20 trades/yr ceiling is **structural**, not data-limited. Extending from 2yr → 6yr of data
produced identical trade rates. More pairs (9→15) adds trades but collapses R/R below 0.8.
5m timeframe collapses WR from 83% → 56%.

### 2. trailing_stop_loss — THE #1 PROBLEM
```
trailing_stop_loss: 16 trades, 0% WR, -$129.76 (avg loss 2.47%)
```
Every single TS exit is a loss. These are trades that went positive, retraced,
and the ATR stop fired — but they might have recovered. The stop is too mechanical.

### 3. time_exit_8h — SECONDARY PROBLEM
```
time_exit_8h: 45 trades, 51% WR, +$10.07 (near-breakeven)
```
These stale trades (at 8h, between +1.5% and +2.0%) coast instead of exiting cleanly.
They route to time_exit because they missed early_profit_take but haven't progressed enough.

### 4. 100% WR Exits Are Working
```
early_profit_take:  26 trades, 100% WR, +$244
dynamic_tp:         13 trades, 100% WR, +$122
roi:                 3 trades, 100% WR, +$22
target_liquidity:    7 trades, 100% WR, +$23
```
These 4 exits handle ~85% of trades perfectly. The problem is the 15% that don't reach them.

### 5. ATR Floor Iteration Pattern
| Floor | TS Exits | Avg Loss | R/R |
|-------|----------|----------|-----|
| -1.5% | 22 | -1.93% | ? |
| -2.0% | 17 | -2.24% | 1.31 |
| -2.3% | 13 | -2.47% | 1.29 (worse!) |
| -2.5% | 30 | -2.82% | 0.74 (catastrophic) |

Wider floor = fewer TS triggers BUT worse R/R. The floor doesn't fix the root problem.

---

## v0.99.78b — OTE-ZONE STRUCTURAL STOP (Current)

**Change:** Replaced ATR-based `custom_stoploss` with OTE-zone structural stop.

**Logic:**
- Longs: stop fires only when price **closes** below OTE lower × 0.9925 (0.75% buffer)
- Shorts: stop fires only when price **closes** above OTE upper × 1.0075
- Fallback: ATR-based stop for non-OTE trades

**Hypothesis:** ATR stops fire on normal retracements. Structural stops only fire when the
zone (support/resistance) is actually broken. The 0.75% buffer lets stop hunts wick through
without triggering, then price reverses.

**Expected:** Fewer TS exits (only real breaks), better R/R, same trade count.

---

## EXPERIMENT LOG (v0.99.68 — v0.99.77)

| Version | Change | Trades | WR | R/R | Annualized | TS Exits | Key Finding |
|---------|--------|--------|-----|-----|------------|----------|-------------|
| v0.99.77 | ATR floor -2.0% | 110 | 65.5% | 1.31 | 4.8%/yr | 16 | Revert from -2.3% |
| v0.99.76 | ATR floor -2.3% | 110 | ? | 1.29 | ? | 13 | Worse than -2.0% |
| v0.99.75 | time_exit_2 +2.0% | 120 | 65.0% | 1.32 | ~5%/yr | 17 | 47→42 time_exit |
| v0.99.71 | DISABLE time_exit_2 | 120 | 75% | 0.74 | 6.7%/yr | 30 | CATASTROPHIC |
| v0.99.70 | ATR floor -2.0% | 120 | 65% | 1.32 | ~5%/yr | 17 | Good |
| v0.99.68 | 6yr data (cache fixed) | 120 | 65% | 1.25 | ~5%/yr | 14 | First real data |

---

## REMOVED PAIRS (with reason)

| Pair | Removed | Reason |
|------|---------|--------|
| UNI/USDT | v0.99.78 | 42.86% WR, -$15.17, R/R < 0.8 |
| NEAR/USDT | v0.99.54 | 33.3% WR, -$3.68, 3 trades |

---

## REMAINING PAIRS (8)

BTC, ETH, ADA, AVAX, AAVE, SOL, MATIC, ATOM, DOT, LINK

---

## NEXT EXPERIMENTS (Priority Order)

### 1. OTE-Zone Stop Buffer Tuning (v0.99.79+)
If v0.99.78b improves R/R:
- Try buffer 0.5% (tighter — more triggers but smaller losses)
- Try buffer 1.0% (looser — fewer triggers but bigger losses when they hit)
- Try NO buffer (pure OTE boundary — validates if buffer is needed at all)

### 2. time_exit_2 Profit Floor Tuning
If time_exit_8h keeps producing near-breakeven exits:
- Lower floor: +1.0% (catch more stale trades earlier)
- Raise floor: +2.5% (only exit at early_profit_take level — gap closure)

### 3. ATR Multiplier Tuning
Current: 4.0× (generates ~2% dynamic SL for BTC)
- Try 5.0× (wider — fewer premature exits, bigger losses when hit)
- Try 3.0× (tighter — more exits, smaller losses when hit)

### 4. 1H Timeframe Test
15m generates ~20/yr. 1H might generate fewer trades but with better WR/R/R.
Test with same entry conditions on 1H candles.

### 5. Pair Expansion (Conservative)
Re-test LINK (was removed at -$2.44, inconclusive).
Try adding one mid-cap with similar volatility profile to existing pairs.

---

## STRATEGIC QUESTIONS FOR MARCO

1. **Is this a live trading candidate?** With ~4.8%/yr and 1.8% max drawdown, it's conservative but profitable. Better than a savings account, worse than S&P500.

2. **Should we pivot?** The OTE-zone stop is the last structural fix attempt. If it doesn't work, the strategy may need a fundamental rethink (trend-following vs mean-reversion, or different timeframe).

3. **What's the real goal?** Income? Capital growth? Learning? The answer changes whether ~5%/yr with 1.8% DD is acceptable.
