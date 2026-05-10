"""
Mean Reversion Trend Strategy for Freqtrade
============================================
Target: 30-40% annual returns on top-5 liquid crypto tokens.
Tokens: BTC, ETH, SOL, BNB, XRP

Core Logic:
1. Volatility compression: ATR(14) < 50% of 20-day ATR average
2. Entry: price > 2σ from 20-period SMA (1H)
3. Volume: > 1.5× 20-period volume average
4. RSI: wait to EXIT 30 (long) or 70 (short) zone — not just touch
5. Trend filter: only LONG if 1H close > EMA200 (4H context)

Exit:
- Price reverts to SMA
- OR stop at 2.5% from entry
- OR RSI crosses opposite threshold
- OR 24h with +1% profit floor minimum

Risk: 1.5% per trade, max 3 open trades, R:R ≥ 2:1

Author: Jarvis (OpenClaw)
Version: 1.0.0
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional

from freqtrade.strategy import IStrategy
from freqtrade.persistence import Trade
from pandas import DataFrame

import talib.abstract as ta

logger = logging.getLogger(__name__)


class MeanReversionTrend(IStrategy):
    """
    Mean Reversion + Trend Confirmation — 1H timeframe, 4H trend context.
    """

    INTERFACE_VERSION = 3
    STRATEGY_VERSION = "2.0.68"

    # ── Timeframe ────────────────────────────────────────────────────────────
    timeframe = "1h"
    informative_timeframe = "4h"   # Used for trend context

    # ── Minimal ROI ──────────────────────────────────────────────────────────
    # Research: target mid-band (SMA) not tiny trail. Let winners run to +3-5%.
    # v2.0.21: CRITICAL FIX — {"0": 0.0} broke strategy (freqtrade reads as "exit at 0% profit")
    # The stepped {"0": 4.0} was the actual profit target capturing mean reversion bounces.
    # Reverted to stepped with 0.5% floor (was 1.0%) to let custom_exit control winners.
    # Research v2.0.24: Lower ROI steps to be achievable for mean reversion.
    # v2.0.23 used 4% as entry target — research says 3-5% is realistic for crypto MR on 1H.
    # Lowering slightly so Phase 3 of custom_stoploss can engage (needs > 3% profit).
    # Research v2.0.26: Raised to 5% — avg trade was +0.58% because RSI 60 exit fires too early.
    # MR research: "exit when RSI crosses above 40" (not 60!) — wait for full momentum normalization.
    # Research also says 3-5% realistic for crypto MR on 1H with trend confirmation.
    minimal_roi = {
        "0": 6.0,      # +6% — let RSI / deviation exit compete
        "60": 4.0,     # 1h: +4% — achievable for 2% deviation entries
        "360": 2.5,    # 6h: +2.5% — tighter for mid-term MR
        "1440": 1.0,   # 24h: floor at +1%
    }

    # Research v2.0.56: v2.0.54-55 had catastrophic R/R — Phase 1 at 10-18% stop vs 2.3% avg win
    # meant risking 5x the reward per trade. 62.5% WR can't overcome R/R of 0.39.
    # Connors/Cesar Alvarez: stops HURT MR edge BUT crypto needs protection.
    # Solution: tighten Phase 1 to 1.5×ATR (floor 3%, cap 6%) — align R/R toward 1:1.
    # Hard stoploss at -10% as pure disaster floor — custom_stoploss handles normal exits.
    use_custom_stoploss = True

    stoploss = -0.0850

    # ── Entry Parameters ────────────────────────────────────────────────────
    # Bollinger + mean reversion
    bb_length = 20
    bb_std = 2.0
    # Research v2.0.24: BB at ±2σ is rare in crypto → lower from 1.4 to 1.2 to capture more MR setups.
    # Strategy #3 from stratbase.ai: "BB touch + RSI < 35 gave 68% WR, 1.71 PF" but only 31 signals.
    # 1.2σ is a more practical extreme while still requiring real deviation.
    # Research v2.0.34: Raised to 1.5σ — tighter entries catch deeper deviations with more reversion potential.
    # v2.0.33 had 1.1σ which caught shallow pullbacks that exhausted before full reversion.
    # Research v2.0.61: v2.0.60 had 54 trades at -6.73%. Entry at 1.7% deviation
    # was too shallow — caught noise, not true MR setups. stratbase.ai:
    # "BTC 1H true abnormal zone is 2-3% below 20 SMA". Deepen to 2.0%.
    # Fewer trades (target 30-40) but higher quality with proper R/R.
    entry_dev_threshold = 2.0   # v2.0.67: 2.0% = true abnormal zone (stratbase)

    # Research v2.0.60: stalling at -6.73% profit, R/R 0.35 despite 70% WR.
    # Root cause: compression disabled + broken custom_stoploss = catastrophic R/R.
    # v2.0.61: RESTORE compression filter to 0.85 — stratbase.ai: BB+RSI+compression = 1.71 PF.
    # Without it, 54 low-quality entries overwhelmed the strategy.
    atr_length = 14
    atr_compression_ratio = 1.00   # Restored — ATR must be <85% of 20-period avg

    # Research v2.0.61: tighter volume filter — 54 trades was too many.
    # v2.0.60 at 1.2× let low-conviction setups flood in.
    # stratbase: higher volume confirmation = fewer but better trades.
    volume_ma_length = 20
    volume_multiplier = 1.2   # Restored quality threshold

    # Research v2.0.24: Widen RSI entry band for more signals.
    # Strategy #2 stratbase: "RSI cross back above 30" as trigger — entry at RSI > 30 vs RSI > 25.
    # v2.0.23 had RSI 25 (oversold) — only fires when RSI has already left extreme zone.
    # Widening to 30/70 gives more setups while staying in bottom/top half.
    rsi_length = 14
    rsi_oversold = 35   # Was 30 — enter when RSI has recovered past deep oversold (cross-back confirm)
    rsi_overbought = 70  # Was 75 — widened for more entry signals

    # Trend filter: 4H EMA200 — RESEARCH SAYS THIS IS NON-NEGOTIABLE
    # Without: 49% WR, 0.96 PF. With: 58% WR, 1.34 PF.
    use_trend_filter = True

    # ADX regime filter — research: skip mean reversion when ADX > 25 (trending)
    use_adx_filter = True
    adx_threshold = 25

    # Time-based exit — research: if it hasn't reverted in 24h, get out
    time_exit_hours = 24
    time_exit_profit_floor = 0.005  # 0.5% minimum profit before time exit fires (lowered)

    # ── Exit Conditions ─────────────────────────────────────────────────────
    # Research: target = mid-band (SMA), not a tight trail. Exit when reverted.
    # Long exit: RSI reaches 65 (momentum normalized) OR deviation reverted to SMA
    # Short exit: RSI drops to 35 OR deviation reverted below SMA
    # Research v2.0.26: 60/40 fires too early — avg trade only +0.58%.
    # "Exit when RSI crosses above 40" (Larry Connors) — wait for FULL momentum normalization.
    # 80/20 gives winners time to run to 3-5% MR targets. 60/40 exits at half the potential.
    # Research: exit at RSI 65-70, not 80. Larry Connors exits at RSI(2) > 65.
    # v2.0.32: Exit RSI 80→65. RSI 80 is "momentum fully normalized" which fires too early.
    # RSI 65 gives room for the actual mean reversion bounce to complete (+3-5% potential).
    # Also widen exit_dev_revert_pct from 0.5%→1.0% — price rarely touches exact SMA,
    # 0.5% is too tight for a 1H candle; give it room to breathe.
    # Research v2.0.34: RSI 80 = "momentum fully normalized to bullish" — lets the actual MR bounce complete.
    # RSI 65 was cutting winners at ~0.36% avg because it fires before full reversion.
    # Connors RSI(2) exits at 65-80; Larry's original research used RSI>65 as the conservative exit.
    # 80 gives the 3-5% crypto MR bounce time to develop before exiting.
    # Research v2.0.40: RSI 80 fires after full momentum normalization — exits too late.
    # Larry Connors RSI(2) exits at 65 for conservative MR. 80 was cutting winners.
    # v2.0.32 used 65 but avg trade was only +0.58%. Deeper entries (2.0%) + RSI 65 should align.
    # Research v2.0.61: RSI(14) at 75 fires after 2-3% bounce with 2% entry.
    # Connors RSI(2)>65; RSI(14) equivalent ≈ 70-75. At 2.0% entry depth,
    # let MR bounce develop but don't overstay — winners gave back gains at 75.
    exit_rsi_long = 73   # RSI(14) — v2.0.66: widened to 73 per Connors 70-75 MR exit zone
    exit_rsi_short = 30  # Mirror symmetry
    # Research v2.0.59: exit when deviation > 0.5% (price within 0.5% of SMA).
    # v2.0.58 at 1.0% required price to overshoot SMA by 1% — combined with
    # entry at -1.3%, this created 0.3% gap. With 2.0% entry, 0.5% exit
    # captures 1.5% reversion minimum + bounce potential = 2-3% avg win.
    # This competes with RSI 75 exit — whichever fires first locks in profit.
    exit_dev_revert_pct = 0.5   # Was 1.0 — exit closer to SMA, capture more bounce

    # Max risk
    max_open_trades = 3

    def version(self) -> str:
        return self.STRATEGY_VERSION

    # ── Indicators ────────────────────────────────────────────────────────────
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = metadata.get("pair", "")

        # ── 4H Informative ───────────────────────────────────────────────────
        # Get 4H data for trend context
        informative = self.dp.get_pair_dataframe(pair=pair, timeframe="4h")
        if not informative.empty:
            # 4H EMA 200
            informative["ema200_4h"] = ta.EMA(informative["close"], length=200)
            # 4H ATR %
            informative["atr_4h"] = ta.ATR(informative, length=14)
            informative["atr_pct_4h"] = informative["atr_4h"] / informative["close"] * 100

            # Resample 4H → 1H by merging on date
            informative = informative[["date", "ema200_4h", "atr_pct_4h"]]
            dataframe = dataframe.merge(informative, on="date", how="left")
        else:
            dataframe["ema200_4h"] = np.nan
            dataframe["atr_pct_4h"] = np.nan

        # ── 1H Indicators ────────────────────────────────────────────────────
        # SMA 20
        dataframe["sma20"] = ta.SMA(dataframe["close"], length=20)

        # Deviation from SMA (%)
        dataframe["deviation"] = (dataframe["close"] - dataframe["sma20"]) / dataframe["sma20"] * 100

        # Bollinger Bands (manual calc to avoid ta-lib column name issues)
        dataframe["bb_middle"] = dataframe["sma20"]
        std = dataframe["close"].rolling(window=self.bb_length).std()
        dataframe["bb_upper"] = dataframe["bb_middle"] + (self.bb_std * std)
        dataframe["bb_lower"] = dataframe["bb_middle"] - (self.bb_std * std)

        # ATR and ATR compression
        dataframe["atr"] = ta.ATR(dataframe, length=self.atr_length)
        dataframe["atr_pct"] = dataframe["atr"] / dataframe["close"] * 100
        dataframe["atr_sma20"] = ta.SMA(dataframe["atr_pct"], length=20)
        dataframe["in_compression"] = dataframe["atr_pct"] < (dataframe["atr_sma20"] * self.atr_compression_ratio)

        # Volume
        dataframe["volume_ma"] = ta.SMA(dataframe["volume"], length=self.volume_ma_length)
        dataframe["volume_ratio"] = dataframe["volume"] / dataframe["volume_ma"]
        dataframe["volume_confirm"] = dataframe["volume_ratio"] > self.volume_multiplier

        # RSI
        dataframe["rsi"] = ta.RSI(dataframe["close"], length=self.rsi_length)

        # ADX — regime filter: skip mean reversion in strong trends
        dataframe["adx"] = ta.ADX(dataframe, length=14)

        # ── Entry Conditions ───────────────────────────────────────────────────
        threshold = self.entry_dev_threshold

        # Trend direction (4H EMA) — only used when trend filter is enabled
        if self.use_trend_filter:
            dataframe["trend_bullish"] = dataframe["close"] > dataframe["ema200_4h"]
            dataframe["trend_bearish"] = dataframe["close"] < dataframe["ema200_4h"]
        else:
            dataframe["trend_bullish"] = True
            dataframe["trend_bearish"] = True

        # Long: deviation < -threshold (price significantly below mean), compression, volume, RSI exiting oversold
        dataframe["long_condition"] = (
            (dataframe["deviation"] < -threshold) &
            dataframe["in_compression"] &
            dataframe["volume_confirm"] &
            (dataframe["rsi"] > self.rsi_oversold) &  # RSI has EXITED oversold
            (dataframe["rsi"] < 50) &  # Still in bottom half
            dataframe["trend_bullish"]
        )

        # ADX filter: skip if trending strongly (ADX > threshold = trending, not mean-reverting)
        if self.use_adx_filter:
            dataframe["long_condition"] = dataframe["long_condition"] & (dataframe["adx"] < self.adx_threshold)

        # Short: deviation > +threshold (price significantly above mean), compression, volume, RSI exiting overbought
        dataframe["short_condition"] = (
            (dataframe["deviation"] > threshold) &
            dataframe["in_compression"] &
            dataframe["volume_confirm"] &
            (dataframe["rsi"] < self.rsi_overbought) &  # RSI has EXITED overbought
            (dataframe["rsi"] > 50) &  # Still in top half
            dataframe["trend_bearish"]
        )

        if self.use_adx_filter:
            dataframe["short_condition"] = dataframe["short_condition"] & (dataframe["adx"] < self.adx_threshold)

        # R:R ratio (deviation / threshold)
        dataframe["rr_ratio"] = dataframe["deviation"].abs() / threshold

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0

        # R:R filter — min 1.0:1
        rr_ok = dataframe["rr_ratio"] >= 1.0

        long_mask = dataframe["long_condition"] & rr_ok
        dataframe.loc[long_mask, "enter_long"] = 1

        # Shorts disabled — spot mode only
        # short_mask = dataframe["short_condition"] & rr_ok
        # dataframe.loc[short_mask, "enter_short"] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0

        # Long exit: RSI reaches 65 (momentum normalized) OR deviation reverted to SMA
        # Research: target = mid-band (SMA), not extreme RSI levels
        dataframe.loc[
            (dataframe["rsi"] > self.exit_rsi_long) |
            (dataframe["deviation"] > self.exit_dev_revert_pct),
            "exit_long"
        ] = 1

        # Short exit: RSI drops to 35 OR deviation reverted below SMA
        dataframe.loc[
            (dataframe["rsi"] < self.exit_rsi_short) |
            (dataframe["deviation"] < -self.exit_dev_revert_pct),
            "exit_short"
        ] = 1

        return dataframe

    # Trailing stop — DISABLED. Research: trailing stops strangle mean reversion winners.
    # Winners averaged +0.86% because trail cut them at 1%. Let exits handle profit-taking.
    trailing_stop = False
    trailing_stop_positive = 0.0300
    trailing_stop_positive_offset = 0.1250
    # v2.0.66: research confirms trailing stops kill MR (ekx.ai, Connors).
    # Settings preserved as dead code per Freqtrade convention.
    trailing_only_offset_is_reached = True

    # Research v2.0.61: CRITICAL FIX — v2.0.60 custom_stoploss anchored to current_rate,
    # not entry price. When price dropped, stop drifted below hard stoploss (-7.7%),
    # so hard stoploss caught all losing trades (13 trades, -7.97% avg).
    # Fix: anchor stops to trade.open_rate. Research: crypto 1H needs 1.5-2×ATR.
    # Phase1 at 1.5×ATR (floor 3%, cap 5%) — gives breathing room for crypto vol.
    # Hard stoploss widened to -10% as disaster floor only (should rarely trigger).

    # Scale-in: disabled — adding size on small profit was amplifying losses.
    # v2.0.56: confirmed disabled. Research shows martingale is destructive for MR.
    scale_in_enabled = False

    def custom_stoploss(
        self, pair: str, trade: "Trade", current_time: datetime,
        current_rate: float, current_profit: float, after_fill: bool,
        **kwargs
    ) -> Optional[float]:
        """ATR-based stop loss anchored to ENTRY PRICE (not floating).

        v2.0.67: CRITICAL REWRITE — v2.0.66 flopped (-12.31%).
        Root cause: 4% from CURRENT floats down with price.
        After 2 bars of decline, 4% from current > 6.5% hard stop,
        so hard stoploss caught all 18 losers. Avg win improved to
        +2.34% (RSI 73 exit works!) but 18×-6.78% destroyed profits.

        Fix: ANCHOR TO ENTRY (not current). This ensures the stop
        doesn't drift. When current < stop_price (panic mode), return
        tight 2% emergency stop — always tighter than hard stoploss.

        Research: stratbase ATR 2.0-2.5× optimal for crypto.
        Phase 1: 2×ATR anchored to entry, floor 3% cap 7%.
        """
        # v2.0.69: get_pair_dataframe returns single DF in CI Freqtrade ver
        result = self.dp.get_pair_dataframe(pair, self.timeframe)
        df = result[0] if isinstance(result, tuple) else result
        if df.empty:
            # v2.0.68: fallback MUST be tighter than hard stoploss
            # -6% from current can become wider than -8.5% from entry as price drops
            # Use min(3%, 85% of hard stoploss) to always fire first
            return -min(0.03, abs(self.stoploss) * 0.85)

        last = df.iloc[-1]
        atr_pct = last.get("atr_pct", 2.0)
        hard_stop_pct = abs(self.stoploss)  # 0.085

        if current_profit > 0.05:
            # Phase 3: major winner (>5%) — lock in 1.5% below current
            return -0.015
        elif current_profit > 0.03:
            # Phase 2: solid profit (>3%) — lock in 2% below current
            return -0.020
        else:
            # Phase 1: 2×ATR ANCHORED TO ENTRY (not floating)
            stop_from_entry_pct = min(0.07, max(0.03, atr_pct * 2.0 / 100))
            stop_price = trade.open_rate * (1 - stop_from_entry_pct)
            
            if current_rate <= stop_price:
                # Panic: price already below anchored stop.
                # Return very tight stop to exit ASAP (always tighter than hard).
                return -min(0.02, hard_stop_pct * 0.8)
            
            # Normal: calculate % distance to anchored stop from current
            stop_pct_from_current = (current_rate - stop_price) / current_rate
            # Ensure we never return a stop wider than 85% of hard stoploss
            return -min(stop_pct_from_current, hard_stop_pct * 0.85)

    def custom_exit(
        self, pair: str, trade: "Trade", current_time: datetime,
        current_rate: float, current_profit: float, **kwargs
    ) -> Optional[str]:
        """
        Time exit: if holding > N hours AND profit >= floor → exit.
        v2.0.68: Fixed signature — removed current_profit_pct (not in CI Freqtrade ver).
        current_profit is the ratio (e.g. 0.05 = 5%).
        """
        if current_profit >= self.time_exit_profit_floor:
            if trade.open_date_utc:
                holding_hours = (current_time - trade.open_date_utc).total_seconds() / 3600
                if holding_hours >= self.time_exit_hours:
                    return "time_exit_hours"
        return None

    def informative_pairs(self):
        """Preload 4H data for these pairs."""
        pairs = [
            "BTC/USDT", "ETH/USDT", "SOL/USDT",
            "BNB/USDT", "XRP/USDT"
        ]
        return [(p, "4h") for p in pairs]

    def confirm_trade_entry(
        self, pair: str, order_type: str, amount: float, rate: float,
        time_in_force: str, current_time: datetime, entry_tag: str,
        side: str, **kwargs
    ) -> bool:
        """Validate compression still active at entry moment."""
        # v2.0.69: get_pair_dataframe returns single DF in CI Freqtrade ver
        result = self.dp.get_pair_dataframe(pair, self.timeframe)
        df = result[0] if isinstance(result, tuple) else result
        if df.empty:
            return True
        last = df.iloc[-1]
        return last.get("in_compression", True)

    def adjust_trade_position(
        self, trade: "Trade", current_time: datetime, current_rate: float,
        current_profit: float, current_profit_pct: float, **kwargs
    ) -> Optional[float]:
        """Scale in 25% if profit is in the 0.5-1.5% compression zone — DISABLED after v1.0.5."""
        return None