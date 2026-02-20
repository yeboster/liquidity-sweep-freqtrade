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
