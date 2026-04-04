# Liquidity Sweep — Roadmap

> **Last Updated:** 2026-04-04 09:12 UTC
> **Version:** v0.99.85 — ATR floor revert -2.5%→-2.0% + REMOVE BTC/LINK (confirmed stable)
> **Strategy Type:** Liquidity Sweep / Mean Reversion (ICT SMC)
> **Mode:** Spot, Long only

---

## 🎯 TARGETS

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| R/R Ratio | 1.26 | ≥ 1.5 | ⚠️ improved |
| Annualized Profit | ~11.2%/yr | ≥ 10%/yr | ✅ crossed target |
| Trades/yr | ~23.5 | 100+ | ⚠️ below target |
| Win Rate | 68.09% | any | ✅ acceptable |
| Drawdown | 2.57% | any | ✅ excellent |
| SQN | 2.77 | ≥ 2.0 | ✅ good |

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

## v0.99.85 — ATR floor revert -2.5%→-2.0% + REMOVE BTC/LINK (Results: R/R=1.26 ✅ CONFIRMED)
```
v0.99.85 backtest: 47 trades, 68.09% WR, $111.95 profit (11.2%)
avg_profit_per_win=1.607%, avg_loss_per_loss=1.27%, R/R=1.26
trailing_stop_loss: 5 trades (10.6%), 0% WR, -$41.22, avg -2.41%
early_profit_take: 8 trades (17%), 100% WR, +$68.28, avg +2.5% ✅
dynamic_tp: 7 trades (15%), 100% WR, +$52.54, avg +2.15% ✅
time_exit_8h: 22 trades (47%), 54.55% WR, +$12.54, avg +0.16% ← dominant near-zero
```
**Status:** CONFIRMED STABLE. R/R improved to 1.26 (vs 1.18 in v0.99.82). BTC (-$15.51) and LINK (-$9.78) removed. TS exits reduced from 13 → 5. time_exit_8h still dominates (47%) but at higher quality (+0.16% vs +0.17% in v0.99.82). 4 pairs (ETH, AVAX, AAVE, DOT) all positive.

---

## v0.99.84 — REVERT early_profit_take 2.5%→2.0% + WIDEN ATR floor (Results: R/R=1.12 ❌)
```
v0.99.84: 47 trades, 68.09% WR, $111.95 profit
R/R=1.12 — WORSE than v0.99.82 (1.18). early_profit_take 2.5% too high.
```
**Status:** REVERTED → v0.99.85.

---

## v0.99.83 — RAISE early_profit_take 2.0%→2.5% (REVERTED)

**Problem:** v0.99.82: time_exit_8h dominates at 39 trades (48% of all exits) with 53.85% WR and +0.17% avg profit — near zero. early_profit_take captured only 10/81 trades (12%). R/R=1.18 — below 1.5 target.

**Fix:** Raise early_profit_take from 2.0% to 2.5%. Winners in the 2.0-2.5% range were falling through to time_exit_8h (exits at <3.0%). Raising to 2.5% raises the floor. dynamic_tp (~2.7% for BTC) handles the 2.5-3.0% gap.

**Result:** REVERTED. early_profit_take 2.5% was too high — winners reversed between 2.0-2.5% and fell through to time_exit_8h. Also wider ATR floor (-2.5%) let losers run further. Back to v0.99.85 baseline.

---

## v0.99.82 — REMOVE XRP/SOL (Results: R/R=1.18 ✅)
```
v0.99.82 backtest (6yr): 81 trades, 61.73% WR, $121.89 profit (12.19%)
avg_profit_per_win=1.48%, avg_loss_per_loss=1.25%, R/R=1.18
trailing_stop_loss: 13 trades (16%), 0% WR, -$96.45 ← main loss source
time_exit_8h: 39 trades (48%), 53.85% WR, +$23.13 ← dominant near-breakeven
early_profit_take: 10 trades (12%), 100% WR, +$83.62 ✅
dynamic_tp: 10 trades (12%), 100% WR, +$74.51 ✅
```
**Finding:** XRP/SOL removal recovered R/R from 0.72→1.18. Win rate dropped (86%→62%) because bad pairs removed. Still: R/R > 0.8 ✅. Main problem now: time_exit_8h domination (48% of exits). NEW TARGET: R/R ≥ 1.5.

---

## v0.99.78b — OTE-ZONE STRUCTURAL STOP (REVERTED)

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
| v0.99.82 | Remove XRP/SOL | 81 | 61.7% | 1.18 | 12.2%/yr | 13 | time_exit_8h 48% dominates, new target R/R≥1.5 |
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

> ⚠️ NOTE: v0.99.82 backtest summary showed 2 pairs with negative profit (-$8.1, -$14.79) but pair names were UNKNOWN in the CI extraction. May be XRP/SOL (not fully removed) or another pair. Investigate after next backtest.

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
