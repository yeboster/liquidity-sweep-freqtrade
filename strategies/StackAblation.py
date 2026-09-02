"""Causal, configurable STACK component-ablation strategy.

This strategy is deliberately separate from ``LiquiditySweep``.  It uses the
pure causal primitives in :mod:`stack_components`, has no SMC dependency, and
only emits spot long entries.  ``COMPONENTS`` is a registry of pre-registered
experiments rather than a Hyperopt surface; callers can override a copy on an
instance with :meth:`set_components`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from pandas import DataFrame

from freqtrade.strategy import IStrategy, merge_informative_pair

try:
    from strategies.stack_components import (
        confirmed_pivots,
        fair_value_gap,
        fvg_lifecycle,
        liquidity_sweep,
        location,
        market_structure,
        structural_rr,
        sweep_to_structure,
    )
except ModuleNotFoundError:  # Freqtrade loads files from strategy_path directly.
    from stack_components import (
        confirmed_pivots,
        fair_value_gap,
        fvg_lifecycle,
        liquidity_sweep,
        location,
        market_structure,
        structural_rr,
        sweep_to_structure,
    )


class StackAblation(IStrategy):
    """15m causal STACK ablation, spot long-only.

    The core trigger is always a sell-side liquidity sweep (wick below a
    previously confirmed low and close back above it) followed by bullish
    BOS/CHoCH within ``SEQUENCE_MAX_BARS`` subsequent candles. Optional gates
    are independently observable in the dataframe and can be switched off
    without changing the core trigger.

    ``protected_low`` and the current confirmed external high are used as the
    long structural leg.  This is an explicit first-version assumption: the
    levels are the latest causal states at entry and are frozen by the
    resulting signal/entry candle, not reconstructed with rolling extrema.
    """

    INTERFACE_VERSION = 3
    STRATEGY_VERSION = "stack-ablation-1.0"
    timeframe = "15m"
    informative_timeframe = "1h"
    can_short = False
    startup_candle_count = 400

    # Fixed conservative exits during entry/filter ablation.
    minimal_roi = {"0": 0.03}
    stoploss = -0.03
    trailing_stop = False

    PIVOT_LEFT = 3
    PIVOT_RIGHT = 3
    SEQUENCE_MAX_BARS = 5
    OTE_LOWER = 0.62
    OTE_UPPER = 0.79
    MIN_RR = 1.5
    RSI_PERIOD = 14
    VOLUME_WINDOW = 20
    FVG_RECENCY_BARS = 30

    COMPONENTS = {
        "htf_bias": True,
        "discount": True,
        "ote": True,
        "fvg": False,
        "fvg_one_time": False,
        "session": False,
        "weekend": True,
        "momentum": False,
        "min_rr": True,
    }

    def __init__(self, config: dict | None = None) -> None:
        super().__init__(config or {})
        # Never mutate the class registry: independent runner instances must
        # not leak a toggle into one another.
        self.components = dict(self.COMPONENTS)
        self.experiment_id = "stack-core"
        cfg = config or {}
        # Explicit config hooks for runners; no arbitrary environment lookup.
        configured = cfg.get("stack_components")
        if configured is None and isinstance(cfg.get("strategy_config"), dict):
            configured = cfg["strategy_config"].get("components")
        if isinstance(configured, dict):
            self.set_components(configured)
        configured_id = cfg.get("stack_experiment_id")
        if configured_id is not None:
            self.experiment_id = str(configured_id)

    def set_components(self, overrides: dict[str, bool] | None = None, **kwargs: bool) -> None:
        """Apply explicit deterministic component overrides to this instance."""
        updates = dict(overrides or {})
        updates.update(kwargs)
        unknown = set(updates) - set(self.COMPONENTS)
        if unknown:
            raise KeyError(f"Unknown STACK component(s): {sorted(unknown)}")
        for name, enabled in updates.items():
            if not isinstance(enabled, (bool, np.bool_)):
                raise TypeError(f"STACK component {name!r} must be bool, got {type(enabled).__name__}")
            self.components[name] = bool(enabled)

    def informative_pairs(self):
        dp = getattr(self, "dp", None)
        if dp is None:
            return []
        pairs = dp.current_whitelist()
        return [(pair, self.informative_timeframe) for pair in pairs]

    @staticmethod
    def _with_date(frame: DataFrame) -> DataFrame:
        out = frame.copy()
        if "date" not in out.columns:
            if isinstance(out.index, pd.DatetimeIndex):
                out["date"] = out.index
            else:
                out["date"] = pd.to_datetime(out.index)
        return out

    @staticmethod
    def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.diff()
        gain = delta.clip(lower=0.0)
        loss = -delta.clip(upper=0.0)
        avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        return (100 - (100 / (1 + rs))).where(avg_loss != 0, 100.0)

    def _add_htf_indicators(self, informative: DataFrame) -> DataFrame:
        info = informative.copy()
        pivots = confirmed_pivots(info, left=self.PIVOT_LEFT, right=self.PIVOT_RIGHT)
        structure = market_structure(
            pd.concat([info, pivots], axis=1),
            pivot_high=pivots["pivot_high"],
            pivot_low=pivots["pivot_low"],
            left=self.PIVOT_LEFT,
            right=self.PIVOT_RIGHT,
        )
        return pd.concat([info, pivots, structure], axis=1)

    def _carry_setup_value(self, value: pd.Series, sweep_event: pd.Series) -> pd.Series:
        """Freeze a setup-row value through its confirmation window.

        The sweep candle is row zero of the setup. A confirmation may occur
        on one of the following ``SEQUENCE_MAX_BARS`` candles, so setup
        context is visible on the sweep row plus exactly that many rows.
        A newer sweep replaces the unresolved setup, matching
        :func:`sweep_to_structure`.
        """
        masked = value.where(sweep_event)
        if pd.api.types.is_bool_dtype(value.dtype):
            # Nullable boolean keeps the temporary missing state typed and
            # avoids pandas' deprecated object->bool silent downcast.
            masked = masked.astype("boolean")
        return masked.ffill(limit=self.SEQUENCE_MAX_BARS)

    def build_stack_indicators(self, dataframe: DataFrame, informative: DataFrame | None = None) -> DataFrame:
        """Build the complete causal indicator/gate-input pipeline.

        ``informative`` is injectable to make chronology and future-shock tests
        independent of a live DataProvider. In production it is read in
        :meth:`populate_indicators` and merged with Freqtrade's causal helper.
        """
        dataframe = dataframe.copy()
        for required in ("open", "high", "low", "close", "volume"):
            if required not in dataframe.columns:
                raise KeyError(f"StackAblation: missing required column {required!r}")
        base_pivots = confirmed_pivots(dataframe, left=self.PIVOT_LEFT, right=self.PIVOT_RIGHT)
        base = pd.concat([dataframe, base_pivots], axis=1)
        structure = market_structure(
            base,
            pivot_high=base_pivots["pivot_high"],
            pivot_low=base_pivots["pivot_low"],
            left=self.PIVOT_LEFT,
            right=self.PIVOT_RIGHT,
        )
        base = pd.concat([base, structure], axis=1)

        # Sell-side sweep only is used by the long core. The helper shifts a
        # supplied state series one row, so a just-confirmed pivot cannot be
        # swept on its own confirmation candle.
        sweep = liquidity_sweep(base, base["external_low"], "low")
        base["sweep_event"] = sweep["sweep_event"]
        base["sweep_level"] = sweep["sweep_level"]
        high_sweep = liquidity_sweep(base, base["external_high"], "high")
        sequence = sweep_to_structure(
            high_sweep["sweep_event"], base["sweep_event"], base["bos"], base["choch"], self.SEQUENCE_MAX_BARS
        )
        base = pd.concat([base, sequence], axis=1)
        base["sequence_confirmed"] = base["sweep_confirmed"].eq(1)

        fvg = fair_value_gap(base)
        lifecycle = fvg_lifecycle(base, fvg)
        base = pd.concat([base, fvg, lifecycle], axis=1)

        # Before a reversal BOS, the known external range is the only causal
        # displacement range available. Location is sampled on the sweep row
        # and frozen through the bounded confirmation window below.
        leg_low = base["external_low"].where(
            base["external_low"] < base["external_high"]
        )
        leg_high = base["external_high"].where(
            base["external_low"] < base["external_high"]
        )
        loc = location(
            base,
            leg_low,
            leg_high,
            "long",
            ote_lower=self.OTE_LOWER,
            ote_upper=self.OTE_UPPER,
        )
        base = pd.concat([base, loc.add_prefix("long_")], axis=1)

        # Optional diagnostics: all use present/past values only.
        base["rsi"] = self._rsi(base["close"], self.RSI_PERIOD)
        base["volume_mean"] = base["volume"].rolling(self.VOLUME_WINDOW, min_periods=self.VOLUME_WINDOW).mean()
        base["volume_ok"] = base["volume"] > base["volume_mean"]
        dates = self._with_date(base)["date"]
        base["session_ok"] = dates.dt.hour.between(8, 16, inclusive="left")
        base["weekend_ok"] = ~dates.dt.dayofweek.isin([5, 6])

        # HTF data is merged before gates are evaluated. The fallback keeps the
        # column explicit and false when no informative frame is available.
        if informative is not None and len(informative):
            info = self._with_date(informative)
            info = self._add_htf_indicators(info)
            merged = merge_informative_pair(
                self._with_date(base), info, self.timeframe, self.informative_timeframe, ffill=True
            )
            # Preserve the exact base index and avoid duplicate date columns.
            base = merged
        htf_col = f"bias_state_{self.informative_timeframe}"
        if htf_col in base:
            base["htf_bias_raw"] = base[htf_col].eq(1)
        else:
            base["htf_bias_raw"] = False

        # Snapshot every entry-quality condition on the setup (sweep) row.
        # Evaluating them on the later BOS candle would answer a different
        # question and makes OTE almost impossible after price breaks higher.
        sweep_event = base["sweep_event"].astype(bool)
        base["htf_bias_ok"] = self._carry_setup_value(base["htf_bias_raw"], sweep_event).fillna(False)
        base["discount_ok"] = self._carry_setup_value(base["long_discount"], sweep_event).fillna(False)
        base["ote_ok"] = self._carry_setup_value(base["long_ote"], sweep_event).fillna(False)

        # FVG presence and one-time validity are deliberately distinct:
        # `fvg` asks whether a bullish imbalance formed recently; the
        # one-time gate additionally requires the latest tracked gap to remain
        # unconsumed at setup time.
        recent_fvg = (
            base["fvg_bullish"].rolling(self.FVG_RECENCY_BARS, min_periods=1).max().astype(bool)
        )
        base["fvg_ok"] = self._carry_setup_value(recent_fvg, sweep_event).fillna(False)
        base["fvg_one_time_ok"] = self._carry_setup_value(
            base["bullish_fvg_unmitigated"], sweep_event
        ).fillna(False)
        base["session_ok"] = self._carry_setup_value(base["session_ok"], sweep_event).fillna(False)
        base["weekend_ok"] = self._carry_setup_value(base["weekend_ok"], sweep_event).fillna(False)
        momentum_raw = (base["rsi"] > 50) & base["volume_ok"]
        base["momentum_ok"] = self._carry_setup_value(momentum_raw, sweep_event).fillna(False)

        # Freeze setup invalidation and target. Entry price is the eventual
        # confirmation close, therefore R/R is recomputed on every pending row
        # against the frozen setup levels. Directional ordering is mandatory;
        # absolute-value R/R alone would accept targets behind the entry.
        base["entry_stop"] = self._carry_setup_value(base["low"], sweep_event)
        base["entry_target"] = self._carry_setup_value(base["external_high"], sweep_event)
        base["rr"] = structural_rr(base["close"], base["entry_stop"], base["entry_target"])
        ordered = (base["entry_stop"] < base["close"]) & (base["close"] < base["entry_target"])
        base.loc[~ordered, "rr"] = np.nan
        base["rr_ok"] = (base["rr"] >= self.MIN_RR).fillna(False)

        return base

    # Alias useful to research runners/tests without coupling them to the
    # Freqtrade callback name.
    compute_indicators = build_stack_indicators

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        informative = None
        dp = getattr(self, "dp", None)
        if dp is not None:
            informative = dp.get_pair_dataframe(
                pair=metadata["pair"], timeframe=self.informative_timeframe
            )
        return self.build_stack_indicators(dataframe, informative)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Expose atomic gates and write only the conjunction to ``enter_long``."""
        df = dataframe
        # This permits focused tests/runners to provide a prepared frame while
        # still failing clearly if a required pipeline output is absent.
        required = [
            "sequence_confirmed", "htf_bias_ok", "discount_ok", "ote_ok", "fvg_ok",
            "fvg_one_time_ok", "session_ok", "weekend_ok", "momentum_ok", "rr_ok",
        ]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise KeyError(f"StackAblation: populate_entry_trend requires prepared columns {missing}")

        gates = {
            "core": df["sequence_confirmed"].astype(bool),
            "htf_bias": df["htf_bias_ok"].astype(bool) if self.components["htf_bias"] else pd.Series(True, index=df.index),
            "discount": df["discount_ok"].astype(bool) if self.components["discount"] else pd.Series(True, index=df.index),
            "ote": df["ote_ok"].astype(bool) if self.components["ote"] else pd.Series(True, index=df.index),
            "fvg": df["fvg_ok"].astype(bool) if self.components["fvg"] else pd.Series(True, index=df.index),
            "fvg_one_time": df["fvg_one_time_ok"].astype(bool) if self.components["fvg_one_time"] else pd.Series(True, index=df.index),
            "session": df["session_ok"].astype(bool) if self.components["session"] else pd.Series(True, index=df.index),
            "weekend": df["weekend_ok"].astype(bool) if self.components["weekend"] else pd.Series(True, index=df.index),
            "momentum": df["momentum_ok"].astype(bool) if self.components["momentum"] else pd.Series(True, index=df.index),
            "min_rr": df["rr_ok"].astype(bool) if self.components["min_rr"] else pd.Series(True, index=df.index),
        }
        for name, value in gates.items():
            df[f"{name}_gate"] = value
        signal = pd.Series(True, index=df.index)
        for value in gates.values():
            signal &= value.fillna(False)
        df["enter_long"] = signal.astype(int)
        df["enter_tag"] = np.where(
            signal,
            f"{self.experiment_id}|long|stack-causal",
            "",
        )
        # Explicitly prevent stale/accidental short columns from being used.
        df["enter_short"] = 0
        return df

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Structural invalidation only; ROI and static stoploss remain active."""
        df = dataframe
        protected = df.get("protected_low", pd.Series(np.nan, index=df.index))
        df["exit_long"] = ((df["close"] < protected) & protected.notna()).astype(int)
        df["exit_tag"] = np.where(df["exit_long"].eq(1), "structural-invalidation", "")
        df["exit_short"] = 0
        return df
