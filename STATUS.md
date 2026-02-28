# Liquidity Sweep Freqtrade — STATUS.md

> Single source of truth for project state, open items, and decisions.

---

## Current State

- **Version:** 0.31.0 (Fix OB detection bug — rolling window recency check)
- **Status:** CI triggered on push. v0.30.0 produced 0 trades (same bug as v0.28.0: OB box too narrow). Fixed.
- **Branch:** `main`

---

## Latest Backtest Results (v0.30.0)

| Metric | Value | Notes |
|--------|-------|-------|
| Total Trades | **0** | ❌ Bug — OB zone (ffill top/bottom) too narrow; price never inside exact historical candle body |
| Root Cause | `in_bullish_ob` always False | Same class of bug as v0.28.0. ffill carries OB top/bottom but price rarely sits inside a historical candle body at entry. |

*Fixed in v0.31.0: rolling(20).max() on ob==1/ob==-1 checks "was a bullish/bearish OB formed within last 20 candles?" — correct SMC recency interpretation.*

---

## Previous Backtest Results (v0.29.0)

| Metric | Value | Change vs v0.27.0 |
|--------|-------|-------------------|
| Timerange | 2024-03-01 → 2026-02-28 | |
| Total Trades | **99** | 📉 -29 (was 128) |
| Win Rate | **24.2%** (24W / 75L) | 📈 +3.1% |
| Profit Total | **-19.16%** | 📈 +7.87% |
| Avg Duration | 2h 33m | ~Same |

### Exit Reason Breakdown
| Exit Reason | Trades | Avg Profit | Wins |
|-------------|--------|-----------|------|
| **roi** | 22 | +0.57% | 100% |
| **time_exit_6h** | 8 | -0.25% | 12.5% |
| **time_exit_4h** | 14 | -0.45% | 0% |
| **trailing_stop_loss** | 36 | -1.61% | 0% |

*Root cause: TSL exits reduced 55→36 (opposite-side imbalance filter worked). But math is still broken: avg win = +0.57% vs avg TSL loss = -1.61% = need 74% WR to break even. Two-pronged fix in v0.30.0: (1) force OB confluence to improve entry quality → expect WR 35-50% (2) widen ROI targets → push avg win from 0.57% to 1.5%+.*

---

## Previous Backtest Results (v0.28.0)

| Metric | Value | Notes |
|--------|-------|-------|
| Total Trades | **0** | ❌ Bug — FVG zone filter blocked ALL entries |
| Root Cause | `active_bullish_fvg` always False | ffill() on boolean series = dead flag |

*Fixed in v0.29.0: now checks if close is INSIDE the zone (top/bottom levels), not if candle IS the FVG candle.*

---

## Previous Backtest Results (v0.27.0)

| Metric | Value | Notes |
|--------|-------|-------|
| Timerange | 2024-03-01 → 2026-02-27 | |
| Total Trades | 128 | Nearly identical to v0.26.0 (129) |
| Win Rate | 21.1% (27W / 101L) | No improvement vs v0.26.0 |
| Profit Total | -27.03% | No improvement |
| Avg Duration | 2h 28m | |

### Exit Reason Breakdown
| Exit Reason | Trades | Avg Profit | Wins |
|-------------|--------|-----------|------|
| **roi** | 25 | +0.55% | 100% |
| **target_liquidity_reached** | 1 | 0.0% | 100% |
| **time_exit_6h** | 11 | -0.26% | 9.1% |
| **time_exit_4h** | 15 | -0.50% | 0% |
| **trailing_stop_loss** | 55 | -1.58% | 0% |

*Root cause analysis: v0.27.0 results identical to v0.26.0. The HTF trend filter had little impact because the 2024-2026 backtest period is heavily bullish (trend_1h==1 most of the time, entries were already mostly long-aligned). The 55 TSL exits at avg 1h04m are a ENTRY QUALITY problem: price is attracted to unmitigated FVGs beyond the stop loss (stop-hunt magnets). Fixed in v0.28.0.*

---

## Previous Backtest Results (v0.26.0)

| Metric | Value | Change vs v0.20.0 |
|--------|-------|-------------------|
| Timerange | 2024-02-29 → 2026-02-27 | |
| Total Trades | 129 | 📉 -301 (was 430) |
| Win Rate | 21.7% (28W / 101L) | 📉 -21.3% |
| Profit Total | -26.66% | 📈 +11.52% |
| Max Drawdown | 27.22% | 📈 Better (was 38.2%) |
| Avg Duration | 2h 27m | 🚀 Faster |

### Exit Reason Breakdown
| Exit Reason | Trades | Avg Profit | Wins |
|-------------|--------|-----------|------|
| **roi** | 26 | +0.59% | 100% |
| **trailing_stop_loss** | 55 | -1.58% | 0% |
| **time_exit_4h** | 15 | -0.50% | 0% |
| **time_exit_6h** | 11 | -0.26% | 9.1% |

*Root cause: 55 trailing_stop_loss exits at avg -1.58% = entries fired against 1H trend (dead variable bug, fixed in v0.27.0).*

---

## Previous Backtest Results (v0.20.0)

| Metric | Value | Change vs v0.19.0 |
|--------|-------|-------------------|
| Timerange | 2024-02-22 → 2026-02-20 | |
| Total Trades| 430 | -35 |
| Win Rate | 43.0% (185W / 245L / 0D) | 📉 -8.2% |
| Profit Total| -38.18% | 📈 +2.51% |
| Profit Mean | -0.334% per trade | 📉 -0.01% |
| Max Drawdown| 38.2% | 📈 Better (was 45.3%) |
| Avg Duration| 2h 55m | 🚀 Much faster (was 11h) |

### Exit Reason Breakdown
| Exit Reason | Trades | Avg Profit | Wins |
|-------------|--------|-----------|------|
| **roi** | 147 | +0.92% | 147 |
| **trailing_stop** | 31 | +0.99% | 31 |
| **time_exit_4h/6h** | 185 | -0.79% | 0 |
| **stop_loss** | 61 | -2.79% | 0 |

*Insight:* Time exit works at cutting losers (185 trades at -0.79%) but it hurts the Win Rate because many marginal winners exit at 4h before hitting ROI.

---

## v0.21.0: SMC Library Integration

Full rewrite of the indicator logic using the `smartmoneyconcepts` library:
- **Liquidity sweeps**: True clustering and swept detection instead of simple rolling max.
- **Order Blocks**: Added `require_ob` filter for confluence.
- **FVG**: Added mitigation tracking (only raw/unmitigated FVGs count).
- **Trend**: Differentiates between BOS (continuation) and ChoCH (reversal).

---

## Pending / Next Steps

- [x] **v0.22.0: Analyze backtest results** — analyze after CI fix is complete
- [x] **Run hyperopt on v0.24.0** (Completed, but yielded overfitted/low-trade results. Needs logic refinement.) — optimize `atr_multiplier`, `ote_lower/upper`, `require_ote`, `min_rr`, and `time_exit` space
- [x] **Per-pair parameter optimization** — Added `custom_pair_params` for dictionary-based overrides (v0.25.0).
- [x] **Migrate hyperopt to Docker CI** — done in v0.23.0 (matches backtest.yml pattern)
- [x] **Fix CI installation of smartmoneyconcepts** — changed to install numba and ignore deps
- [x] **Time exits hyperoptimization** — implemented in v0.24.0
- [x] **ATR-based dynamic SL** — implemented in v0.22.0
- [x] **OTE filter tightened to 30-70%** — done in v0.23.0 (was 20-90%, now clean Fib zone)
- [x] **v0.26.0: Decouple sweep from confirmation** — Fixed same-candle logic bug. 5-candle rolling sweep window + ChoCH signal. CI running.
- [x] **Analyze v0.26.0 backtest results** — 129 trades, 21.7% WR, -26.66%. Root cause: HTF trend dead variable (see v0.27.0).
- [x] **Analyze v0.27.0 backtest results** — 128 trades, 21.1% WR, -27.03%. Identical to v0.26.0. HTF trend filter ineffective in 2024-2026 bull period. Root cause: entry quality (imbalance magnets).
- [x] **Analyze v0.28.0 backtest results** — ❌ 0 trades. FVG zone detection bug. Fixed in v0.29.0.
- [x] **Analyze v0.29.0 backtest results** — 99 trades, 24.2% WR, -19.16%. Improvement over v0.27.0 (+3.1% WR, +7.87% profit). TSL exits reduced 55→36. Still not profitable. Root cause: avg win +0.57% vs avg loss -1.61% = terrible R:R. Fixed in v0.30.0.
- [x] **Analyze v0.30.0 backtest results** — ❌ 0 trades. OB zone detection bug (same class as v0.28.0). Fixed in v0.31.0.
- [ ] **Analyze v0.31.0 backtest results** — expect 40-80 trades. OB recency check (20-candle rolling window). WR target 30-45%. With wider ROI from v0.30.0, avg win should approach 1.5%+.

---

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| SMC Library (v0.21) | Drops hand-rolled code for battle-tested ICT concepts |
| Time exit (v0.20) | Cutting stale trades at 4h instead of waiting 12h for break-even |
| Trailing stop (v0.20) | Lock in +0.8% after +1.5% profit avoids winners turning into losers |
| OTE disabled (v0.19) | Doubles trade volume without significantly hurting WR |
| Custom stoploss disabled (v0.18) | Was creating trailing effect via updating swing levels |
| Static SL only | Simplest approach after trailing/custom SL issues in v0.15-0.18 |
| 3x leverage | Conservative for swing trades; avoids liquidation on 4% SL |
| Spot mode | Safer than futures; no funding rate drag |

---

## Session Log

| Date | Version | What Changed |
|------|---------|--------------|
| 2026-02-08 | 0.1-0.9 | Initial strategy build through hyperopt optimization |
| 2026-02-12 | 0.10 | Testing looser entry (optional OTE); 811 trades but -62% profit |
| 2026-02-13 | 0.10 | Decided to re-introduce OTE filter |
| 2026-02-19 | 0.15-0.17 | Custom SL fixes, trailing stop experiments |
| 2026-02-20 | 0.18-0.19 | Disabled custom SL + trailing, tightened static SL to -4%, disabled OTE |
| 2026-02-23 | 0.20.0 | **Tighten risk**: SL → -2.5%, time exit 4h, trailing after +1%, drop LINK. Result: 430 trades, Win Rate dropped to 43.0% (-8.2%), Profit -38.2% (+2.5%), DD 38.2% (better). Time exits caught losers early but hurt win rate. |
| 2026-02-23 | 0.21.0 | **SMC Refactor**: Replaced hand-rolled indicators with `smartmoneyconcepts` library. Added OB confluence, FVG mitigation tracking. |
| 2026-02-26 | 0.22.0 | **ATR dynamic SL**: Replaced fixed -2.5% SL with 1.5x ATR(14). Floor -1.5%, ceiling -4.0%. Re-enabled OTE filter (loose 20-90%). CI triggered on push. |
| 2026-02-26 | 0.23.0 | **Docker CI + OTE 30-70%**: Migrated hyperopt from pip-based to Docker (freqtradeorg/freqtrade:stable) to fix silent failures. Tightened OTE from 20-90% to 30-70% (cleaner Fib retracement zone). Hyperopt now manual-only via workflow_dispatch. |
| 2026-02-26 | 0.24.0 | **Hyperoptable Time Exits**: Migrated hardcoded 4h/6h time-based exits into tuning `sell` parameters so hyperopt can find the optimal stale-trade cutoff thresholds. |
| 2026-02-27 | 0.24.0 | **Time Exit Optimization**: Replaced fixed 4h and 6h time exits with hyperoptable integer and decimal parameters within `sell` space, letting the optimizer determine best parameters for duration and profitability threshold. |
| 2026-02-27 | 0.25.0 | **Per-pair overrides**: Implemented a dictionary-based `custom_pair_params` configuration to override strategy parameters (like `atr_multiplier` and `require_ote`) explicitly per pair (e.g., BTC vs. ADA) to address highly variable win-rates. |
| 2026-02-27 | 0.26.0 | **Decouple sweep from ChoCH**: Fixed core logic bug from v0.21.0 — sweep + structure break were required on the *same candle*, which killed trade volume. Now: `recent_sweep_high/low` tracks sweeps over last 5 candles (1h15m window), and entry fires when a proper ChoCH follows. Matches real ICT/SMC logic. |
| 2026-02-28 | 0.27.0 | **Restore HTF trend alignment**: Found critical dead-variable bug — `htf_trend_col` was declared in `populate_entry_trend` but never used in filter conditions. Result: entries fired against 1H trend, causing 55/129 trades to trail-stop immediately (avg -1.58%, 1h04m). Fix: longs now require `trend_1h == 1`, shorts require `trend_1h == -1`. |
| 2026-02-28 | 0.28.0 | **FVG confluence + opposite-side imbalance filter**: v0.27.0 results identical to v0.26.0 — HTF trend filter had no impact (2024-2026 is heavily bullish, most entries were already long-aligned). Root cause of 55 TSL exits is ENTRY QUALITY: price attracted to unmitigated FVGs beyond SL. Fix: (1) `require_fvg=True` — only enter inside active unmitigated FVG zone; (2) Opposite-side imbalance check — skip if bearish FVG below long SL or bullish FVG above short SL; (3) `min_rr` raised to 1.5. **RESULT: 0 trades — FVG zone detection bug.** |
| 2026-02-28 | 0.29.0 | **Fix FVG zone detection bug**: v0.28.0 `active_bullish_fvg` was always False because `ffill()` was applied to a boolean series (not NaN series). Fix: forward-fill FVG zone top/bottom levels, then check `close >= fvg_bottom AND close <= fvg_top`. Correctly detects "price is inside an active FVG zone." `require_fvg` default changed to False — opposite-side imbalance is primary gate. CI running. |
| 2026-02-28 | 0.29.0 results | **99 trades, 24.2% WR, -19.16%**: TSL exits reduced 55→36 (imbalance filter worked). Still losing due to poor R:R (avg win +0.57% vs avg TSL loss -1.61%). Fixed in v0.30.0. |
| 2026-02-28 | 0.30.0 | **Mandatory OB confluence + wider ROI targets**: Two-pronged fix: (1) `require_ob=True` — only enter inside active Order Block zone (institutional demand/supply); expected WR 35-50%. (2) ROI widened (5%/3.5%/2%/1.2%/0.5%) to push avg win from 0.57% to 1.5%+. CI triggered on push. **RESULT: 0 trades — OB zone detection bug (exact price-in-box never true).** |
| 2026-02-28 | 0.31.0 | **Fix OB detection bug**: Replace `in_bullish_ob` (price inside narrow ffill box) with rolling(20).max() on ob==1/ob==-1. Checks "was a bullish/bearish OB formed in last 20 candles?" — correct SMC recency interpretation. OB box is the OB candle's body; price is rarely inside it at entry — the signal is that institutional money WAS present recently. Wider ROI from v0.30.0 retained. CI running. |
