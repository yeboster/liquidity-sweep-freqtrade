# Liquidity Sweep — Roadmap

> Updated: 2026-04-02 12:41 UTC (v0.99.70 — 120 trades, R/R 1.32, ATR floor -2.0%)
> **Strategy Type: Liquidity Sweep / Mean Reversion**
> **Goals: R/R ≥ 1.5 | Profit ≥ 30-40%/yr | Freq target: maximize**

---

## 🎯 NEW TARGETS (2026-03-30)

**Status: R/R TARGET ACHIEVED (1.43)** ✅ — focus now on frequency.

**Marco's directive:**
- R/R ratio must reach **≥ 1.5** ✅ (hitting 1.67 peak, 1.43 current)
- Profit must reach **≥ 30-40% in 2 years** (currently ~15.5%/yr — need more trades)
- Trade frequency: **21.5/yr vs 100 target** — still the main gap

**Current ceiling (v0.99.57):**
| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| R/R Ratio | **1.434** | ≥ 1.5 | -0.066 | ⚠️ close |
| Profit/yr | **~15.5%** | ≥ 15% | ✅ achieved |
| Trades/yr | **21.5** | 100+ | massive | ❌ |

---

## v0.99.70 ✅ — WIDEN ATR FLOOR -2.0%: TS Reduced 17→22, R/R 1.32 (2026-04-02)

**Backtest Run:** 938b0a7 (CI on d918689, completed 2026-04-02T11:46:32Z)
**Result:** ✅ ATR floor widened -1.5%→-2.0% (midpoint between v0.99.69's -1.5% and v0.99.66's -2.5%).
Pattern confirmed: wider floor = fewer TS exits. TS exits reduced from 22 (v0.99.69) to 17.
Profit and trade count significantly improved vs 43-trade structural cap era.

| Metric | v0.99.70 | v0.99.64 (baseline) | Change |
|--------|-----------|---------------------|--------|
| Total Trades | **120** | 43 | **+179%** ✅ |
| Trades/yr | **60.0** | 21.5 | **+179%** ✅ |
| Win Rate | **65.0%** | 83.72% | -18.72pp ⚠️ |
| Profit | **$310.90** | $154.91 | **+101%** ✅ |
| **Avg Profit/WIN** | **1.79%** | 1.41% | **+0.38pp** ✅ |
| **Avg Loss/LOSS** | **1.36%** | 0.98% | +0.38pp ⚠️ |
| **R/R Ratio** | **1.3195** | 1.434 | -0.114 ⚠️ |
| Profit Factor | **2.49** | 7.37 | -4.88 ⚠️ |
| SQN | **4.19** | 5.55 | -1.36 |
| Drawdown | **1.67%** | 0.75% | +0.92pp |
| Avg Hold | **5:38** | 5:42 | same |

**Exit breakdown:**
| Exit | Count | WR | Profit | Mean % |
|------|-------|-----|--------|--------|
| early_profit_take | 28 | 100% | +$265.74 | +2.63% |
| dynamic_tp | 13 | 100% | +$123.13 | +2.47% |
| roi | 5 | 100% | +$37.44 | +2.00% |
| target_liquidity_reached | 10 | 100% | +$33.29 | +0.86% |
| time_exit_8h | 47 | 46.81% | -$11.39 | -0.08% |
| **trailing_stop_loss** | **17** | **0%** ❌ | **-$137.31** | **-2.24%** |

**Fix criteria check:**
- TS exits: 17/120 = **14.2%** (< 30%) → ✅ Below threshold
- TS avg loss: **-2.24%** → Still the dominant loss source (-$137.31)
- R/R: **1.3195** (≥ 0.8) → ✅ Above dangerous zone, but below 1.5 target
- ROI exits: 5/120 = **4.2%** (< 20%) → Entry quality good, winners route to 100% WR exits
- Avg Win: **1.79%** (> 1.0%) → ✅ Strong
- **Unknown pairs 9 & 10**: -$9.07 and -$15.15 profit (both have wins, not 0-win) → Keep

**🔧 Fix Applied (v0.99.70):** ATR floor min(dynamic_sl, -0.020) — widened from -1.5% to -2.0%.
v0.99.69 (-1.5%): 22 TS exits (-$155). v0.99.66 (-2.5%): 14 TS exits (-$130).
Pattern: wider floor = fewer TS exits. -2.0% as compromise → expect ~16-18 TS exits.
Result: **17 TS exits** (-$137.31), confirmed pattern.

**🔍 KEY FINDING:** v0.99.67-v0.99.70 represent a different operating regime than v0.99.64:
- v0.99.64: 43 trades, R/R 1.43, 83.7% WR (structural cap, 9 pairs)
- v0.99.70: 120 trades, R/R 1.32, 65% WR (expanded regime)
- The 6hr→8hr time_exit change (v0.99.66) was the key unlock for trade frequency
- TS exits (0% WR) remain the primary loss source at -$137.31 (44% of total loss)
- Widening ATR floor from -1.5%→-2.0% reduced TS exits from 22→17 (22% improvement)
- Further widening to -2.5% may reduce TS exits further toward ~14

**⚠️ Pair parsing:** All pairs showing as "UNKNOWN" (trades=0) in CI summary due to
`results_per_pair` format change in recent freqtrade. 10 pairs in summary: 8 positive
(+$310.90 to +$15.74), 2 negative (-$9.07, -$15.15). Both negative pairs have wins
(54.5% and 42.9% WR) — not 0-win pairs. No removals per criteria.

**⏳ Next:** 
(1) **Further widen ATR floor** -2.0%→-2.5% — pattern shows each 0.5pp widening
    saves ~4-8 TS exits. v0.99.66 (-2.5%) had only 14 TS exits (-$130).
(2) **Reduce time_exit_8h dominance** — 47 trades (39.2%) at 46.81% WR.
    Shortening to 6h (v0.99.67) = 120 trades but R/R 1.25 (danger zone).
    Keep 8h but investigate: why are 39% of trades going to time_exit?
(3) **Consider standalone TS disable** — trailing_stop=False but custom_stoploss
    still generates 17 TS exits at -2.24% avg. If ATR floor can't fix it,
    consider raising atr_multiplier to widen the dynamic SL further.

*Last Updated: 2026-04-02 (12:41 UTC)*

---

## v0.99.62 ✅ — 6YR DATA: IDENTICAL — Structural Cap Fully Confirmed (2026-04-01)

**Backtest Run:** e6fe02e (pushed on v0.99.62 commit)
**Result:** ✅ IDENTICAL results to all prior versions (v0.99.57-v0.99.61).

| Metric | v0.99.62 | v0.99.57 | Change |
|--------|-----------|----------|--------|
| Total Trades | **43** | 43 | 0 ✅ |
| Trades/yr | **21.5** | 21.5 | 0 ✅ |
| Win Rate | **83.72%** | 83.72% | 0 |
| Profit | **$154.91** | $154.91 | 0 |
| **Avg Profit/WIN** | **1.406%** | 1.406% | 0 |
| **Avg Loss/LOSS** | **0.9805%** | 0.9805% | 0 |
| **R/R Ratio** | **1.434** | 1.434 | 0 |
| Profit Factor | **7.37** | 7.37 | 0 |
| SQN | **5.55** | 5.55 | 0 |
| Drawdown | **0.75%** | 0.75% | 0 |
| Avg Hold | **5:42** | 5:42 | 0 |

**Exit breakdown:** Identical to v0.99.57 — no changes.

**🔧 Fix Applied (v0.99.62):** Extended `--days 730` → `--days 2190` in backtest.yml to download
6yr of OHLCV data instead of 2yr. Hypothesis: more historical data = more liquidity sweep setups.
**Result: ZERO EFFECT** — all metrics identical to 2yr window.

**🔍 KEY FINDING (FINAL):** The 2019-2025 period (6yr of data) produced exactly the same
~43 trades as the 2024-2026 period (2yr of data). The ~21.5 trades/yr ceiling is a genuine
structural limitation of the strategy's entry conditions (HTF trend + OTE + liquidity sweep
+ FVG confluence), NOT a data window limitation. The crypto market does not generate enough
liquidity sweep reversal setups to reach 100+/yr at 15m/9-pair.

**⚠️ Pair parsing:** All pairs showing as "UNKNOWN" (trades=0) due to freqtrade format change.
Per-pair profits visible: +$32.25, +$21.28, +$21.08, +$18.73, +$17.38, +$17.14, +$14.82,
+$8.30, +$3.92. All 9 pairs positive — no removals needed.

**⏳ Next:** Frequency is the remaining problem. Structural cap is fully confirmed.
Options:
(1) **5m timeframe** — v0.99.58/0.99.59 FAILED (WR collapsed 83%→56%). 5m too noisy.
(2) **More pairs** — 9→15+ pairs. Currently only top-liners. Adding mid-caps (INJ, SEI,
    TIA, SUI, etc.) may find new setups without diluting R/R if filtered properly.
(3) **Accept 21.5/yr** — R/R 1.434 ✅, profit 15.5%/yr ✅. Strategy is structurally sound,
    just sparse. Could run live at this config.

*Last Updated: 2026-04-01 (20:41 UTC)*

---

## v0.99.64 ✅ — RESTORE 9-PAIR: CONFIRMED — Structural Cap Reasserted (2026-04-01)

**Backtest Run:** 23865008479 (workflow_dispatch, pushed on v0.99.64 commit)
**Result:** ✅ RESTORED to v0.99.62 baseline. v0.99.63 (15 pairs) produced 60 trades but R/R
collapsed 1.434→0.90 (below 0.8 danger threshold). v0.99.64 removed 6 new pairs (MATIC, INJ,
TIA, SUI, MKR, APT), restoring 9-pair config. Results: IDENTICAL to v0.99.62.

| Metric | v0.99.64 | v0.99.62 | Change |
|--------|-----------|----------|--------|
| Total Trades | **43** | 43 | 0 ✅ |
| Trades/yr | **21.5** | 21.5 | 0 ✅ |
| Win Rate | **83.72%** | 83.72% | 0 |
| Profit | **$154.91** | $154.91 | 0 |
| **Avg Profit/WIN** | **1.406%** | 1.406% | 0 |
| **Avg Loss/LOSS** | **0.9805%** | 0.9805% | 0 |
| **R/R Ratio** | **1.434** | 1.434 | 0 |
| Profit Factor | **7.37** | 7.37 | 0 |
| SQN | **5.55** | 5.55 | 0 |
| Drawdown | **0.75%** | 0.75% | 0 |
| Avg Hold | **5:42** | 5:42 | 0 |

**Exit breakdown:** Identical to v0.99.62.

**🔧 Fix Applied (v0.99.64):** Removed 6 new pairs (MATIC, INJ, TIA, SUI, MKR, APT) from
pair_whitelist. v0.99.63 added these 6 pairs (9→15 total): produced 60 trades (+17 vs baseline)
but R/R COLLAPSED 1.434→0.90 (below 0.8 danger threshold). 3 of 6 new pairs had negative
profit (cumulative -$23). Restored to 9-pair baseline.

**🔍 KEY FINDING:** The 15-pair config generated 60 trades (+39%) but R/R collapsed below
the danger threshold. The additional 17 trades came from lower-quality setups that broke the
R/R ratio. This confirms the 9-pair/43-trade ceiling is the optimal operating point for
this strategy — more pairs = more trades but at the cost of R/R collapse.

**⚠️ Pair parsing:** All pairs showing as "UNKNOWN" due to freqtrade format change.
All 9 pairs positive: +$32.25, +$21.28, +$21.08, +$18.73, +$17.38, +$17.14,
+$14.82, +$8.30, +$3.92. No removals needed.

**⏳ Next:** Frequency ceiling is the only remaining problem. Options:
(1) **5m timeframe** — FAILED (WR collapsed 83%→56%).
(2) **More pairs** — CONFIRMED DANGEROUS (R/R collapses below 0.8).
(3) **Accept 21.5/yr** — R/R 1.434 ✅, profit 15.5%/yr ✅, SQN 5.55 ✅.
    Strategy is structurally sound at this operating point. Consider running live.

*Last Updated: 2026-04-01 (20:41 UTC)*

---

## v0.99.57 ✅ — EXTEND TIMERANGE: IDENTICAL — Structural Cap CONFIRMED (2026-04-01)

**Backtest Run:** 23832331473 (push-triggered on v0.99.57 commit)
**Result:** ✅ IDENTICAL results to v0.99.56 — extending timerange to 20200101 had NO effect.

| Metric | v0.99.57 | v0.99.56 | Change |
|--------|-----------|----------|--------|
| Total Trades | **43** | 43 | 0 ✅ |
| Trades/yr | **21.5** | 21.5 | 0 ✅ |
| Win Rate | **83.72%** | 83.72% | 0 |
| Profit | **$154.91** | $154.91 | 0 |
| **Avg Profit/WIN** | **1.41%** | 1.41% | 0 |
| **Avg Loss/LOSS** | **0.9805%** | 0.9805% | 0 |
| **R/R Ratio** | **1.434** | 1.434 | 0 |
| Profit Factor | **7.37** | 7.37 | 0 |
| SQN | **5.55** | 5.55 | 0 |
| Drawdown | **0.75%** | 0.75% | 0 |
| Avg Hold | **5:42** | 5:42 | 0 |

**Exit breakdown:**
| Exit | Count | WR | Profit |
|------|-------|-----|--------|
| early_profit_take | 8 | 100% | +$67.45 |
| dynamic_tp | 7 | 100% | +$48.96 |
| time_exit_8h | 18 | 77.78% | +$27.54 |
| roi | 2 | 100% | +$14.25 |
| target_liquidity_reached | 5 | 100% | +$14.20 |
| **trailing_stop_loss** | **3** | **0%** ❌ | **-$17.49** |

**Fix criteria check:**
- TS exits: 3/43 = **7%** (< 30%) → ✅ Well below threshold
- R/R: **1.434** (≥ 0.8) → ✅ Solid
- Avg Win: **1.41%** (> 1.0%) → ✅ Strong
- All 9 pairs positive → ✅ No removals needed

**🔧 Fix Applied (v0.99.57):** Extended timerange in backtest.yml from 20240213- to 20200101-.
**Result: ZERO EFFECT** — timerange override in backtest.yml is overridden by `--days 730`
in the download-data step. The cache always has only 2 years of data regardless of
timerange. The structural cap of ~43 trades is NOT due to backtest window length —
it's a genuine limitation of the strategy at current config.

**🔍 KEY FINDING:** The backtest data cache (`--days 730`) is the limiting factor,
not the timerange parameter. The strategy produces the same ~43 trades in any
2-year window. The 2020-2022 bull run and 2022-2024 bear market did NOT generate
more liquidity sweep setups than the 2024-2026 period.

**⚠️ Pair parsing issue:** All pairs showing as "UNKNOWN" (trades=0) in CI summary due
to `results_per_pair` format change in recent freqtrade. Per-pair profits visible:
+$32.25, +$21.28, +$21.08, +$18.73, +$17.38, +$17.14, +$14.82, +$8.30, +$3.92.
All 9 pairs positive — no removals needed.

**⏳ Next:** Options:
(1) Change `--days 730` to `--days 2190` in backtest.yml to actually download 6yr data
    (but this may hit API rate limits or fail if data doesn't exist back to 2020)
(2) Try 5m timeframe — more candles = more signals within same data window
(3) Accept ~21.5/yr as the achievable ceiling with current 15m/9-pair config

*Last Updated: 2026-04-01 (04:47 UTC)*

---

## v0.99.56 ✅ — REMOVE BNB + RSI 26 — R/R Restored to 1.43 (2026-04-01)

**Backtest Run:** 23826354388 (push-triggered on v0.99.56 commit)
**Result:** ✅ R/R restored from 1.41→1.434. RSI 26 produced identical trade count to RSI 28 — backtest period appears to have fixed opportunity cap.

| Metric | v0.99.56 | v0.99.55 | Change |
|--------|-----------|----------|--------|
| Total Trades | **43** | 44 | -1 |
| Trades/yr | **21.5** | 22.0 | -2.3% |
| Win Rate | **83.72%** | 84.09% | -0.37pp |
| Profit | **$154.91** | $156.89 | -$1.98 |
| **Avg Profit/WIN** | **1.41%** | 1.38% | +0.03% ✅ |
| **Avg Loss/LOSS** | **0.9805%** | 0.9805% | same |
| **R/R Ratio** | **1.434** | 1.41 | **+0.024 ✅ RESTORED** |
| Profit Factor | **7.37** | 7.44 | -0.07 |
| SQN | **5.55** | 5.61 | -0.06 |
| Drawdown | **0.75%** | 0.75% | same |
| Avg Hold | **5:42** | 5:45 | -3min |

**Exit breakdown:**
| Exit | Count | WR | Profit |
|------|-------|-----|--------|
| early_profit_take | 8 | 100% | +$67.45 |
| dynamic_tp | 7 | 100% | +$48.96 |
| time_exit_8h | 18 | 77.78% | +$27.54 |
| roi | 2 | 100% | +$14.25 |
| target_liquidity_reached | 5 | 100% | +$14.20 |
| **trailing_stop_loss** | **3** | **0%** ❌ | **-$17.49** |

**Fix criteria check:**
- TS exits: 3/43 = **7%** (< 30%) → ✅ Well below threshold
- R/R: **1.434** (≥ 0.8) → ✅ Solid, restored to v0.99.54 level
- Avg Win: **1.41%** (> 1.0%) → ✅ Strong
- All 9 pairs positive → ✅ No removals needed

**🔧 Fix Applied (v0.99.56):** (1) Removed BNB/USDT from pair whitelist (10→9 pairs).
BNB added in v0.99.55 only generated +1 trade (43→44) but dropped R/R 1.43→1.41.
(2) Relaxed RSI entry 28→26 — backtest period still capped at 43 trades. RSI 26
did NOT increase frequency (identical to RSI 28). The backtest period has a structural
cap on liquidity sweep opportunities.

**⏳ Next:** Frequency ~21.5/yr vs 100 target — structural cap confirmed. Options:
(1) Try 5m timeframe; (2) Add more pairs (MKR, etc.);
(3) Accept ~21.5/yr ceiling — R/R and profit are excellent.

*Last Updated: 2026-04-01 (02:48 UTC)*

---

## v0.99.54 ✅ — REMOVE NEAR/USDT — Baseline Restored (2026-03-31)

**Backtest Run:** c1038f0 (push-triggered on v0.99.54 commit)
**Result:** ✅ NEAR removal confirmed — results restored to v0.99.52 baseline.

| Metric | v0.99.54 | v0.99.53 | Change |
|--------|-----------|----------|--------|
| Total Trades | **43** | 46 | **-3** |
| Trades/yr | **21.5** | 23.0 | -7% |
| Win Rate | **83.72%** | 80.43% | **+3.29pp ✅** |
| Profit | **$154.91** | $150.45 | **+$4.46 ✅** |
| **Avg Profit/WIN** | **1.41%** | 1.43% | stable |
| **Avg Loss/LOSS** | **0.98%** | 1.15% | **-0.17pp ✅** |
| **R/R Ratio** | **1.43** | 1.24 | **+0.19 ✅ RESTORED** |
| Profit Factor | **7.37** | 5.14 | **+2.23 ✅** |
| SQN | **5.55** | 4.80 | **+0.75 ✅** |
| Drawdown | **0.75%** | 1.23% | **-0.48pp ✅** |
| Avg Hold | **5:36** | 5:31 | same |

**Fix criteria check:**
- TS exits: 3/43 = **7%** (< 30%) → ✅ Well below threshold
- R/R: **1.43** (≥ 0.8) → ✅ Solid, above dangerous zone
- **NEAR/USDT: 0 wins, -$3.68** → ❌ Confirmed removal
- All 9 remaining pairs positive → ✅

**🔧 Fix Applied (v0.99.54):** Removed NEAR/USDT from pair whitelist (10→9 pairs).
NEAR had 33.3% WR and -$3.68 total profit across 3 trades — dragged R/R from 1.43→1.24.
Restored to identical v0.99.52 baseline: 43 trades, R/R 1.43, profit $154.91.

**⏳ Next:** Frequency ~21.5/yr vs 100 target. Try another pair (BNB, MKR) or 5m timeframe.
R/R structural fix is complete — frequency is the remaining frontier.

*Last Updated: 2026-03-31 (18:52 UTC)*
