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

## Iteration v2: 2026-05-09 03:17:42
- Profit: 10.97% | Trades: 22 | WR: 90.9% | R/R: 0.3421 | SQN: 2.1969 | DD: 3.42%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=0(0%WR, $0.00), time=0(0%WR, $0.00)
- Changes: Loosen: dev 1.6→1.5, atr 0.9→0.9, v2.0.42→2.0.43
- Reason: General loosen to increase signals

## Iteration v2: 2026-05-09 05:17:41
- Profit: 12.67% | Trades: 25 | WR: 92.0% | R/R: 0.3279 | SQN: 2.5243 | DD: 3.42%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=0(0%WR, $0.00), time=0(0%WR, $0.00)
- Changes: Loosen: dev 1.5→1.4, atr 0.9→0.9, v2.0.43→2.0.44
- Reason: General loosen to increase signals

## Iteration v2: 2026-05-09 07:17:48
- Profit: 12.69% | Trades: 27 | WR: 88.9% | R/R: 0.4453 | SQN: 2.4897 | DD: 3.42%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=0(0%WR, $0.00), time=0(0%WR, $0.00)
- Changes: Loosen: dev 1.4→1.2999999999999998, atr 0.9→0.9, v2.0.44→2.0.45
- Reason: General loosen to increase signals

## Iteration v2: 2026-05-09 09:17:44
- Profit: 10.63% | Trades: 31 | WR: 80.7% | R/R: 0.5910 | SQN: 1.9303 | DD: 4.75%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=0(0%WR, $0.00), time=0(0%WR, $0.00)
- Changes: Loosen: dev 1.3→1.2, atr 0.9→0.9, v2.0.45→2.0.46
- Reason: General loosen to increase signals

## Iteration v2: 2026-05-09 11:17:50
- Profit: 7.19% | Trades: 35 | WR: 77.1% | R/R: 0.4904 | SQN: 1.1119 | DD: 4.75%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=0(0%WR, $0.00), time=0(0%WR, $0.00)
- Changes: Loosen: dev 1.2→1.0999999999999999, atr 0.9→0.9, v2.0.46→2.0.47
- Reason: General loosen to increase signals

## Iteration v2: 2026-05-09 13:17:50
- Profit: 1.24% | Trades: 38 | WR: 68.4% | R/R: 0.5033 | SQN: 0.1308 | DD: 8.44%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=1(0%WR, $-63.95), time=0(0%WR, $0.00)
- Changes: Loosen: dev 1.1→1.0, atr 0.9→0.9, v2.0.48→2.0.49
- Reason: General loosen to increase signals

## Iteration v2: 2026-05-09 15:17:41
- Profit: 0.75% | Trades: 46 | WR: 67.4% | R/R: 0.5119 | SQN: 0.0761 | DD: 8.18%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=1(0%WR, $-64.11), time=0(0%WR, $0.00)
- Changes: Loosen: dev 1.0→1.0, atr 0.9→0.9, v2.0.49→2.0.50
- Reason: General loosen to increase signals

## Iteration v2: 2026-05-09 17:19:54
- Profit: 3.10% | Trades: 11 | WR: 72.7% | R/R: 0.6105 | SQN: 0.5885 | DD: 3.39%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=1(0%WR, $-34.63), time=0(0%WR, $0.00)
- Changes: Low volume: dev 2.0→1.7, atr 0.9→1.0, vol 1.2→1.0999999999999999, v2.0.51→2.0.52
- Reason: Too few trades — need more entry signals

## Iteration v2: 2026-05-09 19:20:21
- Profit: -5.10% | Trades: 64 | WR: 68.8% | R/R: 0.4094 | SQN: -0.3967 | DD: 12.17%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=10(0%WR, $-324.71), time=0(0%WR, $0.00)
- Changes: Fix R/R: trail 0.03→0.03, offset 0.1→0.10500000000000001, stop -0.1→-0.097, v2.0.52→2.0.53
- Reason: R/R broken — trailing stop too tight vs stop loss

## Iteration v2: 2026-05-09 20:00:14
- Profit: 1.90% | Trades: 5 | WR: 80.0% | R/R: 0.5421 | SQN: 0.6611 | DD: 1.64%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=0(0%WR, $0.00), time=0(0%WR, $0.00)
- Changes: Low volume: dev 1.7→1.4, atr 0.85→1.0, vol 1.3→1.2, v2.0.54→2.0.55
- Reason: Too few trades — need more entry signals

## Iteration v2: 2026-05-09 20:11:54
- Profit: 0.76% | Trades: 5 | WR: 80.0% | R/R: 0.3247 | SQN: 0.1949 | DD: 2.73%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=1(0%WR, $-28.00), time=0(0%WR, $0.00)
- Changes: Low volume: dev 1.6→1.3, atr 0.85→1.0, vol 1.35→1.25, v2.0.56→2.0.57
- Reason: Too few trades — need more entry signals

## Iteration v2: 2026-05-09 21:19:53
- Profit: -17.43% | Trades: 80 | WR: 61.2% | R/R: 0.4290 | SQN: -1.4299 | DD: 18.25%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=19(0%WR, $-469.52), time=0(0%WR, $0.00)
- Changes: Fix R/R: trail 0.03→0.03, offset 0.105→0.11, stop -0.08→-0.077, v2.0.57→2.0.58
- Reason: R/R broken — trailing stop too tight vs stop loss

## Iteration v2: 2026-05-09 23:19:52
- Profit: -0.99% | Trades: 3 | WR: 66.7% | R/R: 0.3198 | SQN: -0.2641 | DD: 2.63%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=1(0%WR, $-26.79), time=0(0%WR, $0.00)
- Changes: Low volume: dev 2.0→1.7, atr 0.85→1.0, vol 1.35→1.25, v2.0.59→2.0.60
- Reason: Too few trades — need more entry signals

## Iteration v2: 2026-05-10 01:19:52
- Profit: 0.73% | Trades: 3 | WR: 66.7% | R/R: 0.9004 | SQN: 0.3304 | DD: 0.94%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=0(0%WR, $0.00), time=0(0%WR, $0.00)
- Changes: Low volume: dev 2.0→1.7, atr 0.85→1.0, vol 1.35→1.25, v2.0.61→2.0.62
- Reason: Too few trades — need more entry signals

## Iteration v2: 2026-05-10 03:19:54
- Profit: 1.70% | Trades: 54 | WR: 72.2% | R/R: 0.4152 | SQN: 0.1641 | DD: 7.34%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=5(0%WR, $-168.33), time=0(0%WR, $0.00)
- Changes: Fix R/R: trail 0.03→0.03, offset 0.11→0.115, stop -0.1→-0.097, v2.0.62→2.0.63
- Reason: R/R broken — trailing stop too tight vs stop loss

## Iteration v2: 2026-05-10 05:19:53
- Profit: 1.05% | Trades: 54 | WR: 72.2% | R/R: 0.4061 | SQN: 0.0993 | DD: 7.06%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=6(0%WR, $-198.13), time=0(0%WR, $0.00)
- Changes: Fix R/R: trail 0.03→0.03, offset 0.115→0.12000000000000001, stop -0.097→-0.094, v2.0.63→2.0.64
- Reason: R/R broken — trailing stop too tight vs stop loss

## Iteration v2: 2026-05-10 07:19:54
- Profit: 1.67% | Trades: 54 | WR: 72.2% | R/R: 0.4148 | SQN: 0.1612 | DD: 6.76%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=6(0%WR, $-192.63), time=0(0%WR, $0.00)
- Changes: Fix R/R: trail 0.03→0.03, offset 0.12→0.125, stop -0.094→-0.091, v2.0.64→2.0.65
- Reason: R/R broken — trailing stop too tight vs stop loss

## Iteration v2: 2026-05-10 09:19:58
- Profit: -9.71% | Trades: 34 | WR: 55.9% | R/R: 0.5188 | SQN: -1.1682 | DD: 11.18%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=15(0%WR, $-271.73), time=0(0%WR, $0.00)
- Changes: Too many stop-outs: tighten stop -0.055→-0.052, v2.0.72→2.0.73
- Reason: Negative profit — R/R problem or bad entries

## Iteration v2: 2026-05-10 11:19:54
- Profit: -10.26% | Trades: 34 | WR: 52.9% | R/R: 0.5684 | SQN: -1.2588 | DD: 11.99%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=16(0%WR, $-274.57), time=0(0%WR, $0.00)
- Changes: Too many stop-outs: tighten stop -0.052→-0.048999999999999995, v2.0.73→2.0.74
- Reason: Negative profit — R/R problem or bad entries

## Iteration v2: 2026-05-10 13:19:53
- Profit: -0.02% | Trades: 11 | WR: 63.6% | R/R: 0.5793 | SQN: -0.0030 | DD: 3.22%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=4(0%WR, $-76.97), time=0(0%WR, $0.00)
- Changes: Low volume: dev 2.0→1.7, atr 0.9→1.0, vol 1.2→1.0999999999999999, v2.0.77→2.0.78
- Reason: Too few trades — need more entry signals

## Iteration v2: 2026-05-10 15:20:06
- Profit: -7.48% | Trades: 65 | WR: 63.1% | R/R: 0.4898 | SQN: -0.6799 | DD: 12.29%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=23(0%WR, $-420.50), time=1(100%WR, $2.00)
- Changes: Fix R/R: trail 0.03→0.03, offset 0.125→0.13, stop -0.055→-0.052, v2.0.78→2.0.79
- Reason: R/R broken — trailing stop too tight vs stop loss

## Iteration v2: 2026-05-10 17:19:52
- Profit: -7.29% | Trades: 65 | WR: 61.5% | R/R: 0.5244 | SQN: -0.6748 | DD: 13.08%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=24(0%WR, $-417.01), time=1(100%WR, $1.99)
- Changes: Too many stop-outs: tighten stop -0.052→-0.048999999999999995, v2.0.79→2.0.80
- Reason: Negative profit — R/R problem or bad entries

## Iteration v2: 2026-05-10 19:19:52
- Profit: -1.04% | Trades: 49 | WR: 69.4% | R/R: 0.4327 | SQN: -0.1071 | DD: 7.59%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=7(0%WR, $-196.55), time=11(0%WR, $-68.80)
- Changes: Fix R/R: trail 0.03→0.03, offset 0.13→0.135, stop -0.085→-0.082, v2.0.83→2.0.84
- Reason: R/R broken — trailing stop too tight vs stop loss

## Iteration v2: 2026-05-10 21:19:54
- Profit: 1.54% | Trades: 49 | WR: 69.4% | R/R: 0.4755 | SQN: 0.1634 | DD: 7.69%
- Exit breakdown: trailing=0(0%WR, $0.00), stop=5(0%WR, $-149.91), time=12(0%WR, $-90.32)
- Changes: Fix R/R: trail 0.03→0.03, offset 0.135→0.14, stop -0.09→-0.087, v2.0.87→2.0.88
- Reason: R/R broken — trailing stop too tight vs stop loss
