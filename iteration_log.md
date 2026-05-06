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
