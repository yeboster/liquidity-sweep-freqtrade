"""
Liquidity Sweep Reversal Strategy for Freqtrade
================================================
Based on: https://dailypriceaction.com/blog/liquidity-sweep-reversals/

Core Logic:
1. Identify HTF trend via Break of Structure / Change of Character
2. Wait for price to retrace into OTE (optional)
3. Detect liquidity sweep (price takes out swing high/low cluster)
4. Enter on confirmation (close beyond triggering swing)
5. Require recent FVG confluence — a bullish/bearish FVG formed within N candles
6. Skip entry if unmitigated imbalance exists beyond stop loss (v0.29.0)

Uses smartmoneyconcepts library for ICT indicator calculations.

Author: Jarvis (OpenClaw)
Version: 0.35.0

Changelog:
- v0.35.0 (2026-03-01): Fix FVG active zone detection — same class of bug as OB window (v0.31.0).
  ROOT CAUSE: `fvg_mitigated.isna()` was supposed to isolate "unmitigated" FVGs.
  But during backtesting the smc library has full future data and sets MitigatedIndex
  for EVERY FVG that is eventually mitigated (nearly all of them). So `fvg_mitigated.isna()`
  was True only for the very last candles → zone forward-fills were essentially empty →
  `active_bullish_fvg` was always False → 0 trades in v0.33.0 and v0.34.0.
  FIX: Rolling window (30 candles, ~7.5h at 15m): "Was a bullish/bearish FVG formed
  within the last 30 candles?" — sensible SMC recency check, analagous to OB fix.
  Also simplified opposite-side imbalance filter to use same rolling zone levels.
  Expected: Restores trade flow to 90+ (similar to v0.27.0/v0.29.0) while keeping
  FVG recency as a quality gate.
- v0.32.0 (2026-02-28): Fix OB recency window — increase from 20 to 100 candles.
  Root cause of v0.31.0 0-trade bug: smc.ob() produces sparse OB candles (one
  every ~50-200 candles). A 20-candle window (~5h at 15m) misses most OBs.
  Fix: expand ob_window from 20 → 100 candles (~25h / ~1 day at 15m).
  Rationale: "Was institutional buying/selling present somewhere in the last day?"
  is a much more sensible SMC recency question. OBs are structural anchors — the
  last down-candle before a bullish BOS may have been printed hours ago and it
  still acts as demand. 100 candles ensures the flag is True for the majority of
  candles following an OB formation, giving ChoCH+sweep signals a chance to fire.
  All other settings unchanged from v0.29.0 (wider ROI, safe_long/short filter).
- v0.34.0 (2026-03-01): Quality Gate Shift + Risk Expansion.
  Problem (v0.32): 2 trades in 2 years. The `smc.ob()` (Order Block) library
  is far too sparse for reliable confluence across the board.
  Fix: Set `require_ob=False` globally.
  Problem (v0.29): TSL avg loss (-1.61%) vs avg ROI win (+0.57%) math is
  inverted. TSL hits occur too early before impulsive reversals.
  Fix: Widen ATR SL from 1.5x -> 2.0x ATR to give ICT reversals room.
  Fix: min_rr reduced 1.5 -> 1.0 (allow standard SMC setups).
  Primary Quality Gate: `require_fvg=True` (active imbalance zone) +
  opposite-side imbalance filter (safe_long/short).


- v0.31.0 (2026-02-28): Fix OB detection bug (0 trades in v0.30.0). Replace
  "price inside exact OB box" check with "recent OB formed within N candles"
  (rolling window). The precise OB box (top/bottom ffill) is too narrow —
  price rarely sits inside the exact OB candle range at entry time. The correct
  SMC interpretation: an OB nearby (within 20 candles) signals institutional
  interest at this price level. Entry at OB + sweep + ChoCH is still high
  confluence. Wider ROI targets from v0.30.0 retained.

- v0.30.0 (2026-02-28): Mandatory Order Block confluence + wider ROI targets.
  Analysis of v0.29.0 (99 trades, 24.2% WR, -19.16%):
  - TSL exits reduced from 55→36 (imbalance filter worked), but still too many.
  - Root cause: avg win = +0.57%, avg TSL loss = -1.61%. Need ~74% WR to break
    even. With SMC signals at 24%, math is broken at the R:R level.
  - Two-pronged fix:
    (1) require_ob=True by default: Force entry to be inside an active Order Block
        zone. OBs are the structural footprint of institutional money — the
        last down-candle before a BOS up (bullish OB) or last up-candle before
        a BOS down (bearish OB). Price returns to OBs as demand/supply zones.
        Entering at OB + sweep + ChoCH = max confluence ICT entry. Fewer trades,
        much higher reversal probability (expected WR 35-50%).
    (2) Widen ROI table to let winners run: avg ROI exit was +0.57% — institutional
        moves at OBs tend to be impulsive (BOS candles). Targets widened to:
        0min→5%, 30min→3.5%, 60min→2%, 120min→1.2%, 240min→0.5%, 480min→-0.5%.
        Goal: push avg ROI exit from 0.57% to 1.5%+, transforming the math.
  Expected: 40-60 trades (OB filter is strict), WR 35-50%, first profitable run.
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
    STRATEGY_VERSION = "0.37.0"

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
    # v0.30.0: Widened ROI targets — OB entries at institutional demand/supply zones
    # tend to produce impulsive moves. Previous +0.57% avg win was too conservative.
    # Target: let institutional momentum trades run to 1.5%+ before taking profit.
    minimal_roi = {
        "0": 0.05,      # 5% immediately (wide for impulsive OB-driven moves)
        "30": 0.035,    # 3.5% after 30 min
        "60": 0.02,     # 2.0% after 1h
        "120": 0.015,   # 1.5% after 2h (v0.36: slightly tighter)
        "480": 0.005,   # 0.5% after 8h (v0.36: delayed stale exit)
        "720": 0        # Exit after 12h
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
    # v0.37.0: Re-expanded for hyperopt (30-85%)
    ote_lower = DecimalParameter(0.30, 0.50, default=0.30, space="buy", optimize=True)
    ote_upper = DecimalParameter(0.55, 0.85, default=0.70, space="buy", optimize=True)
    require_ote = CategoricalParameter([True, False], default=True, space="buy", optimize=True)
    
    # ATR-based SL — new in v0.22.0
    # v0.34.0: ATR Multiplier increase to 2.0x (from 1.5x)
    # The avg TSL loss in v0.29.0 was -1.61% vs avg win +0.57%. Loosening SL
    # gives institutional reversals room to breathe.
    atr_multiplier = DecimalParameter(1.0, 3.0, default=2.0, space="buy", optimize=True)
    atr_period = IntParameter(10, 20, default=14, space="buy", optimize=False)
    
    # Entry filters
    min_rr = DecimalParameter(0.5, 4.0, default=1.0, space="buy", optimize=True)
    require_fvg = CategoricalParameter([True, False], default=True, space="buy", optimize=True)
    # v0.30.0: Order Block now mandatory by default (was False).
    # OB = structural demand/supply zone created by institutional move. Entering
    # at OB + sweep + ChoCH = max confluence ICT setup. Expected to cut TSL exits
    # dramatically (price at OB has structural support, less likely to continue against us).
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
        
        # v0.35.0 FIX: FVG "active zone" detection was broken in all prior versions.
        #
        # ROOT CAUSE (v0.29.0 → v0.34.0):
        # The condition `fvg_mitigated.isna()` was used to identify "unmitigated" FVGs.
        # During backtesting, the smartmoneyconcepts library has access to the full dataset
        # and marks the MitigatedIndex for EVERY FVG that eventually gets mitigated.
        # Since nearly all historical FVGs are eventually mitigated, `fvg_mitigated.isna()`
        # is almost always False. The resulting zone forward-fills had near-zero coverage,
        # making `active_bullish_fvg` essentially always False → 0 trades.
        # This is the same class of bug as the OB window issue (v0.31.0/v0.32.0):
        # point-in-time signals used in a way that makes them always False.
        #
        # FIX (v0.35.0): Use a rolling window approach (identical to OB fix in v0.31.0).
        # "Was a bullish/bearish FVG formed within the last N candles?"
        # FVG window of 30 candles (~7.5h at 15m): recent imbalance signal.
        # This is sensible SMC: an FVG formed today is still an active imbalance zone
        # worth trading from — mitigation (price touching it) is EXPECTED on the return move.
        fvg_window = 30  # ~7.5h at 15m — "Was imbalance created recently?"
        dataframe['active_bullish_fvg'] = (
            dataframe['fvg']
            .eq(1)
            .rolling(window=fvg_window, min_periods=1)
            .max()
            .astype(bool)
        )
        dataframe['active_bearish_fvg'] = (
            dataframe['fvg']
            .eq(-1)
            .rolling(window=fvg_window, min_periods=1)
            .max()
            .astype(bool)
        )
        
        # Keep zone level tracking for opposite-side imbalance filter
        # (These use the raw fvg_top/bottom columns, not mitigation-dependent)
        dataframe['bullish_fvg_zone_top'] = dataframe['fvg_top'].where(dataframe['fvg'] == 1).ffill()
        dataframe['bullish_fvg_zone_bottom'] = dataframe['fvg_bottom'].where(dataframe['fvg'] == 1).ffill()
        dataframe['bearish_fvg_zone_top'] = dataframe['fvg_top'].where(dataframe['fvg'] == -1).ffill()
        dataframe['bearish_fvg_zone_bottom'] = dataframe['fvg_bottom'].where(dataframe['fvg'] == -1).ffill()
        
        # v0.28.0: Opposite-side imbalance check (Marco's SMC rule)
        # v0.35.0: simplified — use the already-computed zone level columns
        # (no longer gated on mitigation status, same fix as active_fvg above)
        dataframe['bearish_fvg_bottom'] = dataframe['bearish_fvg_zone_bottom']
        dataframe['bullish_fvg_top'] = dataframe['bullish_fvg_zone_top']
        
        # 4. Order Blocks
        ob_data = smc.ob(ohlc, swing_data, close_mitigation=False)
        dataframe['ob'] = ob_data['OB']                  # 1=bullish, -1=bearish
        dataframe['ob_top'] = ob_data['Top']
        dataframe['ob_bottom'] = ob_data['Bottom']
        dataframe['ob_volume'] = ob_data.get('OBVolume', 0)
        
        # v0.32.0 FIX: OB zone detection (rolling window expanded from 20→100).
        # The previous approach (price inside exact OB box via ffill) produced 0
        # trades because the OB candle range is too narrow — price rarely sits
        # precisely inside a historical candle's body at entry time.
        #
        # Correct SMC interpretation: an Order Block formed RECENTLY (within the
        # last 20 candles) signals that institutional money was active at this
        # price level. The OB doesn't need to be "open" — it needs to be nearby
        # in time. Entry is still high confluence: OB (institutional interest
        # recently) + sweep + ChoCH (confirmation of reversal).
        #
        # Rolling window: 20 candles (~20h on 1h TF). A bullish OB formed within
        # the last 20 candles confirms institutional buying pressure is recent.
        ob_window = 100  # v0.32.0: expanded from 20 → 100 candles (~25h at 15m). OBs are sparse
        # (smc.ob() marks one every ~50-200 candles). A 20-candle (~5h) window missed
        # almost all of them → 0 trades in v0.31.0. 100 candles = "institutional footprint
        # present somewhere in the last day?" which is a sensible SMC recency check.
        dataframe['in_bullish_ob'] = (
            dataframe['ob']
            .eq(1)
            .rolling(window=ob_window, min_periods=1)
            .max()
            .astype(bool)
        )
        dataframe['in_bearish_ob'] = (
            dataframe['ob']
            .eq(-1)
            .rolling(window=ob_window, min_periods=1)
            .max()
            .astype(bool)
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
        
        # v0.36.0: Enhanced FVG confluence (Price inside/near the zone)
        # Instead of just "an FVG formed recently", we ensure price is actually 
        # testing the imbalance.
        fvg_check_short = (
            dataframe['active_bearish_fvg'] & 
            (dataframe['close'] >= dataframe['bearish_fvg_zone_bottom']) & 
            (dataframe['close'] <= dataframe['bearish_fvg_zone_top'])
        ) if req_fvg else True
        
        fvg_check_long = (
            dataframe['active_bullish_fvg'] & 
            (dataframe['close'] <= dataframe['bullish_fvg_zone_top']) & 
            (dataframe['close'] >= dataframe['bullish_fvg_zone_bottom'])
        ) if req_fvg else True
        
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
        # v0.36.0 FIX: Logic was inverted since v0.28.0. 
        # For LONGS: SL is below. Magnet is a BULLISH FVG (support) even deeper.
        # For SHORTS: SL is above. Magnet is a BEARISH FVG (resistance) even higher.
        sl_buffer = self.buffer_pips.value
        long_sl_level = dataframe['swing_low_level'] - sl_buffer
        short_sl_level = dataframe['swing_high_level'] + sl_buffer

        safe_long = ~(
            dataframe['bullish_fvg_zone_top'].notna() &
            (dataframe['bullish_fvg_zone_top'] < long_sl_level)
        )
        safe_short = ~(
            dataframe['bearish_fvg_zone_bottom'].notna() &
            (dataframe['bearish_fvg_zone_bottom'] > short_sl_level)
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
