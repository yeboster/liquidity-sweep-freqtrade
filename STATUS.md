# Liquidity Sweep — STATUS

## Current Version
**v0.65.0** — 2-year backtest confirmed stable, BUT trade frequency too low.

## Problem
35 trades / 2 years = ~17/year. Need 100-200/year.

## Next Action
**Run FF-2 backtest:** OTE 20-80%, no confirmation, no FVG, no imbalance.

## Changes for FF-2 (high-frequency)
| Parameter | Current | FF-2 |
|----------|---------|------|
| OTE zone | 30-70% | 20-80% |
| Confirmation candle | YES | NO |
| FVG filter | YES | NO |
| Imbalance filter | YES | NO |
| atr_offset_v2 | 2.0x | 2.0x |
| stoploss | -0.99% | -0.99% |

## Files
- `user_data/strategies/LiquiditySweep.py` — strategy code
- `config.json` — trading config
- `hyperopts/` — exit/opt hyperopt files
