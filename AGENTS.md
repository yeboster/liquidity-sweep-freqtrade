# AGENTS.md — Liquidity Sweep Freqtrade Strategy

> Read this first. Everything you need to operate this repo without onboarding.

## What This Is

A Freqtrade strategy implementing the **Liquidity Sweep Reversal** pattern.
- **Signal:** Price wicks above a swing high (sweeping buy-side liquidity) then closes below the triggering low → short entry.
- **Entry Refinement:** Optional FVG (Fair Value Gap) limit order for better fill.
- **Timeframe:** 15m entry, 1H/4H context.
- **Exchange:** OKX | **Pairs:** BTC/USDT, ETH/USDT, SOL/USDT, XRP/USDT, DOGE/USDT, ADA/USDT, AVAX/USDT, LINK/USDT, MATIC/USDT, DOT/USDT

## Current State

- **Latest Version:** v0.13.0
- **Status:** Negative profitability (-46%), 585 trades, 24.6% win rate
- **Next Hypothesis:** Re-introduce OTE filter (30-70%), migrate hyperopt to Docker CI
- **Iteration Log:** `iteration_log.md` — full history of every change and result

## Key Files

| File | Purpose |
|------|---------|
| `LiquiditySweep.json` | Latest hyperopt parameters |
| `LiquiditySweep_optimized.json` | Best known optimized params |
| `config.json` | Freqtrade config (OKX, pairs, stake) |
| `iteration_log.md` | Full version history with results |
| `backtest_results/` | Backtest output files |
| `hyperopt_results/` | Hyperopt output |

## Common Commands

```bash
# Backtest
freqtrade backtesting --strategy LiquiditySweep --config config.json --timerange 20230101-20241231

# Hyperopt
freqtrade hyperopt --strategy LiquiditySweep --config config.json --hyperopt-loss SharpeHyperOptLoss --epochs 200

# Plot backtest result
freqtrade plot-dataframe --strategy LiquiditySweep --config config.json
```

## Strategy Parameters (v0.13.0)

- `pivot_lookback`: 3 (swing detection sensitivity)
- `ote_lower`: 0.20 (widened from 0.62 for more signals)
- `ote_upper`: 0.79
- `entry_refinement`: `market` (previously `limit_fvg_50`)
- `min_rr`: 0.7

## Iteration Workflow

1. Hypothesize a change
2. Update strategy file
3. Run backtest
4. Log result in `iteration_log.md` with version, changes, result
5. Commit with message: `"Strategy vX.Y.Z: <short description>"`
6. Push to origin

## Active Goals

- [ ] Re-introduce OTE filter at 30-70% (v0.14.0 hypothesis)
- [ ] Migrate hyperopt to Docker-based GitHub CI (fix silent failures)
- [ ] Install `smart-money-concepts` lib and test FVG-based signals
- [ ] Run FVG backtest vs v0.13.0 baseline
