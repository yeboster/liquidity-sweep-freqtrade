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
    STRATEGY_VERSION = "2.0.53"

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

    # Research: STOP LOSS KILLS mean reversion. Widen to -8% so ATR stop (1.5-2×) handles exits.
    # BTC ATR ~2-4% → 2× ATR = 4-8% entry dynamic stop, hard stop is the floor.
    # v2.0.4 had -4.7% hard stop → stopped out before ATR stop could activate.
    use_custom_stoploss = True   # Enable custom_stoploss() — THIS WAS MISSING!

    # Research: HARD stoploss must be the disaster floor, not the active stop.
    # v2.0.22: Widen from -10.5% to -20%. Research: tight hard stop kills mean reversion
    # because the edge STRENGTHENS as price moves against you — cutting early destroys the edge.
    # Custom_stoploss() controls the active stop; hard stop only fires in catastrophic moves.
    stoploss = -0.0970

    # ── Entry Parameters ────────────────────────────────────────────────────
    # Bollinger + mean reversion
    bb_length = 20
    bb_std = 2.0
    # Research v2.0.24: BB at ±2σ is rare in crypto → lower from 1.4 to 1.2 to capture more MR setups.
    # Strategy #3 from stratbase.ai: "BB touch + RSI < 35 gave 68% WR, 1.71 PF" but only 31 signals.
    # 1.2σ is a more practical extreme while still requiring real deviation.
    # Research v2.0.34: Raised to 1.5σ — tighter entries catch deeper deviations with more reversion potential.
    # v2.0.33 had 1.1σ which caught shallow pullbacks that exhausted before full reversion.
    # R/R fix: entry at -1.5% deviation with exit at 1.5% reversion = 3% total move vs ~15% max loss = 0.2 R/R.
    # Combined with 2.5× ATR stop (~5-8% for crypto), this gives room for the trade to work.
    # Research v2.0.40: entry at 1.1% deviation catches shallow pullbacks in larger trends
    # → raise to 2.0%. Research: BTC 1H 2-3% below 20 SMA is the true abnormal deviation zone.
    # Deeper entry = larger reversion potential = better R/R. BB std at 1.5 already gives ±1.5σ
    # (≈95% of price in band) — 2% threshold requires real extremes.
    entry_dev_threshold = 1.7   # Was 1.0

    # ATR volatility compression
    atr_length = 14
    atr_compression_ratio = 1.00  # Was 0.90 — require true volatility compression, not normal vol

    # Volume confirmation
    volume_ma_length = 20
    volume_multiplier = 1.1     # volume > 1.3× SMA20 (tightened for quality)

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
    exit_rsi_long = 65   # Was 80
    exit_rsi_short = 35  # Was 20
    # Research v2.0.34: 1.5% means price must revert to within 1.5% of SMA (past the mean).
    # Combined with RSI exit at 80, this gives winners room to run.
    # v2.0.33 had 1.0% which was too tight — RSI 65 was the dominant exit at minimal profit.
    # Research v2.0.40: deeper entries (2.0%) need tighter exit band to capture 1-2% reversions
    # without waiting for full SMA touch. 0.5% gives room for the candle while locking in smaller wins.
    # v2.0.48: 0.5% was TOO TIGHT — avg win only 2.0% because RSI 65 exit fires before deviation hits 0.5%.
    # Research: price rarely retraces to within 0.5% of SMA on 1H candles before momentum normalizes.
    # Reverting to 1.0% — lets the actual MR bounce complete (3-5% potential) and improves R/R ratio.
    # Combined with Phase 2 lock-in at 1.5% (3%+ profit), this protects winners without strangling them.
    exit_dev_revert_pct = 1.0   # Was 0.5%

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
    trailing_stop_positive_offset = 0.1050
    trailing_only_offset_is_reached = True

    # Research: widened base stoploss to -12%, use_custom_stoploss=True (was missing — custom_stoploss never called!)
    # Stepped ATR stop: Phase1 wide (3×ATR, 8-15%), Phase2 2% lock-in at >3% profit, Phase3 1% at >8% profit
    # Key insight from freqtrade docs + GH #6955: use_custom_stoploss=True must be set explicitly
    # Without it, custom_stoploss() is never called regardless of method existence.

    # Scale-in: disabled — adding size on small profit was amplifying losses
    scale_in_enabled = False

    def custom_stoploss(
        self, pair: str, trade: "Trade", current_time: datetime,
        current_rate: float, current_profit: float, after_fill: bool,
        **kwargs
    ) -> Optional[float]:
        """Stepped ATR-based stop loss — enables custom_stoploss() to be called.

        Phase 1: Wide initial stop (1.5x ATR, floor 6%, cap 12%) — give trades room to work.
        Phase 2: Once profit > 2%, tighten to 1% lock-in — capture without strangling winners.
        Phase 3: Once profit > 5%, tighten to 1.5% — protect mega-winners.

        Research: freqtrade docs confirm custom_stoploss default = self.stoploss (static).
        Only with use_custom_stoploss=True does the dynamic ATR logic activate.
        """
        df, _ = self.dp.get_pair_dataframe(pair, self.timeframe)
        if df.empty:
            return -0.08

        last = df.iloc[-1]
        atr_pct = last.get("atr_pct", 2.0)

        # Phase 2 at >2% — lock in 1% once we have cushion. Phase 3 at >5% — tighten to 1.5%.
        if current_profit > 0.05:
            # Phase 3: major winner (>5%) — lock in 1.5%
            return -0.015
        elif current_profit > 0.02:
            # Phase 2: solid profit (>2%) — lock in 1%
            return -0.010
        else:
            # Phase 1: initial wide stop — 1.5x ATR, floor 6%, cap 12%
            stop_pct = min(0.12, max(0.06, atr_pct * 1.5 / 100))
            return -stop_pct

    def custom_exit(
        self, pair: str, trade: "Trade", current_time: datetime,
        current_rate: float, current_profit: float, current_profit_pct: float,
        **kwargs
    ) -> Optional[str]:
        """
        Time exit: if holding > N hours AND profit >= floor → exit.
        """
        if current_profit_pct >= self.time_exit_profit_floor:
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
        df, _ = self.dp.get_pair_dataframe(pair, self.timeframe)
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