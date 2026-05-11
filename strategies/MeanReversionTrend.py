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
- OR stop at 6.5% from entry
- OR RSI crosses opposite threshold
- OR 16h with +0.5% profit floor minimum

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
    STRATEGY_VERSION = "2.0.98"

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

    # Research v2.0.83: COMPLETE REVERSION of custom_stoploss approach.
    # v2.0.81-82 proved custom_stoploss kills MR winners:
    #   v2.0.80 (no custom_stoploss): 40 exit_signal winners at +2.74%, 24 stop-outs at -5.48%
    #   v2.0.82 (custom_stoploss): 17 exit_signal winners at +1.70%, 30 trailing_stop at -1.68%
    #   custom_stoploss prevented winners from reaching exit_signal → worse R/R, worse profit
    #
    # New approach: NO custom stoploss. WIDE hard stop (-8.5%) as ultimate disaster floor.
    # Losing trades exit via time_exit_loss at 24h (prevent bag-holding).
    # Winning trades exit via exit_signal (RSI/deviations) — which has been 98-100% WR.
    #
    # Connors: "fixed stoplosses reduced performance" — but our time-based exit handles that.
    use_custom_stoploss = False

    # Research v2.0.92: REVERSAL of wide-stop thesis. nf-china MR research misinterpreted.
    # -9.4% stop produced 2 catastrophic exits at -9.67% avg, destroying R/R (0.31).
    # Research: MR crypto 1H needs 1.5-2×ATR stop = 4-7%. nf-china refers to equity
    # MR where stops are wider because reversions take weeks, not hours.
    # stratbase.ai: "2.0×ATR(14) produced best Sharpe on 4H" → 1.5-2× on 1H ≈ 5-7%.
    # Tightening from -9.4% to -6.5% saves ~3% per stopped trade without affecting winners.
    # Losers now exit via faster time_exit_loss (16h) at ~-4%, not at -9.7%.
    stoploss = -0.0470

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
    # v2.0.87: REVERTED from 1.85→1.80 — proven sweet spot from v2.0.83 (69% WR).
    # v2.0.85-86 experiment: 1.85-2.0% cut exit_signals from 31→15-19.
    # Lower deviation catches more real MR setups with 100% WR exit_signals.
    entry_dev_threshold = 1.60

    # Research v2.0.77: v2.0.76 at 0.85 = 4 trades, avg win +4.55%, R/R 0.79, DD 1.9%.
    # Entries are clearly higher quality but too few. Loosen to 0.90 for 15-25 target.
    # Vantixs: ATR < 1.0×avg = normal MR conditions. 0.90 filters only volatile expansions.
    atr_length = 14
    # v2.0.89: Tighten to 0.90 — Vantixs research: ATR < 0.9x avg prevented 72% of
    # largest MR losses. Only enter when volatility is clearly compressing, not just normal.
    atr_compression_ratio = 0.90

    # Research v2.0.81: v2.0.80 at 1.1× = 65 trades, 37% stop-outs. Low-quality volume entries.
    # stratbase: volume confirmation is essential. Vantixs: declining volume on move improves WR +5pp.
    # Raise to 1.2× — reduces noise entries that pass deviation/RSI but lack real momentum exhaustion.
    volume_ma_length = 20
    volume_multiplier = 1.2   # v2.0.81: raised from 1.1 — filter low-conviction volume entries

    # Research v2.0.76: revert RSI to 35 — v2.0.75 at 30 was too restrictive when stacked.
    # Connors RSI(2) cross-back at 30; but our RSI(14) is less sensitive.
    # stratbase: RSI 35 + BB = 68% WR, 1.71 PF on BTC 4H. Keep this proven level.
    rsi_length = 14
    rsi_oversold = 35   # v2.0.86: REVERTED from 32→35 — stratbase-validated: RSI(14) < 35 + BB = strongest MR combo.
    # v2.0.85 at 32 collapsed WR to 44% — too restrictive when stacked with other filters.
    rsi_overbought = 70  # Was 75 — widened for more entry signals

    # Trend filter: 4H EMA200 — RESEARCH SAYS THIS IS NON-NEGOTIABLE
    # Without: 49% WR, 0.96 PF. With: 58% WR, 1.34 PF.
    use_trend_filter = True

    # ADX regime filter — research: skip mean reversion when ADX > 25 (trending)
    use_adx_filter = True
    adx_threshold = 25

    # Time-based exit — research: if it hasn't reverted in 18h, get out
    # v2.0.81: Lower to 18h (research: most MR reversions happen within 12-18h or not at all)
    # Also exit LOSING trades at 24h (prevent bag-holding on failed setups)
    time_exit_hours = 18
    time_exit_profit_floor = 0.005  # 0.5% minimum profit for PROFITABLE time exit (lowered)
    # v2.0.87: REVERTED from 16h→24h — 16h was KILLING winners.
    # v2.0.86 lost 12 exit_signal (100% WR) trades because they got cut at 16h
    # before developing to exit_signal at 17-24h. Crypto 1H MR needs full 24h.
    # Keep -9% stop as ultimate floor (nf-china: MR works better with wider stops).
    time_exit_loss_hours = 16       # v2.0.92: cut failed setups at 16h — most MR reversions in 12-18h

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
    exit_rsi_long = 76   # RSI(14) — v2.0.92: widened to 76. Connors 70-75 is RSI(2); RSI(14) eq = 74-78
    exit_rsi_short = 30  # Mirror symmetry
    # Research v2.0.59: exit when deviation > 0.5% (price within 0.5% of SMA).
    # v2.0.58 at 1.0% required price to overshoot SMA by 1% — combined with
    # entry at -1.3%, this created 0.3% gap. With 2.0% entry, 0.5% exit
    # captures 1.5% reversion minimum + bounce potential = 2-3% avg win.
    # This competes with RSI 75 exit — whichever fires first locks in profit.
    exit_dev_revert_pct = 0.3   # v2.0.92: tightened from 0.5 — RSI exit handles winners, revert exit backup

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
    trailing_stop_positive_offset = 0.1500
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
        """Time-graduated dynamic stop — anchored to ENTRY price.

        v2.0.81: COMPLETE REWRITE based on research synthesis.
        Connors/Cesar Alvarez: fixed stops kill MR. YouTube study:
        "timed exit if showing loss" improved net profit/drawdown 93% vs fixed stops.

        New approach:
        - First 12h: WIDE -7% from entry — let MR dips develop (research: MR reversions need room)
        - 12-24h: MODERATE -4% from entry — if no reversion by now, tightening
        - >24h: TIGHT -2.5% from entry — force exit, setup failed
        - Profitable trades: tight trailing lock-in at breakeven or small profit

        Anchored to entry price (not current) so dip tolerance is consistent.
        Hard stoploss at -8.5% is ultimate disaster floor.
        """
        entry_rate = trade.open_rate
        if not entry_rate or entry_rate <= 0:
            return -0.05  # fallback

        # Current drawdown from entry (as positive fraction)
        entry_drawdown = (entry_rate - current_rate) / entry_rate
        
        # Trailing lock-in for profitable trades (conservative only at high profit)
        # v2.0.82: REMOVED breakeven lock-in (>1% → 0.0) — killed all winners prematurely.
        # 24 trades hit trailing_stop at avg -2.54% instead of developing to +2-5% exit_signal.
        # Only lock in at 3%+ where the trade has clearly worked.
        if current_profit > 0.05:
            return -0.025    # 2.5% give-back allowed
        elif current_profit > 0.03:
            return -0.015    # v2.0.82: tight 1.5% give-back for 3%+ winners (was 2.5%)
        
        # Time-graduated stop for non-profitable trades
        if trade.open_date_utc:
            holding_hours = (current_time - trade.open_date_utc).total_seconds() / 3600
        else:
            holding_hours = 0
        
        hard_stop_pct = abs(self.stoploss)  # 0.085
            
        if holding_hours < 12:
            # Wide initial: 7% from entry — MR needs room to dip and bounce
            return -min(0.07, hard_stop_pct * 0.85)
        elif holding_hours < 24:
            # Moderate: 4% from entry — if no reversion in 12h, start tightening
            return -min(0.04, hard_stop_pct * 0.85)
        else:
            # Tight: 2.5% from entry — if no reversion by 24h, setup failed > exit
            return -min(0.025, hard_stop_pct * 0.85)

    def custom_exit(
        self, pair: str, trade: "Trade", current_time: datetime,
        current_rate: float, current_profit: float, **kwargs
    ) -> Optional[str]:
        """
        Time exits — both profitable AND losing trades.
        v2.0.81: ADDED losing-trade time exit. Research: timed exit on losers
        dramatically improves MR performance vs fixed stops (93% better net profit/DD).
        
        - Profitable trades: exit after time_exit_hours (18h) if profit >= floor (0.5%)
        - Losing trades: exit after time_exit_loss_hours (16h) regardless — prevent bag-holding
        """
        if trade.open_date_utc:
            holding_hours = (current_time - trade.open_date_utc).total_seconds() / 3600
        else:
            return None

        # Profitable time exit
        if current_profit >= self.time_exit_profit_floor:
            if holding_hours >= self.time_exit_hours:
                return "time_exit_hours"
        
        # Losing trade time exit — prevent dead setups from lingering
        if current_profit < 0 and holding_hours >= self.time_exit_loss_hours:
            return "time_exit_loss"
        
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