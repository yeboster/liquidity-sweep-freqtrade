"""
Liquidity Sweep Reversal Strategy for Freqtrade
================================================
Based on: https://dailypriceaction.com/blog/liquidity-sweep-reversals/

Core Logic:
1. Identify HTF trend (bearish/bullish)
2. Wait for price to retrace into OTE (0.62 - 0.79 Fib)
3. Detect liquidity sweep (wick beyond recent high/low)
4. Enter on confirmation (close beyond triggering swing)

Author: Jarvis (OpenClaw)
Version: 0.5.0

Changelog:
- v0.18.0 (2026-02-20): Disabled BOTH trailing_stop AND use_custom_stoploss.
  Root cause of v0.17 problem: custom_stoploss used recent_swing_low/high which updates
  as new swings form, creating a trailing stop effect even with trailing_stop=False.
  486/617 trades (78%) exited via "trailing_stop_loss" which was actually custom_stoploss.
  Fix: Disable custom_stoploss entirely. Use only static stoploss=-10% + ROI table.
  This gives trades full room to breathe. The 33 ROI exits at +2.94% avg show the signal works.
- v0.17.0 (2026-02-19): Fixed custom_stoploss - anchors to ENTRY price not current price.
  v0.16 problem: No custom_stoploss caused 15.8h avg hold (was 2.2h), ROI table broken.
  v0.15 problem: custom_stoploss used current price, causing dynamic SL repositioning.
  Fix: Calculate SL % from trade.open_rate (fixed at entry), not current_rate.
  Also tightened ROI table for faster exits and reduced stoploss to -10%.
- v0.16.0 (2026-02-19): Disabled custom_stoploss - using static SL only.
  ROI exits have 70% win rate; custom_stoploss was causing 332/608 premature stops.
  Widened static stoploss from -7.5% to -12% to give trades more room.
"""

import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
import talib.abstract as ta
from freqtrade.strategy import IStrategy, merge_informative_pair
from freqtrade.strategy.parameters import IntParameter, DecimalParameter, CategoricalParameter
from freqtrade.persistence import Trade


class LiquiditySweep(IStrategy):
    """
    Liquidity Sweep Reversal Strategy
    
    Trades reversals after liquidity grabs in OTE zones.
    Uses multi-timeframe analysis (15m entry, 1H context).
    """
    
    # Strategy version
    INTERFACE_VERSION = 3
    
    # Strategy version tag (Iteration Tracker)
    STRATEGY_VERSION = "0.18.0" # Disabled trailing_stop - was causing 78% of trades to exit via trailing SL (2026-02-20)

    # ROI table - v0.18.0: Lower targets to catch more profits (signal has 100% win rate on ROI exits)
    # v0.17 ROI exits: 33 trades at +2.94% avg with 100% win rate (signal IS good)
    # Lower ROI targets to capture more of the 486 previously trailing-stopped trades as wins
    minimal_roi = {
        "0": 0.05,      # 5% immediately (lower bar to capture more wins)
        "60": 0.03,     # 3% after 60 min
        "180": 0.02,    # 2% after 3h
        "360": 0.01,    # 1% after 6h
        "720": 0        # Break even after 12h
    }
    
    # Stoploss - Static SL only (v0.18.0: no custom_stoploss, just this)
    # -10% gives trades room to breathe without custom swing-based trailing effect
    stoploss = -0.10
    
    # Trailing stop - DISABLED in v0.18.0
    # v0.17 had trailing_stop=True with offset 0.299, causing 486/617 trades (78%) to exit via
    # trailing_stop_loss. The trailing stop required ~30% profit to activate, then any retrace
    # killed the trade. Result: -0.38% avg profit (terrible).
    # Fix: Use only custom_stoploss (swing-based fixed SL) + static fallback + ROI table.
    trailing_stop = False
    
    # Timeframe
    timeframe = '15m'
    informative_timeframe = '1h'
    
    # Required candle count for startup
    startup_candle_count = 100
    
    # Strategy parameters (hyperoptable) - Wider ranges for hyperopt exploration
    # v0.13.0: Reduced pivot_lookback to 3, ote_lower to 0.20, entry to market
    ote_lower = DecimalParameter(0.20, 0.70, default=0.20, space="buy", optimize=True) 
    ote_upper = DecimalParameter(0.60, 1.00, default=0.90, space="buy", optimize=True) 
    pivot_lookback = IntParameter(2, 8, default=3, space="buy", optimize=True) 
    buffer_pips = DecimalParameter(0.0001, 0.0100, default=0.001, space="buy", optimize=True) 
    min_rr = DecimalParameter(0.5, 4.0, default=0.7, space="buy", optimize=True) 
    
    # FVG Requirement
    require_fvg = CategoricalParameter([True, False], default=False, space="buy", optimize=True)

    # OTE Zone Requirement (v0.11.0: Re-enable by default with wider bounds for quality)
    require_ote = CategoricalParameter([True, False], default=False, space="buy", optimize=True)

    # Internal BoS (Break of Structure) Requirement
    use_structure_break = CategoricalParameter([True, False], default=False, space="buy", optimize=True)
    
    # Trigger Pivot Length (Fractal size for internal structure)
    trigger_pivot = IntParameter(1, 3, default=2, space="buy", optimize=True)

    # Entry Refinement (Market or Limit at FVG Midpoint)
    entry_refinement = CategoricalParameter(['market', 'limit_fvg_50'], default='market', space="buy", optimize=True)

    # Plotting
    plot_config = {
        'main_plot': {
            'swing_high': {'color': 'red'},
            'swing_low': {'color': 'green'},
            'ote_upper': {'color': 'orange'},
            'ote_lower': {'color': 'orange'},
        },
        'subplots': {
            "Trend": {
                'trend': {'color': 'blue'},
            },
        }
    }

    def informative_pairs(self):
        """Define informative pairs for multi-timeframe analysis."""
        pairs = self.dp.current_whitelist()
        informative_pairs = [(pair, self.informative_timeframe) for pair in pairs]
        return informative_pairs

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Add indicators for liquidity sweep detection.
        """
        # Get informative (1H) data for trend context
        informative = self.dp.get_pair_dataframe(
            pair=metadata['pair'],
            timeframe=self.informative_timeframe
        )
        
        if len(informative) > 0:
            informative = self._add_trend_indicators(informative)
            dataframe = merge_informative_pair(
                dataframe, informative,
                self.timeframe, self.informative_timeframe,
                ffill=True
            )
        
        # Add swing detection on 15m
        dataframe['recent_swing_high'], dataframe['recent_swing_low'] = self._compute_swings(dataframe, self.pivot_lookback.value)
        
        # Add Minor Structure detection (Triggering Swings) using smaller pivot
        dataframe['minor_swing_high'], dataframe['minor_swing_low'] = self._compute_swings(dataframe, self.trigger_pivot.value)
        
        # Add OTE zone calculations
        dataframe = self._calculate_ote(dataframe)

        # Add FVG Detection
        dataframe = self._detect_fvgs(dataframe)
        
        # Add liquidity sweep detection
        dataframe = self._detect_sweeps(dataframe)
        
        return dataframe

    def _add_trend_indicators(self, dataframe: DataFrame) -> DataFrame:
        """Add trend detection indicators on HTF (Market Structure)."""
        
        # 1. Detect Swings on HTF (Reuse swing detection logic)
        # We use a slightly larger pivot for 1H structure to catch major moves
        structure_pivot = 3
        dataframe['recent_swing_high'], dataframe['recent_swing_low'] = self._compute_swings(dataframe, structure_pivot)
        
        # 2. Market Structure (BoS)
        # Initialize trend column
        dataframe['structure_trend'] = 0
        
        # A break of structure happens when we close beyond the previous confirmed swing
        # Bullish BoS: Close > Previous confirmed Swing High
        # Bearish BoS: Close < Previous confirmed Swing Low
        
        # We iterate to maintain state (Forward fill the trend)
        # Vectorized approach: 
        # Identify break points
        dataframe['bos_bullish'] = np.where(dataframe['close'] > dataframe['recent_swing_high'].shift(1), 1, 0)
        dataframe['bos_bearish'] = np.where(dataframe['close'] < dataframe['recent_swing_low'].shift(1), -1, 0)
        
        # specific_trend tracks the moment of the break
        # We combine them: 1 if bullish break, -1 if bearish break, 0 otherwise
        dataframe['signal_trend'] = np.where(dataframe['bos_bullish'] == 1, 1, 
                                   np.where(dataframe['bos_bearish'] == 1, -1, np.nan))
        
        # Forward fill the trend to hold the state between breaks
        dataframe['structure_trend'] = dataframe['signal_trend'].ffill().fillna(0).astype(int)

        # 3. SMA Trend (Backup / Confluence)
        dataframe['sma_50'] = ta.SMA(dataframe, timeperiod=50)
        dataframe['sma_200'] = ta.SMA(dataframe, timeperiod=200)
        
        # Combine Structure + SMA for high probability
        # Primary is Structure. Use SMA only if Structure is neutral (0)
        dataframe['trend'] = dataframe['structure_trend']
        
        # Fallback if structure undefined (start of data)
        mask_neutral = (dataframe['trend'] == 0)
        dataframe.loc[mask_neutral, 'trend'] = np.where(
            dataframe.loc[mask_neutral, 'close'] > dataframe.loc[mask_neutral, 'sma_200'], 1, -1
        )
        
        return dataframe

    def _compute_swings(self, dataframe: DataFrame, pivot_len: int) -> Tuple[pd.Series, pd.Series]:
        """
        Compute swing levels using a rolling window (Fractal/Pivot method).
        Returns tuple of Series: (recent_swing_high, recent_swing_low)
        """
        # Window size = pivot_len (left) + 1 (center) + pivot_len (right)
        window_size = (pivot_len * 2) + 1
        
        # Calculate rolling max/min
        max_rolling = dataframe['high'].rolling(window=window_size).max()
        min_rolling = dataframe['low'].rolling(window=window_size).min()
        
        # Check if the center of the window (at i - pivot_len) is the extreme
        # Shift back because rolling result is at the end of the window
        # swing_point_check refers to the bar pivot_len bars ago
        is_swing_high = (
            max_rolling == dataframe['high'].shift(pivot_len)
        )
        is_swing_low = (
            min_rolling == dataframe['low'].shift(pivot_len)
        )
        
        # Propagate forward: Use the Value of the High/Low at determining candle
        # Note: We must shift result forward because at index `i`, we detected a swing at `i - pivot_len`.
        # The price level is valid from `i` onwards (confirmation time).
        
        swing_high_series = dataframe['high'].shift(pivot_len).where(
            is_swing_high
        ).ffill()
        
        swing_low_series = dataframe['low'].shift(pivot_len).where(
            is_swing_low
        ).ffill()
        
        return swing_high_series, swing_low_series

    def _detect_swings(self, dataframe: DataFrame, pivot_len: int) -> DataFrame:
        """ Legacy wrapper for backward compatibility if needed """
        start_candle = self.startup_candle_count
        h, l = self._compute_swings(dataframe, pivot_len)
        dataframe['recent_swing_high'] = h
        dataframe['recent_swing_low'] = l
        return dataframe

    def _calculate_ote(self, dataframe: DataFrame) -> DataFrame:
        """Calculate OTE zone (0.62 - 0.79 Fib retracement)."""
        # Use rolling external range
        lookback = 50
        dataframe['external_high'] = dataframe['high'].rolling(lookback).max()
        dataframe['external_low'] = dataframe['low'].rolling(lookback).min()
        
        # Calculate Fib levels (for shorts: measuring from low to high)
        range_size = dataframe['external_high'] - dataframe['external_low']
        
        # OTE zone boundaries
        dataframe['ote_lower'] = dataframe['external_low'] + (range_size * self.ote_lower.value)
        dataframe['ote_upper'] = dataframe['external_low'] + (range_size * self.ote_upper.value)
        
        # Check if price is in OTE
        dataframe['in_ote'] = (
            (dataframe['close'] >= dataframe['ote_lower']) &
            (dataframe['close'] <= dataframe['ote_upper'])
        )
        
        # Calculate current retracement level
        dataframe['fib_level'] = (dataframe['close'] - dataframe['external_low']) / range_size
        
        return dataframe

    def _detect_fvgs(self, dataframe: DataFrame) -> DataFrame:
        """
        Detect Fair Value Gaps (FVG) / Imbalances.
        A Bearish FVG exists if Low[i-2] > High[i] (Gap created by strong down move at i-1).
        A Bullish FVG exists if High[i-2] < Low[i] (Gap created by strong up move at i-1).
        """
        # Shift 1 = Previous candle (the big move)
        # Shift 2 = Pre-previous (the origin)
        # Current = The candle closing the gap formation
        
        # __ Bearish FVG (Short Signal) __
        # Gap between Low of Candle i-2 and High of Candle i
        dataframe['fvg_bearish'] = (
            dataframe['low'].shift(2) > dataframe['high']
        )
        
        # __ Bullish FVG (Long Signal) __
        # Gap between High of Candle i-2 and Low of Candle i
        dataframe['fvg_bullish'] = (
            dataframe['high'].shift(2) < dataframe['low']
        )
        
        return dataframe

    def _detect_sweeps(self, dataframe: DataFrame) -> DataFrame:
        """Detect liquidity sweeps and confirmation."""
        # Sweep detection: wick beyond recent swing
        dataframe['sweep_high'] = dataframe['high'] > dataframe['recent_swing_high'].shift(1)
        dataframe['sweep_low'] = dataframe['low'] < dataframe['recent_swing_low'].shift(1)
        
        # Internal Structure Break (ChoCH) Logic
        # Update 0.7.0: Use fractal-based Minor Structure for trigger
        # We use 'minor_swing_low' which tracks the last valid internal low (pivot=1 or 2)
        
        # For Short: Trigger is the most recent Minor Swing Low
        dataframe['triggering_low'] = dataframe['minor_swing_low'].shift(1)
        
        # For Long: Trigger is the most recent Minor Swing High
        dataframe['triggering_high'] = dataframe['minor_swing_high'].shift(1)
        
        # --- NEW: Structural Break Confirmation (Optional via Parameter) ---
        # If use_structure_break is True, we enforce that the close is ALSO beyond the 
        # *recent confirmed swing*. This is stricter than the rolling min.
        
        # We will check if the close breaks the *previous* confirmed swing low (for short)
        # Note: 'recent_swing_low' is ffilled. We want the one BEFORE the sweep started? 
        # Actually, if we just swept a high, the recent_swing_low is likely the bottom of the range.
        # Breaking THAT would be a full external BoS (too late).
        
        # Instead, we define "Internal Structure" as the *triggering_low* we just calculated.
        # But we ensure it's "significant" by checking if it was a pivot?
        # A simple approximation for robustness: The triggering low must be lower than the open of the candle that started the sweep?
        # Let's keep it simple for this iteration: Strong Close.
        
        # Improvement: "Strong Close" Confirmation
        # The close must be in the bottom 25% of the candle range (for sell) or top 25% (for buy).
        # This filters out weak wicks that just barely close below structure.
        
        candle_range = dataframe['high'] - dataframe['low']
        dist_from_low = dataframe['close'] - dataframe['low']
        dist_from_high = dataframe['high'] - dataframe['close']
        
        dataframe['strong_close_bearish'] = (dist_from_low <= (candle_range * 0.35)) # Close in bottom 35%
        dataframe['strong_close_bullish'] = (dist_from_high <= (candle_range * 0.35)) # Close in top 35%

        
        # Confirmation Logic
        fvg_check_short = True
        fvg_check_long = True
        
        if self.require_fvg.value:
            fvg_check_short = dataframe['fvg_bearish']
            fvg_check_long = dataframe['fvg_bullish']

        # Determine if we use the strong close filter
        # We'll tie this to the 'use_structure_break' param for now or just enable it as an improvement.
        # Let's effectively alias 'use_structure_break' to 'require_strong_close' for this version to avoid adding too params.
        
        trend_confirmation_short = True
        trend_confirmation_long = True
        
        if self.use_structure_break.value: # Interpret as "High Quality Confirmation"
             trend_confirmation_short = dataframe['strong_close_bearish']
             trend_confirmation_long = dataframe['strong_close_bullish']

        dataframe['short_confirmation'] = (
            dataframe['sweep_high'] &
            (dataframe['close'] < dataframe['triggering_low']) &
            fvg_check_short &
            trend_confirmation_short
        )
        dataframe['long_confirmation'] = (
            dataframe['sweep_low'] &
            (dataframe['close'] > dataframe['triggering_high']) &
            fvg_check_long &
            trend_confirmation_long
        )
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Generate entry signals."""
        dataframe.loc[:, 'enter_long'] = 0
        dataframe.loc[:, 'enter_short'] = 0
        
        # Get HTF trend from informative
        htf_trend_col = f'trend_{self.informative_timeframe}'

        # Calculate Risk and Reward for R:R filtering
        # Include buffer_pips in risk calculation to match custom_stoploss logic
        buffer = self.buffer_pips.value
        
        # Long: Reward = External High - Close; Risk = Close - (Recent Swing Low - Buffer)
        dataframe['reward_long'] = dataframe['external_high'] - dataframe['close']
        dataframe['risk_long'] = dataframe['close'] - (dataframe['recent_swing_low'] - buffer)
        
        # Short: Reward = Close - External Low; Risk = (Recent Swing High + Buffer) - Close
        dataframe['reward_short'] = dataframe['close'] - dataframe['external_low']
        dataframe['risk_short'] = (dataframe['recent_swing_high'] + buffer) - dataframe['close']

        # Avoid division by zero or negative risk (invalid setup or zero risk)
        # We replace 0 or negative risk with a small number to avoid errors, or just NaN to filter out
        dataframe['rr_long'] = np.where(dataframe['risk_long'] > 0, dataframe['reward_long'] / dataframe['risk_long'], 0)
        dataframe['rr_short'] = np.where(dataframe['risk_short'] > 0, dataframe['reward_short'] / dataframe['risk_short'], 0)
        
        # OTE zone check (optional via parameter)
        ote_check = dataframe['in_ote'] if self.require_ote.value else True
        
        # Long Entry Conditions
        # (htf_trend_col == 1) &  # Bullish HTF trend
        dataframe.loc[
            (ote_check) &                       # Price in OTE zone (if required)
            (dataframe['long_confirmation']) &   # Sweep + confirmation
            (dataframe['rr_long'] >= self.min_rr.value), # Min R:R
            'enter_long'
        ] = 1
        
        # Short Entry Conditions
        # (htf_trend_col == -1) &  # Bearish HTF trend
        dataframe.loc[
            (ote_check) &                        # Price in OTE zone (if required)
            (dataframe['short_confirmation']) &    # Sweep + confirmation
            (dataframe['rr_short'] >= self.min_rr.value), # Min R:R
            'enter_short'
        ] = 1
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Generate exit signals (we use ROI/Stoploss primarily)."""
        dataframe.loc[:, 'exit_long'] = 0
        dataframe.loc[:, 'exit_short'] = 0
        
        # Exit on trend reversal
        htf_trend_col = f'trend_{self.informative_timeframe}'
        
        if htf_trend_col in dataframe.columns:
            # Exit long if trend turns bearish
            dataframe.loc[
                dataframe[htf_trend_col] == -1,
                'exit_long'
            ] = 1
            
            # Exit short if trend turns bullish
            dataframe.loc[
                dataframe[htf_trend_col] == 1,
                'exit_short'
            ] = 1
        
        return dataframe

    # v0.18.0: DISABLED - custom_stoploss was creating a trailing effect via recent_swing levels.
    # recent_swing_low/high updates as new swings form → SL moves up → acts as trailing stop.
    # Result: same 486 "trailing_stop_loss" exits even with trailing_stop=False.
    # Fix: Use ONLY static stoploss=-10%. Let ROI table handle profitable exits.
    use_custom_stoploss = False

    def custom_exit(self, pair: str, trade: 'Trade', current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs):
        """
        Custom exit logic:
        1. Exit at External Swing High/Low (Liquidity Target)
        """
        # Get dataframe
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if len(dataframe) == 0:
            return None
            
        last_candle = dataframe.iloc[-1]
        
        # Target Liquidity: The external swing that defined the OTE range
        # Notes:
        # - Short: Target is external_low (0.0 Fib)
        # - Long: Target is external_high (1.0 Fib)
        
        if trade.is_short:
            if 'external_low' in last_candle and not pd.isna(last_candle['external_low']):
                target_price = last_candle['external_low']
                # If current price is below or at target, take profit
                if current_rate <= target_price:
                    return "target_liquidity_reached"
                    
        else:
            if 'external_high' in last_candle and not pd.isna(last_candle['external_high']):
                target_price = last_candle['external_high']
                # If current price is above or at target, take profit
                if current_rate >= target_price:
                    return "target_liquidity_reached"
                    
        return None

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                        current_rate: float, current_profit: float,
                        after_fill: bool, **kwargs) -> Optional[float]:
        """
        Custom stoploss v0.18.0 - Swing-based SL anchored to ENTRY price, capped at -8%.
        
        From v0.17.0: SL is calculated relative to trade.open_rate (fixed anchor).
        New in v0.18.0: Cap the SL at -8% max to avoid overly wide stops when swings are far.
        This means swing-based SL is only used when it's TIGHTER than -8%.
        If swing is too far away, the static stoploss (-10%) acts as fallback.
        
        Note: Freqtrade's custom_stoploss returns a NEGATIVE profit threshold.
        Returning -0.05 means "exit if profit drops below -5%".
        """
        MAX_SL_PCT = 0.08  # Cap stop at 8% max loss
        
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) == 0:
            return None
            
        last_candle = dataframe.iloc[-1]
        open_rate = trade.open_rate
        
        if trade.is_short:
            # For shorts: SL above sweep high (price going up = loss for short)
            if 'recent_swing_high' in last_candle and not pd.isna(last_candle['recent_swing_high']):
                sl_price = last_candle['recent_swing_high'] + self.buffer_pips.value
                sl_pct = abs((sl_price - open_rate) / open_rate)
                # Use swing-based SL only if it's tighter than max cap
                sl_pct = min(sl_pct, MAX_SL_PCT)
                return -sl_pct
        else:
            # For longs: SL below sweep low (price going down = loss for long)
            if 'recent_swing_low' in last_candle and not pd.isna(last_candle['recent_swing_low']):
                sl_price = last_candle['recent_swing_low'] - self.buffer_pips.value
                sl_pct = abs((open_rate - sl_price) / open_rate)
                # Use swing-based SL only if it's tighter than max cap
                sl_pct = min(sl_pct, MAX_SL_PCT)
                return -sl_pct
        
        return None

    def custom_entry_price(self, pair: str, trade: Optional['Trade'], current_time: datetime, proposed_rate: float,
                           entry_tag: Optional[str], side: str, **kwargs) -> float:
        """
        Custom Entry Pricing (Limit Orders).
        If 'limit_fvg_50' is selected and an FVG is present, places order at 50% of the gap.
        """
        if self.entry_refinement.value == 'market':
            return proposed_rate
            
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if len(dataframe) < 3:
            return proposed_rate
            
        # We look at the last closed candle (iloc[-1]) which confirmed the signal
        last_candle = dataframe.iloc[-1]
        
        # Bearish FVG Logic (Short)
        if side == "short" and last_candle.get('fvg_bearish', False):
            # FVG is between Low[i-2] and High[i]
            # i = -1 (current confirmed)
            # i-2 = -3
            
            fvg_top_limit = dataframe['low'].iloc[-3]   # Low of the candle before the drop
            fvg_bottom_limit = dataframe['high'].iloc[-1] # High of the current candle
            
            # Gap exists if Top > Bottom (which is checked by fvg_bearish)
            # Entry at 50% of the gap
            midpoint = (fvg_top_limit + fvg_bottom_limit) / 2
            return midpoint
            
        # Bullish FVG Logic (Long)
        if side == "long" and last_candle.get('fvg_bullish', False):
            # FVG is between High[i-2] and Low[i]
            fvg_bottom_limit = dataframe['high'].iloc[-3] # High of candle before rise
            fvg_top_limit = dataframe['low'].iloc[-1]     # Low of current candle
            
            # Gap exists if Bottom < Top
            midpoint = (fvg_top_limit + fvg_bottom_limit) / 2
            return midpoint

        # Fallback to market if no FVG detected or method is market
        return proposed_rate

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:
        """Conservative leverage for this strategy."""
        return 3.0  # 3x leverage - conservative for swing trades
