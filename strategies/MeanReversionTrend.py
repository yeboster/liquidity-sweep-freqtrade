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
    STRATEGY_VERSION = "1.0.0"

    # ── Timeframe ────────────────────────────────────────────────────────────
    timeframe = "1h"
    informative_timeframe = "4h"   # Used for trend context

    # ── Minimal ROI ──────────────────────────────────────────────────────────
    minimal_roi = {
        "0": 5.0,      # +5% initial target — let early exits handle via custom_exit
        "60": 3.0,     # 1h: +3%
        "180": 2.0,    # 3h: +2%
        "1440": 1.0,   # 24h: floor at +1%
    }

    # Hard stoploss (absolute backstop — not normally reached)
    stoploss = -0.025   # -2.5%

    # ── Entry Parameters ────────────────────────────────────────────────────
    # Bollinger + mean reversion
    bb_length = 20
    bb_std = 2.0
    entry_dev_threshold = 2.0   # σ multiplier for entry

    # ATR volatility compression
    atr_length = 14
    atr_compression_ratio = 0.5  # ATR must be < X% of 20-day ATR average

    # Volume confirmation
    volume_ma_length = 20
    volume_multiplier = 1.5     # volume > X × SMA20

    # RSI confirmation
    rsi_length = 14
    rsi_oversold = 30
    rsi_overbought = 70

    # Trend filter: 4H EMA200
    use_trend_filter = True

    # Time-based exit
    time_exit_hours = 24
    time_exit_profit_floor = 0.01  # 1% minimum profit before time exit fires

    # Trailing — disabled (use fixed exits)
    trailing_stop = False

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

            # Resample 4H → 1H
            informative["date_4h"] = informative["date"]
            informative = informative[["date_4h", "ema200_4h", "atr_pct_4h"]]
            dataframe = dataframe.merge(informative, on="date_4h", how="left")
        else:
            dataframe["ema200_4h"] = np.nan
            dataframe["atr_pct_4h"] = np.nan

        # ── 1H Indicators ────────────────────────────────────────────────────
        # SMA 20
        dataframe["sma20"] = ta.SMA(dataframe["close"], length=20)

        # Deviation from SMA (%)
        dataframe["deviation"] = (dataframe["close"] - dataframe["sma20"]) / dataframe["sma20"] * 100

        # Bollinger Bands
        bollinger = ta.BBANDS(
            dataframe["close"],
            length=self.bb_length,
            nbdevup=self.bb_std,
            nbdevdn=self.bb_std
        )
        dataframe["bb_upper"] = bollinger["BBU_20_2.0"]
        dataframe["bb_middle"] = bollinger["BBM_20_2.0"]
        dataframe["bb_lower"] = bollinger["BBL_20_2.0"]

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

        # ── Entry Conditions ───────────────────────────────────────────────────
        threshold = self.entry_dev_threshold

        # Trend direction (4H EMA)
        dataframe["trend_bullish"] = dataframe["close"] > dataframe["ema200_4h"]
        dataframe["trend_bearish"] = dataframe["close"] < dataframe["ema200_4h"]

        # Long: deviation < -threshold (price significantly below mean), compression, volume, RSI exiting oversold
        dataframe["long_condition"] = (
            (dataframe["deviation"] < -threshold) &
            dataframe["in_compression"] &
            dataframe["volume_confirm"] &
            (dataframe["rsi"] > self.rsi_oversold) &  # RSI has EXITED oversold (<30)
            (dataframe["rsi"] < 50) &  # Still in bottom half
            dataframe["trend_bullish"]
        )

        # Short: deviation > +threshold (price significantly above mean), compression, volume, RSI exiting overbought
        dataframe["short_condition"] = (
            (dataframe["deviation"] > threshold) &
            dataframe["in_compression"] &
            dataframe["volume_confirm"] &
            (dataframe["rsi"] < self.rsi_overbought) &  # RSI has EXITED overbought (>70)
            (dataframe["rsi"] > 50) &  # Still in top half
            dataframe["trend_bearish"]
        )

        # R:R ratio (deviation / threshold)
        dataframe["rr_ratio"] = dataframe["deviation"].abs() / threshold

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0

        # R:R filter — min 2:1
        rr_ok = dataframe["rr_ratio"] >= 2.0

        long_mask = dataframe["long_condition"] & rr_ok
        dataframe.loc[long_mask, "enter_long"] = 1

        short_mask = dataframe["short_condition"] & rr_ok
        dataframe.loc[short_mask, "enter_short"] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0

        # Long exit: RSI overbought OR deviation reverted to within 0.5% of SMA
        dataframe.loc[
            (dataframe["rsi"] > self.rsi_overbought) |
            (dataframe["deviation"] > -0.5),
            "exit_long"
        ] = 1

        # Short exit: RSI oversold OR deviation reverted to within 0.5% above SMA
        dataframe.loc[
            (dataframe["rsi"] < self.rsi_oversold) |
            (dataframe["deviation"] < 0.5),
            "exit_short"
        ] = 1

        return dataframe

    def custom_stoploss(
        self, pair: str, trade: "Trade", current_time: datetime,
        current_rate: float, current_profit: float, after_fill: bool,
        **kwargs
    ) -> Optional[float]:
        """Fixed -2.5% stoploss."""
        return -0.025

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
        """
        Scale in 25% if profit is in the 0.5-1.5% compression zone.
        """
        if 0.005 < current_profit_pct < 0.015:
            return 0.25
        return None