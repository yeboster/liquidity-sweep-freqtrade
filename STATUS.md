# Liquidity Sweep Freqtrade — STATUS.md

> Single source of truth for project state, open items, and decisions.

---

## Current State

- **Version:** 0.25.0 (Per-pair parameter dictionary overrides)
- **Status:** Implementing dictionary-based parameter overrides for pair-specific logic (BTC vs ADA volatility).
- **Branch:** `main`

---

## Latest Backtest Results (v0.20.0)

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
