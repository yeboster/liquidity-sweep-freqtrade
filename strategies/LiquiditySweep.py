"""
Liquidity Sweep Reversal Strategy for Freqtrade
================================================
Based on: https://dailypriceaction.com/blog/liquidity-sweep-reversals/

Core Logic:
1. Identify HTF trend via Break of Structure / Change of Character
2. Wait for price to retrace into OTE (optional)
3. Detect liquidity sweep (price takes out swing high/low cluster)
4. Enter on confirmation (close beyond triggering swing)
5. Optional: Order Block / FVG confluence for higher probability entries
6. Skip entry if unmitigated imbalance exists beyond stop loss (v0.29.0)

Uses smartmoneyconcepts library for ICT indicator calculations.

Author: Jarvis (OpenClaw)
Version: 0.29.0

Changelog:
- v0.29.0 (2026-02-28): Fix FVG zone detection bug (0 trades in v0.28.0).
  Bug: v0.28.0 produced ZERO trades. Root cause: `active_bullish_fvg` used
  `.ffill()` on a boolean series (always False except sparse FVG candles), so
  it never propagated True forward. The logic checked if the CURRENT candle IS
  an FVG candle, not if price is INSIDE a recent FVG zone.
  Fix: Track unmitigated FVG zone levels (top/bottom) via forward-fill, then
  check if current close is within the zone: close >= fvg_bottom AND close <= fvg_top.
  This correctly detects "price is trading inside an active FVG imbalance zone."
  Also: require_fvg default changed to False — the opposite-side imbalance filter
  (safe_long/safe_short) is the primary quality gate. require_fvg is available as
  an optional confluence filter for hyperopt to evaluate.
  Expected: Restores trade flow from v0.27.0 (~128 trades), with TSL exits reduced
  by opposite-side imbalance filter.
- v0.28.0 (2026-02-28): FVG confluence + opposite-side imbalance filter.
  Problem: v0.27.0 results identical to v0.26.0 (128 trades, 21.1% WR, -27.03%).
  Analysis: 55/128 trades hit trailing_stop_loss in avg 1h04m. Even trend-aligned
  entries get stopped out immediately — this is an ENTRY QUALITY problem, not a
  trend-alignment problem. The ATR SL is being hit because price is attracted to
  unmitigated FVGs beyond the stop loss (liquidity magnets, stop-hunt risk).
  Fixes:
  (1) require_fvg=True by default: Only enter when price is inside an active
      unmitigated FVG zone. This ensures we enter where market structure supports
      a reversal (imbalance needs to be filled).
  (2) Opposite-side imbalance check: Skip trade if there's an unmitigated FVG
      on the other side of the stop loss. Key concept (Marco's SMC rule):
      "Is there an obvious imbalance on the opposite side of where my stop would
      go? If YES → Skip (price will be attracted there). If NO → Take trade."
  (3) min_rr default raised to 1.5 (was 1.0) — require better setups only.
  Expected: Fewer trades, higher quality, WR target 45-55%.
- v0.27.0 (2026-02-27): Restore HTF trend alignment filter.
  Root cause of v0.26.0's 21.7% win rate found: the HTF trend column was computed 
  in populate_indicators but the `htf_trend_col` variable in populate_entry_trend was 
  declared but NEVER used in any filter condition — it was a dead variable dropped during 
  the v0.21.0 SMC refactor. This meant entries fired against the 1H trend direction 
  (entering longs in bear markets, shorts in bull markets), leading to 55 immediate 
  trailing_stop_loss exits at avg -1.58%.
  Fix: Added `htf_trend_col` to both long and short entry conditions.
  Long entries now require trend_1h == 1 (bullish 1H structure).
  Short entries now require trend_1h == -1 (bearish 1H structure).
  Expected: Fewer trades, significantly higher win rate.
- v0.26.0 (2026-02-27): Decouple sweep from ChoCH confirmation.
  Fixed a logic bug introduced in v0.21.0 where both the liquidity sweep AND the structure 
  break (close below swing low) were required on the *same* 15m candle, devastating trade volume.
  Now uses a 5-candle rolling window for recent sweeps, and checks for a proper SMC ChoCH.
- v0.25.0 (2026-02-27): Per-pair parameter overrides.
  Added a custom_pair_params dictionary to allow overriding hyperoptable parameters
  (like atr_multiplier, require_ote, time_exit hours) explicitly for pairs with different 
  volatile profiles (e.g. BTC vs ADA).
- v0.24.0 (2026-02-27): Made time-based exits hyperoptable.
  Problem: Static time exits (4h and 6h) have been hurting win rate by cutting marginal
  winners prematurely. By making these parameters hyperoptable within the "sell" space,
  we allow the optimizer to determine the best duration and profit thresholds,
  or disable time exits altogether if dynamic stop loss handles it well enough.
- v0.22.0 (2026-02-26): ATR-based dynamic stoploss + OTE filter re-enabled by default.
  Problem: v0.20 had 61 SL exits at avg -2.79%. Fixed -2.5% SL was too blunt — too tight
  for BTC (high vol) causing premature stops, too wide in calm markets (ETH, ADA).
  Fixes:
  (1) use_custom_stoploss = True — ATR-based SL at 1.5x ATR(14) from entry candle.
      Floor: -1.5% (max precision), Ceiling: -4.0% (don't let it run).
  (2) require_ote default → True (loose: 20-90%). Re-enables quality filter.
      Motivation: v0.19 disabled OTE, volume went up but quality fell. v0.20 kept it off
      but signal quality wasn't the bottleneck — SL placement was.
  (3) atr_multiplier added as hyperopt param (1.0-2.5x) for future optimization.
  static stoploss remains at -0.04 as absolute backstop (Freqtrade requirement).
- v0.21.0 (2026-02-23): MAJOR REFACTOR — replaced all hand-rolled indicators with smartmoneyconcepts library.
  New features: proper liquidity sweep detection (clustered highs/lows + swept tracking),
  FVG with mitigation tracking, BOS + ChoCH distinction, Order Block confluence.
  Risk management preserved from v0.20.0 (SL -2.5%, trailing after +1.5%, time exit 4h).
- v0.20.0 (2026-02-23): Tighter risk management overhaul.
  v0.19 analysis: 51% WR but -40.7% total due to loss:win ratio of 4.3:1.
  349 profitable exits (ROI+target) at +1% avg, 0 losses. Signal is GOOD.
  116 SL exits at -4.29% avg destroy all gains. 111 draws waste time.
  Fixes: (1) SL tightened -4% -> -2.5% (2) Trailing stop after +1.5% profit
  (3) Time-based exit at 4h if not profitable (4) Drop LINK/USDT (35% WR)
  (5) Negative ROI at 8h to cut stale trades (6) Faster profit-taking via ROI table.
- v0.19.0 (2026-02-20): Loosened entry by disabling OTE requirement, but tightened risk.
- v0.18.0 (2026-02-20): Disabled BOTH trailing_stop AND use_custom_stoploss.
- v0.17.0 (2026-02-19): Fixed custom_stoploss - anchors to ENTRY price not current price.
- v0.16.0 (2026-02-19): Disabled custom_stoploss - using static SL only.
"""

import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional, Dict, Any
import talib.abstract as ta
from freqtrade.strategy import IStrategy, merge_informative_pair
from freqtrade.strategy.parameters import IntParameter, DecimalParameter, CategoricalParameter
from freqtrade.persistence import Trade
from smartmoneyconcepts import smc


class LiquiditySweep(IStrategy):
    """
    Liquidity Sweep Reversal Strategy — powered by smartmoneyconcepts.
    
    Trades reversals after liquidity grabs, with optional OTE zone + Order Block confluence.
    Uses multi-timeframe analysis (15m entry, 1H context).
    """
    
    INTERFACE_VERSION = 3
    STRATEGY_VERSION = "0.29.0"

    # ── Per-Pair Parameter Overrides ──────────────────────────────────────────
    # Keys should match parameter names exactly. If a pair is not listed, the strategy
    # falls back to the default/hyperopted global parameters.
    custom_pair_params = {
        "BTC/USDT": {
            "atr_multiplier": 2.0,       # BTC is volatile, use wider dynamic SL
            "require_ote": False,        # BTC trends hard, often misses OTE
            "time_exit_1_hours": 6       # Give BTC more time to play out
        },
        "ADA/USDT": {
            "atr_multiplier": 1.2,       # ADA is less volatile, tighter SL
            "require_ote": True,         # Quality filter for ADA
            "time_exit_1_hours": 4       # Cut early if it stalls
        }
    }

    def get_param(self, param_name: str, pair: str, default_value: Any) -> Any:
        """Helper to fetch pair-specific parameter or fallback to global"""
        if pair in self.custom_pair_params and param_name in self.custom_pair_params[pair]:
            return self.custom_pair_params[pair][param_name]
        return default_value


    # ── Risk Management ───────────────────────────────────────────────────────
    minimal_roi = {
        "0": 0.04,      # 4% immediately
        "30": 0.025,    # 2.5% after 30 min
        "60": 0.015,    # 1.5% after 1h
        "120": 0.008,   # 0.8% after 2h
        "240": 0.003,   # 0.3% after 4h
        "480": -0.005   # -0.5% after 8h (stale trade exit)
    }
    
    # Absolute backstop required by Freqtrade — custom_stoploss will use ATR, this is fallback
    stoploss = -0.04   # -4.0% absolute backstop (ATR SL should hit first)
    
    # Trailing stop — still active as profit protection (unchanged from v0.20)
    trailing_stop = True
    trailing_stop_positive = 0.007      # Trail 0.7% behind peak
    trailing_stop_positive_offset = 0.015  # Activate after +1.5%
    trailing_only_offset_is_reached = True
    
    # ATR-based dynamic stoploss enabled in v0.22.0
    use_custom_stoploss = True

    # ── Timeframes ────────────────────────────────────────────────────────────
    timeframe = '15m'
    informative_timeframe = '1h'
    startup_candle_count = 100

    # ── Hyperoptable Parameters ───────────────────────────────────────────────
    # Swing detection
    swing_length = IntParameter(3, 15, default=5, space="buy", optimize=True)
    htf_swing_length = IntParameter(5, 20, default=10, space="buy", optimize=True)
    
    # OTE zone — tightened in v0.23.0 to 30-70% (quality filter, avoids extremes)
    ote_lower = DecimalParameter(0.30, 0.50, default=0.30, space="buy", optimize=True)
    ote_upper = DecimalParameter(0.55, 0.70, default=0.70, space="buy", optimize=True)
    require_ote = CategoricalParameter([True, False], default=True, space="buy", optimize=True)
    
    # ATR-based SL — new in v0.22.0
    atr_multiplier = DecimalParameter(1.0, 2.5, default=1.5, space="buy", optimize=True)
    atr_period = IntParameter(10, 20, default=14, space="buy", optimize=False)
    
    # Entry filters
    min_rr = DecimalParameter(0.5, 4.0, default=1.5, space="buy", optimize=True)
    require_fvg = CategoricalParameter([True, False], default=False, space="buy", optimize=True)
    require_ob = CategoricalParameter([True, False], default=False, space="buy", optimize=True)
    
    # Liquidity detection
    liquidity_range_pct = DecimalParameter(0.005, 0.03, default=0.01, space="buy", optimize=True)
    
    # Buffer for SL placement
    buffer_pips = DecimalParameter(0.0001, 0.0100, default=0.002, space="buy", optimize=True)

    # Time-based custom exits (hyperoptable in v0.24.0)
    time_exit_1_enabled = CategoricalParameter([True, False], default=True, space="sell", optimize=True)
    time_exit_1_hours = IntParameter(2, 6, default=4, space="sell", optimize=True)
    time_exit_1_profit = DecimalParameter(-0.02, 0.01, default=0.0, space="sell", optimize=True)
    
    time_exit_2_enabled = CategoricalParameter([True, False], default=True, space="sell", optimize=True)
    time_exit_2_hours = IntParameter(5, 12, default=6, space="sell", optimize=True)
    time_exit_2_profit = DecimalParameter(0.0, 0.02, default=0.005, space="sell", optimize=True)

    # ── Plotting ──────────────────────────────────────────────────────────────
    plot_config = {
        'main_plot': {
            'swing_high_level': {'color': 'red'},
            'swing_low_level': {'color': 'green'},
        },
        'subplots': {
            "Structure": {
                'htf_trend': {'color': 'blue'},
            },
        }
    }

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        return [(pair, self.informative_timeframe) for pair in pairs]

    def _prepare_ohlc(self, dataframe: DataFrame) -> DataFrame:
        """Ensure DataFrame has lowercase columns for SMC library."""
        # Freqtrade already uses lowercase, but let's be safe
        ohlc = dataframe[['open', 'high', 'low', 'close']].copy()
        if 'volume' in dataframe.columns:
            ohlc['volume'] = dataframe['volume']
        return ohlc

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Add all indicators using smartmoneyconcepts library."""
        
        # ── HTF (1H) Indicators ───────────────────────────────────────────────
        informative = self.dp.get_pair_dataframe(
            pair=metadata['pair'],
            timeframe=self.informative_timeframe
        )
        
        if len(informative) > 0:
            informative = self._add_htf_indicators(informative)
            dataframe = merge_informative_pair(
                dataframe, informative,
                self.timeframe, self.informative_timeframe,
                ffill=True
            )
        
        # ── 15m Indicators ────────────────────────────────────────────────────
        ohlc = self._prepare_ohlc(dataframe)
        
        # 1. Swing Highs & Lows
        swing_data = smc.swing_highs_lows(ohlc, swing_length=self.swing_length.value)
        dataframe['swing_hl'] = swing_data['HighLow']      # 1=swing high, -1=swing low
        dataframe['swing_level'] = swing_data['Level']       # Price level of swing
        
        # Extract latest swing high/low levels (forward-filled)
        dataframe['swing_high_level'] = dataframe['swing_level'].where(
            dataframe['swing_hl'] == 1
        ).ffill()
        dataframe['swing_low_level'] = dataframe['swing_level'].where(
            dataframe['swing_hl'] == -1
        ).ffill()
        
        # 2. Break of Structure & Change of Character (15m)
        bos_choch_data = smc.bos_choch(ohlc, swing_data, close_break=True)
        dataframe['bos'] = bos_choch_data['BOS']       # 1=bullish, -1=bearish
        dataframe['choch'] = bos_choch_data['CHOCH']    # 1=bullish, -1=bearish
        dataframe['structure_level'] = bos_choch_data['Level']
        
        # 3. Fair Value Gaps
        fvg_data = smc.fvg(ohlc, join_consecutive=True)
        dataframe['fvg'] = fvg_data['FVG']              # 1=bullish, -1=bearish
        dataframe['fvg_top'] = fvg_data['Top']
        dataframe['fvg_bottom'] = fvg_data['Bottom']
        dataframe['fvg_mitigated'] = fvg_data['MitigatedIndex']
        
        # v0.29.0 FIX: Track active FVG zone levels (not candle flags).
        # Problem: v0.28.0 checked if the current candle IS an FVG candle (sparse,
        # almost always False). We need "is price currently INSIDE an unmitigated FVG zone?"
        # Solution: Forward-fill the top/bottom levels of the latest unmitigated FVG,
        # then check if close is within [bottom, top].
        dataframe['bullish_fvg_zone_top'] = np.where(
            (dataframe['fvg'] == 1) & (dataframe['fvg_mitigated'].isna()),
            dataframe['fvg_top'], np.nan
        )
        dataframe['bullish_fvg_zone_bottom'] = np.where(
            (dataframe['fvg'] == 1) & (dataframe['fvg_mitigated'].isna()),
            dataframe['fvg_bottom'], np.nan
        )
        dataframe['bearish_fvg_zone_top'] = np.where(
            (dataframe['fvg'] == -1) & (dataframe['fvg_mitigated'].isna()),
            dataframe['fvg_top'], np.nan
        )
        dataframe['bearish_fvg_zone_bottom'] = np.where(
            (dataframe['fvg'] == -1) & (dataframe['fvg_mitigated'].isna()),
            dataframe['fvg_bottom'], np.nan
        )
        # Forward-fill: carry the most recent unmitigated FVG zone levels forward
        dataframe['bullish_fvg_zone_top'] = dataframe['bullish_fvg_zone_top'].ffill()
        dataframe['bullish_fvg_zone_bottom'] = dataframe['bullish_fvg_zone_bottom'].ffill()
        dataframe['bearish_fvg_zone_top'] = dataframe['bearish_fvg_zone_top'].ffill()
        dataframe['bearish_fvg_zone_bottom'] = dataframe['bearish_fvg_zone_bottom'].ffill()
        # Active FVG zone: price is inside the most recent unmitigated FVG range
        dataframe['active_bullish_fvg'] = (
            dataframe['bullish_fvg_zone_top'].notna() &
            (dataframe['close'] >= dataframe['bullish_fvg_zone_bottom']) &
            (dataframe['close'] <= dataframe['bullish_fvg_zone_top'])
        )
        dataframe['active_bearish_fvg'] = (
            dataframe['bearish_fvg_zone_top'].notna() &
            (dataframe['close'] >= dataframe['bearish_fvg_zone_bottom']) &
            (dataframe['close'] <= dataframe['bearish_fvg_zone_top'])
        )
        
        # v0.28.0: Opposite-side imbalance check (Marco's SMC rule)
        # Track the most recent FVG bottom and top levels for zone-based filtering
        # These are used in populate_entry_trend to check if an unmitigated
        # imbalance exists BELOW the swing low (for longs) or ABOVE swing high (for shorts)
        # Bearish FVG bottom below price = danger zone for long stop
        dataframe['bearish_fvg_bottom'] = np.where(
            (dataframe['fvg'] == -1) & (dataframe['fvg_mitigated'].isna()),
            dataframe['fvg_bottom'], np.nan
        )
        dataframe['bearish_fvg_bottom'] = dataframe['bearish_fvg_bottom'].ffill()
        # Bullish FVG top above price = danger zone for short stop
        dataframe['bullish_fvg_top'] = np.where(
            (dataframe['fvg'] == 1) & (dataframe['fvg_mitigated'].isna()),
            dataframe['fvg_top'], np.nan
        )
        dataframe['bullish_fvg_top'] = dataframe['bullish_fvg_top'].ffill()
        
        # 4. Order Blocks
        ob_data = smc.ob(ohlc, swing_data, close_mitigation=False)
        dataframe['ob'] = ob_data['OB']                  # 1=bullish, -1=bearish
        dataframe['ob_top'] = ob_data['Top']
        dataframe['ob_bottom'] = ob_data['Bottom']
        dataframe['ob_volume'] = ob_data.get('OBVolume', 0)
        
        # Track if price is in an active order block zone
        # Bullish OB: price near OB zone (within the block for longs)
        dataframe['in_bullish_ob'] = (
            (dataframe['close'] >= dataframe['ob_bottom'].ffill()) &
            (dataframe['close'] <= dataframe['ob_top'].ffill()) &
            (dataframe['ob'].ffill() == 1)
        )
        dataframe['in_bearish_ob'] = (
            (dataframe['close'] >= dataframe['ob_bottom'].ffill()) &
            (dataframe['close'] <= dataframe['ob_top'].ffill()) &
            (dataframe['ob'].ffill() == -1)
        )
        
        # 5. Liquidity Detection
        liq_data = smc.liquidity(ohlc, swing_data, range_percent=self.liquidity_range_pct.value)
        dataframe['liquidity'] = liq_data['Liquidity']    # 1=buy-side, -1=sell-side
        dataframe['liquidity_level'] = liq_data['Level']
        dataframe['liquidity_swept'] = liq_data['Swept']  # Index where swept
        
        # Detect sweep events: liquidity was swept on this candle
        # The 'Swept' column contains the index where the sweep happened
        # We need to check if a sweep just happened
        dataframe['buy_liq_swept'] = False
        dataframe['sell_liq_swept'] = False
        
        # Vectorized sweep detection:
        # A buy-side liquidity sweep = price went ABOVE a buy-side liquidity level
        # → bearish signal (grabbed stops above, likely to reverse down)
        # A sell-side liquidity sweep = price went BELOW a sell-side liquidity level  
        # → bullish signal (grabbed stops below, likely to reverse up)
        
        # Use the swept column: if it's not NaN for a row, that liquidity was swept
        swept_mask = liq_data['Swept'].notna()
        dataframe.loc[swept_mask & (liq_data['Liquidity'] == 1), 'buy_liq_swept'] = True
        dataframe.loc[swept_mask & (liq_data['Liquidity'] == -1), 'sell_liq_swept'] = True
        
        # Also detect sweeps via price action (fallback / supplement)
        # Price wicks above swing high cluster = buy-side sweep
        dataframe['wick_sweep_high'] = (
            (dataframe['high'] > dataframe['swing_high_level'].shift(1)) &
            (dataframe['close'] < dataframe['swing_high_level'].shift(1))
        )
        # Price wicks below swing low cluster = sell-side sweep  
        dataframe['wick_sweep_low'] = (
            (dataframe['low'] < dataframe['swing_low_level'].shift(1)) &
            (dataframe['close'] > dataframe['swing_low_level'].shift(1))
        )
        
        # Combined sweep signal (either SMC library detected OR wick-based)
        dataframe['sweep_high'] = dataframe['buy_liq_swept'] | dataframe['wick_sweep_high']
        dataframe['sweep_low'] = dataframe['sell_liq_swept'] | dataframe['wick_sweep_low']
        
        # State: Was liquidity swept recently? (5 candles = 1h15m to form ChoCH)
        dataframe['recent_sweep_high'] = dataframe['sweep_high'].rolling(window=5, min_periods=1).max() > 0
        dataframe['recent_sweep_low'] = dataframe['sweep_low'].rolling(window=5, min_periods=1).max() > 0
        
        # 6. OTE Zone
        dataframe = self._calculate_ote(dataframe)
        
        # 7. ATR for dynamic stoploss (v0.22.0)
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=self.atr_period.value)
        # Normalize ATR as % of close for cross-asset comparison
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close']
        
        return dataframe

    def _add_htf_indicators(self, dataframe: DataFrame) -> DataFrame:
        """Add trend indicators on HTF (1H) using SMC library."""
        ohlc = self._prepare_ohlc(dataframe)
        
        # Swing detection on 1H
        htf_swings = smc.swing_highs_lows(ohlc, swing_length=self.htf_swing_length.value)
        
        # BOS + ChoCH on 1H for trend detection
        htf_structure = smc.bos_choch(ohlc, htf_swings, close_break=True)
        
        # Derive trend from structure breaks
        # BOS confirms existing trend, ChoCH signals reversal
        # Bullish BOS/ChoCH = 1, Bearish = -1
        dataframe['bos_signal'] = htf_structure['BOS']
        dataframe['choch_signal'] = htf_structure['CHOCH']
        
        # Combined trend signal: ChoCH is stronger (reversal), BOS confirms
        # Priority: ChoCH > BOS
        dataframe['trend_signal'] = np.where(
            htf_structure['CHOCH'].notna(), htf_structure['CHOCH'],
            np.where(htf_structure['BOS'].notna(), htf_structure['BOS'], np.nan)
        )
        dataframe['trend'] = pd.Series(dataframe['trend_signal']).ffill().fillna(0).astype(int)
        
        # SMA backup for when structure is undefined
        dataframe['sma_50'] = ta.SMA(dataframe, timeperiod=50)
        dataframe['sma_200'] = ta.SMA(dataframe, timeperiod=200)
        
        mask_neutral = (dataframe['trend'] == 0)
        dataframe.loc[mask_neutral, 'trend'] = np.where(
            dataframe.loc[mask_neutral, 'close'] > dataframe.loc[mask_neutral, 'sma_200'], 1, -1
        )
        
        return dataframe

    def _calculate_ote(self, dataframe: DataFrame) -> DataFrame:
        """Calculate OTE zone using swing levels."""
        lookback = 50
        dataframe['external_high'] = dataframe['high'].rolling(lookback).max()
        dataframe['external_low'] = dataframe['low'].rolling(lookback).min()
        
        range_size = dataframe['external_high'] - dataframe['external_low']
        
        dataframe['ote_lower'] = dataframe['external_low'] + (range_size * self.ote_lower.value)
        dataframe['ote_upper'] = dataframe['external_low'] + (range_size * self.ote_upper.value)
        
        dataframe['in_ote'] = (
            (dataframe['close'] >= dataframe['ote_lower']) &
            (dataframe['close'] <= dataframe['ote_upper'])
        )
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Generate entry signals using SMC indicators."""
        dataframe.loc[:, 'enter_long'] = 0
        dataframe.loc[:, 'enter_short'] = 0
        
        htf_trend_col = f'trend_{self.informative_timeframe}'
        
        # ── Filters ───────────────────────────────────────────────────────────
        
        # We need pair metadata to fetch custom parameters
        pair = metadata.get('pair', '')
        
        req_ote = self.get_param('require_ote', pair, self.require_ote.value)
        req_fvg = self.get_param('require_fvg', pair, self.require_fvg.value)
        req_ob = self.get_param('require_ob', pair, self.require_ob.value)
        
        ote_check = dataframe['in_ote'] if req_ote else True
        fvg_check_short = dataframe['active_bearish_fvg'] if req_fvg else True
        fvg_check_long = dataframe['active_bullish_fvg'] if req_fvg else True
        ob_check_short = dataframe['in_bearish_ob'] if req_ob else True
        ob_check_long = dataframe['in_bullish_ob'] if req_ob else True
        
        # ── R:R Calculation ───────────────────────────────────────────────────
        buffer = self.buffer_pips.value
        
        # Long: reward = external high - close, risk = close - (swing low - buffer)
        dataframe['reward_long'] = dataframe['external_high'] - dataframe['close']
        dataframe['risk_long'] = dataframe['close'] - (dataframe['swing_low_level'] - buffer)
        dataframe['rr_long'] = np.where(
            dataframe['risk_long'] > 0,
            dataframe['reward_long'] / dataframe['risk_long'], 0
        )
        
        # Short: reward = close - external low, risk = (swing high + buffer) - close
        dataframe['reward_short'] = dataframe['close'] - dataframe['external_low']
        dataframe['risk_short'] = (dataframe['swing_high_level'] + buffer) - dataframe['close']
        dataframe['rr_short'] = np.where(
            dataframe['risk_short'] > 0,
            dataframe['reward_short'] / dataframe['risk_short'], 0
        )
        
        # ── HTF Trend Alignment ───────────────────────────────────────────────
        # v0.27.0 FIX: htf_trend_col was computed but never used in entry filters
        # (dead variable introduced during v0.21.0 SMC refactor). This caused
        # counter-trend entries and was the root cause of the 21.7% win rate.
        htf_bearish = dataframe[htf_trend_col] == -1 if htf_trend_col in dataframe.columns else True
        htf_bullish = dataframe[htf_trend_col] == 1 if htf_trend_col in dataframe.columns else True

        # ── Opposite-Side Imbalance Filter (v0.28.0) ─────────────────────────
        # Marco's SMC rule: "Is there an obvious imbalance on the opposite side
        # of where my stop would go? If YES → Skip (liquidity magnet, stop-hunt
        # risk). If NO → Proceed (liquidity was already taken, safer entry)."
        #
        # For LONGS: SL is below swing_low_level. Skip if there's an unmitigated
        # bearish FVG bottom BELOW the swing low (price attracted downward).
        # For SHORTS: SL is above swing_high_level. Skip if there's an unmitigated
        # bullish FVG top ABOVE the swing high (price attracted upward).
        sl_buffer = self.buffer_pips.value
        long_sl_level = dataframe['swing_low_level'] - sl_buffer
        short_sl_level = dataframe['swing_high_level'] + sl_buffer

        safe_long = ~(
            dataframe['bearish_fvg_bottom'].notna() &
            (dataframe['bearish_fvg_bottom'] < long_sl_level)
        )
        safe_short = ~(
            dataframe['bullish_fvg_top'].notna() &
            (dataframe['bullish_fvg_top'] > short_sl_level)
        )

        # ── Short Entry ───────────────────────────────────────────────────────
        # Sweep of buy-side liquidity (highs) → price reverses down
        # Confirmation: Bearish Change of Character (ChoCH) + bearish HTF trend
        dataframe.loc[
            (htf_bearish) &                                          # HTF trend alignment (v0.27.0)
            (dataframe['recent_sweep_high']) &                       # Liquidity swept above recently
            (dataframe['choch'] == -1) &                             # Confirmation break
            (ote_check) &                                            # OTE (if required)
            (fvg_check_short) &                                      # FVG confluence (v0.28.0 default=True)
            (ob_check_short) &                                       # Order Block (if required)
            (safe_short) &                                           # No imbalance magnet beyond SL (v0.28.0)
            (dataframe['rr_short'] >= self.min_rr.value),           # Min R:R (v0.28.0 default=1.5)
            'enter_short'
        ] = 1
        
        # ── Long Entry ────────────────────────────────────────────────────────
        # Sweep of sell-side liquidity (lows) → price reverses up
        # Confirmation: Bullish Change of Character (ChoCH) + bullish HTF trend
        dataframe.loc[
            (htf_bullish) &                                          # HTF trend alignment (v0.27.0)
            (dataframe['recent_sweep_low']) &                        # Liquidity swept below recently
            (dataframe['choch'] == 1) &                              # Confirmation break
            (ote_check) &                                            # OTE (if required)
            (fvg_check_long) &                                       # FVG confluence (v0.28.0 default=True)
            (ob_check_long) &                                        # Order Block (if required)
            (safe_long) &                                            # No imbalance magnet beyond SL (v0.28.0)
            (dataframe['rr_long'] >= self.min_rr.value),            # Min R:R (v0.28.0 default=1.5)
            'enter_long'
        ] = 1
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Exit on HTF trend reversal (ChoCH is strongest signal)."""
        dataframe.loc[:, 'exit_long'] = 0
        dataframe.loc[:, 'exit_short'] = 0
        
        htf_trend_col = f'trend_{self.informative_timeframe}'
        
        if htf_trend_col in dataframe.columns:
            dataframe.loc[dataframe[htf_trend_col] == -1, 'exit_long'] = 1
            dataframe.loc[dataframe[htf_trend_col] == 1, 'exit_short'] = 1
        
        # Also exit on ChoCH on entry timeframe (stronger reversal signal)
        dataframe.loc[dataframe['choch'] == -1, 'exit_long'] = 1
        dataframe.loc[dataframe['choch'] == 1, 'exit_short'] = 1
        
        return dataframe

    # ── Custom Stoploss (ATR-based, v0.22.0) ─────────────────────────────────

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> float:
        """
        ATR-based dynamic stoploss (v0.22.0).
        
        SL is placed at 1.5x ATR(14) below entry price (longs) or above (shorts).
        This makes the stoploss:
        - Tighter in calm markets (ETH/ADA) → less loss per stop hit
        - Wider in volatile markets (BTC/SOL) → fewer premature exits
        
        Floor: -1.5% (don't place SL too tight — chop zone)
        Ceiling: -4.0% (don't let it run beyond backstop SL)
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        
        # Safety: can't compute SL without data
        if len(dataframe) == 0:
            return self.stoploss  # Fallback to static
        
        # Use the entry candle's ATR for stability (not current candle which may be mid-move)
        # Find candle at trade open time
        trade_open_dt = trade.open_date_utc
        entry_candle = dataframe[dataframe['date'] <= trade_open_dt]
        
        if len(entry_candle) == 0 or 'atr_pct' not in entry_candle.columns:
            return self.stoploss  # Fallback
        
        entry_atr_pct = entry_candle.iloc[-1]['atr_pct']
        
        if pd.isna(entry_atr_pct) or entry_atr_pct <= 0:
            return self.stoploss  # Fallback
            
        # Dynamically fetch ATR multiplier for this pair
        atr_mult = self.get_param('atr_multiplier', pair, self.atr_multiplier.value)
        
        # Dynamic SL = ATR multiplier * ATR% (as negative ratio)
        dynamic_sl = -(atr_mult * entry_atr_pct)
        
        # Apply floor and ceiling
        dynamic_sl = max(dynamic_sl, -0.04)   # No worse than -4%
        dynamic_sl = min(dynamic_sl, -0.015)  # No tighter than -1.5%
        
        # Return as ratio from current_rate perspective
        # Freqtrade expects: stoploss relative to current_rate (not entry)
        # But custom_stoploss must return value relative to entry price
        # so we convert: if current profit is positive, SL from current is less negative
        # Actually Freqtrade custom_stoploss returns value relative to CURRENT rate
        # A return of -0.05 means: if current rate drops 5% from now, stop.
        # But we want entry-based. Use: return stoploss_from_open()
        from freqtrade.strategy import stoploss_from_open
        return stoploss_from_open(dynamic_sl, current_profit, is_short=trade.is_short)

    def custom_exit(self, pair: str, trade: 'Trade', current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs):
        """
        Custom exit logic:
        1. Time-based exit: cut stale trades (v0.20.0)
        2. Target liquidity reached
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if len(dataframe) == 0:
            return None
            
        last_candle = dataframe.iloc[-1]
        
        # Time-based exit
        trade_duration = (current_time - trade.open_date_utc).total_seconds() / 3600
        
        # Fetch custom exits for pair
        te1_enabled = self.get_param('time_exit_1_enabled', pair, self.time_exit_1_enabled.value)
        te1_hours = self.get_param('time_exit_1_hours', pair, self.time_exit_1_hours.value)
        te1_profit = self.get_param('time_exit_1_profit', pair, self.time_exit_1_profit.value)
        
        te2_enabled = self.get_param('time_exit_2_enabled', pair, self.time_exit_2_enabled.value)
        te2_hours = self.get_param('time_exit_2_hours', pair, self.time_exit_2_hours.value)
        te2_profit = self.get_param('time_exit_2_profit', pair, self.time_exit_2_profit.value)
        
        if te1_enabled:
            if trade_duration >= te1_hours and current_profit <= te1_profit:
                return f"time_exit_{te1_hours}h"
        
        if te2_enabled:
            if trade_duration >= te2_hours and current_profit < te2_profit:
                return f"time_exit_{te2_hours}h"
        
        # Target liquidity
        if trade.is_short:
            if 'external_low' in last_candle and not pd.isna(last_candle.get('external_low')):
                if current_rate <= last_candle['external_low'] and current_profit > 0:
                    return "target_liquidity_reached"
        else:
            if 'external_high' in last_candle and not pd.isna(last_candle.get('external_high')):
                if current_rate >= last_candle['external_high'] and current_profit > 0:
                    return "target_liquidity_reached"
                    
        return None

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:
        """Conservative leverage."""
        return 3.0
