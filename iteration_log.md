# Iteration Completed: Fixed Custom SL (Anchor to Entry) + Tuned ROI

**Project:** `projects/liquidity-sweep-freqtrade`
**Version:** 0.17.0

**Changes:**
1.  **Fixed Custom SL:** Anchored stoploss calculation to `trade.open_rate` instead of `current_rate` (or so I thought).
2.  **Tuned ROI:** Tightened ROI to 10% @ 0m, 5% @ 60m.

**Results (v0.17.0):**
-   **Total Trades:** 617 (Volume is good)
-   **Win Rate:** 19.9% (Low)
-   **Profit Mean:** -0.38%
-   **Avg Hold:** 1h 15m
-   **Exit Reasons:**
    -   `trailing_stop_loss`: 486 trades (78%) - **MAJOR ISSUE**
    -   `stop_loss`: 92 trades
    -   `roi`: 33 trades (+2.94% avg - High Quality)

**Analysis:**
I accidentally created a **trailing stop**.
By returning a fixed percentage (e.g. -0.05 based on entry) from `custom_stoploss`, Freqtrade applied that percentage to the *current price* at every step.
-   Entry: 100. Target SL: 95. I return -0.05. SL set at 95.
-   Price moves to 102. I return -0.05. SL moves to 96.9 (Trails up).
-   Price retraces to 97. Stopped out at 96.9 (Loss).
-   Original Fixed SL at 95 would have survived.

**Action Plan (v0.18.0):**
Fix `custom_stoploss` to calculate percentage relative to **current_rate** so that the target price remains fixed.
Formula: `(target_sl_price - current_rate) / current_rate`.

## Iteration: 2026-05-06 01:09:39
- Profit: -32.98% | Trades: 192 | WR: 48.96% | R/R: 0.3836 | DD: None%
- Changes: Loosen: dev 1.2→1.2, atr 1.0→0.8, Version: 1.0.7→1.0.8
- Reason: profit < 10% — loosen filters (lower dev threshold, widen ATR compression)

## Iteration: 2026-05-06 03:05:48
- Profit: -2.53% | Trades: 8 | WR: 50.0% | R/R: 0.3092 | DD: 2.5337%
- Changes: Loosen: dev 1.2→1.2, atr 0.8→0.8, Version: 1.0.8→1.0.9
- Reason: profit < 10% — loosen filters (lower dev threshold, widen ATR compression)

## Iteration: 2026-05-06 05:05:45
- Profit: -2.53% | Trades: 8 | WR: 50.0% | R/R: 0.3092 | DD: 2.5337%
- Changes: Loosen: dev 1.2→1.2, atr 0.8→0.8, Version: 1.0.9→1.0.10
- Reason: profit < 10% — loosen filters (lower dev threshold, widen ATR compression)

## Iteration: 2026-05-06 07:05:53
- Profit: -2.53% | Trades: 8 | WR: 50.0% | R/R: 0.3092 | DD: 2.5337%
- Changes: Loosen: dev 1.2→1.2, atr 0.8→0.8, Version: 1.0.10→1.0.11
- Reason: profit < 10% — loosen filters (lower dev threshold, widen ATR compression)

## Iteration: 2026-05-06 09:05:54
- Profit: -2.53% | Trades: 8 | WR: 50.0% | R/R: 0.3092 | DD: 2.5337%
- Changes: Loosen: dev 1.2→1.2, atr 0.8→0.8, Version: 1.0.11→1.0.12
- Reason: profit < 10% — loosen filters (lower dev threshold, widen ATR compression)

## Iteration: 2026-05-06 11:05:46
- Profit: -2.53% | Trades: 8 | WR: 50.0% | R/R: 0.3092 | DD: 2.5337%
- Changes: Loosen: dev 1.2→1.2, atr 0.8→0.8, Version: 1.0.12→1.0.13
- Reason: profit < 10% — loosen filters (lower dev threshold, widen ATR compression)

## Iteration: 2026-05-06 13:05:44
- Profit: -2.53% | Trades: 8 | WR: 50.0% | R/R: 0.3092 | DD: 2.5337%
- Changes: Loosen: dev 1.2→1.2, atr 0.8→0.8, Version: 1.0.13→1.0.14
- Reason: profit < 10% — loosen filters (lower dev threshold, widen ATR compression)

## Iteration: 2026-05-06 15:05:41
- Profit: -2.53% | Trades: 8 | WR: 50.0% | R/R: 0.3092 | DD: 2.5337%
- Changes: Loosen: dev 1.2→1.2, atr 0.8→0.8, Version: 1.0.14→1.0.15
- Reason: profit < 10% — loosen filters (lower dev threshold, widen ATR compression)

## Iteration: 2026-05-06 17:05:48
- Profit: -2.53% | Trades: 8 | WR: 50.0% | R/R: 0.3092 | DD: 2.5337%
- Changes: Loosen: dev 1.2→1.2, atr 0.8→0.8, Version: 1.0.15→1.0.16
- Reason: profit < 10% — loosen filters (lower dev threshold, widen ATR compression)

## Iteration: 2026-05-06 19:05:42
- Profit: -2.53% | Trades: 8 | WR: 50.0% | R/R: 0.3092 | DD: 2.5337%
- Changes: Loosen: dev 1.2→1.2, atr 0.8→0.8, Version: 1.0.16→1.0.17
- Reason: profit < 10% — loosen filters (lower dev threshold, widen ATR compression)

## Iteration v2: 2026-05-06 21:05:41
- Profit: -6.02% | Trades: 29 | WR: 55.2% | R/R: 0.4988 | SQN: -1.1495 | DD: 6.83%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=11(0%WR, $-150.42), time=0(0%WR, $0.00)
- Changes: Fix R/R: trail 0.015→0.02, offset 0.03→0.034999999999999996, stop -0.04→-0.037, v2.0.0→2.0.1
- Reason: R/R broken — trailing stop too tight vs stop loss

## Iteration v2: 2026-05-06 23:05:41
- Profit: -6.22% | Trades: 29 | WR: 55.2% | R/R: 0.4922 | SQN: -1.2150 | DD: 6.69%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=12(0%WR, $-152.59), time=0(0%WR, $0.00)
- Changes: Fix R/R: trail 0.02→0.025, offset 0.035→0.04, stop -0.037→-0.033999999999999996, v2.0.1→2.0.2
- Reason: R/R broken — trailing stop too tight vs stop loss

## Iteration v2: 2026-05-07 01:05:44
- Profit: -3.88% | Trades: 29 | WR: 62.1% | R/R: 0.4490 | SQN: -0.6838 | DD: 4.68%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=8(0%WR, $-137.57), time=0(0%WR, $0.00)
- Changes: Fix R/R: trail 0.025→0.03, offset 0.04→0.045, stop -0.05→-0.047, v2.0.3→2.0.4
- Reason: R/R broken — trailing stop too tight vs stop loss

## Iteration v2: 2026-05-07 01:11:11
- Profit: -4.98% | Trades: 29 | WR: 58.6% | R/R: 0.4755 | SQN: -0.8938 | DD: 6.15%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=9(0%WR, $-144.40), time=0(0%WR, $0.00)
- Changes: Fix R/R: trail 0.03→0.03, offset 0.045→0.049999999999999996, stop -0.08→-0.077, v2.0.5→2.0.6
- Reason: R/R broken — trailing stop too tight vs stop loss

## Iteration v2: 2026-05-07 03:05:47
- Profit: -1.09% | Trades: 34 | WR: 73.5% | R/R: 0.3375 | SQN: -0.1600 | DD: 3.62%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=5(0%WR, $-132.77), time=0(0%WR, $0.00)
- Changes: Fix R/R: trail 0.03→0.03, offset 0.05→0.055, stop -0.077→-0.074, v2.0.6→2.0.7
- Reason: R/R broken — trailing stop too tight vs stop loss

## Iteration v2: 2026-05-07 05:05:42
- Profit: 2.36% | Trades: 34 | WR: 76.5% | R/R: 0.3791 | SQN: 0.3485 | DD: 4.90%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=2(0%WR, $-80.70), time=0(0%WR, $0.00)
- Changes: Fix R/R: trail 0.03→0.03, offset 0.055→0.06, stop -0.12→-0.11699999999999999, v2.0.8→2.0.9
- Reason: R/R broken — trailing stop too tight vs stop loss

## Iteration v2: 2026-05-07 07:17:42
- Profit: 2.57% | Trades: 34 | WR: 76.5% | R/R: 0.3860 | SQN: 0.3863 | DD: 4.70%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=2(0%WR, $-78.77), time=0(0%WR, $0.00)
- Changes: Fix R/R: trail 0.03→0.03, offset 0.06→0.065, stop -0.117→-0.114, v2.0.9→2.0.10
- Reason: R/R broken — trailing stop too tight vs stop loss

## Iteration v2.0.16 [research]: 2026-05-07 15:24
- Profit: 6.45% | Trades: 34 | WR: 82.3% | R/R: 0.3341 | SQN: 0.9025 | DD: 3.97%
- Exit breakdown: exit_signal=32(87.5%WR, $141.59, mean 1.34%), stop=2(0%WR, $-77.05, mean -11.66%)
- Changes: minimal_roi 8%→4%, exit_dev_revert_pct 0.0→0.5%
- Reason: Research — 8% ROI forced premature exit (avg win only $1.01). Partial reversion more realistic than exact SMA. Mean reversion optimal: WR 70-80%, R/R 1:1-1.5.

## Iteration v2: 2026-05-07 17:17:41
- Profit: 6.45% | Trades: 34 | WR: 82.3% | R/R: 0.3341 | SQN: 0.9025 | DD: 3.97%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=2(0%WR, $-77.05), time=0(0%WR, $0.00)
- Changes: Fix R/R: trail 0.03→0.03, offset 0.065→0.07, stop -0.114→-0.111, v2.0.16→2.0.17
- Reason: R/R broken — trailing stop too tight vs stop loss

## Iteration v2: 2026-05-07 19:17:41
- Profit: 6.67% | Trades: 34 | WR: 82.3% | R/R: 0.3398 | SQN: 0.9473 | DD: 3.77%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=2(0%WR, $-75.12), time=0(0%WR, $0.00)
- Changes: Fix R/R: trail 0.03→0.03, offset 0.07→0.07500000000000001, stop -0.111→-0.108, v2.0.17→2.0.18
- Reason: R/R broken — trailing stop too tight vs stop loss

## Iteration v2: 2026-05-07 21:17:41
- Profit: 6.89% | Trades: 34 | WR: 82.3% | R/R: 0.3458 | SQN: 0.9934 | DD: 3.66%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=2(0%WR, $-73.18), time=0(0%WR, $0.00)
- Changes: Fix R/R: trail 0.03→0.03, offset 0.075→0.08, stop -0.108→-0.105, v2.0.18→2.0.19
- Reason: R/R broken — trailing stop too tight vs stop loss

## Iteration v2: 2026-05-07 23:17:42
- Profit: 12.09% | Trades: 34 | WR: 85.3% | R/R: 0.4438 | SQN: 2.1326 | DD: 3.42%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=0(0%WR, $0.00), time=0(0%WR, $0.00)
- Changes: Loosen: dev 1.5→1.4, atr 0.95→0.9, v2.0.22→2.0.23
- Reason: General loosen to increase signals

## Iteration v2: 2026-05-08 01:17:47
- Profit: 5.95% | Trades: 31 | WR: 77.4% | R/R: 0.4903 | SQN: 1.0491 | DD: 3.42%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=0(0%WR, $0.00), time=0(0%WR, $0.00)
- Changes: Loosen: dev 1.2→1.0999999999999999, atr 0.9→0.9, v2.0.24→2.0.25
- Reason: General loosen to increase signals

## Iteration v2: 2026-05-08 03:17:51
- Profit: -0.75% | Trades: 34 | WR: 73.5% | R/R: 0.3516 | SQN: -0.0828 | DD: 6.74%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=1(0%WR, $-69.45), time=0(0%WR, $0.00)
- Changes: Fix R/R: trail 0.03→0.03, offset 0.08→0.085, stop -0.2→-0.197, v2.0.26→2.0.27
- Reason: R/R broken — trailing stop too tight vs stop loss

## Iteration v2: 2026-05-08 05:17:45
- Profit: -0.64% | Trades: 34 | WR: 73.5% | R/R: 0.3539 | SQN: -0.0718 | DD: 6.65%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=1(0%WR, $-68.42), time=0(0%WR, $0.00)
- Changes: Fix R/R: trail 0.03→0.03, offset 0.085→0.09000000000000001, stop -0.197→-0.194, v2.0.28→2.0.29
- Reason: R/R broken — trailing stop too tight vs stop loss

## Iteration v2: 2026-05-08 07:17:43
- Profit: -0.54% | Trades: 34 | WR: 73.5% | R/R: 0.3562 | SQN: -0.0606 | DD: 6.55%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=1(0%WR, $-67.40), time=0(0%WR, $0.00)
- Changes: Fix R/R: trail 0.03→0.03, offset 0.09→0.095, stop -0.194→-0.191, v2.0.30→2.0.31
- Reason: R/R broken — trailing stop too tight vs stop loss

## Iteration v2: 2026-05-08 09:18:02
- Profit: -2.90% | Trades: 34 | WR: 64.7% | R/R: 0.4721 | SQN: -0.3072 | DD: 7.74%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=1(0%WR, $-67.16), time=0(0%WR, $0.00)
- Changes: Fix R/R: trail 0.03→0.03, offset 0.095→0.1, stop -0.191→-0.188, v2.0.32→2.0.33
- Reason: R/R broken — trailing stop too tight vs stop loss

## Iteration v2: 2026-05-08 13:17:43
- Profit: 4.55% | Trades: 22 | WR: 68.2% | R/R: 0.6951 | SQN: 0.7207 | DD: 3.82%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=0(0%WR, $0.00), time=0(0%WR, $0.00)
- Changes: Loosen: dev 1.5→1.4, atr 0.9→0.9, v2.0.34→2.0.35
- Reason: General loosen to increase signals

## Iteration v2: 2026-05-08 15:17:43
- Profit: 4.97% | Trades: 24 | WR: 66.7% | R/R: 0.7564 | SQN: 0.7802 | DD: 3.82%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=0(0%WR, $0.00), time=0(0%WR, $0.00)
- Changes: Loosen: dev 1.4→1.2999999999999998, atr 0.9→0.9, v2.0.35→2.0.36
- Reason: General loosen to increase signals

## Iteration v2: 2026-05-08 17:18:10
- Profit: 5.13% | Trades: 27 | WR: 63.0% | R/R: 0.8842 | SQN: 0.8002 | DD: 3.82%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=0(0%WR, $0.00), time=0(0%WR, $0.00)
- Changes: Loosen: dev 1.3→1.2, atr 0.9→0.9, v2.0.36→2.0.37
- Reason: General loosen to increase signals

## Iteration v2: 2026-05-08 21:17:44
- Profit: 3.96% | Trades: 31 | WR: 61.3% | R/R: 0.8287 | SQN: 0.5631 | DD: 4.03%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=0(0%WR, $0.00), time=0(0%WR, $0.00)
- Changes: Loosen: dev 1.2→1.0999999999999999, atr 0.9→0.9, v2.0.37→2.0.38
- Reason: General loosen to increase signals

## Iteration v2: 2026-05-08 23:17:43
- Profit: -1.53% | Trades: 34 | WR: 61.8% | R/R: 0.5842 | SQN: -0.1585 | DD: 6.58%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=1(0%WR, $-65.70), time=0(0%WR, $0.00)
- Changes: Too many stop-outs: tighten stop -0.188→-0.185, v2.0.38→2.0.39
- Reason: Negative profit — R/R problem or bad entries

## Iteration v2: 2026-05-08 23:58:40
- Profit: 0.08% | Trades: 1 | WR: 100.0% | R/R: 0.0000 | SQN: -100.0000 | DD: 0.00%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=0(0%WR, $0.00), time=0(0%WR, $0.00)
- Changes: Low volume: dev 2.0→1.7, atr 0.8→0.9500000000000001, vol 1.3→1.2, v2.0.40→2.0.41
- Reason: Too few trades — need more entry signals

## Iteration v2: 2026-05-09 01:17:42
- Profit: 11.11% | Trades: 33 | WR: 81.8% | R/R: 0.4703 | SQN: 1.7031 | DD: 3.42%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=0(0%WR, $0.00), time=0(0%WR, $0.00)
- Changes: Loosen: dev 1.7→1.5999999999999999, atr 0.95→0.9, v2.0.41→2.0.42
- Reason: General loosen to increase signals
