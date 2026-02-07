# Iteration Completed: Improved Swing Detection

**Project:** `projects/liquidity-sweep-freqtrade`
**Version:** 0.1.1

**Changes:**
1.  **Removed Lookahead Bias:** The original `rolling(lookback, center=True)` function was removed. This function used future data to determine swings, which is invalid for live trading.
2.  **Implemented Proper Pivot Detection:**
    -   Added `pivot_lookback` parameter (default 3 candles).
    -   Implemented a lag-based fractal/pivot detection: A swing is confirmed only after `pivot_lookback` candles have passed where the central candle remains the highest/lowest.
    -   This introduces a realistic delay in signal generation but ensures robustness.
3.  **Updated Logic:**
    -   Replaced `_detect_swings` entirely with the new logic.
    -   Updated `populate_indicators` to use `pivot_lookback`.

**Next Steps:**
-   Backtest the new logic (expect fewer signals but higher quality).
-   Consider adding FVG detection in the next iteration.

**Commit:** `9171d54` - "Iteration: Improve swing detection (remove lookahead bias, use pivot logic)"
