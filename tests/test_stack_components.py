"""Tests for causal STACK component primitives.

Task 2 covers `confirmed_pivots`, a pure helper that emits a swing level
**only** at the candle that confirms it (after `right` additional bars have
closed). It must never backfill the pivot onto the pivot candle or onto
later candles, must handle ties / NaNs / flat sequences deterministically,
and must be forward-only (no future shocks change past values).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from strategies.stack_components import confirmed_pivots, MAX_PIVOT_WINDOW


# ---- Fixtures ---------------------------------------------------------------

@pytest.fixture
def frame() -> pd.DataFrame:
    """Small deterministic OHLCV frame with one clear peak and one clear trough.

    Layout (index, high, low):
        0: 10, 9
        1: 11, 10
        2: 12, 11
        3: 13, 12   <- global peak (high == 13)
        4: 12, 11
        5: 11, 10
        6: 10, 9
        7:  9, 8    <- global trough (low == 8)
        8: 10, 9
        9: 11, 10
    """
    highs = [10, 11, 12, 13, 12, 11, 10, 9, 10, 11]
    lows = [9, 10, 11, 12, 11, 10, 9, 8, 9, 10]
    closes = [h - 1 for h in highs]
    opens = [c for c in closes]
    volumes = [1.0] * len(highs)
    idx = pd.date_range("2024-01-01", periods=len(highs), freq="15min")
    return pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes},
        index=idx,
    )


# ---- Pivot emission / confirmation timing ----------------------------------

class TestConfirmedPivotsEmitAtConfirmation:
    def test_pivot_high_unavailable_on_pivot_candle(self, frame):
        out = confirmed_pivots(frame, left=2, right=2)
        # Index 3 is the peak. Window is [1..5]. Row 3 is the centre. The pivot
        # is only confirmed once row 5 closes (right bars available).
        assert pd.isna(out.loc[frame.index[3], "pivot_high"])

    def test_pivot_high_emitted_only_at_confirmation(self, frame):
        out = confirmed_pivots(frame, left=2, right=2)
        # Index 5 is the row that confirms index 3.
        assert out.loc[frame.index[5], "pivot_high"] == frame.loc[frame.index[3], "high"]

    def test_pivot_high_not_present_before_confirmation(self, frame):
        out = confirmed_pivots(frame, left=2, right=2)
        # Row 4 has only one bar after the peak; the peak isn't confirmed yet.
        assert pd.isna(out.loc[frame.index[4], "pivot_high"])

    def test_pivot_low_confirmed_at_right_bars(self, frame):
        out = confirmed_pivots(frame, left=2, right=2)
        # Index 7 is the trough. Window [5..9]. Confirmed on index 9.
        assert pd.isna(out.loc[frame.index[7], "pivot_low"])
        assert pd.isna(out.loc[frame.index[8], "pivot_low"])
        assert out.loc[frame.index[9], "pivot_low"] == frame.loc[frame.index[7], "low"]


# ---- Future-shock safety ---------------------------------------------------

def _make_long_frame(n: int = 200, seed: int = 0) -> pd.DataFrame:
    """Deterministic OHLCV frame of length ``n`` with enough history
    for a ``left=3, right=3`` window (need >= 7 rows; we use 200).

    Built from a fixed-seed RNG so the fixture is reproducible across
    runs and CI. ``high`` strictly dominates ``low`` row-by-row so the
    shape itself is sane (no negative spreads).

    The base price is constructed from a random walk superimposed on a
    slow sine-like drift, which produces many strict-unique extremes
    inside 7-row windows — that's exactly the property the future-shock
    test needs to be non-vacuous (without dense pivots, NaN == NaN would
    satisfy every equality check trivially).
    """
    rng = np.random.default_rng(seed)
    drift = np.sin(np.linspace(0, 8 * np.pi, n)) * 5.0
    walk = rng.normal(loc=0.0, scale=0.5, size=n).cumsum()
    base = 1000.0 + drift + walk
    spread = rng.uniform(0.5, 1.5, size=n)
    highs = base + spread
    lows = base - spread
    opens = base + rng.normal(scale=0.2, size=n)
    closes = base + rng.normal(scale=0.2, size=n)
    volumes = rng.uniform(0.5, 5.0, size=n)
    idx = pd.date_range("2024-01-01", periods=n, freq="15min")
    return pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
        },
        index=idx,
    )


class TestNoFutureLeakage:
    def test_future_shock_does_not_change_past_pivots(self):
        # Use a frame long enough that mutating the tail (iloc[80:]) actually
        # changes data. The original fixture was 10 rows, so iloc[80:] was an
        # empty slice and the assertion was vacuously true.
        n = 200
        left, right = 3, 3
        baseline_frame = _make_long_frame(n=n, seed=0)
        baseline = confirmed_pivots(baseline_frame, left=left, right=right)

        # Cutoff is the last row whose pivot can ever depend on a future bar.
        # With (left, right), row i's pivot depends on rows [i-left, i+right].
        # A shock at index j affects any pivot at i where i+right >= j, i.e.
        # i >= j - right. Conversely, row i is safe iff i < j - right, i.e.
        # the cutoff is exclusive: rows strictly less than j - right.
        shock_start = 80
        cutoff = shock_start - right  # exclusive: rows < cutoff cannot change

        # Sanity: at least one row strictly before the cutoff must carry a
        # finite pivot in the baseline. Without this guard, the equality
        # check below would be vacuous (NaN == NaN everywhere).
        assert baseline.iloc[:cutoff]["pivot_high"].notna().any() or \
               baseline.iloc[:cutoff]["pivot_low"].notna().any(), (
            "test setup: no finite pivot exists before cutoff; "
            "the future-shock equality check would be vacuous"
            )

        shocked = baseline_frame.copy()
        high_idx = shocked.columns.get_loc("high")
        low_idx = shocked.columns.get_loc("low")
        shocked.iloc[shock_start:, [high_idx, low_idx]] *= 10.0

        # Real mutation guard: the shocked frame must ACTUALLY differ from
        # the baseline frame in the mutated region (and ONLY there). If the
        # slice were empty, the test would silently pass; if the shock
        # somehow didn't change the values, the equality check would be
        # vacuous. Both guards are checked explicitly.
        shocked_tail = shocked.iloc[shock_start:].reset_index(drop=True)
        baseline_tail = baseline_frame.iloc[shock_start:].reset_index(drop=True)
        assert not shocked_tail.equals(baseline_tail), (
            "shock did not actually modify the frame; "
            "the future-shock test would be vacuous"
        )
        # Real mutation guard, the dual half: the rows we are about to
        # compare must be byte-identical in the prefix that the test
        # treats as "past". Without this, a typo in ``shock_start`` would
        # silently leak data into the "past" region.
        pd.testing.assert_frame_equal(
            shocked.iloc[:cutoff].reset_index(drop=True),
            baseline_frame.iloc[:cutoff].reset_index(drop=True),
        )

        actual = confirmed_pivots(shocked, left=left, right=right)

        # Compare the FULL safe prefix [:shock_start] (not the tighter
        # [:cutoff]) per the spec. Rows in [cutoff, shock_start) cannot
        # depend on any shocked bar either — the shock at index j can
        # only affect pivots whose window reaches j, i.e. pivots at
        # row i with i+right >= j (so i >= j - right = cutoff). A pivot
        # at row i in [cutoff, shock_start) has i+right < shock_start+right
        # and thus never reaches the shock, so the equality must hold
        # for the whole [:shock_start] prefix. Comparing only [:cutoff]
        # would under-test the boundary by leaving a right-wide band
        # where leakage could hide.
        before_baseline = baseline.iloc[:shock_start].reset_index(drop=True)
        before_actual = actual.iloc[:shock_start].reset_index(drop=True)
        # Element-by-element (NaN-aware) so we catch every kind of
        # transition: NaN -> value, value -> NaN, value -> different value.
        for col in before_baseline.columns:
            b = before_baseline[col].to_numpy()
            a = before_actual[col].to_numpy()
            both_nan = np.isnan(b) & np.isnan(a)
            equal = (b == a) | both_nan
            assert equal.all(), (
                f"future shock changed past pivot in column {col!r} within "
                f"the safe prefix [:shock_start] (shock_start={shock_start}); "
                f"row(s) where baseline != actual: "
                f"{np.where(~equal)[0].tolist()[:10]}"
            )

    def test_prepending_data_does_not_shift_prior_outputs(self, frame):
        # Adding more history before the frame must not change confirmed pivots
        # in the original region (only future bars matter for confirmation).
        base = confirmed_pivots(frame, left=2, right=2)
        extra = pd.DataFrame(
            {
                "open": [9.0] * 5,
                "high": [10.0] * 5,
                "low": [9.0] * 5,
                "close": [9.5] * 5,
                "volume": [1.0] * 5,
            },
            index=pd.date_range("2023-12-31", periods=5, freq="15min"),
        )
        longer = pd.concat([extra, frame])
        shifted = confirmed_pivots(longer, left=2, right=2).iloc[5:].reset_index(drop=True)
        baseline = base.reset_index(drop=True)
        pd.testing.assert_frame_equal(shifted, baseline)


# ---- Edge cases: ties, NaNs, flat, monotonic -------------------------------

class TestEdgeCases:
    def test_flat_series_emits_no_pivots(self):
        idx = pd.date_range("2024-01-01", periods=20, freq="15min")
        flat = pd.DataFrame(
            {
                "open": [100.0] * 20,
                "high": [100.0] * 20,
                "low": [100.0] * 20,
                "close": [100.0] * 20,
                "volume": [1.0] * 20,
            },
            index=idx,
        )
        out = confirmed_pivots(flat, left=2, right=2)
        assert out["pivot_high"].isna().all()
        assert out["pivot_low"].isna().all()

    def test_strictly_monotonic_increasing_emits_no_high_pivots(self):
        idx = pd.date_range("2024-01-01", periods=20, freq="15min")
        highs = [float(i) for i in range(20)]
        lows = [h - 1 for h in highs]
        df = pd.DataFrame(
            {
                "open": [h - 0.5 for h in highs],
                "high": highs,
                "low": lows,
                "close": [h - 0.5 for h in highs],
                "volume": [1.0] * 20,
            },
            index=idx,
        )
        out = confirmed_pivots(df, left=2, right=2)
        # No pivot_high because there's no local maximum surrounded by smaller
        # values within the window.
        assert out["pivot_high"].isna().all()

    def test_strictly_monotonic_decreasing_emits_no_low_pivots(self):
        idx = pd.date_range("2024-01-01", periods=20, freq="15min")
        highs = [20 - float(i) for i in range(20)]
        lows = [h - 1 for h in highs]
        df = pd.DataFrame(
            {
                "open": [h - 0.5 for h in highs],
                "high": highs,
                "low": lows,
                "close": [h - 0.5 for h in highs],
                "volume": [1.0] * 20,
            },
            index=idx,
        )
        out = confirmed_pivots(df, left=2, right=2)
        assert out["pivot_low"].isna().all()

    def test_tied_highs_emit_no_pivot(self):
        # Two equal highs at positions 3 and 4 with a (left=2, right=2)
        # window: both fall inside each other's confirmation window, so the
        # strict-tie-break rule means NO pivot is emitted. This matches the
        # module docstring: "Tied centres produce no pivot, which is
        # deterministic and avoids ambiguous 'first vs last tied bar' choices."
        idx = pd.date_range("2024-01-01", periods=10, freq="15min")
        highs = [10, 11, 12, 13, 13, 12, 11, 10, 9, 9]  # tie at 3 and 4
        lows = [h - 1 for h in highs]
        df = pd.DataFrame(
            {
                "open": [h - 0.5 for h in highs],
                "high": highs,
                "low": lows,
                "close": [h - 0.5 for h in highs],
                "volume": [1.0] * 10,
            },
            index=idx,
        )
        # Determinism: two runs must produce identical output.
        out_a = confirmed_pivots(df, left=2, right=2)
        out_b = confirmed_pivots(df, left=2, right=2)
        pd.testing.assert_frame_equal(out_a, out_b)
        # Tied centres produce no pivot at all (per docs).
        assert bool(out_a["pivot_high"].isna().all()), (
            f"tied highs at index 3 and 4 must emit no pivot_high, "
            f"got: {out_a['pivot_high'].dropna().to_list()}"
        )
        # The low series is unaffected by the tie in `high`.
        assert bool(out_a["pivot_low"].isna().all())

    def test_documented_tie_emits_no_pivot_around_left_right_window(self):
        # Stricter tie variant: the tie is exactly at the centre and the
        # neighbour rows on the right of one centre are the other centre.
        # Window [left=1, right=1] -> 3-bar: (i-1, i, i+1). Place equal
        # values at i and i+1 so the centre's own window contains another
        # equal value, which disqualifies both.
        idx = pd.date_range("2024-01-01", periods=7, freq="15min")
        highs = [10.0, 11.0, 12.0, 13.0, 13.0, 12.0, 11.0]  # tie at 3 and 4
        lows = [h - 1 for h in highs]
        df = pd.DataFrame(
            {
                "open": [h - 0.5 for h in highs],
                "high": highs,
                "low": lows,
                "close": [h - 0.5 for h in highs],
                "volume": [1.0] * 7,
            },
            index=idx,
        )
        out = confirmed_pivots(df, left=1, right=1)
        # With left=1, right=1, candidate at row 3 has window [2..4]; row 3
        # equals row 4 (both 13), so row 3 is not strictly greater than every
        # other bar in the window => no pivot.
        assert bool(out["pivot_high"].isna().all())

    def test_nans_in_high_low_yield_no_false_pivots(self):
        # The implementation uses np.max / np.min over a sliding window,
        # which means any NaN in the window propagates through the extreme
        # calculation. The contract is: a window that contains ANY NaN
        # cannot produce a pivot (no false pivot around incomplete data).
        idx = pd.date_range("2024-01-01", periods=15, freq="15min")
        highs = [10.0, 11.0, np.nan, 13.0, 12.0, 11.0, 10.0, 9.0,
                 10.0, 11.0, 12.0, 13.0, 12.0, 11.0, 10.0]
        lows = [9.0, 10.0, 11.0, 12.0, np.nan, 10.0, 9.0, 8.0,
                9.0, 10.0, 11.0, 12.0, 11.0, 10.0, 9.0]
        df = pd.DataFrame(
            {
                "open": [9.5] * 15,
                "high": highs,
                "low": lows,
                "close": [9.5] * 15,
                "volume": [1.0] * 15,
            },
            index=idx,
        )
        out = confirmed_pivots(df, left=2, right=2)

        # 1. Must not raise and must produce a well-formed result.
        assert isinstance(out, pd.DataFrame)
        assert set(out.columns) >= {"pivot_high", "pivot_low"}

        # 2. No pivot_high anywhere whose confirmation window contains the
        # NaN at index 2. With (left=2, right=2), a pivot at confirmation
        # row c depends on candidates in [c-4, c-2] (inclusive), so a
        # candidate at row 3 has window [1..5] which contains the NaN at
        # row 2. Equivalently, a pivot at row i (after shift) is suspect
        # if there exists a candidate in its window with NaN; but the
        # stricter, sufficient check is: a pivot at row i cannot be the
        # result of a candidate whose window includes row 2. A pivot at
        # confirmation row r corresponds to candidate row r - right;
        # candidate's window includes row 2 iff r - 2 <= 2 <= r - 2 + 4,
        # i.e. 0 <= r <= 6. So rows 0..6 (i.e. candidate rows <= 4) cannot
        # have a finite pivot_high.
        suspect_high_rows = list(idx[0:7])  # rows 0..6
        assert bool(out.loc[suspect_high_rows, "pivot_high"].isna().all()), (
            f"pivot_high emitted in NaN-contaminated window; "
            f"got: {out.loc[suspect_high_rows, 'pivot_high'].dropna().to_dict()}"
        )

        # 3. Same check for low: NaN at index 4 (low). Candidate's window
        # includes row 4 iff r - right <= 4 <= r - right + window - 1, i.e.
        # the candidate row c has 2 <= c <= 6. With right=2, confirmation
        # row r = c + 2, so r in 4..8.
        suspect_low_rows = list(idx[4:9])
        assert bool(out.loc[suspect_low_rows, "pivot_low"].isna().all()), (
            f"pivot_low emitted in NaN-contaminated window; "
            f"got: {out.loc[suspect_low_rows, 'pivot_low'].dropna().to_dict()}"
        )

    def test_nan_at_centre_row_is_not_a_pivot(self):
        # Centre bar itself is NaN: the strict-tie-break rule must not
        # confuse this with a "tied" extreme, and the centre-vs-extreme
        # comparison must fail.
        idx = pd.date_range("2024-01-01", periods=7, freq="15min")
        highs = [10.0, 11.0, 12.0, np.nan, 12.0, 11.0, 10.0]
        lows = [9.0, 10.0, 11.0, np.nan, 11.0, 10.0, 9.0]
        df = pd.DataFrame(
            {
                "open": [9.5] * 7,
                "high": highs,
                "low": lows,
                "close": [9.5] * 7,
                "volume": [1.0] * 7,
            },
            index=idx,
        )
        out = confirmed_pivots(df, left=1, right=1)
        # No finite pivot value can ever come from a NaN centre.
        assert bool(out["pivot_high"].isna().all())
        assert bool(out["pivot_low"].isna().all())

    def test_all_nan_series_emits_no_pivots(self):
        # Degenerate input: every value is NaN. Must not raise, must emit
        # only NaNs.
        idx = pd.date_range("2024-01-01", periods=10, freq="15min")
        df = pd.DataFrame(
            {
                "open": [np.nan] * 10,
                "high": [np.nan] * 10,
                "low": [np.nan] * 10,
                "close": [np.nan] * 10,
                "volume": [1.0] * 10,
            },
            index=idx,
        )
        out = confirmed_pivots(df, left=2, right=2)
        assert isinstance(out, pd.DataFrame)
        assert bool(out["pivot_high"].isna().all())
        assert bool(out["pivot_low"].isna().all())

    def test_insufficient_history_yields_no_pivots_at_head(self):
        idx = pd.date_range("2024-01-01", periods=5, freq="15min")
        df = pd.DataFrame(
            {
                "open": [1.0] * 5,
                "high": [2.0] * 5,
                "low": [0.5] * 5,
                "close": [1.5] * 5,
                "volume": [1.0] * 5,
            },
            index=idx,
        )
        out = confirmed_pivots(df, left=3, right=3)
        # Need 3 left + 1 + 3 right = 7 rows minimum; we only have 5.
        assert out["pivot_high"].isna().all()
        assert out["pivot_low"].isna().all()


# ---- API / dtype sanity -----------------------------------------------------

class TestApi:
    def test_returns_dataframe_with_expected_columns(self, frame):
        out = confirmed_pivots(frame, left=2, right=2)
        assert isinstance(out, pd.DataFrame)
        assert "pivot_high" in out.columns
        assert "pivot_low" in out.columns

    def test_output_index_matches_input(self, frame):
        out = confirmed_pivots(frame, left=2, right=2)
        assert list(out.index) == list(frame.index)

    def test_left_right_validation(self, frame):
        with pytest.raises(ValueError):
            confirmed_pivots(frame, left=0, right=2)
        with pytest.raises(ValueError):
            confirmed_pivots(frame, left=2, right=0)

    def test_required_columns_present(self, frame):
        for col in ("high", "low"):
            assert col in frame.columns
        # Confirm missing-column behaviour.
        bad = frame.drop(columns=["high"])
        with pytest.raises(KeyError):
            confirmed_pivots(bad, left=2, right=2)

    def test_non_negative_left_right(self, frame):
        # left/right of zero should be rejected.
        with pytest.raises(ValueError):
            confirmed_pivots(frame, left=-1, right=2)
        with pytest.raises(ValueError):
            confirmed_pivots(frame, left=2, right=-1)

    def test_window_upper_bound_enforced(self, frame):
        # The implementation caps ``left + 1 + right`` at
        # ``MAX_PIVOT_WINDOW`` (401) to keep the as_strided matrix
        # bounded. Without the cap, ``left=200, right=200`` would build
        # an n * 401 matrix on every call and torch the process on
        # production-sized data. The error must be a ``ValueError``,
        # not ``TypeError`` (the inputs are well-typed) and not a
        # silent success. Note: ``left=200, right=200`` is the
        # boundary (left + 1 + right = 401), which by design does
        # NOT raise — that's covered by ``test_window_at_boundary_is_allowed``.
        with pytest.raises(ValueError, match=r"practical cap of 401"):
            confirmed_pivots(frame, left=MAX_PIVOT_WINDOW, right=1)
        with pytest.raises(ValueError, match=r"practical cap of 401"):
            confirmed_pivots(frame, left=1, right=MAX_PIVOT_WINDOW)
        with pytest.raises(ValueError, match=r"practical cap of 401"):
            confirmed_pivots(frame, left=200, right=201)

    def test_window_at_boundary_is_allowed(self, frame):
        # The boundary ``left + 1 + right == MAX_PIVOT_WINDOW`` is the
        # last legal value — must NOT raise. This protects against an
        # off-by-one in the cap (e.g. ``>=`` vs ``>``) where the
        # boundary would be silently rejected.
        boundary = MAX_PIVOT_WINDOW  # 401
        # 200 + 1 + 200 == 401 (legal). Need at least ``boundary`` rows
        # so the early-exit short-circuit doesn't mask a real bug.
        n = boundary
        highs = np.linspace(10.0, 10.0 + n, num=n, endpoint=False)
        lows = highs - 1.0
        df = pd.DataFrame(
            {
                "open": highs,
                "high": highs,
                "low": lows,
                "close": highs,
                "volume": [1.0] * n,
            },
            index=pd.date_range("2024-01-01", periods=n, freq="15min"),
        )
        out = confirmed_pivots(df, left=200, right=200)
        assert isinstance(out, pd.DataFrame)
        assert set(out.columns) >= {"pivot_high", "pivot_low"}

    def test_string_high_column_raises_type_error(self):
        # String/object columns must be rejected up front, before the
        # vectorised comparisons silently turn string-lex into a
        # numeric comparison. Confirms a precise TypeError.
        idx = pd.date_range("2024-01-01", periods=10, freq="15min")
        df = pd.DataFrame(
            {
                "open": [1.0] * 10,
                "high": [str(i) for i in range(10)],  # object dtype
                "low": [float(i) for i in range(10)],
                "close": [1.0] * 10,
                "volume": [1.0] * 10,
            },
            index=idx,
        )
        with pytest.raises(TypeError, match="must be a numeric price series"):
            confirmed_pivots(df, left=2, right=2)

    def test_object_dtype_low_column_raises_type_error(self):
        # Object dtype on ``low`` must also be rejected — symmetric
        # coverage for the second column.
        idx = pd.date_range("2024-01-01", periods=10, freq="15min")
        df = pd.DataFrame(
            {
                "open": [1.0] * 10,
                "high": [10.0 + i for i in range(10)],
                "low": [None] * 10,  # None -> object dtype in pandas
                "close": [1.0] * 10,
                "volume": [1.0] * 10,
            },
            index=idx,
        )
        with pytest.raises(TypeError, match="must be a numeric price series"):
            confirmed_pivots(df, left=2, right=2)

    def test_bool_column_raises_type_error(self):
        # Bool columns are technically numeric-ish in some pandas paths
        # but are categorically wrong for a price series. The validator
        # must reject them to prevent silent nonsense (True/False
        # would compare fine and emit a "pivot" of 0/1).
        idx = pd.date_range("2024-01-01", periods=10, freq="15min")
        df = pd.DataFrame(
            {
                "open": [True] * 10,
                "high": [True] * 10,
                "low": [False] * 10,
                "close": [True] * 10,
                "volume": [1.0] * 10,
            },
            index=idx,
        )
        with pytest.raises(TypeError, match="must be a numeric price series"):
            confirmed_pivots(df, left=2, right=2)

    def test_numeric_dtypes_accepted(self):
        # Sanity: the validator must let the realistic dtypes through —
        # float64 (the default from read_feather), float32, int64.
        # Without this we would over-reject and break production.
        idx = pd.date_range("2024-01-01", periods=10, freq="15min")
        for dtype in (np.float64, np.float32, np.int64):
            highs = np.arange(10, dtype=dtype)
            lows = highs - 1
            df = pd.DataFrame(
                {
                    "open": highs,
                    "high": highs,
                    "low": lows,
                    "close": highs,
                    "volume": [1.0] * 10,
                },
                index=idx,
            )
            out = confirmed_pivots(df, left=2, right=2)
            assert isinstance(out, pd.DataFrame)
            assert set(out.columns) >= {"pivot_high", "pivot_low"}
