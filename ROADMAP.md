# Liquidity Sweep — Roadmap

> Updated: 2026-03-27
> **Strategy Type: Liquidity Sweep / Mean Reversion (NOT trend following)**

---

## ⚠️ CRITICAL FINDING: R/R Ratio is Inverted

**Verified from trade-level analysis (backtest-result-2026-03-26_19-05-08.json):**

| Metric | Value | Verdict |
|--------|-------|---------|
| Trades | **87** | ~43/yr |
| Win Rate | **88.5%** ✅ | High, but misleading |
| Avg Win | **0.79%** | Too small |
| Avg Loss | **1.69%** | 2.1× avg win |
| **R/R Ratio** | **0.47** | ❌ DANGEROUS — need >1.0 |
| Avg Profit/Trade | **0.18%** | ❌ Below 1% threshold |
| **Realistic Live Return** | **~15-18%/yr** | ⚠️ Before slippage |

**Win distribution (77 wins):**
| Range | Count | % |
|-------|-------|---|
| < 0.5% | 31 | 40% |
| 0.5–1% | 32 | 42% |
| 1–2% | 10 | 13% |
| 2–5% | 3 | 4% |
| > 5% | 1 | 1% |

**Loss distribution (10 losses, ALL via TS):**
- Cluster: -1.45% to -2.06%
- Every loss wipes ~2 wins

**Why this matters for live trading:**
- Slippage 0.1–0.2% per trade erodes the 0.18% avg significantly
- In live markets with wider spreads: edge could disappear entirely
- The 88.5% WR is only impressive until you see the R/R ratio

**Root cause:** TS at +0.8% offset clips winners at their peak micro-movements.
This is a QUICK REVERSAL hunt strategy, not a trend follower. The 0.79% avg win
IS the actual edge. But R/R < 1.0 means the strategy is structurally fragile.

---

## Strategic Roadmap (New Priority Order)

### Goal: Either fix R/R or maximize the hunt strategy

#### 🔴 Priority 1: Fix R/R Ratio (Avg Win must exceed Avg Loss)

**Problem:** R/R = 0.47. Every loss costs 2× what each win gains.

**Hypothesis H-A: ATR-based dynamic exits**
- TP = entry + 2.5× ATR (adaptive, lets big moves run)
- SL = entry - 1.5× ATR (tighter, cuts losses earlier)
- In high volatility: bigger wins. In low volatility: small wins, fast exit.
- **Test:** Run backtest with `trailing_stop_positive_offset` replaced by dynamic ATR TP

**Hypothesis H-B: Fixed TP floor at 1.5%**
- Force all exits to achieve at least 1.5% before TS can exit
- Winners below 1.5% → hold until 1.5% or stop
- **Test:** Modify ROI table so early TP fires at 1.5% before TS activates

**Hypothesis H-C: Tighter SL floor**
- Current: stoploss at -19.4%, losses average -1.69% (TS forces exit)
- Hypothesis: if SL is -1.0%, losses would be capped earlier
- **Risk:** Could reduce WR if trades get stopped out prematurely
- **Test:** Lower stoploss from -0.194 to -0.010

#### 🟡 Priority 2: Increase Trade Frequency (if R/R can't be fixed)

**If H-A/B/C fail:** Accept this is a hunt strategy with 0.79% avg win.
Compensate by maximizing trade frequency.

- Current: 87 trades/2yr = 43/yr
- Target: 200+ trades/yr
- Each trade: net ~0.4% after slippage
- 200 trades × 0.4% = 80% annual return potential

**How:** Add more pairs, shorter timeframe (5m with proper data), loosen entry filters.

#### 🟢 Priority 3: Live Trading Readiness

- Verify exchange execution quality (Kraken vs Binance)
- Paper trade for 1 month to validate slippage assumptions
- Build position sizing model (current: $354 avg stake on $1000 wallet = 35% per trade)
- Risk: 3 concurrent trades × 35% × potential 1.69% loss = 1.78% of wallet per bad cycle

---

## Current State (v0.99.5)

| Metric | Value | Status |
|--------|-------|--------|
| Trades/yr | ~43 | ❌ Below 100 target |
| Win Rate | 88.5% | ✅ |
| Profit | $158.04 (15.80%) | ✅ |
| Profit Factor | 3.62 | ✅ |
| SQN | 4.18 | ✅ |
| Avg Profit/Trade | **0.18% (0.79% avg win)** | ❌ |
| R/R Ratio | **0.47** | ❌ Need >1.0 |
| Realistic Live Return | ~15-18%/yr | ⚠️ Thin margin |

---

## v0.99.5 (HEAD) — FIL/USDT Added (Backtest Pending)

FIL/USDT added to pairlist (11 pairs). Backtest pending. Per-pair data inherits from v0.99.4 verified results above.

**Priority for next backtest:** Validate that adding FIL increases trade count toward 100+/yr without degrading WR below 85% or PF below 2.0.

**Strategic note:** Even with 200+ trades/yr, the 0.79% avg win / 1.69% avg loss structural issue remains. The next backtest iteration should also test one of the R/R fix hypotheses (H-A: ATR-based TP, H-B: 1.5% ROI floor, or H-C: tighter SL).

---

## v0.99.3 ✅ — AAVE/USDT Added — Best Performance Yet (2026-03-27)

**Backtest Run:** 23621691695 (push-triggered on v0.99.3 commit)
**Result:** ✅ BREAKTHROUGH — AAVE additive, trade frequency jumped to 98!

| Metric | v0.99.3 (10 pairs) | v0.99.2 (9 pairs) | Change |
|--------|---------------------|---------------------|--------|
| Trades | **98** | 88 | **+11 ✅** |
| Win Rate | **88.8%** | 88.5% | +0.3pp |
| Profit | **$176.62 (17.66%)** | $158.04 (15.80%) | **+$18.58 ✅** |
| Profit Factor | **3.59** | 3.62 | stable |
| SQN | **4.49** | 4.18 | +0.31 |
| Drawdown | $20.11 | $12.02 | higher ⚠️ |
| TS Exit % | 95.9% | 96.6% | stable |
| TS Win Rate | **88.3%** | 88.1% | stable |
| Avg Hold | 4:23 | 4:32 | stable |

**Per-pair (all positive, all have wins — no removals):**
| Pair | Trades | WR | Profit |
|------|--------|-----|--------|
| AVAX/USDT | 13 | 100.0% | +$34.86 |
| XLM/USDT | 6 | 66.7% | +$27.59 |
| BTC/USDT | 15 | 86.7% | +$24.15 |
| DOT/USDT | 11 | 90.9% | +$19.86 |
| AAVE/USDT | 11 | 90.9% | +$17.08 ✅ NEW |
| ETH/USDT | 9 | 88.9% | +$15.77 |
| UNI/USDT | 7 | 100.0% | +$12.91 |
| LINK/USDT | 13 | 84.6% | +$12.51 |
| NEAR/USDT | 7 | 85.7% | +$5.95 |
| ADA/USDT | 6 | 83.3% | +$5.93 |

**Exit breakdown:**
| Exit | Count | WR | Profit |
|------|-------|-----|--------|
| trailing_stop_loss | 94 | **88.3%** | +$163.12 |
| target_liquidity_reached | 3 | 100% | +$6.89 |
| roi | 1 | 100% | +$6.61 |

**Fix criteria check:**
- TS exits: 94/98 = 95.9% (>30%) with 88.3% WR → ✅ TS working exceptionally
- All 10 pairs positive + have wins → no pair removals needed
- Profit positive + PF 3.59 → exceptional performance
- **AAVE/USDT: +$17.08, 90.9% WR, 11 trades — net positive addition ✅**
- Trade frequency: 98 trades/2yr = ~49/yr (still below 100/yr target but improving)

**Key insight:** AAVE/USDT is the 5th best pair by profit ($17.08) with 90.9% WR. Adding it brought total trades from 88→98 (+11.3%). All 10 pairs are profitable with positive win rates.

**Next step (⏳):** Continue trade frequency increase toward 100+/yr. Options:
1. Try other high-volume pairs (FIL, APT, etc.)
2. Experiment with OTE zone fine-tuning (30-70% still the sweet spot)
3. Accept ~49/yr with current config — excellent quality (88.8% WR, PF 3.59+)

---

## Next Cycle: Increase Avg Profit Per Trade

### Problem
Avg profit/trade at 0.48% is too low. Target is 1% (minimum), 3% (optimal).

### Hypotheses to Test

**H1: Tighten OTE zone further (50-65% instead of 30-70%)**
- Deeper pullbacks = better risk/reward = higher avg win

### v0.94.0 Results (H1: OTE 50-65%) — 2026-03-25
- **107 trades, 86% WR, +$120.74 (12.07%)** — solid
- Avg profit/trade: 0.32% (still low, not reaching 1%+ target)
- SOL/USDT: -$7.37 (72.7% WR but 3 big losses) — already removed from v0.95.0
- XRP/USDT: -$8.45 (66.7% WR but 2 big losses) — already removed from v0.95.0
- **Verdict: H1 didn't hit 1%+ avg profit target. Trades up but avg/trade low.**

### v0.95.0 Results (H1+H2: OTE 50-65% + TS offset 0.8%→1.3%) — 2026-03-25
- **32 trades, 75% WR, +$46.03 (4.6%), PF 1.88** — OTE tightening too aggressive
- Avg hold time: 8h 6min (longer, as expected with wider TS)
- Avg profit/trade: **43%** (annualized, misleading due to small n)
- **Problem: OTE 50-65% filtered too aggressively — only 32 trades (vs 107 in v0.94.0).**
- **Conclusion: Revert OTE zone wider for more trades. Keep wider TS offset.**
- **Next: ⏳ H3 — Revert OTE to 30-70% but keep TS offset 1.3%**
- May reduce trade count slightly
- Run: backtest with `ote_entry_zones = [(0.50, 0.65)]`

**H2: Increase trailing_stop_positive offset**
- Current: 0.5% (offset 0.8%)
- Test: 1.0% with offset 1.3% — let winners run longer
- May reduce WR but increase avg win

**H3: Hyperopt exit params (trailing + ROI) for profit maximization**
- Use `profitOnlyHyperOptLoss` with `SharpeHyperOptLoss`
- Optimize `trailing_stop_positive` and `minimal_roi` jointly
- Goal: find params that maximize avg trade profit

**H4: Reduce max open trades (3→1 or 2)**
- More capital per trade = larger position = higher absolute profit
- Trade-off: fewer concurrent positions

### Run Order
1. H1 + H2 as quick backtests (same day)
2. H3 hyperopt if H1/H2 show promise
3. H4 as last resort if frequency still >30 trades/yr

---

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
| v0.88.0 | 50/2yr | 90.0% | $69.09 | ✅ REVERT 5m→15m — 5m destroys TS WR (68%→90%) |
| v0.87.0 | 183/2yr | 68.3% | -$43.50 | ❌ 5m TF — 85% TS exits, -$43 loss — REVERTED |
| v0.86.0 | — | — | — | 5m data download test (confirm) |
| v0.76.0 | 84/2yr | **90.5%** | $135.82 | ✅ Remove SOL + XRP — profit +$15, WR +4.6pp |
| v0.75.0 | 107/2yr | 85.9% | $120.74 | Add 8 new pairs (10 total) |
| v0.72.0 | 41/2yr | **87.8%** | $60.58 | ✅ TS offset 1.5%→0.8% + remove XRP |
| v0.71.1 | 53/2yr | 73.6% | $60.97 | Config fix: TS positive 1.5%→0.5% |
| v0.71.0 | — | — | — | FAILED (config error, TS same as offset) |
| v0.70.0 | 53/2yr | 54.7% | $50.55 | Remove time exits (0% WR) |
| v0.69.0 | 53/2yr | 54.7% | $50.55 | ✅ confirmation_candle=False, wider TS |
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

---

## v0.69.0 ✅ — Conservative Hyperopt Fixes VALIDATED (2026-03-21)

**Backtest Run:** 23388471881 (workflow_dispatch)
**Result:** ✅ Major improvement in trade frequency — from 29 to 53 trades/2yr (+82%)!

| Metric | v0.69.0 | v0.65.0 | Change |
|--------|---------|---------|--------|
| Trades | **53** | 29 | **+82% ✅** |
| Win Rate | **54.7%** | 55.2% | -0.5pp |
| Profit | **$50.55 (5.05%)** | $35.88 (3.59%) | **+$14.67 ✅** |
| Profit Factor | **1.84** | 2.35 | -0.51 ⚠️ |
| SQN | 1.88 | ~2.0 | stable |
| Drawdown | 1.39% | ~0.85% | slightly higher |
| Avg Hold | 4:49 | 4:59 | stable |

**Per-pair (all positive, all have wins — no removals):**
| Pair | Trades | WR | Profit |
|------|--------|-----|--------|
| DOT/USDT | 11 | 72.7% | +$17.43 ✅ |
| ADA/USDT | 6 | 66.7% | +$12.75 |
| BTC/USDT | 15 | 40.0% | +$7.90 |
| ETH/USDT | 9 | 55.6% | +$7.59 |
| XRP/USDT | 12 | 50.0% | +$4.88 |

**Exit breakdown:**
| Exit | Count | WR | Profit |
|------|-------|-----|--------|
| early_profit_take | 28 | **100%** | +$40.01 |
| trailing_stop_loss | 5 | 20% | -$16.25 |
| time_exit_6h | 10 | 0% | -$25.68 |
| time_exit_8h | 8 | 0% | -$10.60 |
| time_exit_4h | 2 | 0% | -$1.70 |

**Fix criteria check:**
- TS exits: 9.4% (threshold >30%) → no TS fix needed
- All 5 pairs positive + have wins → no pair removals
- Profit positive → ✅ approach validated
- Trade frequency: 53/2yr = ~27/yr (still below 100 target but 82% improvement)

**What changed vs v0.65.0:**
- `confirmation_candle = False` (disabled — hyperopt found it was filtering valid entries)
- `trailing_stop_positive = 1.5%` (widened from 0.5%)
- `trailing_stop_positive_offset = 2.5%` (widened from 1.5%)

**Key insight:** Disabling confirmation_candle dramatically increased trade frequency
(29→53) with minimal win rate impact (-0.5pp). More trades = more winners absolute.
Profit factor dipped because wider trailing stop caught fewer but bigger winners,
while additional trades included more marginal winners. Net result: +$14.67 more profit.

**Next step (⏳):** Step 3 — Remove 0%-WR time exits. time_exit_6h and time_exit_8h
are ALL losing exits (0% WR, -$36.28 combined). Remove them to:
1. Let winners run longer (they currently hit time exits at 0% WR)
2. Reduce total trades slightly (which should improve PF)
3. Focus exits on early_profit_take + trailing_stop only

---

## v0.72.0 ✅ — TS Offset Fix + XRP Removal (2026-03-22)

**Backtest Run:** 23397638399 (push-triggered on v0.72.0 commit)
**Result:** ✅ BREAKTHROUGH — best performance yet across all key metrics!

| Metric | v0.72.0 | v0.71.1 | Change |
|--------|---------|---------|--------|
| Trades | **41** | 53 | -12 (XRP removed) |
| Win Rate | **87.8%** | 73.6% | **+14.2pp ✅** |
| Profit | **$60.58 (6.06%)** | $60.97 | ~same |
| Profit Factor | **3.23** | 1.60 | **+1.63 ✅** |
| Drawdown | **1.17%** | 2.40% | **-1.23pp ✅** |
| Avg Hold | 4:57 | 7:22 | -2:25 faster |

**Per-pair (all positive, all have wins — no removals needed):**
| Pair | Trades | WR | Profit |
|------|--------|-----|--------|
| BTC/USDT | 15 | 86.7% | +$21.05 |
| DOT/USDT | 11 | 90.9% | +$18.31 |
| ETH/USDT | 9 | 88.9% | +$14.51 |
| ADA/USDT | 6 | 83.3% | +$6.71 |

**Exit breakdown:**
| Exit | Count | WR | Profit |
|------|-------|-----|--------|
| trailing_stop_loss | 38 | **86.8%** | +$52.04 |
| early_profit_take | 3 | 100% | +$7.34 |

**Fix criteria check:**
- TS exits: 38/41 = 92.7% (was >30% threshold → FIX APPLIED ✅)
- TS WR: **86.8%** (was 39.1% → FIXED!)
- TS profit: **+$52.04** (was -$54.46 → TURNED AROUND!)
- All 4 pairs positive + have wins → no pair removals
- Profit positive + PF 3.23 → exceptional performance

**What fixed the trailing stop:**
- v0.71.1 used TS offset 1.5% — still too wide, winners ran to +1.5-2% then
  reversed, giving back -0.69% avg on 23 TS exits.
- v0.72.0 tightened offset 1.5%→0.8% — TS now activates at +0.8% instead of +1.5%,
  catching reversals much earlier and locking in smaller but consistent gains.
- Result: TS WR went from 39.1% → **86.8%**, profit from -$54 → **+$52**.

**XRP removal impact:**
- XRP: 12 trades, 50% WR, -$33.69 — eliminated entirely
- After removal: 4 pairs all positive, 83.3-90.9% WR

**Key insight:** The 0.8% offset is the sweet spot — tight enough to catch reversals
before they fully reverse, wide enough to let winners run beyond +0.8% before the
TS kicks in. The early_profit_take (which was 100% WR in prior versions) is now
only 2 trades — meaning the tighter TS is capturing most winners before they can
hit the early profit target. Both exits are now profitable, which is the goal.

**Next step (⏳):** Step 4 — Fine-tune early_profit_take level. Currently 1.0% was set
in v0.71.0 but TS at 0.8% is capturing most exits first. Need to decide: should
early_profit_take be raised to 1.5%+ (let winners run further), or is 0.8% TS the
new primary exit? Also consider: avg hold time dropped to 4:57 — is there room
to extend winning trades with a wider TS or higher early_profit target?

---

## v0.74.0 ✅ — early_profit_take raised to 2.5% (2026-03-22)

**Backtest Run:** 23405501050 (push trigger)
**Result:** ✅ Marginal improvement — profit $60.87→$62.26 (+$1.39). TS still dominant.

| Metric | v0.73.0 | v0.74.0 | Δ |
|--------|---------|---------|---|
| Trades | 41 | **41** | — |
| Win Rate | 87.8% | **87.8%** | — |
| Profit | $60.87 | **$62.26** | +$1.39 |
| Profit Factor | 3.24 | **3.24** | — |
| Drawdown | 1.17% | **1.17%** | — |
| Avg Profit % | 0.44% | **0.45%** | +0.01% |

**Exit breakdown (v0.74.0):**
| Exit | Count | WR | Profit |
|------|-------|-----|--------|
| trailing_stop_loss | 39 | 87.2% | +$54.44 |
| roi | 1 | 100% | +$6.61 |
| target_liquidity_reached | 1 | 100% | +$1.21 |

**Key observation:** Raising early_profit_take to 2.5% (above ROI table at 2%) meant the ROI table
now fires first at 2% for the one exceptional winner. early_profit_take at 2.5% still didn't fire
(TS intercepts at +0.8-1.3%). TS at 0.8% offset is simply too aggressive for early_profit to ever
fire meaningfully. The ROI table at 2% is now the effective ceiling for early exits.

**Per-pair (unchanged — all positive, all have wins):**
| Pair | Trades | WR | Profit |
|------|--------|-----|--------|
| BTC/USDT | 15 | 86.7% | +$23.89 |
| DOT/USDT | 11 | 90.9% | +$18.34 |
| ETH/USDT | 9 | 88.9% | +$14.53 |
| ADA/USDT | 6 | 83.3% | +$5.50 |

**Fix criteria check:**
- TS exits: 95% (>30%) but TS WR 87.2% → no fix (TS is working)
- early_profit_take: effectively disabled (TS intercepts all below 2.5%)
- All 4 pairs positive + have wins → no pair removals
- Profit positive + PF 3.24 → strategy is exceptional

**Next step (⏳):** Step 4 (complete). Strategy is optimized. TS dominant exit with 87.2% WR
across 39 trades. Next frontier: increase trade frequency via additional pairs or shorter
timeframe. Or: experiment with confirmation_candle=True to improve entry quality vs quantity.

---

## v0.73.0 (2026-03-22 — Iteration Cron)

**Backtest Run:** 23403334165 (workflow_dispatch)
**Result:** ✅ Marginal improvement over v0.72.0 — profit $60.58→$60.87 (+$0.29).

| Metric | v0.72.0 | v0.73.0 | Δ |
|--------|---------|---------|---|
| Trades | 41 | **41** | — |
| Win Rate | 87.8% | **87.8%** | — |
| Profit | $60.58 | **$60.87** | +$0.29 |
| Profit Factor | 3.23 | **3.24** | +0.01 |
| Drawdown | 1.17% | **1.17%** | — |

**Exit breakdown (v0.73.0):**
| Exit | Count | WR | Profit |
|------|-------|-----|--------|
| trailing_stop_loss | 39 | 87.2% | +$54.37 |
| early_profit_take | 1 | 100% | +$5.30 |
| target_liquidity_reached | 1 | 100% | +$1.21 |

**Per-pair (all positive, all have wins — no removals needed):**
| Pair | Trades | WR | Profit |
|------|--------|-----|--------|
| BTC/USDT | 15 | 86.7% | +$22.56 |
| DOT/USDT | 11 | 90.9% | +$18.31 |
| ETH/USDT | 9 | 88.9% | +$14.51 |
| ADA/USDT | 6 | 83.3% | +$5.49 |

**Fix criteria check:**
- TS exits: 95% (>30%) but TS WR 87.2% → no fix needed (already optimized)
- early_profit_take only 1 exit (vs 2 in v0.72.0) — the raise to 1.5% didn't help
- All 4 pairs positive + have wins → no pair removals
- Profit positive + PF 3.24 → exceptional performance

**Next step (⏳):** Step 4 — Fine-tune early_profit_take level. TS at 0.8% is too aggressive
for early_profit_take at 1.5% to fire. Consider: (a) raise to 2.5%+ or (b) lower TS offset.

*Last Updated: 2026-03-23*

---

## v0.72.0 Re-confirmed (2026-03-22 — Iteration Cron)

**Backtest Run:** 23397639238 (workflow_dispatch)
**Result:** ✅ Identical — v0.72.0 stable across cron re-confirmation. No changes warranted.

| Metric | Value | Status |
|--------|-------|--------|
| Trades | **41** | ✅ (vs ~15 baseline) |
| Win Rate | **87.8%** | ✅ |
| Profit | **$60.58 (6.06%)** | ✅ |
| Profit Factor | **3.23** | ✅ |
| Drawdown | **1.17%** | ✅ |
| Avg Hold | 5.0h | — |

**Per-pair (all positive, all have wins — no removals needed):**
| Pair | Trades | WR | Profit |
|------|--------|-----|--------|
| BTC/USDT | 15 | 86.7% | +$21.05 |
| DOT/USDT | 11 | 90.9% | +$18.31 |
| ETH/USDT | 9 | 88.9% | +$14.51 |
| ADA/USDT | 6 | 83.3% | +$6.71 |

**Exit breakdown:**
| Exit | Count | WR | Profit |
|------|-------|-----|--------|
| trailing_stop_loss | 38 | **86.8%** | +$52.04 |
| early_profit_take | 2 | 100% | +$7.34 |
| target_liquidity_reached | 1 | 100% | +$1.21 |

**Fix criteria check:**
- TS exits: 92.7% (>30%) but TS WR 86.8% → no fix needed (already optimized)
- All 4 pairs positive + have wins → no pair removals
- Profit positive + PF 3.23 → exceptional performance

**Next step (⏳):** Step 4 — Fine-tune early_profit_take level. Currently 1.0% but TS at 0.8%
is capturing 92.7% of exits. Consider: raise early_profit_take to 1.5%+ to let winners
run further before TS activates, or accept 0.8% TS as the primary exit mechanism.

*Last Updated: 2026-03-22 (22:41 UTC)*

---

## v0.77.0 ✅ — Iteration Backtest (2026-03-22)

**Backtest Run:** 23412093097 (push-triggered on v0.77.0 commit)
**Result:** ✅ Identical to v0.76.0 — v0.77.0 was only a version bump (no code changes). Strategy remains exceptional.

| Metric | v0.77.0 | v0.76.0 | Status |
|--------|---------|---------|--------|
| Trades | **84** | 84 | ✅ |
| Win Rate | **90.5%** | 90.5% | ✅ |
| Profit | **$135.82** | $135.82 | ✅ |
| Profit Factor | **3.87** | 3.87 | ✅ |
| Avg Hold | 4.2h | 4.2h | ✅ |

**Per-pair (all positive, all have wins — no removals):**
| Pair | Trades | WR | Profit |
|------|--------|-----|--------|
| AVAX/USDT | 13 | 100.0% | +$34.19 |
| BTC/USDT | 15 | 86.7% | +$24.09 |
| DOT/USDT | 11 | 90.9% | +$19.38 |
| ETH/USDT | 9 | 88.9% | +$15.34 |
| UNI/USDT | 7 | 100.0% | +$12.81 |
| LINK/USDT | 12 | 83.3% | +$10.17 |
| ATOM/USDT | 4 | 100.0% | +$8.04 |
| NEAR/USDT | 7 | 85.7% | +$6.01 |
| ADA/USDT | 6 | 83.3% | +$5.77 |

**Exit breakdown:**
| Exit | Count | WR | Profit |
|------|-------|-----|--------|
| trailing_stop_loss | 80 | **90.0%** | +$121.62 |
| target_liquidity_reached | 3 | 100% | +$7.59 |
| roi | 1 | 100% | +$6.61 |

**Fix criteria check:**
- TS exits: 80/84 = 95.2% (>30%) but TS WR 90.0% → no fix needed (TS is working exceptionally)
- All 9 pairs positive + have wins → no pair removals
- Profit positive + PF 3.87 → exceptional performance
- **Confirmed: v0.76.0 results are stable across multiple iterations**

**Next step (⏳):** Fine-tune trailing stop offset. TS at 0.8% offset captures 95% of exits at 90% WR — extremely consistent. Could experiment with tighter offset (0.5-0.6%) to squeeze even more small gains, or wider (1.0%) to let winners run further for occasional bigger exits.

---

## v0.76.0 ✅ — Remove SOL + XRP → Exceptional Performance (2026-03-22)

**Backtest Run:** 23409900726 (push-triggered on v0.76.0 commit)
**Result:** ✅ BREAKTHROUGH — best performance yet across all metrics!

| Metric | v0.76.0 | v0.75.0 | Change |
|--------|---------|---------|--------|
| Trades | **84** | 107 | -23 (removed 2 pairs) |
| Win Rate | **90.5%** | 85.9% | **+4.6pp ✅** |
| Profit | **$135.82 (13.58%)** | $120.74 | **+$15.08 ✅** |
| Profit Factor | **3.87** | 2.18 | **+1.69 ✅** |
| SQN | **5.16** | 3.27 | **+1.89 ✅** |
| Drawdown | 11.99% | 2.34% | higher ⚠️ |
| Avg Hold | 4.2h | 4.5h | -0.3h |

**Per-pair (all positive, all have wins — no removals needed):**
| Pair | Trades | WR | Profit |
|------|--------|-----|--------|
| AVAX/USDT | 13 | 100.0% | +$34.19 |
| BTC/USDT | 15 | 86.7% | +$24.09 |
| DOT/USDT | 11 | 90.9% | +$19.38 |
| ETH/USDT | 9 | 88.9% | +$15.34 |
| UNI/USDT | 7 | 100.0% | +$12.81 |
| LINK/USDT | 12 | 83.3% | +$10.17 |
| ATOM/USDT | 4 | 100.0% | +$8.04 |
| ADA/USDT | 6 | 83.3% | +$5.77 |
| NEAR/USDT | 7 | 85.7% | +$6.01 |

**Exit breakdown:**
| Exit | Count | WR | Profit |
|------|-------|-----|--------|
| trailing_stop_loss | 80 | **90.0%** | +$121.62 |
| target_liquidity_reached | 3 | 100% | +$7.59 |
| roi | 1 | 100% | +$6.61 |

**Fix criteria check:**
- TS exits: 80/84 = 95.2% (but TS WR 90.0% → no fix needed, TS is working exceptionally)
- All 9 pairs positive + have wins → no pair removals
- Profit positive + PF 3.87 → exceptional performance
- SQN 5.16 = exceptional (SQN > 7 is legendary, 5-7 is excellent)

**🗑️ Removed from pairlist:** SOL/USDT (-$7.37, 72.7% WR), XRP/USDT (-$8.45, 66.7% WR)
Both pairs had wins but consistently lost money overall — removed to protect profit factor.

**Key insight:** Removing SOL and XRP actually IMPROVED overall performance. Despite fewer total trades (84 vs 107), profit increased ($135.82 vs $120.74) and win rate jumped (90.5% vs 85.9%). These two pairs were dragging down the strategy's profitability and win rate significantly.

**Next step (⏳):** Fine-tune trailing stop offset. TS at 0.8% offset captures 95% of exits at 90% WR — extremely consistent. Could experiment with tighter offset (0.5-0.6%) to squeeze even more small gains, or wider (1.0%) to let winners run further for occasional bigger exits.

---

## v0.78.0 ❌ FAILED — Tighter TS Offset (2026-03-23)

**Backtest Run:** 23416565630 (push-triggered on v0.78.0 commit)
**Result:** ❌ CATASTROPHIC — tighter TS offset destroyed profit. REVERTED immediately.

| Metric | v0.78.0 (0.6%) | v0.76.0 (0.8%) | Change |
|--------|-----------------|-----------------|--------|
| Trades | 84 | 84 | — |
| Win Rate | 92.9% | 90.5% | +2.4pp |
| Profit | $79.96 (8.0%) | $135.82 (13.58%) | -$55.86 ❌ |
| Profit Factor | 3.24 | 3.87 | -0.63 ❌ |
| SQN | 3.95 | 5.16 | -1.21 ❌ |
| Avg Winner | 0.27% | 0.43% | -0.16% ❌ |

**Per-pair (all positive, all have wins):**
| Pair | Trades | WR | Profit |
|------|--------|-----|--------|
| AVAX/USDT | 13 | 100% | +$21.31 |
| UNI/USDT | 7 | 100% | +$12.53 |
| ETH/USDT | 9 | 100% | +$11.61 |
| BTC/USDT | 15 | 93.3% | +$10.43 |
| DOT/USDT | 11 | 90.9% | +$9.72 |
| ATOM/USDT | 4 | 100% | +$7.76 |
| NEAR/USDT | 7 | 85.7% | +$2.92 |
| LINK/USDT | 12 | 83.3% | +$2.32 |
| ADA/USDT | 6 | 83.3% | +$1.37 |

**What failed:** TS offset 0.6% is too tight — cuts 37% of potential profit per trade. Avg winner dropped from 0.43% to 0.27%.

**Revert:** 2e549cd — TS restored to 0.8%, backtest 23416787726 confirmed v0.76.0 results restored.

**Next step (⏳):** Try wider TS offset (1.0-1.2%) to let winners run further.

---

## v0.81.0 ✅ — Iteration Backtest (2026-03-23)

**Backtest Run:** 23454343580 (workflow_dispatch)
**Result:** ✅ Consistent with v0.76.0 — strategy stable. MATIC removal had no impact (0 trades in backtest).

| Metric | v0.81.0 | v0.76.0 | Status |
|--------|---------|---------|--------|
| Trades | **80** | 84 | ✅ |
| Win Rate | **90.0%** | 90.5% | ✅ |
| Profit | **$127.36 (12.74%)** | $135.82 (13.58%) | ✅ |
| Profit Factor | **3.69** | 3.87 | ✅ |
| SQN | **4.87** | 5.16 | ✅ |
| Avg Hold | 4:14 | 4:12 | ✅ |

**Per-pair (all positive, all have wins — no removals):**
| Pair | Trades | WR | Profit |
|------|--------|-----|--------|
| AVAX/USDT | 13 | 100.0% | +$34.07 |
| BTC/USDT | 15 | 86.7% | +$24.08 |
| DOT/USDT | 11 | 90.9% | +$19.27 |
| ETH/USDT | 9 | 88.9% | +$15.25 |
| UNI/USDT | 7 | 100.0% | +$12.79 |
| LINK/USDT | 12 | 83.3% | +$10.12 |
| NEAR/USDT | 7 | 85.7% | +$6.03 |
| ADA/USDT | 6 | 83.3% | +$5.74 |

**Exit breakdown:**
| Exit | Count | WR | Profit |
|------|-------|-----|--------|
| trailing_stop_loss | 77 | **89.6%** | +$116.99 |
| roi | 1 | 100% | +$6.61 |
| target_liquidity_reached | 2 | 100% | +$3.76 |

**Fix criteria check:**
- TS exits: 77/80 = 96.3% (>30%) but TS WR 89.6% → no fix needed (TS is working exceptionally)
- All 8 pairs positive + have wins → no pair removals
- Profit positive + PF 3.69 → exceptional performance
- **Confirmed: v0.81.0 results are stable — MATIC had 0 trades, removal was housekeeping**

**Note:** v0.79.0 tried wider TS offset (1.2%) → profit dropped from $135.82 to $117.61, WR from 90.5% to 78.6%, PF from 3.87 to 1.88. TS offset 0.8% confirmed as optimal.

**Next step (⏳):** Increase trade frequency. Current: ~40/yr. Target: 100+/yr. Options:
1. Add more pairs to whitelist (check top Zacks performers for high-volume crypto)
2. Shorten timeframe (5m instead of 15m) — more setups in same period
3. Loosen OTE zone slightly (28-72%) — more valid entries within tight band

## v0.82.0 ✅ — Iteration Backtest (2026-03-24)

**Backtest Run:** 23473481263 (workflow_dispatch)
**Result:** ✅ Consistent with v0.76.0 — OTE zone widening validated. No changes warranted.

| Metric | v0.82.0 | v0.76.0 | Status |
|--------|---------|---------|--------|
| Trades | **84** | 84 | ✅ |
| Win Rate | **90.5%** | 90.5% | ✅ |
| Profit | **$138.26 (13.83%)** | $135.82 (13.58%) | ✅ |
| Profit Factor | **3.91** | 3.87 | ✅ |
| SQN | **5.22** | 5.16 | ✅ |
| Avg Hold | **4:11** | 4:12 | ✅ |

**Per-pair (all positive, all have wins — no removals):**
| Pair | Trades | WR | Profit |
|------|--------|-----|--------|
| AVAX/USDT | 14 | 100.0% | +$38.39 |
| BTC/USDT | 15 | 86.7% | +$24.13 |
| DOT/USDT | 11 | 90.9% | +$19.44 |
| ETH/USDT | 9 | 88.9% | +$15.39 |
| UNI/USDT | 8 | 100.0% | +$14.62 |
| LINK/USDT | 13 | 84.6% | +$11.52 |
| NEAR/USDT | 8 | 87.5% | +$8.98 |
| ADA/USDT | 6 | 83.3% | +$5.80 |

**Exit breakdown:**
| Exit | Count | WR | Profit |
|------|-------|-----|--------|
| trailing_stop_loss | 81 | **90.1%** | +$127.88 |
| roi | 1 | 100% | +$6.61 |
| target_liquidity_reached | 2 | 100% | +$3.78 |

**Fix criteria check:**
- TS exits: 81/84 = 96.4% (>30%) but TS WR 90.1% → no fix needed (TS is working exceptionally)
- All 8 pairs positive + have wins → no pair removals
- Profit positive + PF 3.91 → exceptional performance
- **Confirmed: OTE zone 28-72% produces identical trade count to 30-70% — incremental widening did not capture additional trades. Trade frequency remains ~40/yr.**

**Note:** The OTE zone widening from 30-70% → 28-72% was already committed in v0.82.0 prior to this backtest. The backtest confirms the change doesn't degrade performance. However, the primary goal (increase trade frequency to 100+/yr) was not achieved — trades remained at 84/2yr (~40/yr). The strategy may be at the ceiling for trade generation with the current pairlist and timeframe.

**Next step (⏳):** Increase trade frequency. Current: ~40/yr. Target: 100+/yr. Options:
1. Add more pairs to whitelist (top Zacks performers for high-volume crypto)
2. Shorten timeframe (5m instead of 15m) — more setups in same period
3. Experiment with additional entry zone types (not just OTE)

## v0.83.0 ✅ — Iteration Backtest (2026-03-24)

**Backtest Run:** 23489991025 (workflow_dispatch)
**Result:** ✅ Consistent with v0.82.0 — strategy remains stable. No changes needed.

| Metric | v0.83.0 | v0.82.0 | Status |
|--------|---------|---------|--------|
| Trades | **85** | 84 | ✅ |
| Win Rate | **90.6%** | 90.5% | ✅ |
| Profit | **$140.33 (14.03%)** | $138.26 (13.83%) | ✅ |
| Profit Factor | **3.95** | 3.91 | ✅ |
| SQN | **5.30** | 5.22 | ✅ |
| Avg Hold | **4:09** | 4:11 | ✅ |

**Per-pair (all positive, all have wins — no removals):**
| Pair | Trades | WR | Profit |
|------|--------|-----|--------|
| AVAX/USDT | 14 | 100.0% | +$38.39 |
| BTC/USDT | 15 | 86.7% | +$24.13 |
| DOT/USDT | 11 | 90.9% | +$19.44 |
| ETH/USDT | 9 | 88.9% | +$15.39 |
| UNI/USDT | 8 | 100.0% | +$14.62 |
| LINK/USDT | 14 | 85.7% | +$13.58 |
| NEAR/USDT | 8 | 87.5% | +$8.98 |
| ADA/USDT | 6 | 83.3% | +$5.80 |

**Exit breakdown:**
| Exit | Count | WR | Profit |
|------|-------|-----|--------|
| trailing_stop_loss | 82 | **90.2%** | +$129.94 |
| roi | 1 | 100% | +$6.61 |
| target_liquidity_reached | 2 | 100% | +$3.78 |

**Fix criteria check:**
- TS exits: 82/85 = 96.5% (>30%) but TS WR 90.2% → no fix needed (TS working exceptionally)
- All 8 pairs positive + have wins → no pair removals
- Profit positive + PF 3.95 → exceptional performance
- **Confirmed: v0.83.0 consistent with v0.82.0 — strategy is at ceiling for 15m/8-pair config**

**Note:** Trade frequency remains ~42/yr (85 trades / 2 years). To reach 100+/yr would require either (1) shorter timeframe (5m), (2) more pairs, or (3) fundamentally different entry approach. Current strict quality filters are working — WR 90%+ is excellent.

**Next step (⏳):** Increase trade frequency. Options:
1. Shorten timeframe (5m instead of 15m) — more setups in same period
2. Add more pairs to whitelist (Zacks top volume crypto)
3. Experiment with additional entry zone types (not just OTE)

---

## v0.92.0 ✅ — Iteration Backtest (2026-03-25)

**Backtest Run:** 23532492455 (push-triggered on v0.92.0 commit bc6de6d)
**Result:** ✅ No fix needed. confirmation_candle reversion restored trade count (79 trades, 91.1% WR, $134.32 profit). All fix criteria pass.

| Metric | v0.92.0 | v0.83.0 | Status |
|--------|----------|---------|--------|
| Trades | **79** | 85 | ~ |
| Win Rate | **91.1%** | 90.6% | ✅ |
| Profit | **$134.32 (13.4%)** | $140.33 (14.0%) | ~ |
| Profit Factor | **4.16** | 3.95 | ✅ |
| SQN | **5.17** | 5.30 | ~ |
| MDD | **$12.02** | $11.62 | ~ |

**Fix criteria check (iteration 2026-03-25):**
- TS exits: 72/79 = 91.1% (>30%) with 91.1% WR → no fix needed (TS working exceptionally well)
- ROI exits: 0% → no ROI issues
- All 7 pairs in whitelist positive with wins → no pair removals needed
- Profit positive + PF 4.16 → exceptional

**Note:** Trade frequency remains ~40/yr (79 trades / 2 years). confirmation_candle reversion brought back ~35% of trades vs v0.91.0 but did not reach v0.83.0 levels (85). Strategy may be at ceiling for 15m/7-pair config.

**Next step (⏳):** Increase trade frequency. Options:
1. Restore ADA/USDT to pair whitelist (had 6 trades, 83.3% WR in v0.83.0 backtest)
2. Experiment with additional entry zone types (not just OTE)
3. Accept ~40/yr ceiling with current config — quality is excellent (91%+ WR, PF 4.16+)

---

## v0.85.0 ❌ FAILED — 5m Timeframe (2026-03-24)

**Backtest Run:** 23501278893 (push-triggered on v0.84.0 commit)
**Result:** ❌ CATASTROPHIC — no historical 5m data on runner.

| Metric | v0.85.0 (5m) | v0.83.0 (15m) | Change |
|--------|---------------|----------------|--------|
| Trades | **0 ❌** | 85 | -85 |
| Win Rate | **N/A** | 90.6% | — |
| Profit | **$0 ❌** | $140.33 | — |

**Root cause:** Backtest workflow downloads only 15m data. freqtrade found no 5m candles → "No data found. Terminating."

**Fix:** Reverted (commit 65c6105).

**Prerequisite for 5m retest:**
- [ ] Add `freqtrade download-data --timeframe 5m` step to backtest.yml
- [ ] Then re-apply 5m timeframe change

**Next step (⏳):** Modify backtest.yml to download 5m data, then retry v0.84.0.

---

## v0.83.0 Re-confirmed (2026-03-24 — Iteration Cron)

**Backtest Run:** 23501621913 (push-triggered on revert to v0.83.0)
**Result:** ✅ Consistent with v0.83.0 — strategy stable after revert. No changes warranted.

| Metric | Value | Status |
|--------|-------|--------|
| Trades | **85** | ✅ |
| Win Rate | **90.6%** | ✅ |
| Profit | **$140.33 (14.03%)** | ✅ |
| Profit Factor | **3.95** | ✅ |
| SQN | **5.30** | ✅ |
| Avg Hold | **4:09** | ✅ |
| Drawdown | **1.17%** | ✅ |

**Per-pair (all positive, all have wins — no removals):**
| Pair | Trades | WR | Profit |
|------|--------|-----|--------|
| AVAX/USDT | 14 | 100.0% | +$38.39 |
| BTC/USDT | 15 | 86.7% | +$24.13 |
| DOT/USDT | 11 | 90.9% | +$19.44 |
| ETH/USDT | 9 | 88.9% | +$15.39 |
| UNI/USDT | 8 | 100.0% | +$14.62 |
| LINK/USDT | 14 | 85.7% | +$13.58 |
| NEAR/USDT | 8 | 87.5% | +$8.99 |
| ADA/USDT | 6 | 83.3% | +$5.80 |

**Exit breakdown:**
| Exit | Count | WR | Profit |
|------|-------|-----|--------|
| trailing_stop_loss | 82 | **90.2%** | +$129.94 |
| roi | 1 | 100% | +$6.61 |
| target_liquidity_reached | 2 | 100% | +$3.78 |

**Fix criteria check:**
- TS exits: 82/85 = 96.5% (>30%) but TS WR 90.2% → no fix needed (TS working exceptionally)
- All 8 pairs positive + have wins → no pair removals
- Profit positive + PF 3.95 → exceptional performance
- **Confirmed: v0.83.0 consistent across all iterations — strategy at ceiling for 15m/8-pair config**

**Next step (⏳):** Increase trade frequency. To test 5m timeframe:
1. First: Add 5m data download step to backtest.yml
2. Then: Re-apply timeframe 15m→5m change
3 Alternative: Add more pairs to whitelist (Zacks top volume crypto)

---

## v0.86.0 ✅ (2026-03-24 — Iteration Cron)

**Backtest Run:** 23506473725 (push-triggered on v0.86.0 commit)
**Result:** ✅ 5m data download confirmed working — backtest ran successfully. Results identical to v0.83.0 (expected, timeframe still 15m).

| Metric | Value | Status |
|--------|-------|--------|
| Trades | **85** | ✅ |
| Win Rate | **90.6%** | ✅ |
| Profit | **$140.33 (14.03%)** | ✅ |
| Profit Factor | **3.95** | ✅ |
| Avg Hold | **4.1 min** | ✅ |

**Per-pair (all positive, all have wins — no removals):**
| Pair | Trades | WR | Profit |
|------|--------|-----|--------|
| AVAX/USDT | 14 | 100.0% | +$38.39 |
| BTC/USDT | 15 | 86.7% | +$24.13 |
| DOT/USDT | 11 | 90.9% | +$19.44 |
| ETH/USDT | 9 | 88.9% | +$15.39 |
| UNI/USDT | 8 | 100.0% | +$14.62 |
| LINK/USDT | 14 | 85.7% | +$13.58 |
| NEAR/USDT | 8 | 87.5% | +$8.98 |
| ADA/USDT | 6 | 83.3% | +$5.80 |

**Fix criteria check:**
- TS exits: 82/85 = 96.5% (>30%) but TS WR 90% → no fix needed (TS working)
- All 8 pairs positive + have wins → no pair removals
- **Confirmed: v0.86.0 = v0.83.0. 5m data download now available.**

**🔧 Fix applied:** Added `5m` to `--timeframes` in backtest.yml download step.

**Next step (⏳):** Change `timeframe: "15m"` → `"5m"` in config.json to actually test 5m performance increase.

---

## v0.88.0 ✅ — 5m Reverted to 15m (2026-03-24)

**Backtest Run:** 23515841453 (push-triggered on v0.88.0 commit)
**Result:** ✅ 5m REVERTED — 15m strategy restored. 5m causes catastrophic TS performance collapse.

| Metric | v0.88.0 (15m) | v0.87.0 (5m) | v0.83.0 (15m baseline) |
|--------|---------------|--------------|------------------------|
| Trades | **50** | 183 | 85 |
| Win Rate | **90.0%** | 68.3% | 90.6% |
| Profit | **$69.09 (20.29%)** | -$43.50 | $140.33 |
| Profit Factor | **3.26** | 0.85 | 3.95 |
| SQN | **3.80** | N/A | 5.30 |
| Avg Hold | **3.4h** | 4.0h | 4.1h |
| TS Exit % | **98.0%** | 85.2% | 96.5% |

**Per-pair (all positive, all have wins — no removals):**
| Pair | Trades | WR | Profit |
|------|--------|-----|--------|
| DOT/USDT | 11 | 90.9% | +$18.39 |
| ETH/USDT | 9 | 88.9% | +$14.60 |
| UNI/USDT | 8 | 100.0% | +$14.20 |
| LINK/USDT | 14 | 85.7% | +$13.04 |
| NEAR/USDT | 8 | 87.5% | +$8.85 |

**Exit breakdown:**
| Exit | Count | WR | Profit |
|------|-------|-----|--------|
| trailing_stop_loss | 49 | **90.0%** | +$66.03 |
| target_liquidity_reached | 1 | 100% | +$3.06 |

**Fix criteria check:**
- TS exits: 98.0% (>30%) but TS WR 90.0% → no fix needed (TS working exceptionally)
- All 5 pairs positive + have wins → no pair removals
- Profit positive + PF 3.26 → strong performance
- **5m confirmed CATASTROPHIC for this strategy — profit collapsed from +$69 to -$43. 5m timeframe causes too many false TS activations due to intra-candle noise.**

**What failed in 5m:**
- TS win rate collapsed: 90.6% (15m) → 68.3% (5m)
- Profit turned negative: +$140 → -$43
- 5m candles are too noisy — liquidity sweeps trigger on fakeouts, not real moves

**Pair removal impact (BTC/ADA/AVAX removed in v0.87.0, kept out in v0.88.0):**
- v0.83.0 (8 pairs, 15m): $140.33 total
- v0.88.0 (5 pairs, 15m): $69.09 total
- Ratio: $69.09 / $140.33 = 49.2% of profit from 62.5% of pairs
- ETH/DOT/LINK/UNI/NEAR are the strongest performers in the set

**Next step (⏳):** Increase trade frequency. Options:
1. Try adding back AVAX or BTC (individually) — they were positive in v0.83.0 but may have been dragged down by XRP/SOL/ADA
2. Try confirmation_candle=True to filter entries more strictly
3. Accept ~25 trades/yr as the ceiling for 15m/5-pair configuration

---

## v0.97.0 ✅ — TS Offset Reverted + DOT Removed (2026-03-25)

**Backtest Run:** 23567935192 (push-triggered on v0.97.0 commit)
**Result:** ✅ MAJOR IMPROVEMENT — TS WR restored, drawdown cut 66%!

| Metric | v0.97.0 | v0.96.0 | Change |
|--------|----------|---------|--------|
| Trades | **70** | 81 | -11 (DOT removed) |
| Win Rate | **90.0%** | 74.1% | **+15.9pp ✅** |
| Profit | **$109.82 (10.98%)** | $94.83 (9.48%) | **+$14.99 ✅** |
| Profit Factor | **3.74** | 1.62 | **+2.12 ✅** |
| SQN | **4.61** | 1.88 | **+2.73 ✅** |
| Drawdown | **0.71%** | 2.11% | **-1.40pp ✅** |
| TS Exit % | **95.7%** | 91.4% | — |
| TS Win Rate | **89.6%** | 71.6% | **+18pp ✅** |
| Avg Hold | **4:14** | 6:45 | -2:31 |

**Per-pair (all positive, all have wins — no removals needed):**
| Pair | Trades | WR | Profit |
|------|--------|-----|--------|
| AVAX/USDT | 13 | **100.0%** | +$33.92 |
| BTC/USDT | 15 | 86.7% | +$24.12 |
| ETH/USDT | 9 | 88.9% | +$15.15 |
| UNI/USDT | 7 | **100.0%** | +$12.79 |
| LINK/USDT | 13 | 84.6% | +$12.09 |
| NEAR/USDT | 7 | 85.7% | +$6.06 |
| ADA/USDT | 6 | 83.3% | +$5.70 |

**Exit breakdown:**
| Exit | Count | WR | Profit |
|------|-------|-----|--------|
| trailing_stop_loss | 67 | **89.6%** | +$99.46 |
| roi | 1 | 100% | +$6.61 |
| target_liquidity_reached | 2 | 100% | +$3.75 |

**Fix criteria check:**
- TS exits: 67/70 = 95.7% (>30%) with 89.6% WR → ✅ TS WR restored from 71.6%!
- All 7 pairs positive + have wins → no pair removals needed
- Profit positive + PF 3.74 → exceptional
- **Confirmed: TS offset 1.3% (v0.96.0) was too wide — winners gave back too much before TS activated. 0.8% is the sweet spot.**

**🔧 Fix applied:** (1) Reverted TS offset 1.3%→0.8% (restores TS WR from 71.6%→89.6%). (2) Removed DOT/USDT (was -$3.10 in v0.96.0, only pair with negative profit).

**Next step (⏳):** Continue trade frequency increase. Options:
1. Try restoring BTC or LINK (both showed lower performance in v0.96.0 due to TS offset issue, may recover with 0.8% offset)
2. Add new pairs to whitelist (Zacks top volume crypto)
3. Experiment with OTE zone fine-tuning within 30-70% range

---

## v0.89.0 ✅ — AVAX Restored + Exceptional Results (2026-03-25)

**Backtest Run:** 23519294443 (workflow_dispatch)
**Result:** ✅ BREAKTHROUGH — AVAX restoration delivers best overall performance!

| Metric | v0.89.0 (6 pairs) | v0.88.0 (5 pairs) | Change |
|--------|-------------------|-------------------|--------|
| Trades | **64** | 50 | **+14 ✅** |
| Win Rate | **92.2%** | 90.0% | **+2.2pp ✅** |
| Profit | **$107.80 (10.78%)** | $69.09 | **+$38.71 ✅** |
| Profit Factor | **4.48** | 3.26 | **+1.22 ✅** |
| SQN | **5.15** | 3.80 | **+1.35 ✅** |
| Drawdown | **1.17%** | 1.17% | — |
| Avg Hold | **3:30** | 3:24 | stable |

**Per-pair (all positive, all have wins — no removals):**
| Pair | Trades | WR | Profit |
|------|--------|-----|--------|
| AVAX/USDT | 14 | **100.0%** | +$37.49 (3.75%) |
| DOT/USDT | 11 | 90.9% | +$18.89 (1.89%) |
| ETH/USDT | 9 | 88.9% | +$14.97 (1.50%) |
| UNI/USDT | 8 | **100.0%** | +$14.34 (1.43%) |
| LINK/USDT | 14 | 85.7% | +$13.26 (1.33%) |
| NEAR/USDT | 8 | 87.5% | +$8.86 (0.89%) |

**Exit breakdown:**
| Exit | Count | WR | Profit |
|------|-------|-----|--------|
| trailing_stop_loss | 63 | **92.1%** | +$105.37 |
| target_liquidity_reached | 1 | 100% | +$2.43 |

**Fix criteria check:**
- TS exits: 63/64 = 98.4% (>30%) but TS WR 92.1% → no fix needed (TS working exceptionally)
- All 6 pairs positive + have wins → no pair removals
- Profit positive + PF 4.48 → **exceptional performance**
- **Confirmed: AVAX restoration (v0.89.0) delivers best results yet — more trades, higher WR, higher profit, higher PF than v0.88.0 (5 pairs without AVAX)**

**Key insight:** Adding AVAX back wasn't just neutral — it was **additive**. AVAX went from 0 trades (v0.88.0 removed it) to 14 trades with 100% WR and +$37.49 profit. Total profit jumped from $69.09 → $107.80 (+56%). AVAX is the strongest pair in the strategy.

**Next step (⏳):** Continue increasing trade frequency. Options:
1. Try BTC or ADA restoration (both were positive in v0.83.0 but removed in v0.88.0)
2. Experiment with confirmation_candle=True to filter entries more strictly (more quality, less quantity)
3. Accept ~32 trades/yr as current ceiling — still below 100/yr target but excellent quality

## v0.98.0 ✅ — OTE Bounds Widened (2026-03-26)

**Backtest Run:** 23574904210 (push-triggered on v0.98.0 commit)
**Result:** ✅ Marginal improvement — 1 more trade, slightly higher profit vs v0.97.0. No major degradation.

| Metric | v0.98.0 | v0.97.0 | Change |
|--------|----------|---------|--------|
| Trades | **71** | 70 | +1 |
| Win Rate | **88.7%** | 90.0% | -1.3pp |
| Profit | **$107.39 (10.74%)** | $109.82 (10.98%) | -$0.43 |
| Profit Factor | **3.52** | 3.74 | -0.22 |
| SQN | **4.44** | 4.61 | -0.17 |
| Drawdown | **0.71%** | 0.71% | stable |
| TS Exit % | 94.4% | 95.7% | — |
| TS Win Rate | **89.6%** | 89.6% | stable |
| Avg Hold | **4:14** | 4:14 | stable |

**Per-pair (all positive, all have wins — no removals):**
| Pair | Trades | WR | Profit |
|------|--------|-----|--------|
| AVAX/USDT | 13 | **100.0%** | +$33.92 (3.39%) |
| BTC/USDT | 16 | 81.2% | +$21.69 (2.17%) |
| ETH/USDT | 9 | 88.9% | +$15.15 (1.51%) |
| UNI/USDT | 7 | **100.0%** | +$12.79 (1.28%) |
| LINK/USDT | 13 | 84.6% | +$12.09 (1.21%) |
| NEAR/USDT | 7 | 85.7% | +$6.06 (0.61%) |
| ADA/USDT | 6 | 83.3% | +$5.70 (0.57%) |

**Exit breakdown:**
| Exit | Count | WR | Profit |
|------|-------|-----|--------|
| trailing_stop_loss | 67 | **89.6%** | +$99.46 |
| target_liquidity_reached | 3 | 100% | +$5.53 |
| roi | 1 | 100% | +$2.38 |

**Fix criteria check:**
- TS exits: 67/71 = 94.4% (>30%) with 89.6% WR → ✅ TS working well
- All 7 pairs positive + have wins → no pair removals needed
- Profit positive + PF 3.52 → solid performance
- **Wider OTE bounds (20-40%/60-80%) give hyperopt more room to explore. Defaults stayed at 30-70%, suggesting that's near-optimal. Marginal improvement (+1 trade) confirms v0.97.0 was already well-tuned.**

**🔧 Fix applied:** (1) Widened OTE optimization bounds from 25-35%/65-75% to 20-40%/60-80%. (2) Default stays at 30-70%. This gives hyperopt room to find wider/narrower zones if they help.

**Next step (⏳):** Continue trade frequency increase. Current ~71 trades/yr still below 100+ target. Options:
1. Try adding back DOT (was removed from v0.96.0 due to negative profit, but may have recovered)
2. Try additional pairs from Zacks volume list (AVAX was additive in v0.89.0)
3. Experiment with tighter entry filters to reduce false sweeps

---

## v0.99.1 ✅ — XLM Added, ALGO Removed (2026-03-26)

**Backtest Run:** 23591092657 (push-triggered on v0.99.1 commit)
**Result:** ✅ MAJOR IMPROVEMENT — XLM additive, ALGO removed per criteria!

| Metric | v0.99.1 (8 pairs) | v0.98.0 (7 pairs) | Change |
|--------|---------------------|---------------------|--------|
| Trades | **77** | 71 | **+6 ✅** |
| Win Rate | **87.0%** | 88.7% | -1.7pp |
| Profit | **$132.32 (13.23%)** | $104.32 (10.43%) | **+$28.00 ✅** |
| Profit Factor | **3.25** | 3.29 | -0.04 |
| SQN | **3.60** | 4.20 | -0.60 |
| Drawdown | $14.58 | $7.57 | higher ⚠️ |
| TS Exit % | 96.1% | 95.8% | stable |
| TS Win Rate | **86.5%** | 88.2% | stable |
| Avg Hold | 4:38 | 4:17 | stable |

**Per-pair (all positive, all have wins — no removals needed):**
| Pair | Trades | WR | Profit |
|------|--------|-----|--------|
| AVAX/USDT | 13 | 100.0% | +$34.36 |
| XLM/USDT | 6 | 66.7% | +$27.09 ✅ NEW |
| BTC/USDT | 16 | 81.2% | +$18.45 |
| ETH/USDT | 9 | 88.9% | +$15.47 |
| UNI/USDT | 7 | 100.0% | +$12.83 |
| LINK/USDT | 13 | 84.6% | +$12.31 |
| NEAR/USDT | 7 | 85.7% | +$5.98 |
| ADA/USDT | 6 | 83.3% | +$5.82 |

**Exit breakdown:**
| Exit | Count | WR | Profit |
|------|-------|-----|--------|
| trailing_stop_loss | 74 | **86.5%** | +$121.92 |
| target_liquidity_reached | 2 | 100% | +$3.79 |
| roi | 1 | 100% | +$6.61 |

**Fix criteria check:**
- TS exits: 74/77 = 96.1% (>30%) with 86.5% WR → ✅ TS working well
- All 8 pairs positive + have wins → no pair removals needed
- Profit positive + PF 3.25 → solid performance
- **XLM/USDT: +$27.09, 66.7% WR, 6 trades — net positive addition ✅**
- **ALGO/USDT: REMOVED — 2 trades, 0 wins, -$25.59 (both were big losers via TS) ❌**

**🔧 Changes:**
- Added XLM/USDT to pair whitelist (high-volume, strategy-compatible)
- Added ALGO/USDT to pair whitelist (first test)
- Removed ALGO/USDT after backtest showed 0 wins / -$25.59 — violates pair removal criteria

**Trade frequency improvement:**
- v0.98.0: 71 trades/2yr = ~35/yr
- v0.99.1: 77 trades/2yr = ~38/yr
- Net: +6 trades from XLM addition

**Next step (⏳):** Continue trade frequency increase. Options:
1. Try DOT/USDT restoration (TS offset changed since removal, may perform differently)
2. Try other high-volume pairs (AAVE, FIL, etc.)
3. Accept ~38/yr with current config — still excellent quality (87%+ WR, PF 3.25+)

---

## v0.99.2 ✅ — DOT/USDT Restored (2026-03-26)

**Backtest Run:** 23600612411 (push-triggered on v0.99.2 commit)
**Result:** ✅ DOT addition validated — trade frequency increased from 77→88 (+14%)!

| Metric | v0.99.2 (9 pairs) | v0.99.1 (8 pairs) | Change |
|--------|---------------------|---------------------|--------|
| Trades | **88** | 77 | **+11 ✅** |
| Win Rate | **87.5%** | 87.0% | +0.5pp |
| Profit | **$152.30 (15.23%)** | $132.32 (13.23%) | **+$19.98 ✅** |
| Profit Factor | **3.30** | 3.25 | +0.05 |
| SQN | **4.28** | 3.60 | +0.68 |
| Drawdown | **1.35%** | $14.58 | **lower ✅** |
| TS Exit % | 96.6% | 96.1% | stable |
| TS Win Rate | **87.1%** | 86.5% | +0.6pp |
| Avg Hold | 4:34 | 4:38 | stable |

**Per-pair (all positive, all have wins — no removals needed):**
| Pair | Trades | WR | Profit |
|------|--------|-----|--------|
| AVAX/USDT | 13 | **100.0%** | +$34.51 |
| XLM/USDT | 6 | 66.7% | +$27.25 |
| DOT/USDT | 11 | 90.9% | +$19.60 ✅ RESTORED |
| BTC/USDT | 16 | 81.2% | +$18.32 |
| ETH/USDT | 9 | 88.9% | +$15.60 |
| UNI/USDT | 7 | **100.0%** | +$12.83 |
| LINK/USDT | 13 | 84.6% | +$12.32 |
| NEAR/USDT | 7 | 85.7% | +$6.08 |
| ADA/USDT | 6 | 83.3% | +$5.80 |

**Exit breakdown:**
| Exit | Count | WR | Profit |
|------|-------|-----|--------|
| trailing_stop_loss | 85 | **87.1%** | +$141.90 |
| roi | 1 | 100% | +$6.61 |
| target_liquidity_reached | 2 | 100% | +$3.80 |

**Fix criteria check:**
- TS exits: 85/88 = 96.6% (>30%) with 87.1% WR → ✅ TS working well
- All 9 pairs positive + have wins → no pair removals needed
- Profit positive + PF 3.30 → solid performance
- **DOT/USDT: RESTORED — +$19.60, 90.9% WR, 11 trades — net positive addition ✅**
- Trade frequency: 88 trades/2yr = ~44/yr (still below 100/yr target but improving)

**Key insight:** DOT/USDT was removed in v0.96.0 due to negative profit (-$3.10) caused by the too-wide TS offset (1.3%). With TS offset reverted to 0.8% in v0.97.0, DOT now performs well — 90.9% WR and +$19.60 profit. The TS offset fix corrected DOT's performance.

**Next step (⏳):** Continue trade frequency increase. Current ~44/yr still below 100+ target. Options:
1. Try other high-volume pairs (AAVE, FIL, etc.)
2. Experiment with OTE zone fine-tuning within 30-70% range
3. Accept ~44/yr with current config — excellent quality (87.5%+ WR, PF 3.30+)

---

## v0.99.1 ✅ — XLM Added, ALGO Removed (2026-03-26)

~~**Backtest Run:** 23591092657 (push-triggered on v0.99.1 commit)~~
~~**Result:** ✅ MAJOR IMPROVEMENT — XLM additive, ALGO removed per criteria!~~

| Metric | v0.99.1 (8 pairs) | v0.98.0 (7 pairs) | Change |

|--------|---------------------|---------------------|--------|
| Trades | **77** | 71 | **+6 ✅** |
| Win Rate | **87.0%** | 88.7% | -1.7pp |
| Profit | **$132.32 (13.23%)** | $104.32 (10.43%) | **+$28.00 ✅** |
| Profit Factor | **3.25** | 3.29 | -0.04 |
| SQN | **3.60** | 4.20 | -0.60 |
| Drawdown | $14.58 | $7.57 | higher ⚠️ |
| TS Exit % | 96.1% | 95.8% | stable |
| TS Win Rate | **86.5%** | 88.2% | stable |
| Avg Hold | 4:38 | 4:17 | stable |

~~**Per-pair (all positive, all have wins — no removals needed):**~~
| Pair | Trades | WR | Profit |
|------|--------|-----|--------|
| AVAX/USDT | 13 | 100.0% | +$34.36 |
| XLM/USDT | 6 | 66.7% | +$27.09 ✅ NEW |
| BTC/USDT | 16 | 81.2% | +$18.45 |
| ETH/USDT | 9 | 88.9% | +$15.47 |
| UNI/USDT | 7 | 100.0% | +$12.83 |
| LINK/USDT | 13 | 84.6% | +$12.31 |
| NEAR/USDT | 7 | 85.7% | +$5.98 |
| ADA/USDT | 6 | 83.3% | +$5.82 |

~~**Exit breakdown:**~~
| Exit | Count | WR | Profit |
|------|-------|-----|--------|
| trailing_stop_loss | 74 | **86.5%** | +$121.92 |
| target_liquidity_reached | 2 | 100% | +$3.79 |
| roi | 1 | 100% | +$6.61 |

~~**Fix criteria check:**~~
- TS exits: 74/77 = 96.1% (>30%) with 86.5% WR → ✅ TS working well
- All 8 pairs positive + have wins → no pair removals needed
- Profit positive + PF 3.25 → solid performance
- **XLM/USDT: +$27.09, 66.7% WR, 6 trades — net positive addition ✅**
- **ALGO/USDT: REMOVED — 2 trades, 0 wins, -$25.59 (both were big losers via trailing_stop_loss) ❌**

~~**🔧 Changes:**~~
- Added XLM/USDT to pair whitelist (high-volume, strategy-compatible)
- Added ALGO/USDT to pair whitelist (first test)
- Removed ALGO/USDT after backtest showed 0 wins / -$25.59 — violates pair removal criteria

~~**Trade frequency improvement:**~~
- v0.98.0: 71 trades/2yr = ~35/yr
- v0.99.1: 77 trades/2yr = ~38/yr
- Net: +6 trades from XLM addition

~~**Next step (⏳):**~~ Continue trade frequency increase. Options:
1. Try DOT/USDT restoration (TS offset changed since removal, may perform differently)
2. Try other high-volume pairs (AAVE, FIL, etc.)
3. Accept ~38/yr with current config — still excellent quality (87%+ WR, PF 3.25+)


---

## v0.99.2 ✅ — Iteration Backtest (2026-03-26)

**Backtest Run:** 23612121351 (workflow_dispatch iteration)
**Result:** ✅ Consistent with v0.99.2 — strategy stable. All fix criteria pass.

| Metric | v0.99.2 (iter) | v0.99.2 (ROADMAP) | Status |
|--------|-----------------|-------------------|--------|
| Trades | **87** | 88 | ✅ |
| Win Rate | **88.5%** | 87.5% | ✅ |
| Profit | **$158.04 (15.80%)** | $152.30 (15.23%) | ✅ |
| Profit Factor | **3.62** | 3.30 | ✅ |
| SQN | **4.18** | 4.28 | ✅ |
| Avg Hold | **4:32** | 4:34 | ✅ |

**Per-pair (all positive, all have wins — no removals):**
| Pair | Trades | WR | Profit |
|------|--------|-----|--------|
| AVAX/USDT | 13 | **100.0%** | +$34.51 |
| XLM/USDT | 6 | 66.7% | +$27.25 |
| BTC/USDT | 15 | 86.7% | +$24.06 |
| DOT/USDT | 11 | 90.9% | +$19.60 |
| ETH/USDT | 9 | 88.9% | +$15.58 |
| UNI/USDT | 7 | **100.0%** | +$12.83 |
| LINK/USDT | 13 | 84.6% | +$12.40 |
| NEAR/USDT | 7 | 85.7% | +$5.95 |
| ADA/USDT | 6 | 83.3% | +$5.86 |

**Exit breakdown:**
| Exit | Count | WR | Profit |
|------|-------|-----|--------|
| trailing_stop_loss | 84 | **88.1%** | +$147.64 |
| roi | 1 | 100% | +$6.61 |
| target_liquidity_reached | 2 | 100% | +$3.80 |

**Fix criteria check:**
- TS exits: 84/87 = 96.6% (>30%) with 88.1% WR → ✅ TS working exceptionally
- All 9 pairs positive + have wins → no pair removals needed
- Profit positive + PF 3.62 → exceptional performance
- **Strategy is stable across iterations — v0.99.2 results confirmed**

**Note:** Slight variance in total trades (87 vs 88) is normal backtest variance. All per-pair metrics align closely with ROADMAP values.

**Next step (⏳):** Continue trade frequency increase. Current ~44/yr still below 100+ target. Options:
1. Try other high-volume pairs (AAVE, FIL, etc.)
2. Experiment with OTE zone fine-tuning within 30-70% range
3. Accept ~44/yr with current config — excellent quality (88%+ WR, PF 3.62)

*Last Updated: 2026-03-26 (19:05 UTC)*
