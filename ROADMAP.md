# Liquidity Sweep — Roadmap

> Updated: 2026-03-21
> **Goal: Increase trade frequency from ~17/yr to 100+/yr**

---

## Current State

| Metric | v0.65.0 | v0.66.0 (FF-2) | Target |
|--------|----------|----------------|--------|
| Trades/yr | ~17 ❌ | ~22 ⚠️ | 100-200 |
| Win Rate | 57.1% ✅ | **11.4% ❌** | 45%+ |
| Profit | +$46.80 ✅ | **-$101.83 ❌** | 5%+ |
| Profit Factor | 2.43 ✅ | **0.13 ❌** | 1.5+ |

**v0.66.0 FF-2 VERDICT: FAILED ❌**
- Trades jumped 17→22/yr (+29%) but quality collapsed
- WR crashed from 57% → 11% — TSL went from 71% WR to **0% WR** (19 trades, -92 USDT)
- Root cause: Loosening OTE to 20-80% captures setups at outer Fibonacci zones (78-88%) which have low reversal probability
- **Action:** Reverted to v0.65.0. FF-2 is dead.

---

## Next Cycle: High-Frequency Experiment

### Step 1: Quick Backtest (FF-2) — loosen filters ✅ TESTED — FAILED

| Change | From | To | Result |
|--------|------|-----|--------|
| OTE zone | 30-70% | 20-80% | ❌ Entries at outer Fibonacci = bad |
| Confirmation candle | YES | NO | ❌ Allowed bad timing entries |
| FVG filter | YES | NO | ❌ Lost confluence quality |
| Imbalance filter | YES | NO | ❌ Allowed liquidity magnet entries |

**Result:** 44 trades, 11.4% WR, -$101.83, PF=0.13 — REVERTED

---

### Step 2: Hyperopt + Targeted Entry Refinement (v0.67.0)

**Strategy:** Instead of wholesale loosening, use hyperopt to find optimal entry parameters
within the current strict framework (30-70% OTE, confirmation candle ON).

**Changes to test:**
1. Keep all current quality filters ON
2. Use hyperopt to optimize: `swing_length`, `htf_swing_length`, `ote_lower`, `ote_upper`, `atr_multiplier`, `min_rr`
3. Goal: More trades WITHOUT sacrificing WR (find sweet spot in param space)

**Run:**
```bash
freqtrade hyperopt -c config.json -s LiquiditySweep \
  --timerange=20240321-20260320 \
  --epochs=500 \
  --hyperopt-loss=SharpeHyperOptLoss \
  --spaces=buy,roi,stoploss,trailing
```

**Success:** ≥25 trades/yr, WR ≥50%, PF ≥2.0

---

### Step 3: Weekend Filter Toggle (per-pair)

**Observation:** Weekend entries (Fri night/Sat) may be lower quality due to thin liquidity.
Test disabling weekend filter only for pairs that show weekend profitability.

---

## v0.65.0 Results (Reference / Best)

| Metric | Value |
|--------|-------|
| Trades | 35 (2yr) |
| Win Rate | 57.1% ✅ |
| Profit | +$46.80 |
| Profit Factor | 2.43 ✅ |
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

## v0.66.0 FF-2 Results (FAILED — REVERTED)

| Metric | Value |
|--------|-------|
| Trades | 44 (2yr, ~22/yr) |
| Win Rate | **11.4% ❌** |
| Profit | **-$101.83 ❌** |
| Profit Factor | **0.13 ❌** |
| SQN | -5.42 |

**Exit breakdown:**
| Exit | Trades | USDT | WR |
|------|--------|------|----|
| trailing_stop_loss | 19 | -92.26 | **0%** |
| exit_signal | 5 | -10.22 | 0% |
| time_exit_4h | 7 | -8.77 | 0% |
| time_exit_6h | 5 | -5.97 | 0% |
| roi | 7 | +15.37 | 57% |

**Key lesson:** OTE zone quality is critical. 78-88% Fibonacci retracements are traps.

---

## Architecture

```
Entry: OTE zone (30-70%) + SSL/BSL sweep + confirmation candle + FVG + imbalance
Exit: early_profit_take (0.8%) + trailing_stop + ROI + time_exit
Stop: atr_offset_v2 (2.0x)
Pairs: BTC, DOGE, DOT, XRP, ETH, ADA
Timeframe: 15m
```

---

## Version History

| Version | Trades | WR | Profit | Notes |
|---------|--------|----|--------|-------|
| v0.66.0 | 44/2yr | 11% | -$101.83 | FF-2 FAILED — REVERTED |
| v0.65.0 | 35/2yr | 57% | $46.80 | Current (reverted to) |
| v0.64.0 | 35/2yr | 57% | $44.69 | Revert |
| v0.62.0 | 35/2yr | 57% | $46.80 | ATH |
| v0.58.0 | 43/1yr | 49% | 3.80% | ChoCH disabled |

---

*Last Updated: 2026-03-21*
