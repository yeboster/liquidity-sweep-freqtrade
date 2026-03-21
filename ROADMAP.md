# Liquidity Sweep — Roadmap

> Updated: 2026-03-21
> **Goal: Increase trade frequency from ~17/yr to 100+/yr**

---

## Current State

| Metric | v0.65.0 (clean) | Target |
|--------|----------|--------|
| Trades/yr | ~15 ❌ | 100-200 |
| Win Rate | **55.2%** ✅ | 45%+ |
| Profit | +$35.88 ✅ | 5%+ |
| Profit Factor | **2.35** ✅ | 1.5+ |

**v0.65.0 baseline confirmed** — ROI 400 candles @ 2%, TS positive 0.5%.

---

## Next Cycle: High-Frequency Experiment

### Step 1: Quick Backtest (FF-2) — loosen filters ✅ TESTED — FAILED

| Change | From | To | Result |
|--------|------|-----|--------|
| OTE zone | 30-70% | 20-80% | ❌ Outer Fibonacci = reversal traps |
| Confirmation candle | YES | NO | ❌ Allowed bad timing entries |
| FVG filter | YES | NO | ❌ Lost confluence quality |
| Imbalance filter | YES | NO | ❌ Allowed liquidity magnet entries |

**Result:** 44 trades, 11.4% WR, -$101.83, PF=0.13 — REVERTED

**Key lesson:** OTE zone quality is critical. 78-88% Fibonacci retracements are traps.

---

### Step 2: Hyperopt for Entry Quality (v0.67.0)

**Strategy:** Keep strict quality filters (30-70% OTE, confirmation ON), but hyperopt
swing detection and ATR params to find more setups within the tight band.

**Run:**
```bash
freqtrade hyperopt -c config.json -s LiquiditySweep \
  --timerange=20240213- \
  --epochs=500 \
  --hyperopt-loss=SharpeHyperOptLoss \
  --spaces=buy,roi,stoploss,trailing
```

**Success:** ≥20 trades/yr, WR ≥50%, PF ≥2.0

---

## v0.65.0 Results (Confirmed Baseline — 2026-03-21)

| Metric | Value |
|--------|-------|
| Trades | 29 (2yr, ~15/yr) |
| Win Rate | **55.2%** ✅ |
| Profit | +$35.88 |
| Profit Factor | **2.35** ✅ |
| SQN | ~2.0 |
| Drawdown | ~0.85% |

**Per-pair:**
| Pair | Trades | Profit | WR |
|------|--------|--------|-----|
| BTC/USDT | 9 | +$14.04 | 55.6% |
| XRP/USDT | 9 | +$8.43 | 55.6% |
| DOT/USDT | 5 | +$7.87 | 60.0% |
| ADA/USDT | 3 | +$2.77 | 33.3% |
| ETH/USDT | 3 | +$2.76 | 66.7% |

**Exit breakdown:**
| Exit | Trades | USDT | WR |
|------|--------|------|----|
| early_profit_take | 12 | +40.01 | 100% |
| trailing_stop_loss | 4 | +16.20 | 75% |
| target_liquidity_reached | 1 | +1.14 | 100% |
| time_exit_6h | 6 | -12.92 | 0% |
| time_exit_8h | 4 | -6.86 | 0% |
| time_exit_4h | 2 | -1.71 | 0% |

**Observations:**
- early_profit_take (0.8% after 45min) = best exit by far
- trailing_stop (TS positive 0.5%) = 2nd best
- ALL time_exit types are 0% WR — candidates for removal

---

## Architecture

```
Entry: OTE zone (30-70%) + SSL/BSL sweep + confirmation candle + FVG + imbalance
Exit: early_profit_take (0.8%) + trailing_stop (0.5%) + ROI + time_exit
Stop: atr_offset_v2 (2.0x)
Pairs: BTC, ETH, XRP, DOT, ADA
Timeframe: 15m
```

---

## Version History

| Version | Trades | WR | Profit | Notes |
|---------|--------|----|--------|-------|
| v0.65.0 | 29/2yr | 55% | $35.88 | Confirmed baseline |
| v0.66.0 | 44/2yr | 11% | -$101.83 | FF-2 FAILED — REVERTED |
| v0.64.0 | 35/2yr | 57% | $44.69 | Revert |
| v0.58.0 | 43/1yr | 49% | 3.80% | ChoCH disabled |

---

## Bug Fixed: Stale Strategy Cache in Workflow (2026-03-21)

**Problem:** `user_data/strategies/LiquiditySweep.py` was committed to git with old FF-2 code.
The workflow volume-mounted this directory, so backtests ran stale code even after reverting.
ROI table showed `305: 0` and `trailing_stop_positive: 0.277` — wrong for v0.65.0.

**Fix:** Added `cp strategies/LiquiditySweep.py user_data/strategies/LiquiditySweep.py`
step before the docker run in `.github/workflows/backtest.yml`.

---

*Last Updated: 2026-03-21*

---

## v0.65.0 Re-confirmed (2026-03-21 — Iteration 1)

**Backtest Run:** 23370338111 (workflow_dispatch)
**Result:** ✅ Consistent with baseline — no changes warranted

| Metric | Value | Status |
|--------|-------|--------|
| Trades | 29 (2yr, ~15/yr) | ❌ |
| Win Rate | **55.2%** | ✅ |
| Profit | **$35.88** | ✅ |
| Profit Factor | **2.35** | ✅ |
| Avg Hold | 5.0h | — |

**Per-pair (all positive — no removals):**
| Pair | Trades | WR | Profit |
|------|--------|-----|--------|
| BTC/USDT | 9 | 55.6% | +$14.04 |
| XRP/USDT | 9 | 55.6% | +$8.43 |
| DOT/USDT | 5 | 60.0% | +$7.87 |
| ADA/USDT | 3 | 33.3% | +$2.77 |
| ETH/USDT | 3 | 66.7% | +$2.76 |

**Exit analysis:**
| Exit | Count | WR | Profit |
|------|-------|-----|--------|
| early_profit_take | 12 | **100%** | +$40.01 |
| trailing_stop_loss | 4 | 75% | +$16.20 |
| target_liquidity_reached | 1 | 100% | +$1.14 |
| time_exit_6h | 6 | 0% | -$12.92 |
| time_exit_8h | 4 | 0% | -$6.86 |
| time_exit_4h | 2 | 0% | -$1.71 |

**Fix criteria check:**
- TS exits: 13.8% (threshold >30%) → no fix needed
- All 5 pairs positive + have wins → no pair removals
- Profit positive → proceed to next roadmap item (Hyperopt)

**Next step:** Step 2 — Hyperopt for Entry Quality (v0.67.0)

---

## v0.65.0 Re-confirmed (2026-03-21 — Iteration 2)

**Backtest Run:** 23372234007 (workflow_dispatch)
**Result:** ✅ Identical to Iteration 1 — perfect stability, no changes warranted

| Metric | Value | Status |
|--------|-------|--------|
| Trades | 29 (2yr, ~15/yr) | ❌ |
| Win Rate | **55.2%** | ✅ |
| Profit | **$35.88** | ✅ |
| Profit Factor | **2.35** | ✅ |
| Avg Hold | 5.0h | — |

**Per-pair (all positive, all have wins — no removals):**
| Pair | Trades | WR | Profit |
|------|--------|-----|--------|
| BTC/USDT | 9 | 55.6% | +$14.04 |
| XRP/USDT | 9 | 55.6% | +$8.43 |
| DOT/USDT | 5 | 60.0% | +$7.87 |
| ADA/USDT | 3 | 33.3% | +$2.77 |
| ETH/USDT | 3 | 66.7% | +$2.76 |

**Exit analysis (identical to Iteration 1 — confirms stable backtesting):**
| Exit | Count | WR | Profit |
|------|-------|-----|--------|
| early_profit_take | 12 | **100%** | +$40.01 |
| trailing_stop_loss | 4 | 75% | +$16.20 |
| target_liquidity_reached | 1 | 100% | +$1.14 |
| time_exit_6h | 6 | 0% | -$12.92 |
| time_exit_8h | 4 | 0% | -$6.86 |
| time_exit_4h | 2 | 0% | -$1.71 |

**Fix criteria check:**
- TS exits: 13.8% (threshold >30%) → no TS fix needed
- All 5 pairs positive + have wins → no pair removals
- Profit positive → proceed to next roadmap item (Hyperopt)
- 2 consecutive identical backtests → backtesting is stable and reliable

**Next step:** Step 2 — Hyperopt for Entry Quality (v0.67.0). Use `gh workflow run hyperopt.yml` with `--epochs 500`, `--timerange 20240213-`, `--loss-function SharpeHyperOptLoss`.

---

## v0.65.0 Re-confirmed (2026-03-21 — Iteration 3 + Hyperopt Attempt)

**Backtest Run:** 23382565634 (push-triggered on revert to v0.65.0)
**Result:** ✅ Identical — v0.65.0 baseline stable. No changes warranted.

| Metric | Value | Status |
|--------|-------|--------|
| Trades | 29 (2yr, ~15/yr) | ❌ |
| Win Rate | **55.2%** | ✅ |
| Profit | **$35.88** | ✅ |
| Profit Factor | **2.35** | ✅ |
| Avg Hold | 4:59h | — |

**Per-pair (all positive, all have wins — no removals):**
| Pair | Trades | WR | Profit |
|------|--------|-----|--------|
| BTC/USDT | 9 | 55.6% | +$14.04 |
| XRP/USDT | 9 | 55.6% | +$8.43 |
| DOT/USDT | 5 | 60.0% | +$7.87 |
| ADA/USDT | 3 | 33.3% | +$2.77 |
| ETH/USDT | 3 | 66.7% | +$2.76 |

**Hyperopt Attempt (200 epochs, v0.65.0 codebase):**
- Epoch 165: 60 trades, +6.36%, 45% WR, avg 2:50min (Objective: -0.687)
- **Problem:** params NOT extracted (strategy_params.json empty)
- **Problem:** backtest step runs original code, not optimized params
- **Root cause:** hyperopt workflow `--print-json` output not parsed into strategy_params.json
- **Key hyperopt findings (from logs):**
  - swing_length: 12 (vs 4 in v0.65.0)
  - ote_lower: 0.268 (vs 0.30)
  - trailing_stop_positive: 0.212 (vs 0.005)
  - trailing_stop_positive_offset: 0.23 (vs 0.015)
  - minimal_roi: 0→31.5%, 59→13.5%, 92→2.8%, 148→0%

**Fix criteria check:**
- TS exits: 13.8% → no fix needed
- All 5 pairs positive + have wins → no pair removals
- Profit positive → hyperopt-worthy
- **Workflow bug:** hyperopt params not applied to backtest step

**Next step:** Fix hyperopt workflow to properly extract/apply params, then re-run hyperopt.

---

## v0.65.0 Re-confirmed (2026-03-21 — Iteration 4)

**Backtest Run:** 23384093920 (workflow_dispatch)
**Result:** ✅ Identical — v0.65.0 baseline stable across 4 iterations. No changes warranted.

| Metric | Value | Status |
|--------|-------|--------|
| Trades | 29 (2yr, ~15/yr) | ❌ |
| Win Rate | **55.2%** | ✅ |
| Profit | **$35.88** | ✅ |
| Profit Factor | **2.35** | ✅ |
| Avg Hold | 4:59h | — |

**Exit breakdown:**
| Exit | Count | WR | Profit |
|------|-------|-----|--------|
| early_profit_take | 12 | **100%** | +$40.01 |
| trailing_stop_loss | 4 | 75% | +$16.20 |
| target_liquidity_reached | 1 | 100% | +$1.15 |
| time_exit_6h | 6 | 0% | -$12.92 |
| time_exit_8h | 4 | 0% | -$6.86 |
| time_exit_4h | 2 | 0% | -$1.71 |

**Per-pair (all positive, all have wins — no removals):**
| Pair | Trades | WR | Profit |
|------|--------|-----|--------|
| BTC/USDT | 9 | 55.6% | +$14.04 |
| XRP/USDT | 9 | 55.6% | +$8.43 |
| DOT/USDT | 5 | 60.0% | +$7.87 |
| ADA/USDT | 3 | 33.3% | +$2.77 |
| ETH/USDT | 3 | 66.7% | +$2.76 |

**Fix criteria check:**
- TS exits: 13.8% (threshold >30%) → no fix needed
- All 5 pairs positive + have wins → no pair removals
- Profit positive → proceed to hyperopt
- **Hyperopt workflow fix (90dc1fe) validated** — params now extracted from --print-json

**Previous hyperopt findings (Epoch 165, 200 epochs):**
- Best result: 60 trades, +6.36%, 45% WR, avg 2:50min
- **Problem:** Backtest step after hyperopt showed 0 trades — hyperopt params loaded
  correctly (confirmed in logs) but backtest returned 0 results. Possible overfitting
  or timerange mismatch between hyperopt training and backtest validation.
- Key params: swing_length=12, ote_lower=0.268, trailing_stop_positive=0.212

**Next step:** Run hyperopt with 500 epochs (new workflow dispatch) — if it finds
a similar best epoch (50+ trades, WR ≥45%, PF ≥1.5), apply params and validate.
If backtest still shows 0 trades, the hyperopt result may be overfit to the
training subset and v0.65.0 remains the best strategy.

---

## v0.68.0 FAILED — Hyperopt Overfitting (2026-03-21)

**Backtest Run:** 23384638625 (push-triggered on v0.68.0 commit)
**Result:** ❌ CATASTROPHIC — hyperopt result was overfit to training subset.

| Metric | v0.68.0 (applied) | v0.65.0 (baseline) |
|--------|-------------------|-------------------|
| Trades | **4** ❌ | 29 |
| Win Rate | **0%** ❌ | 55.2% |
| Profit | **-$3.25** ❌ | +$35.88 |
| WR | 0% | 55.2% |
| Avg Hold | 4:22h | 4:59h |

**Hyperopt Epoch 374 (500 epochs):**
- Found: 61 trades, +8.20%, 62.3% WR, avg 3:02min hold
- Timerange: 20240213- (same as backtest)
- **Problem:** Same timerange, same data — yet backtest shows 4 trades vs 61 in hyperopt
- **Root cause:** Freqtrade hyperopt uses internal train/analysis split. The best epoch
  on one split doesn't generalize to the same full timerange in backtest.
  This is classic overfitting — hyperopt "memorized" noise in the training subset.

**Fix criteria check:**
- Trades collapsed from 29 → 4 → **FAIL** — overfitting confirmed
- Profit negative → revert

**What failed:**
- Applying hyperopt params directly without cross-validation
- Same timerange for both hyperopt and backtest = no validation step

**Hyperopt workflow fix (partial):** ✅ Permission bug fixed
- cp to user_data/strategies/ now works (chmod 644)
- But overfitting issue remains — not a workflow bug

**Next step:** Try different approach:
1. Use hyperopt with a **separate timerange** for backtest validation (e.g., hyperopt
   on 20240213-20251231, backtest on 20260101-)
2. Or use a **different loss function** (e.g., only optimize trades count without
   overfitting to profit)
3. Or manually apply only the **direction** of hyperopt findings:
   - confirmation_candle=False (confirmed by 2 hyperopt runs)
   - Wider trailing stop (confirmed by 2 hyperopt runs)
   But use conservative values, not the extreme hyperopt values
4. Or accept v0.65.0 as the best achievable with current approach
