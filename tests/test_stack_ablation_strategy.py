"""Focused contract tests for the causal StackAblation strategy."""

from __future__ import annotations

import inspect

import numpy as np
import pandas as pd
import pytest

from strategies.StackAblation import StackAblation


def candles(n: int = 320, start: str = "2024-01-01") -> pd.DataFrame:
    """Deterministic OHLCV candles with no shared mutable state."""
    idx = pd.date_range(start, periods=n, freq="15min")
    x = np.arange(n, dtype=float)
    close = 100 + 2.5 * np.sin(x / 7) + 0.015 * x
    return pd.DataFrame(
        {
            "date": idx,
            "open": close - 0.15,
            "high": close + 0.55,
            "low": close - 0.55,
            "close": close,
            "volume": 1000 + 100 * (x % 7),
        },
        index=idx,
    )


def prepared_fixture() -> pd.DataFrame:
    """One synthetic row with every optional gate true.

    Gate columns are intentionally explicit: this test isolates strategy
    composition from the pure helper tests and makes one-toggle attrition
    deterministic.
    """
    idx = pd.date_range("2024-01-03 10:00", periods=1, freq="15min")
    return pd.DataFrame(
        {
            "close": [100.0],
            "protected_low": [95.0],
            "sequence_confirmed": [True],
            "htf_bias_ok": [True],
            "discount_ok": [True],
            "ote_ok": [True],
            "fvg_ok": [True],
            "fvg_one_time_ok": [True],
            "session_ok": [True],
            "weekend_ok": [True],
            "momentum_ok": [True],
            "rr_ok": [True],
        },
        index=idx,
    )


class FakeDP:
    def __init__(self, informative: pd.DataFrame):
        self.informative = informative

    def current_whitelist(self):
        return ["BTC/USDT"]

    def get_pair_dataframe(self, pair: str, timeframe: str):
        assert pair == "BTC/USDT"
        assert timeframe == "1h"
        return self.informative.copy()


def test_strategy_metadata_and_spot_long_only():
    strategy = StackAblation({})
    assert strategy.INTERFACE_VERSION == 3
    assert strategy.timeframe == "15m"
    assert strategy.informative_timeframe == "1h"
    assert strategy.can_short is False
    assert strategy.startup_candle_count == 400
    assert strategy.minimal_roi == {"0": 0.03}
    assert strategy.stoploss == -0.03
    assert set(strategy.COMPONENTS) == {
        "htf_bias", "discount", "ote", "fvg", "fvg_one_time", "session",
        "weekend", "momentum", "min_rr",
    }
    assert strategy.components == strategy.COMPONENTS


def test_components_are_instance_local_and_explicitly_overridable():
    first = StackAblation({})
    second = StackAblation({})
    first.set_components({"momentum": True})
    assert first.components["momentum"] is True
    assert second.components["momentum"] is False
    with pytest.raises(KeyError):
        first.set_components({"not_registered": True})
    with pytest.raises(TypeError):
        first.set_components({"momentum": "yes"})


def test_config_can_select_experiment_and_components():
    strategy = StackAblation({
        "stack_experiment_id": "exp-007",
        "stack_components": {"weekend": False},
    })
    assert strategy.experiment_id == "exp-007"
    assert strategy.components["weekend"] is False


def test_setup_values_are_frozen_only_through_confirmation_window():
    strategy = StackAblation({})
    strategy.SEQUENCE_MAX_BARS = 2
    index = pd.RangeIndex(8)
    values = pd.Series([1, 10, 99, 99, 20, 99, 99, 99], index=index)
    sweeps = pd.Series([False, True, False, False, True, False, False, False], index=index)
    carried = strategy._carry_setup_value(values, sweeps)
    assert carried.tolist() == pytest.approx(
        [np.nan, 10, 10, 10, 20, 20, 20, np.nan], nan_ok=True
    )


def test_fake_dp_pipeline_merges_causal_htf_columns():
    strategy = StackAblation({})
    base = candles()
    info = candles(100, "2024-01-01")
    info = info.iloc[::4].copy()
    output = strategy.build_stack_indicators(base, info)
    for column in (
        "pivot_high", "pivot_low", "bos", "choch", "protected_low",
        "sweep_event", "sweep_confirmed", "fvg_bullish",
        "bullish_fvg_unmitigated", "long_discount", "long_ote", "rr",
        "htf_bias_ok", "sequence_confirmed",
    ):
        assert column in output.columns, column
    assert len(output) == len(base)
    assert strategy.informative_pairs() == []
    strategy.dp = FakeDP(info)
    assert strategy.informative_pairs() == [("BTC/USDT", "1h")]
    via_callback = strategy.populate_indicators(base, {"pair": "BTC/USDT"})
    assert len(via_callback) == len(base)
    assert "htf_bias_ok" in via_callback


def test_core_happy_path_and_tag_are_long_only():
    strategy = StackAblation({})
    strategy.set_components({name: False for name in strategy.COMPONENTS})
    df = strategy.populate_entry_trend(prepared_fixture(), {"pair": "BTC/USDT"})
    assert df["enter_long"].tolist() == [1]
    assert df["enter_short"].tolist() == [0]
    assert df.loc[df.index[0], "enter_tag"] == "stack-core|long|stack-causal"


@pytest.mark.parametrize("component", sorted(StackAblation.COMPONENTS))
def test_each_enabled_component_independently_blocks_same_fixture(component):
    strategy = StackAblation({})
    strategy.set_components({name: False for name in strategy.COMPONENTS})
    fixture = prepared_fixture()
    source_column = {
        "min_rr": "rr_ok",
        "fvg_one_time": "fvg_one_time_ok",
    }.get(component, f"{component}_ok")
    fixture.loc[:, source_column] = False
    # The strategy reads the gate source column by component name.  The
    # explicit aliases above document the two source names that are not a
    # literal ``<component>_ok`` spelling.
    output = strategy.populate_entry_trend(fixture, {})
    assert output["enter_long"].iloc[0] == 1

    strategy.set_components({component: True})
    output = strategy.populate_entry_trend(fixture, {})
    assert output["enter_long"].iloc[0] == 0


def test_core_trigger_cannot_be_disabled_and_blocks_without_sequence():
    strategy = StackAblation({})
    strategy.set_components({name: False for name in strategy.COMPONENTS})
    fixture = prepared_fixture()
    fixture.loc[:, "sequence_confirmed"] = False
    output = strategy.populate_entry_trend(fixture, {})
    assert output["enter_long"].iloc[0] == 0
    assert output["enter_short"].eq(0).all()


def test_gate_columns_are_exposed():
    strategy = StackAblation({})
    output = strategy.populate_entry_trend(prepared_fixture(), {})
    for name in ("core", *StackAblation.COMPONENTS):
        assert f"{name}_gate" in output


def test_future_shock_does_not_change_completed_pipeline_prefix():
    strategy = StackAblation({})
    base = candles()
    baseline = strategy.build_stack_indicators(base, candles(100, "2024-01-01"))
    shocked_base = base.copy()
    shocked_info = candles(100, "2024-01-01")
    shocked_base.iloc[260:, shocked_base.columns.get_indexer(["high", "low", "close"])] *= 10
    shocked_info.iloc[70:, shocked_info.columns.get_indexer(["high", "low", "close"])] *= 10
    actual = strategy.build_stack_indicators(shocked_base, shocked_info)
    # Informative merge and all local helpers must be point-in-time: the first
    # 200 rows precede both shocks and therefore cannot differ.
    safe = 200
    for col in ("pivot_high", "pivot_low", "bos", "choch", "protected_low", "sweep_event", "sequence_confirmed"):
        pd.testing.assert_series_equal(
            baseline[col].iloc[:safe].reset_index(drop=True),
            actual[col].iloc[:safe].reset_index(drop=True),
            check_names=False,
        )


def test_pipeline_rr_never_accepts_stop_or_target_on_wrong_side():
    strategy = StackAblation({})
    output = strategy.build_stack_indicators(candles())
    accepted = output["rr_ok"]
    assert (
        (output.loc[accepted, "entry_stop"] < output.loc[accepted, "close"])
        & (output.loc[accepted, "close"] < output.loc[accepted, "entry_target"])
    ).all()


def test_pipeline_marks_inverted_external_range_undefined_instead_of_crashing(monkeypatch):
    strategy = StackAblation({})
    original = __import__("strategies.StackAblation", fromlist=["market_structure"])

    def inverted_structure(frame, **kwargs):
        index = frame.index
        return pd.DataFrame(
            {
                "external_high": 90.0,
                "external_low": 100.0,
                "protected_high": np.nan,
                "protected_low": np.nan,
                "bos": 0,
                "choch": 0,
                "bias_state": np.nan,
            },
            index=index,
        )

    monkeypatch.setattr(original, "market_structure", inverted_structure)
    output = strategy.build_stack_indicators(candles(40))
    assert output["long_retracement"].isna().all()
    assert not output["discount_ok"].any()
    assert not output["ote_ok"].any()


def test_fvg_presence_and_one_time_validity_are_distinct_sources():
    source = inspect.getsource(StackAblation.build_stack_indicators)
    assert 'base["fvg_bullish"].rolling' in source
    assert 'base["bullish_fvg_unmitigated"]' in source
    assert 'base["fvg_ok"] = base["bullish_fvg_unmitigated"]' not in source


def test_no_smartmoneyconcepts_dependency_or_short_signal_code():
    module_source = inspect.getsource(inspect.getmodule(StackAblation))
    source = inspect.getsource(StackAblation)
    assert "smartmoneyconcepts" not in source
    assert "smc." not in source
    assert "except ImportError" not in module_source
    strategy = StackAblation({})
    output = strategy.populate_entry_trend(prepared_fixture(), {})
    assert output["enter_short"].eq(0).all()
    exits = strategy.populate_exit_trend(
        prepared_fixture().assign(protected_low=[101.0]), {},
    )
    assert exits["exit_short"].eq(0).all()
