# Liquidity Sweep — Roadmap

> Updated: 2026-03-20
> **Goal: Increase trade frequency from ~17/yr to 100+/yr**

---

## Current State

| Metric | v0.65.0 | Target |
|--------|----------|--------|
| Trades/yr | **~17** ❌ | 100-200 |
| Win Rate | 57.1% ✅ | 45%+ |
| Profit | 4.68% ⚠️ | 5%+ |
| Profit Factor | 2.43 ✅ | 1.5+ |

**Problem:** 35 trades / 2 years = 1 every 3 weeks. Too sparse for a mean reversion strategy on 15m TF.

---

## Next Cycle: High-Frequency Experiment

### Step 1: Quick Backtest (FF-2) — loosen filters

**Goal:** Measure trade count jump from removing blocking filters.

| Change | From | To |
|--------|------|-----|
| OTE zone | 30-70% | 20-80% |
| Confirmation candle | YES | NO |
| FVG filter | YES | NO |
| Imbalance filter | YES | NO |

**Run:**
```bash
freqtrade backtesting -c config.json -s LiquiditySweep --timerange=20240321-20260320
```

**Success:** ≥40 trades/yr with WR ≥45%, PF ≥1.5

---

### Step 2: If FF-2 passes — tighten risk (FF-3)

| Change | From | To |
|--------|------|-----|
| ATR stop offset | 2.0x | 1.5x |
| OTE zone | 20-80% | 10-90% |
| Stoploss | -0.99% | -1.5% |

**Run:** Same timerange
**Success:** ≥60 trades/yr, WR ≥45%, PF ≥1.5

---

### Step 3: Hyperopt for optimal params

**If FF-2 or FF-3 shows improvement:**
```bash
freqtrade hyperopt -c config.json -s LiquiditySweep \
  --timerange=20240321-20260320 \
  --epochs=300 \
  --hyperopt-loss=SharpeHyperOptLoss \
  --spaces=buy,roi,stoploss,trailing
```

**Goal:** Find globally optimal params for high-frequency regime.

---

## v0.65.0 Results (Reference)

| Metric | Value |
|--------|-------|
| Trades | 35 (2yr) |
| Win Rate | 57.1% |
| Profit | +$46.80 |
| Profit Factor | 2.43 |
| SQN | 2.10 |
| Drawdown | 0.85% |

**Exit breakdown:**
| Exit | Trades | USDT | WR |
|------|--------|------|----|
| early_profit_take | 14 | +46.18 | 100% |
| trailing_stop_loss | 7 | +22.17 | 71% |
| time_exit_6h | 7 | -14.12 | 0% |
| time_exit_8h | 4 | -6.87 | 0% |
| time_exit_4h | 2 | -1.71 | 0% |

---

## Architecture

```
Entry: OTE zone + SSL/BSL sweep + confirmation candle + FVG + imbalance
Exit: early_profit_take (0.8%) + trailing_stop + ROI + time_exit
Stop: atr_offset_v2 (2.0x)
Pairs: BTC, DOGE, DOT, XRP, ETH, ADA
Timeframe: 15m
```

---

## Version History

| Version | Trades | WR | Profit | Notes |
|---------|--------|----|--------|-------|
| v0.65.0 | 35/2yr | 57% | $46.80 | Current |
| v0.64.0 | 35/2yr | 57% | $44.69 | Revert |
| v0.62.0 | 35/2yr | 57% | $46.80 | ATH |
| v0.58.0 | 43/1yr | 49% | 3.80% | ChoCH disabled |

---

*Last Updated: 2026-03-20*
