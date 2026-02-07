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
Version: 0.1.0
"""

import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional, Tuple, Dict, Any
import talib.abstract as ta
from freqtrade.strategy import IStrategy, merge_informative_pair
from freqtrade.strategy.parameters import IntParameter, DecimalParameter


class LiquiditySweep(IStrategy):
    """
    Liquidity Sweep Reversal Strategy
    
    Trades reversals after liquidity grabs in OTE zones.
    Uses multi-timeframe analysis (15m entry, 1H context).
    """
    
    # Strategy version
    INTERFACE_VERSION = 3
    
    # ROI table - we use fixed TP based on swing levels, but need defaults
    minimal_roi = {
        "0": 0.10,   # 10% - fallback, we use custom TP
        "60": 0.05,
        "120": 0.02,
    }
    
    # Stoploss - conservative, we override with sweep high
    stoploss = -0.03  # 3% fallback
    
    # Trailing stop disabled - we use fixed SL at sweep high
    trailing_stop = False
    
    # Timeframe
    timeframe = '15m'
    informative_timeframe = '1h'
    
    # Required candle count for startup
    startup_candle_count = 100
    
    # Strategy parameters (hyperoptable)
    ote_lower = DecimalParameter(0.55, 0.65, default=0.62, space="buy", optimize=True)
    ote_upper = DecimalParameter(0.75, 0.85, default=0.79, space="buy", optimize=True)
    swing_lookback = IntParameter(10, 30, default=20, space="buy", optimize=True)
    buffer_pips = DecimalParameter(0.0002, 0.001, default=0.0005, space="buy", optimize=True)
    min_rr = DecimalParameter(1.5, 3.0, default=2.0, space="buy", optimize=True)
    
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
        dataframe = self._detect_swings(dataframe, self.swing_lookback.value)
        
        # Add OTE zone calculations
        dataframe = self._calculate_ote(dataframe)
        
        # Add liquidity sweep detection
        dataframe = self._detect_sweeps(dataframe)
        
        return dataframe

    def _add_trend_indicators(self, dataframe: DataFrame) -> DataFrame:
        """Add trend detection indicators on HTF."""
        # Simple trend: compare current close to SMA
        dataframe['sma_50'] = ta.SMA(dataframe, timeperiod=50)
        dataframe['sma_200'] = ta.SMA(dataframe, timeperiod=200)
        
        # Trend: 1 = bullish, -1 = bearish, 0 = neutral
        dataframe['trend'] = 0
        dataframe.loc[
            (dataframe['close'] > dataframe['sma_50']) & 
            (dataframe['sma_50'] > dataframe['sma_200']),
            'trend'
        ] = 1  # Bullish
        dataframe.loc[
            (dataframe['close'] < dataframe['sma_50']) & 
            (dataframe['sma_50'] < dataframe['sma_200']),
            'trend'
        ] = -1  # Bearish
        
        # Structure-based trend (swing highs/lows)
        dataframe['swing_high_htf'] = dataframe['high'].rolling(20).max()
        dataframe['swing_low_htf'] = dataframe['low'].rolling(20).min()
        
        return dataframe

    def _detect_swings(self, dataframe: DataFrame, lookback: int) -> DataFrame:
        """Detect swing highs and lows for liquidity pools."""
        # Rolling max/min for swing detection
        dataframe['swing_high'] = dataframe['high'].rolling(lookback, center=True).max()
        dataframe['swing_low'] = dataframe['low'].rolling(lookback, center=True).min()
        
        # Mark actual swing points
        dataframe['is_swing_high'] = (dataframe['high'] == dataframe['swing_high'])
        dataframe['is_swing_low'] = (dataframe['low'] == dataframe['swing_low'])
        
        # Get recent swing levels (last confirmed swing)
        dataframe['recent_swing_high'] = dataframe['high'].where(
            dataframe['is_swing_high']
        ).ffill()
        dataframe['recent_swing_low'] = dataframe['low'].where(
            dataframe['is_swing_low']
        ).ffill()
        
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

    def _detect_sweeps(self, dataframe: DataFrame) -> DataFrame:
        """Detect liquidity sweeps and confirmation."""
        # Sweep detection: wick beyond recent swing
        dataframe['sweep_high'] = dataframe['high'] > dataframe['recent_swing_high'].shift(1)
        dataframe['sweep_low'] = dataframe['low'] < dataframe['recent_swing_low'].shift(1)
        
        # Find triggering swing (the swing that launched the move)
        # For shorts: the swing low before the sweep high
        # For longs: the swing high before the sweep low
        
        # Simplified: use recent swing as triggering level
        dataframe['triggering_low'] = dataframe['recent_swing_low'].shift(1)
        dataframe['triggering_high'] = dataframe['recent_swing_high'].shift(1)
        
        # Confirmation: close beyond triggering level
        dataframe['short_confirmation'] = (
            dataframe['sweep_high'] &
            (dataframe['close'] < dataframe['triggering_low'])
        )
        dataframe['long_confirmation'] = (
            dataframe['sweep_low'] &
            (dataframe['close'] > dataframe['triggering_high'])
        )
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Generate entry signals."""
        dataframe.loc[:, 'enter_long'] = 0
        dataframe.loc[:, 'enter_short'] = 0
        
        # Get HTF trend from informative
        htf_trend_col = f'trend_{self.informative_timeframe}'
        
        # Long Entry Conditions
        if htf_trend_col in dataframe.columns:
            dataframe.loc[
                (dataframe[htf_trend_col] == 1) &  # Bullish HTF trend
                (dataframe['in_ote']) &             # Price in OTE zone
                (dataframe['long_confirmation']),    # Sweep + confirmation
                'enter_long'
            ] = 1
            
            # Short Entry Conditions
            dataframe.loc[
                (dataframe[htf_trend_col] == -1) &  # Bearish HTF trend
                (dataframe['in_ote']) &              # Price in OTE zone
                (dataframe['short_confirmation']),    # Sweep + confirmation
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

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                        current_rate: float, current_profit: float,
                        after_fill: bool, **kwargs) -> Optional[float]:
        """
        Custom stoploss based on sweep high/low + buffer.
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        if len(dataframe) == 0:
            return None
            
        last_candle = dataframe.iloc[-1]
        
        if trade.is_short:
            # For shorts: SL above sweep high
            if 'recent_swing_high' in last_candle:
                sl_price = last_candle['recent_swing_high'] + self.buffer_pips.value
                sl_percent = (sl_price - current_rate) / current_rate
                return sl_percent
        else:
            # For longs: SL below sweep low
            if 'recent_swing_low' in last_candle:
                sl_price = last_candle['recent_swing_low'] - self.buffer_pips.value
                sl_percent = (current_rate - sl_price) / current_rate
                return -sl_percent
        
        return None

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:
        """Conservative leverage for this strategy."""
        return 3.0  # 3x leverage - conservative for swing trades
