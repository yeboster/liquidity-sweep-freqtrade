# Liquidity Sweep — Roadmap

> **Last Updated:** 2026-04-03 20:41 UTC
> **Version:** v0.99.82 — REMOVE XRP/SOL (R/R=0.72 danger fix)
> **Strategy Type:** Liquidity Sweep / Mean Reversion (ICT SMC)
> **Mode:** Spot, Long only

---

## 🎯 TARGETS

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| R/R Ratio | 0.72 | ≥ 1.5 | 🚨 DANGER |
| Annualized Profit | ~5.4%/yr | ≥ 10%/yr | ⚠️ below S&P500 |
| Trades/yr | ~46 | 100+ | ⚠️ improved |
| Win Rate | 86% | any | ✅ excellent |
| Drawdown | 1.8% | any | ✅ excellent |
| SQN | ~4.0 | ≥ 2.0 | ✅ good |

**Problem:** Strategy is conservative, low-frequency, and R/R < 1.5. The annualized return is below S&P500.

---

## KEY FINDINGS (6yr backtest, 110 trades)

### 1. Trade Frequency Ceiling — CONFIRMED
The ~20 trades/yr ceiling is **structural**, not data-limited. Extending from 2yr → 6yr of data
produced identical trade rates. More pairs (9→15) adds trades but collapses R/R below 0.8.
5m timeframe collapses WR from 83% → 56%.

### 2. R/R < 0.8 — DANGER (v0.99.81)
```
v0.99.81 (15m/1H revert): 107 trades, 86% WR, $120.74 profit
BUT: avg_profit_per_win=1.13%, avg_loss_per_loss=1.56%, R/R=0.72
Winner avg hold: 3:59 | Loser avg hold: 7:39 → 2× longer
trailing_stop_loss: 102 trades, 85.4% WR, +0.30% avg (mostly wins!)
```
**Root problem:** Winners held 2× shorter than losers. The strategy takes profits too early on
winners (TS fires at +0.3%) while losers run 2× longer before stopping. R/R collapses to 0.72.

### 3. Holding Time R/R Inversion (v0.99.81)
```
Winners: 3h59m avg | Losers: 7h39m avg
```
Reversal strategy should have winners held longer. Instead, winners are cut short (TS).
This is the OPPOSITE of what a good mean-reversion strategy should do.

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
| v0.99.81 | 15m/1H revert | 107 | 86.0% | 0.72 | 5.4%/yr | 102 | 🚨 R/R DANGER |
| v0.99.76 | ATR floor -2.3% | 110 | ? | 1.29 | ? | 13 | Worse than -2.0% |
| v0.99.75 | time_exit_2 +2.0% | 120 | 65.0% | 1.32 | ~5%/yr | 17 | 47→42 time_exit |
| v0.99.71 | DISABLE time_exit_2 | 120 | 75% | 0.74 | 6.7%/yr | 30 | CATASTROPHIC |
| v0.99.70 | ATR floor -2.0% | 120 | 65% | 1.32 | ~5%/yr | 17 | Good |
| v0.99.68 | 6yr data (cache fixed) | 120 | 65% | 1.25 | ~5%/yr | 14 | First real data |

---

## REMOVED PAIRS (with reason)

| Pair | Removed | Reason |
|------|---------|--------|
| XRP/USDT | v0.99.82 | 66.7% WR, -$8.45, 12 trades, R/R < 0.8 |
| SOL/USDT | v0.99.82 | 72.7% WR, -$7.37, 11 trades, R/R < 0.8 |
| UNI/USDT | v0.99.78 | 42.86% WR, -$15.17, R/R < 0.8 |
| NEAR/USDT | v0.99.54 | 33.3% WR, -$3.68, 3 trades |

---

## REMAINING PAIRS (8)

BTC, ETH, ADA, AVAX, AAVE, MATIC, ATOM, DOT, LINK

---

## NEXT EXPERIMENTS (Priority Order)

### 1. 🚨 R/R RECOVERY (v0.99.82+)
**Priority:** CRITICAL. v0.99.81 R/R=0.72 (below 0.8 danger threshold).
Root cause: winners held 3:59 vs losers 7:39 — 2× shorter!

Fixes to test:
1. **Widen trailing_stop_positive_offset** — TS fires too early on winners (+0.3% avg)
   - Current: ~0.8-1.0%. Try 2.0-3.0% to let winners ride longer
2. **Raise early_profit_take** 1.5%→2.0% — take more medium winners via 100% WR exits
3. **Disable trailing_stop** entirely — route ALL trades through roi/early_profit_take/dynamic_tp
4. **Tighten ATR floor** -2.0%→-1.5% — fewer -2% losers, smaller avg loss

### 2. OTE-Zone Stop Buffer Tuning (v0.99.79+)
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
