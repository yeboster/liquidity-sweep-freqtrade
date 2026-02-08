# Liquidity Sweep Reversal Strategy
**Source**: https://dailypriceaction.com/blog/liquidity-sweep-reversals/
**Timeframe**: 15-Minute (Entry), 1H/4H (Context)
*   *Note*: 5m or 1m timeframes are possible, but 15m is preferred to filter noise ("sweet spot").
*   *Fractal Note*: Source charts often show the setup on the 1H timeframe for readability. The pattern is fractal and can appear on HTF, but execution is standard on 15m.
**Asset Class**: Forex (EURUSD example), applicable to others.

## Core Concepts
1.  **Market Structure**: Trade with the Higher Time Frame (HTF) trend.
    *   *Visuals*: Charts use **BoS** (Break of Structure) markers to confirm the trend (e.g., lower lows in a downtrend).
2.  **Liquidity Sweep**: A move beyond a key high/low to take stops before reversing.
    *   *Vs ChoCH*: The sweep entry is significantly faster ("top entry"). Visual analysis (Chart 1) shows it can confirm ~25 pips earlier than a full Change of Character (ChoCH). We enter on the "internal" break (Triggering Low) rather than waiting for an external structure break.
    *   *Why it works*: A wick on the 15m often looks like a "break and close" on the 1m chart. This traps lower-timeframe traders into the wrong direction just before the reversal.
3.  **OTE (Optimal Trade Entry)**: Fibonacci retracement **62% - 79%** of the external range.
    *   *Chart Visuals*: Often show **0.62, 0.705, and 0.79** levels.
4.  **Mean Reversion (Context)**: Price often moves in "Distribution Channels" around a mean.
    *   *Visual*: Parallel lines (channel) descending or ascending. Price oscillates around the center dotted line (**Mean/Average Price**).
    *   *Key Visual*: Look for price pushing *outside* the channel boundaries. Charts label these extremes as **"Buy-side distributions"** (top) and **"Sell-side distributions"** (bottom).
    *   *Logic*: When price extends far from the mean into OTE (Buy-side distribution in a downtrend), a snap-back is highly probable.

## Logic Steps (Short Setup)

### 1. Context & Setup (HTF)
*   **Condition**: Identify Bearish Market Structure on 1H/4H (Lower Highs, Lower Lows).
*   **Condition**: Price must retrace into **OTE** (62% - 79% of the recent external range).
    *   *Fib Drawing*: From the external High (1.0) to the external Low (0.0).
    *   *Rule*: If price is not in OTE (above 0.62), no trade.
*   **Action**: Switch to 15m timeframe once price is in OTE.

### 2. Pattern Formation (15m)
*   **Step 1 (Liquidity Build)**: A swing high forms *inside* the OTE zone.
    *   *Visual*: Look for a clean level where retail stops would logically accumulate ("Liquidity Pool"). Charts often show a **flat top** (double/triple tap) or small consolidation zone just prior to the sweep. This "builds" the liquidity for the grab.
*   **Step 2 (The Sweep)**: Price wicks *above* this swing high.
    *   *Note*: Candle body can close above or below, but the high MUST exceed the previous swing high. The size of the sweep (5 pips vs 50 pips) does not matter.
    *   *Key*: This is the "Sweep" or "Grab" of buy-side liquidity.
*   **Step 3 (Confirmation)**: Price must **CLOSE** below the "Triggering Low".
    *   *Definition*: The **Triggering Low** is the most recent **internal structure low** or **consolidation floor** (specifically the lowest wick) that launched the price up into the sweep. While often a clear swing low, visual analysis shows it can be the immediate low of the small consolidation preceding the sweep.
    *   **Logic**: `Current_Close < Triggering_Internal_Low_Wick`
    *   **Significance**: Shows acceptance back inside the range.
    *   **Visual Tip*: The confirmation candle should ideally have a **strong body closing near its low**, indicating genuine selling conviction rather than indecision.
    *   **Invalidation (Breakout)**: If price fails to close below the triggering low and instead holds/consolidates above the sweep high, this is a **Breakout**, not a sweep. Abort the setup.

### 3. Execution
*   **Trigger**: On the **Close** of the confirmation candle (Step 3).
*   **Entry**:
    *   **Option A (Standard)**: Market Sell on the close. Use this if the move is clean and leaves no massive imbalance.
    *   **Option B (Refined)**: If the confirmation move created a large, unmitigated **Fair Value Gap (FVG)**, place a Limit Sell at the FVG to catch the retrace.
*   **Stop Loss**:
    *   **Conservative (Recommended)**: Above the Sweep High + Buffer (2-5 pips).
        *   *Pro Tip*: **Do not place the stop exactly on the high.** The buffer is critical. It avoids being stopped out by a secondary sweep ("double tap") before the move triggers. This small tweak can improve win rate by 10-15%.
    *   **Aggressive**: Above the internal structure lower high (Higher risk of stop hunt).
*   **Take Profit**:
    *   **Target 1**: Recent External Swing Low (Sell-side Liquidity).
    *   **Requirement**: Minimum Reward-to-Risk (R:R) of 2R; prefer 3R.

## Logic Steps (Long Setup - Inverse)
*   **Context**: Bullish Structure (Higher Highs) on 1H/4H.
*   **Setup**: Price retraces to OTE (Discount).
*   **Pattern**:
    1.  Swing Low forms in OTE.
    2.  Price sweeps *below* the swing low.
    3.  Price **CLOSES** above the "Triggering High" (the swing high that launched the sweep).
*   **Entry**: Buy on Close (or retrace to FVG).
*   **SL**: Below Sweep Low - Buffer.
*   **TP**: Recent External High.

## Iteration Log

| Date       | Version | Change                                      | Author |
|------------|---------|---------------------------------------------|--------|
| 2026-02-08 | 0.6.0   | Added Strong Close confirmation (Internal BoS) | Jarvis |
| 2026-02-08 | 0.5.0   | Implemented HTF Market Structure (BoS)      | Jarvis |
| 2026-02-08 | 0.4.0   | Improved triggering swing logic (rolling win) | Jarvis |
| 2026-02-07 | 0.3.0   | Added take profit at external swing levels  | Jarvis |
| 2026-02-07 | 0.2.0   | Added FVG (Fair Value Gap) detection logic  | Jarvis |
| 2026-01-26 | 0.1.0   | Initial Strategy Implementation             | Jarvis |

## Roadmap

- [x] Initial Strategy Skeleton
- [x] OTE Zone Calculation
- [x] Basic Sweep Detection
- [x] FVG Detection (Refined Entry)
- [x] Improved Triggering Swing Logic
- [x] Take Profit at External Swing Levels
- [x] Break of Structure (BoS) Confirmation (Internal Strong Close)
- [x] Market Structure Trend (HTF BoS)
- [ ] Hyperopt Optimization

## Pseudo-Code Representation

```python
def check_liquidity_sweep_short(candles_15m, trend_1h):
    # 1. Check Trend
    if trend_1h != "BEARISH":
        return False

    # 2. Check OTE
    swing_high, swing_low = get_external_range(trend_1h)
    fib_level = get_current_retracement(swing_high, swing_low)
    if not (0.62 <= fib_level <= 0.79):
        return False

    # 3. Detect Sweep
    # Look for recent local high in OTE where liquidity built up
    local_high = find_liquidity_pool(candles_15m[-20:]) 
    
    # Check if current/recent candle swept it
    latest_candle = candles_15m[-1]
    if latest_candle.high > local_high.high:
        # Check Confirmation (Step 3)
        # Find the swing low that initiated the move to local_high
        triggering_low = get_last_swing_low(candles_15m, before=latest_candle)
        
        # MUST Close below the triggering low
        if latest_candle.close < triggering_low.low:
            has_large_fvg = check_fvg(candles_15m)
            entry_type = "LIMIT" if has_large_fvg else "MARKET"
            
            return {
                "signal": "SELL",
                "entry_type": entry_type,
                "stop_loss": latest_candle.high + 0.0005, # +5 pips buffer
                "take_profit": swing_low
            }
            
    return False
```
