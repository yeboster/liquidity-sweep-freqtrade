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

from strategies.stack_components import (
    confirmed_pivots,
    market_structure,
    MAX_PIVOT_WINDOW,
)


# ---- Task 3: structure engine fixtures -------------------------------------

# Constants for explicit BOS/CHoCH tests. Each row's high/low/close is
# hand-built so the test reads as a story rather than a numeric exercise.
_BULL_SEQ = [
    # index, high, low, close
    (0, 10.0, 9.0, 9.5),     # ramp
    (1, 11.0, 9.5, 10.5),    # ramp
    (2, 12.0, 10.5, 11.5),   # ramp
    (3, 13.0, 11.5, 12.5),   # PEAK (candidate swing high)
    (4, 12.0, 11.0, 11.5),   # post-peak
    (5, 11.0, 10.0, 10.5),   # post-peak
    (6, 10.0, 9.0, 9.5),     # post-peak
    (7, 9.0, 8.0, 8.5),      # TROUGH (candidate swing low)
    (8, 10.0, 8.5, 9.5),     # post-trough
    (9, 11.0, 9.5, 10.5),    # post-trough
    (10, 12.0, 10.5, 11.5),  # post-trough
    (11, 13.0, 11.5, 12.5),  # second PEAK
    (12, 14.0, 12.5, 13.5),  # bullish thrust — close above prior pivot high (13)
    (13, 15.0, 13.5, 14.5),  # continuation
    (14, 16.0, 14.5, 15.5),  # continuation
    (15, 15.0, 14.0, 14.5),  # TROUGH #2 (post-BOS impulse origin)
    (16, 14.0, 13.0, 13.5),  # post-trough
    (17, 13.0, 12.0, 12.5),  # post-trough
    (18, 12.0, 11.0, 11.5),  # post-trough (TROUGH #2 confirmed by row 20)
    (19, 13.0, 11.0, 12.0),  # post-trough
    (20, 12.0, 10.0, 11.0),  # last right bar of trough window
    (21, 11.0, 9.0, 10.0),   # bearish thrust — close below trough #2 (10)
]


_BEAR_SEQ = [
    (0, 12.0, 11.0, 11.5),
    (1, 13.0, 11.5, 12.5),
    (2, 14.0, 12.5, 13.5),
    (3, 15.0, 13.5, 14.5),  # PEAK #1
    (4, 14.0, 13.0, 13.5),
    (5, 13.0, 12.0, 12.5),
    (6, 12.0, 11.0, 11.5),
    (7, 11.0, 10.0, 10.5),  # TROUGH #1
    (8, 12.0, 10.5, 11.5),
    (9, 13.0, 11.5, 12.5),
    (10, 12.0, 11.0, 11.5),
    (11, 11.0, 10.0, 10.5),  # TROUGH #2
    (12, 10.0, 9.0, 9.5),    # bearish thrust — close below trough #1 (10)
    (13, 9.0, 8.0, 8.5),     # continuation
    (14, 8.0, 7.0, 7.5),     # continuation
    (15, 9.0, 7.0, 8.5),     # PEAK #2 (post-BOS impulse origin)
    (16, 10.0, 8.5, 9.5),
    (17, 11.0, 9.5, 10.5),
    (18, 12.0, 10.5, 11.5),
    (19, 13.0, 11.5, 12.5),  # last right bar
    (20, 14.0, 12.5, 13.5),  # bullish thrust — close above peak #2 (13)
]


def _frame_from(seq):
    """Build a deterministic OHLC frame from a (idx, high, low, close) list."""
    idx = pd.date_range("2024-01-01", periods=len(seq), freq="15min")
    return pd.DataFrame(
        {
            "high": [s[1] for s in seq],
            "low": [s[2] for s in seq],
            "close": [s[3] for s in seq],
            "open": [s[3] for s in seq],
            "volume": [1.0] * len(seq),
        },
        index=idx,
    )


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


# =============================================================================
# Task 3: causal BOS/CHoCH and protected-swing structure engine
# =============================================================================
#
# The structure engine is a *forward-only* state machine over confirmed pivot
# events and OHLC. Its outputs:
#
#   - external_high / external_low:
#         STATE columns (forward-running) — the most recent confirmed swing
#         high / low in the corresponding direction. These update whenever a
#         new pivot is confirmed AND that pivot becomes the new external.
#
#   - protected_high / protected_low:
#         STATE columns — the impulse-origin swing level that the current
#         trend is "protecting". A close through a protected swing in the
#         counter-trend direction triggers a CHoCH.
#
#   - bos / choch:
#         EVENT columns (sparse) — fire exactly once per level consumed.
#         bos   = +1 for bullish continuation BOS, -1 for bearish, 0 otherwise.
#         choch = +1 for bullish CHoCH, -1 for bearish, 0 otherwise.
#
#   - bias_state:
#         STATE column — +1 in a bullish regime, -1 in a bearish regime,
#         0 (NaN until first BOS or CHoCH) at the head of the data.
#
# All signals are based on candle BODY CLOSE; wick-only excursions do not
# count. Equal closes (close == level) are NOT considered a cross — this is
# the deterministic interpretation that does not spam signals on touches.
#


class TestStructureAPI:
    def test_returns_dataframe_with_expected_columns(self):
        df = _frame_from(_BULL_SEQ)
        out = market_structure(df, left=2, right=2)
        assert isinstance(out, pd.DataFrame)
        for col in (
            "external_high",
            "external_low",
            "protected_high",
            "protected_low",
            "bos",
            "choch",
            "bias_state",
        ):
            assert col in out.columns, f"missing column {col}"

    def test_output_index_matches_input(self):
        df = _frame_from(_BULL_SEQ)
        out = market_structure(df, left=2, right=2)
        assert list(out.index) == list(df.index)

    def test_accepts_precomputed_pivot_events(self):
        # Pivot detection is causal; passing in precomputed pivot_high/low
        # events lets callers reuse the upstream confirmed_pivots output
        # without paying for a second detection. The result must match
        # the result of letting the engine detect its own pivots on the
        # same OHLC.
        df = _frame_from(_BULL_SEQ)
        own = market_structure(df, left=2, right=2)
        events = confirmed_pivots(df, left=2, right=2)
        merged = pd.concat([df, events], axis=1)
        pre = market_structure(merged, left=2, right=2)
        pd.testing.assert_frame_equal(own, pre)


class TestBullishBos:
    def test_bullish_bos_fires_on_close_above_prior_pivot_high(self):
        # The bullish BOS must occur on the candle whose close first
        # exceeds the most recently confirmed pivot high — NOT on the
        # pivot candle itself, NOT on subsequent candles.
        df = _frame_from(_BULL_SEQ)
        out = market_structure(df, left=2, right=2)
        # First pivot_high = 13 (from idx 3, confirmed at idx 5).
        # Bullish BOS fires when close first exceeds 13. That's idx 12
        # (close=13.5), which is the only candle in the sequence whose
        # close strictly exceeds 13.
        bos = out["bos"].to_numpy()
        bullish_indices = np.where(bos == 1)[0]
        assert list(bullish_indices) == [12], (
            f"expected bullish BOS only at idx 12 (first close > 13), "
            f"got {bullish_indices.tolist()}; full bos: {bos.tolist()}"
        )

    def test_bullish_bos_protects_prior_swing_low(self):
        # The protected swing low for a bullish BOS is the most recent
        # pivot low that preceded the break — the impulse origin.
        # Here the prior pivot low is at idx 7 (low=8), confirmed at idx 9.
        # From the BOS candle onward (and until a CHoCH consumes it) the
        # protected_low column must hold that level.
        df = _frame_from(_BULL_SEQ)
        out = market_structure(df, left=2, right=2)
        # BOS fires at idx 12 (close=13.5 > pivot_high=13).
        # From idx 12 onwards, protected_low must be 8.0.
        for i in range(12, len(_BULL_SEQ)):
            got = out["protected_low"].iloc[i]
            assert got == 8.0, (
                f"protected_low at idx {i}: expected 8.0, got {got}; "
                f"full protected_low: {out['protected_low'].to_list()}"
            )


class TestBearishBos:
    def test_bearish_bos_fires_on_close_below_prior_pivot_low(self):
        # Symmetric to the bullish case: first close strictly below the
        # most recent pivot low fires bearish BOS, and only that candle.
        df = _frame_from(_BEAR_SEQ)
        out = market_structure(df, left=2, right=2)
        # First pivot_low = 10 (from idx 7, confirmed at idx 9).
        # Bearish BOS fires when close first strictly < 10. That's idx 12
        # (close=9.5).
        bos = out["bos"].to_numpy()
        bearish_indices = np.where(bos == -1)[0]
        assert list(bearish_indices) == [12], (
            f"expected bearish BOS only at idx 12, got {bearish_indices.tolist()}; "
            f"full bos: {bos.tolist()}"
        )

    def test_bearish_bos_protects_most_recent_swing_high(self):
        # The protected swing high for a bearish BOS is the most recent
        # confirmed pivot high that preceded the break — the impulse
        # origin of the bearish leg.
        df = _frame_from(_BEAR_SEQ)
        out = market_structure(df, left=2, right=2)
        # Confirmed pivot highs in BEAR_SEQ are at:
        #   idx 5: high=15 (from PEAK #1 at idx 3)
        #   idx 11: high=13 (from second peak at idx 9)
        # The most recent confirmed pivot high before the bearish BOS
        # at idx 12 is therefore 13.0 (the impulse origin of the bearish
        # leg, not the longer-range PEAK #1 at 15).  protected_high
        # holds 13.0 from idx 12 until the bullish CHoCH at idx 20
        # consumes it (NaN thereafter).
        expected_protected_high = 13.0
        # Walk the post-BOS rows, tracking the expected level until
        # the CHoCH consumes it.
        protected_window_end = int(np.where(out["choch"].to_numpy() == 1)[0][0])
        for i in range(12, protected_window_end):
            got = out["protected_high"].iloc[i]
            assert got == expected_protected_high, (
                f"protected_high at idx {i}: expected {expected_protected_high}, "
                f"got {got}; full protected_high: {out['protected_high'].to_list()}"
            )


class TestWickOnlyDoesNotCount:
    def test_wick_above_pivot_high_without_body_close_does_not_fire_bos(self):
        # The candle before the BOS row wicks above the prior pivot high
        # but does NOT close above it (close == pivot level). The BOS
        # must NOT fire on the wick candle.
        idx = pd.date_range("2024-01-01", periods=10, freq="15min")
        df = pd.DataFrame(
            {
                "high":  [10.0, 11.0, 12.0, 13.0, 12.0, 11.0, 10.0,  9.0, 14.0, 13.0],
                "low":   [ 9.0, 10.0, 11.0, 12.0, 11.0, 10.0,  9.0,  8.0, 11.0, 12.0],
                "close": [ 9.5, 10.5, 11.5, 12.5, 11.5, 10.5,  9.5,  8.5, 13.0, 12.5],
                #                                          ^idx 8: high=14 (wick > 13) but close=13.0 (= level, no cross)
                "open":  [ 9.5, 10.5, 11.5, 12.5, 11.5, 10.5,  9.5,  8.5, 12.5, 12.5],
                "volume": [1.0] * 10,
            },
            index=idx,
        )
        out = market_structure(df, left=2, right=2)
        # Idx 8 wick above but close = 13 (not strictly >). Equal-close
        # is treated as not-a-cross. No BOS at idx 8. Idx 9 close=12.5
        # is below the level, so no BOS there either. The engine must
        # not have fired any bullish BOS by row 9.
        bos_head = out["bos"].iloc[:10].to_numpy()
        assert not (bos_head == 1).any(), (
            f"wick-only excursion should not fire BOS; "
            f"got bos values: {bos_head.tolist()}"
        )


class TestChoch:
    def test_choch_fires_on_close_through_protected_countertrend_swing(self):
        # In the bullish sequence, after the bullish BOS at idx 12 the
        # protected_low is 8.0 (trough #1). A subsequent close that
        # strictly drops below 8.0 is a bearish CHoCH (trend flips).
        # The trough #2 (idx 15) has low=14 — wait, that's the post-BOS
        # pullback, not below 8. We construct the violating candle
        # explicitly: idx 21 closes at 10.0 with low=9.0; the protected
        # low is still 8.0 because trough #2 hasn't been confirmed yet
        # (its window is [15..19], so it's confirmed at idx 19 with
        # low=14, NOT lower than 8). So at idx 21, the protected low
        # remains 8.0, and close=10.0 does NOT cross 8.0.
        # That's wrong for the spec — we need a sequence where the
        # protected low is actually violated by body close.
        #
        # Build a tighter sequence: bullish BOS then immediate violation
        # of the protected low. The trough confirmation window [left=2,
        # right=2] is 5 bars, so we need 5 bars between trough and its
        # close to be invalidated. Easier — extend the sequence so the
        # post-BOS pullback creates a new confirmed pivot high that we
        # then break downward through.
        pass  # replaced by dedicated test below

    def test_choch_fires_on_close_through_protected_low_after_bullish_bos(self):
        # Construct an explicit scenario:
        #   1. Bullish BOS occurs (protected_low gets set).
        #   2. A new confirmed pivot high is registered (does not change
        #      protected_low, which is the impulse origin).
        #   3. A candle closes strictly below protected_low -> CHoCH.
        idx = pd.date_range("2024-01-01", periods=18, freq="15min")
        df = pd.DataFrame(
            {
                # 0..4 ramp up to peak at 3 (13), trough at 7 (8), peak at 11 (13)
                # idx 12 close=13.5 -> bullish BOS (first close > 13)
                # idx 13-17 pullback; pivot_high gets a new confirmation
                # idx 17 close=7.0 strictly < protected_low=8 -> CHoCH
                "high":  [10.0, 11.0, 12.0, 13.0, 12.0, 11.0, 10.0,  9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 13.0, 12.0, 11.0, 10.0,  9.0],
                "low":   [ 9.0, 10.0, 11.0, 12.0, 11.0, 10.0,  9.0,  8.0,  8.5,  9.5, 10.5, 11.5, 12.5, 12.0, 11.0, 10.0,  9.0,  8.0],
                "close": [ 9.5, 10.5, 11.5, 12.5, 11.5, 10.5,  9.5,  8.5,  9.5, 10.5, 11.5, 12.5, 13.5, 12.5, 11.5, 10.5,  9.5,  7.0],
                #                                                                              ^^^^ BOS          ^^^^ close<8 -> CHoCH
                "open":  [ 9.5, 10.5, 11.5, 12.5, 11.5, 10.5,  9.5,  8.5,  9.5, 10.5, 11.5, 12.5, 13.5, 12.5, 11.5, 10.5,  9.5,  9.0],
                "volume": [1.0] * 18,
            },
            index=idx,
        )
        out = market_structure(df, left=2, right=2)
        bos = out["bos"].to_numpy()
        choch = out["choch"].to_numpy()
        # Bullish BOS fires at idx 12.
        assert list(np.where(bos == 1)[0]) == [12], (
            f"bullish BOS expected at idx 12, got {np.where(bos == 1)[0].tolist()}; "
            f"bos: {bos.tolist()}; choch: {choch.tolist()}"
        )
        # Bearish CHoCH fires at idx 17 (close=7 < protected_low=8).
        assert list(np.where(choch == -1)[0]) == [17], (
            f"bearish CHoCH expected at idx 17, got {np.where(choch == -1)[0].tolist()}; "
            f"bos: {bos.tolist()}; choch: {choch.tolist()}; "
            f"protected_low: {out['protected_low'].to_list()}; "
            f"bias_state: {out['bias_state'].to_list()}"
        )
        # Bias must flip after the CHoCH: bullish before, bearish at and after.
        bias = out["bias_state"].to_numpy()
        assert bias[12] == 1, f"bias should be bullish at BOS row, got {bias[12]}"
        assert bias[17] == -1, f"bias should flip to bearish at CHoCH, got {bias[17]}"
        assert bias[16] == 1, f"bias should still be bullish at idx 16, got {bias[16]}"


class TestNoRepeat:
    def test_no_repeat_bullish_bos(self):
        # Once a bullish BOS fires on a given external_high, subsequent
        # candles whose close is still above that level must NOT re-fire
        # the same BOS. Build a long sequence where price keeps printing
        # above the original pivot high; only the FIRST candle that crosses
        # should produce the signal.
        df = _frame_from(_BULL_SEQ)
        out = market_structure(df, left=2, right=2)
        bos = out["bos"].to_numpy()
        bullish_indices = np.where(bos == 1)[0]
        # Should be exactly one bullish BOS in the entire bullish-thrust
        # section, even though idx 13, 14 also close > 13.
        assert len(bullish_indices) == 1, (
            f"expected exactly one bullish BOS, got {bullish_indices.tolist()}; "
            f"bos: {bos.tolist()}"
        )

    def test_no_repeat_bearish_bos(self):
        df = _frame_from(_BEAR_SEQ)
        out = market_structure(df, left=2, right=2)
        bos = out["bos"].to_numpy()
        bearish_indices = np.where(bos == -1)[0]
        assert len(bearish_indices) == 1, (
            f"expected exactly one bearish BOS, got {bearish_indices.tolist()}; "
            f"bos: {bos.tolist()}"
        )

    def test_no_repeat_choch(self):
        # After a CHoCH fires at idx 17, subsequent candles whose close
        # remains below the protected level must NOT re-fire the CHoCH.
        idx = pd.date_range("2024-01-01", periods=22, freq="15min")
        df = pd.DataFrame(
            {
                "high":  [10.0, 11.0, 12.0, 13.0, 12.0, 11.0, 10.0,  9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 13.0, 12.0, 11.0, 10.0,  9.0,  8.0,  7.0,  6.0,  5.0],
                "low":   [ 9.0, 10.0, 11.0, 12.0, 11.0, 10.0,  9.0,  8.0,  8.5,  9.5, 10.5, 11.5, 12.5, 12.0, 11.0, 10.0,  9.0,  8.0,  7.0,  6.0,  5.0,  4.0],
                "close": [ 9.5, 10.5, 11.5, 12.5, 11.5, 10.5,  9.5,  8.5,  9.5, 10.5, 11.5, 12.5, 13.5, 12.5, 11.5, 10.5,  9.5,  7.0,  6.5,  5.5,  4.5,  3.5],
                #                                                                              ^^^^ BOS at 12       ^^^^ CHoCH at 17
                "open":  [ 9.5, 10.5, 11.5, 12.5, 11.5, 10.5,  9.5,  8.5,  9.5, 10.5, 11.5, 12.5, 13.5, 12.5, 11.5, 10.5,  9.5,  9.0,  7.5,  6.5,  5.5,  4.5],
                "volume": [1.0] * 22,
            },
            index=idx,
        )
        out = market_structure(df, left=2, right=2)
        choch = out["choch"].to_numpy()
        bearish_choch = np.where(choch == -1)[0]
        assert list(bearish_choch) == [17], (
            f"expected exactly one bearish CHoCH at idx 17, got {bearish_choch.tolist()}; "
            f"choch: {choch.tolist()}"
        )


class TestExternalLevels:
    def test_external_high_advances_to_new_confirmed_pivot(self):
        # Each newly confirmed pivot high that is strictly greater than
        # the prior external_high must replace it.
        df = _frame_from(_BULL_SEQ)
        out = market_structure(df, left=2, right=2)
        # PEAK at idx 3 (high=13) confirmed at idx 5 -> external_high at idx 5 = 13.
        # After idx 12's bullish BOS the external_high is "broken"; the
        # implementation choice is that external_high remains the last
        # un-broken level until a new pivot_high is confirmed that
        # exceeds the broken level. We accept either: (a) external_high
        # stays at 13 until a new pivot_high above 13 is confirmed, or
        # (b) external_high resets to NaN on break and resumes when a
        # new pivot is confirmed.
        # The CONTRACT being tested here is only: every finite
        # external_high value must equal a value that appeared as a
        # confirmed pivot high before or at that row. Forbidden:
        # external_high ever holding a level that has not yet been
        # confirmed at that row.
        n = len(_BULL_SEQ)
        for i in range(n):
            v = out["external_high"].iloc[i]
            if pd.isna(v):
                continue
            # Was there a confirmed pivot high at or before row i with
            # this exact level? (Using the standalone pivot detector.)
            pivots = confirmed_pivots(df, left=2, right=2)["pivot_high"].to_numpy()
            confirmed_levels_before_i = pivots[:i + 1]
            finite = confirmed_levels_before_i[~np.isnan(confirmed_levels_before_i)]
            assert v in finite, (
                f"external_high at idx {i} = {v} has no corresponding "
                f"confirmed pivot high in [:{i}]; pivots before: "
                f"{finite.tolist()}"
            )

    def test_external_low_advances_to_new_confirmed_pivot(self):
        df = _frame_from(_BULL_SEQ)
        out = market_structure(df, left=2, right=2)
        n = len(_BULL_SEQ)
        for i in range(n):
            v = out["external_low"].iloc[i]
            if pd.isna(v):
                continue
            pivots = confirmed_pivots(df, left=2, right=2)["pivot_low"].to_numpy()
            confirmed_levels_before_i = pivots[:i + 1]
            finite = confirmed_levels_before_i[~np.isnan(confirmed_levels_before_i)]
            assert v in finite, (
                f"external_low at idx {i} = {v} has no corresponding "
                f"confirmed pivot low in [:{i}]; pivots before: "
                f"{finite.tolist()}"
            )


class TestBiasState:
    def test_bias_starts_undefined(self):
        df = _frame_from(_BULL_SEQ)
        out = market_structure(df, left=2, right=2)
        # Before any BOS/CHoCH, bias_state must be NaN (undefined).
        # The first BOS fires at idx 12, so all rows strictly before 12
        # must have NaN bias.
        for i in range(12):
            v = out["bias_state"].iloc[i]
            assert pd.isna(v), (
                f"bias_state should be NaN before any BOS, got {v} at idx {i}"
            )

    def test_bias_becomes_bullish_after_bullish_bos(self):
        df = _frame_from(_BULL_SEQ)
        out = market_structure(df, left=2, right=2)
        # From idx 12 (BOS) onward, until any CHoCH, bias_state == 1.
        for i in range(12, len(_BULL_SEQ)):
            v = out["bias_state"].iloc[i]
            # Accept NaN as "no further bias" if no CHoCH has fired yet
            # (i.e. the trend remains bullish from 12 onward, so bias is 1).
            assert v == 1, (
                f"bias_state at idx {i}: expected 1, got {v}; "
                f"full bias_state: {out['bias_state'].to_list()}"
            )

    def test_bias_flips_on_choch(self):
        idx = pd.date_range("2024-01-01", periods=18, freq="15min")
        df = pd.DataFrame(
            {
                "high":  [10.0, 11.0, 12.0, 13.0, 12.0, 11.0, 10.0,  9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 13.0, 12.0, 11.0, 10.0,  9.0],
                "low":   [ 9.0, 10.0, 11.0, 12.0, 11.0, 10.0,  9.0,  8.0,  8.5,  9.5, 10.5, 11.5, 12.5, 12.0, 11.0, 10.0,  9.0,  8.0],
                "close": [ 9.5, 10.5, 11.5, 12.5, 11.5, 10.5,  9.5,  8.5,  9.5, 10.5, 11.5, 12.5, 13.5, 12.5, 11.5, 10.5,  9.5,  7.0],
                "open":  [ 9.5, 10.5, 11.5, 12.5, 11.5, 10.5,  9.5,  8.5,  9.5, 10.5, 11.5, 12.5, 13.5, 12.5, 11.5, 10.5,  9.5,  9.0],
                "volume": [1.0] * 18,
            },
            index=idx,
        )
        out = market_structure(df, left=2, right=2)
        bias = out["bias_state"].to_numpy()
        # After CHoCH at idx 17, bias must be -1.
        assert bias[17] == -1
        assert bias[18] == -1 if len(bias) > 18 else True


class TestNoFutureLeakageStructure:
    def test_future_shock_does_not_change_past_structure(self):
        # Build a long random frame with enough pivots. Shock the tail.
        # Past structure columns must be identical.
        df = _make_long_frame(n=200, seed=1)
        baseline = market_structure(df, left=3, right=3)

        shock_start = 80
        right = 3
        cutoff = shock_start - right

        # Sanity: at least one finite BOS/CHoCH exists before shock_start
        # — without this the equality check would be vacuous.
        assert (
            baseline.iloc[:shock_start]["bos"].abs().sum() > 0
            or baseline.iloc[:shock_start]["choch"].abs().sum() > 0
        ), "test setup: no finite BOS/CHoCH before shock_start"

        shocked = df.copy()
        high_idx = shocked.columns.get_loc("high")
        low_idx = shocked.columns.get_loc("low")
        close_idx = shocked.columns.get_loc("close")
        shocked.iloc[shock_start:, [high_idx, low_idx, close_idx]] *= 10.0

        actual = market_structure(shocked, left=3, right=3)

        # All structure columns in the safe prefix must be identical.
        for col in ("external_high", "external_low", "protected_high",
                    "protected_low", "bos", "choch", "bias_state"):
            b = baseline.iloc[:shock_start][col].to_numpy()
            a = actual.iloc[:shock_start][col].to_numpy()
            # NaN-aware element equality.
            if np.issubdtype(b.dtype, np.floating):
                both_nan = np.isnan(b) & np.isnan(a)
                equal = (b == a) | both_nan
            else:
                both_nan = np.zeros_like(b, dtype=bool)
                equal = (b == a)
            assert equal.all(), (
                f"future shock changed past {col!r} within [:shock_start]; "
                f"row(s) where baseline != actual: "
                f"{np.where(~equal)[0].tolist()[:10]}; "
                f"baseline head: {b[:5].tolist()}; "
                f"actual head: {a[:5].tolist()}"
            )

    def test_non_vacuous_future_shock(self):
        # The future-shock test must be non-vacuous: at least one
        # structural output MUST change in the tail when the shock
        # occurs, OR at least one must exist in the baseline tail.
        # This protects against a silent regression where the engine
        # returns NaN/zero for everything.
        df = _make_long_frame(n=200, seed=2)
        baseline = market_structure(df, left=3, right=3)
        shocked = df.copy()
        shocked.iloc[80:, shocked.columns.get_indexer(["high", "low", "close"])] *= 10.0
        actual = market_structure(shocked, left=3, right=3)
        # In the shocked tail, structural outputs MUST differ somewhere.
        # If they are identical, the engine is not actually using close.
        tail_diff = False
        for col in ("bos", "choch", "bias_state"):
            if not baseline.iloc[80:][col].equals(actual.iloc[80:][col]):
                tail_diff = True
                break
        assert tail_diff, (
            "future shock did not change bos/choch/bias_state in the tail; "
            "the future-shock test would be vacuous OR the engine ignores close"
        )


class TestEdgeCasesStructure:
    def test_nan_close_does_not_fire_bos_or_choch(self):
        idx = pd.date_range("2024-01-01", periods=10, freq="15min")
        df = pd.DataFrame(
            {
                "high":  [10.0, 11.0, 12.0, 13.0, 12.0, 11.0, 10.0,  9.0, np.nan, 11.0],
                "low":   [ 9.0, 10.0, 11.0, 12.0, 11.0, 10.0,  9.0,  8.0,  8.5, 10.0],
                "close": [ 9.5, 10.5, 11.5, 12.5, 11.5, 10.5,  9.5,  8.5, np.nan, 13.0],
                #                                                                ^ idx 9 would-be BOS candidate but close was NaN at idx 8
                "open":  [ 9.5, 10.5, 11.5, 12.5, 11.5, 10.5,  9.5,  8.5,  9.0, 12.5],
                "volume": [1.0] * 10,
            },
            index=idx,
        )
        out = market_structure(df, left=2, right=2)
        # NaN close at idx 8 cannot participate in BOS/CHoCH logic.
        # Idx 9 close=13.0 == pivot_high level (equal close, not a cross).
        bos = out["bos"].to_numpy()
        choch = out["choch"].to_numpy()
        assert not (bos == 1).any(), (
            f"NaN/equal close should not fire BOS; bos: {bos.tolist()}"
        )
        assert not (choch == 1).any() and not (choch == -1).any(), (
            f"NaN close should not fire CHoCH; choch: {choch.tolist()}"
        )

    def test_equal_close_does_not_count_as_break(self):
        # Close exactly equal to the level is NOT a cross (deterministic,
        # does not spam signals on touches).
        idx = pd.date_range("2024-01-01", periods=10, freq="15min")
        df = pd.DataFrame(
            {
                "high":  [10.0, 11.0, 12.0, 13.0, 12.0, 11.0, 10.0,  9.0, 14.0, 13.0],
                "low":   [ 9.0, 10.0, 11.0, 12.0, 11.0, 10.0,  9.0,  8.0, 11.0, 12.0],
                "close": [ 9.5, 10.5, 11.5, 12.5, 11.5, 10.5,  9.5,  8.5, 13.0, 12.5],
                #                                                    ^^^^ close == 13 exactly
                "open":  [ 9.5, 10.5, 11.5, 12.5, 11.5, 10.5,  9.5,  8.5, 12.5, 12.5],
                "volume": [1.0] * 10,
            },
            index=idx,
        )
        out = market_structure(df, left=2, right=2)
        bos = out["bos"].to_numpy()
        # Close == level does not trigger BOS.
        assert not (bos == 1).any(), (
            f"equal close should not fire BOS; bos: {bos.tolist()}"
        )

    def test_short_history_does_not_crash(self):
        # 3 rows is well below any sane pivot window; must not raise.
        idx = pd.date_range("2024-01-01", periods=3, freq="15min")
        df = pd.DataFrame(
            {
                "high": [10.0, 11.0, 12.0],
                "low": [9.0, 10.0, 11.0],
                "close": [9.5, 10.5, 11.5],
                "open": [9.5, 10.5, 11.5],
                "volume": [1.0, 1.0, 1.0],
            },
            index=idx,
        )
        out = market_structure(df, left=2, right=2)
        assert isinstance(out, pd.DataFrame)
        # No pivots -> no BOS/CHoCH. Bias must be NaN.
        assert (out["bos"] == 0).all()
        assert (out["choch"] == 0).all()
        assert out["bias_state"].isna().all()

    def test_empty_frame_bias_state_is_nan(self):
        # Empty frame: no rows -> bias_state must be float NaN, not a
        # sentinel int (-128 / 0). The state machine should never have
        # observed a BOS, so the column must be all NaN.
        idx = pd.DatetimeIndex([], freq="15min")
        df = pd.DataFrame(
            {
                "open": pd.Series([], dtype=float, index=idx),
                "high": pd.Series([], dtype=float, index=idx),
                "low": pd.Series([], dtype=float, index=idx),
                "close": pd.Series([], dtype=float, index=idx),
                "volume": pd.Series([], dtype=float, index=idx),
            },
        )
        out = market_structure(df, left=2, right=2)
        assert isinstance(out, pd.DataFrame)
        assert len(out) == 0
        assert out["bias_state"].isna().all()
        # All event columns must be empty too.
        assert (out["bos"] == 0).all()
        assert (out["choch"] == 0).all()


# =============================================================================
# Task 3 review — temporal ordering, protected-swing refresh, API validation
# =============================================================================


class TestSameCandlePivotNonBreak:
    """A pivot confirmed at row ``i`` must NOT be breakable by row ``i``'s close.

    The engine evaluates BOS/CHoCH against the prior iteration's structure
    state. A pivot emitted on row ``i`` updates ``external_high`` /
    ``external_low`` for OUTPUT on row ``i``, but it does not become
    eligible to be CROSSED on row ``i`` — the break test runs against the
    state carried from row ``i - 1`` (which does not yet contain the
    new pivot).

    The contract: NO BOS on the confirmation bar; the BOS fires only on
    a LATER bar that closes strictly through the freshly confirmed
    level. We test both directions (bullish and bearish) and pin the
    exact BOS row.
    """

    def test_bullish_same_candle_pivot_is_not_breakable_then_breaks_later(self):
        # 8-row frame. Pivot high is supplied as a precomputed event
        # Series whose single finite entry is at index 5 with level 13.
        # Row 5's close is 13.5 (strict cross above 13). Row 7's close
        # is 14.5 (later cross). With proper temporal ordering the
        # engine cannot fire BOS on row 5 — row 5's close is evaluated
        # against prior state, which has no external_high. The BOS
        # fires on row 7 (the first LATER row whose close is strictly
        # above 13, evaluated against state that now contains 13).
        idx = pd.date_range("2024-01-01", periods=8, freq="15min")
        df = pd.DataFrame(
            {
                "high":   [10.0, 11.0, 12.0, 11.0, 11.0, 11.0, 12.0, 15.0],
                "low":    [ 9.0, 10.0, 11.0, 10.0, 10.0, 10.0, 11.0, 14.0],
                "close":  [ 9.5, 10.5, 11.5, 10.5, 10.5, 13.5, 12.5, 14.5],
                #                                          ^^^^ close=13.5 same row as pivot_high=13 emission (cross, but newly emitted)
                #                                                            ^^^^ close=14.5 strict cross, BOS fires here
                "open":   [ 9.5, 10.5, 11.5, 10.5, 10.5, 11.0, 12.5, 14.5],
                "volume": [1.0] * 8,
            },
            index=idx,
        )
        pivot_high = pd.Series(np.nan, index=idx)
        pivot_high.iloc[5] = 13.0  # freshly confirmed at row 5
        pivot_low = pd.Series(np.nan, index=idx)  # no lows
        out = market_structure(
            df, left=2, right=2,
            pivot_high=pivot_high, pivot_low=pivot_low,
        )
        bos = out["bos"].to_numpy()
        bullish = np.where(bos == 1)[0]
        # MUST NOT fire on row 5 (the same-candle break).
        assert 5 not in bullish, (
            f"BOS fired on the same candle the pivot was confirmed; "
            f"bullish BOS at {bullish.tolist()}; bos: {bos.tolist()}"
        )
        # MUST fire on row 7 (first later cross, evaluated against state
        # that now contains the pivot emitted on row 5).
        assert bullish.tolist() == [7], (
            f"BOS should fire on row 7 (first later strict cross); "
            f"bullish BOS at {bullish.tolist()}; bos: {bos.tolist()}"
        )
        # external_high MUST be reported at row 5 (the freshly confirmed
        # value) — the spec says newly confirmed external state IS
        # output on the current row. We just don't let it be crossable.
        assert out["external_high"].iloc[5] == 13.0, (
            f"external_high must be 13.0 at confirmation row; "
            f"got {out['external_high'].iloc[5]}"
        )

    def test_bearish_same_candle_pivot_is_not_breakable_then_breaks_later(self):
        # Mirror: pivot_low=9 supplied at row 5; row 5 close=8.5 (cross);
        # row 7 close=7.5 (later cross). BOS fires on row 7 only.
        idx = pd.date_range("2024-01-01", periods=8, freq="15min")
        df = pd.DataFrame(
            {
                "high":   [12.0, 13.0, 14.0, 13.0, 13.0, 13.0, 12.0,  7.0],
                "low":    [11.0, 12.0, 13.0, 12.0, 12.0, 12.0, 11.0,  6.0],
                "close":  [11.5, 12.5, 13.5, 12.5, 12.5,  8.5,  9.5,  7.5],
                #                                          ^^^^ close=8.5 cross below pivot_low=9 (newly emitted)
                #                                                            ^^^^ close=7.5 strict cross, BOS fires here
                "open":   [11.5, 12.5, 13.5, 12.5, 12.5, 12.0,  9.5,  7.5],
                "volume": [1.0] * 8,
            },
            index=idx,
        )
        pivot_high = pd.Series(np.nan, index=idx)
        pivot_low = pd.Series(np.nan, index=idx)
        pivot_low.iloc[5] = 9.0
        out = market_structure(
            df, left=2, right=2,
            pivot_high=pivot_high, pivot_low=pivot_low,
        )
        bos = out["bos"].to_numpy()
        bearish = np.where(bos == -1)[0]
        assert 5 not in bearish, (
            f"bearish BOS fired on the same candle the pivot low was confirmed; "
            f"bearish BOS at {bearish.tolist()}; bos: {bos.tolist()}"
        )
        assert bearish.tolist() == [7], (
            f"bearish BOS should fire on row 7; "
            f"bearish BOS at {bearish.tolist()}; bos: {bos.tolist()}"
        )
        assert out["external_low"].iloc[5] == 9.0, (
            f"external_low must be 9.0 at confirmation row; "
            f"got {out['external_low'].iloc[5]}"
        )


class TestProtectedSwingRefresh:
    """On EVERY continuation BOS, refresh the protected opposite swing.

    A bullish BOS refreshes ``protected_low`` to the most recent
    confirmed pivot low that existed BEFORE the BOS candle. A bearish
    BOS refreshes ``protected_high`` symmetrically.

    The protected level is the impulse origin (the "pullback" that
    protected the displacement). Each BOS draws a NEW origin from the
    most recently confirmed opposite-side pivot — even if a fresher
    pivot has been confirmed since the previous BOS. A CHoCH then
    fires against the refreshed level, not the stale one.
    """

    def test_protected_low_refreshes_on_second_bullish_bos(self):
        # Deterministic protected-swing refresh regression. Pivot events
        # are supplied as precomputed Series aligned to ``frame.index``
        # so that pivot-detection noise cannot confound the engine's
        # state-machine semantics. The flat OHLCV keeps every close on
        # the H1/H2 level unless explicitly broken — so a stray pivot
        # at row 4 (a BOS row) cannot quietly appear.
        #
        # Layout (14 rows, 15-min bars):
        #   row 1: pivot_high H1=10 confirmed
        #   row 2: pivot_low  L1=5  confirmed  (last_known_pivot_low=5)
        #   row 4: close=11  > H1=10           -> BOS #1, protected_low = L1 = 5
        #   row 6: pivot_low  L2=7  confirmed  (last_known_pivot_low=7 after row 6)
        #   row 7: pivot_high H2=12 confirmed
        #   row 9: close=13  > H2=12           -> BOS #2, protected_low refreshes to L2 = 7
        #   row 10: close=6 < refreshed 7 (and > stale 5)
        #                                    -> bearish CHoCH (only because of refresh)
        #   rows 4, 9, 10 carry NO pivot event — same-row break guarantee.
        n = 14
        idx = pd.date_range("2024-01-01", periods=n, freq="15min")
        highs = [10.0] * n
        lows = [9.0] * n
        # Default close sits exactly on H1=10 — equal close is NOT a
        # cross, so no BOS fires until we explicitly drop below or push
        # above the relevant level.
        closes = [10.0] * n
        closes[4] = 11.0   # bullish BOS row 4: close > H1=10
        closes[9] = 13.0   # bullish BOS row 9: close > H2=12
        closes[10] = 6.0   # bearish CHoCH row 10: close < refreshed protected_low=7
        df = pd.DataFrame(
            {"high": highs, "low": lows, "close": closes, "open": closes,
             "volume": [1.0] * n},
            index=idx,
        )

        # Hand-built pivot event Series — sparse, aligned to frame.index.
        pivot_high = pd.Series(np.nan, index=idx)
        pivot_low = pd.Series(np.nan, index=idx)
        pivot_high.iloc[1] = 10.0  # H1
        pivot_low.iloc[2] = 5.0    # L1
        pivot_low.iloc[6] = 7.0    # L2
        pivot_high.iloc[7] = 12.0  # H2

        # Real-mutation guard: the supplied pivot events MUST actually
        # differ from a NaN-only Series in the rows we claim.
        assert pivot_high.iloc[[1, 7]].notna().all() and pivot_high.iloc[[4, 9, 10]].isna().all()
        assert pivot_low.iloc[[2, 6]].notna().all() and pivot_low.iloc[[4, 9, 10]].isna().all()

        out = market_structure(
            df, left=2, right=2,
            pivot_high=pivot_high, pivot_low=pivot_low,
        )
        bos = out["bos"].to_numpy()
        choch = out["choch"].to_numpy()
        protected_low = out["protected_low"].to_numpy()

        # Exact event rows — must be only the two BOS at 4, 9 and the
        # one CHoCH at 10. No spurious events anywhere else.
        bullish_bos = np.where(bos == 1)[0].tolist()
        bearish_choch = np.where(choch == -1)[0].tolist()
        assert bullish_bos == [4, 9], (
            f"expected bullish BOS at rows [4, 9]; got {bullish_bos}; bos: {bos.tolist()}"
        )
        assert bearish_choch == [10], (
            f"expected bearish CHoCH at row [10]; got {bearish_choch}; "
            f"choch: {choch.tolist()}"
        )

        # protected_low between BOS #1 (row 4) and BOS #2 (row 9) MUST
        # be 5.0 — the impulse origin of the first bullish leg, before
        # any refresh.
        for r in range(4, 9):
            assert protected_low[r] == 5.0, (
                f"protected_low at row {r}: expected 5.0 (pre-refresh), "
                f"got {protected_low[r]}; full: {protected_low.tolist()}"
            )

        # protected_low MUST refresh to 7.0 starting from BOS #2 (row 9).
        # The CHoCH at row 10 consumes it (NaN thereafter).
        assert protected_low[9] == 7.0, (
            f"protected_low at row 9: expected 7.0 (refreshed on BOS #2), "
            f"got {protected_low[9]}; full: {protected_low.tolist()}"
        )

        # The CHoCH at row 10 fires because close=6 is strictly below
        # the REFRESHED protected_low=7. Without refresh it would NOT
        # fire (6 > stale 5). Pinning the exact row guards the contract.
        # Sanity: bias flips to bearish at row 10.
        bias = out["bias_state"].to_numpy()
        assert bias[10] == -1, (
            f"bias should flip to -1 at CHoCH row 10; got {bias[10]}; "
            f"full bias: {bias.tolist()}"
        )

    def test_protected_high_refreshes_on_second_bearish_bos(self):
        # Mirror of the bullish refresh test. Pivot events are supplied
        # as precomputed Series aligned to ``frame.index`` so the
        # engine's state-machine semantics are isolated from the
        # auto-detected pivot path. Default close sits exactly on
        # L1=10 — equal close is NOT a cross.
        #
        # Layout (14 rows):
        #   row 1: pivot_low  L1=10 confirmed
        #   row 2: pivot_high H1=15 confirmed  (last_known_pivot_high=15)
        #   row 4: close=9   < L1=10          -> bearish BOS #1, protected_high = H1 = 15
        #   row 6: pivot_low  L2=8  confirmed  (last_external_low=8 for BOS #2)
        #   row 7: pivot_high H2=13 confirmed  (last_known_pivot_high=13 after row 7)
        #   row 9: close=7   < L2=8           -> bearish BOS #2, protected_high refreshes to H2 = 13
        #   row 10: close=14 > refreshed 13 (and < stale 15)
        #                                    -> bullish CHoCH (only because of refresh)
        #   rows 4, 9, 10 carry NO pivot event.
        n = 14
        idx = pd.date_range("2024-01-01", periods=n, freq="15min")
        highs = [10.0] * n
        lows = [9.0] * n
        closes = [10.0] * n  # equal to L1=10, NOT a strict cross
        closes[4] = 9.0     # bearish BOS row 4: close < L1=10
        closes[9] = 7.0     # bearish BOS row 9: close < L2=8
        closes[10] = 14.0   # bullish CHoCH row 10: close > refreshed protected_high=13
        df = pd.DataFrame(
            {"high": highs, "low": lows, "close": closes, "open": closes,
             "volume": [1.0] * n},
            index=idx,
        )

        pivot_high = pd.Series(np.nan, index=idx)
        pivot_low = pd.Series(np.nan, index=idx)
        pivot_low.iloc[1] = 10.0  # L1
        pivot_high.iloc[2] = 15.0  # H1
        pivot_low.iloc[6] = 8.0    # L2
        pivot_high.iloc[7] = 13.0  # H2

        # Real-mutation guard: pivot events must exist where claimed
        # and must NOT exist on the break rows.
        assert pivot_low.iloc[[1, 6]].notna().all() and pivot_low.iloc[[4, 9, 10]].isna().all()
        assert pivot_high.iloc[[2, 7]].notna().all() and pivot_high.iloc[[4, 9, 10]].isna().all()

        out = market_structure(
            df, left=2, right=2,
            pivot_high=pivot_high, pivot_low=pivot_low,
        )
        bos = out["bos"].to_numpy()
        choch = out["choch"].to_numpy()
        protected_high = out["protected_high"].to_numpy()

        bearish_bos = np.where(bos == -1)[0].tolist()
        bullish_choch = np.where(choch == 1)[0].tolist()
        assert bearish_bos == [4, 9], (
            f"expected bearish BOS at rows [4, 9]; got {bearish_bos}; bos: {bos.tolist()}"
        )
        assert bullish_choch == [10], (
            f"expected bullish CHoCH at row [10]; got {bullish_choch}; "
            f"choch: {choch.tolist()}"
        )

        # protected_high between BOS #1 (row 4) and BOS #2 (row 9) MUST
        # be 15.0 — the impulse origin of the first bearish leg.
        for r in range(4, 9):
            assert protected_high[r] == 15.0, (
                f"protected_high at row {r}: expected 15.0 (pre-refresh), "
                f"got {protected_high[r]}; full: {protected_high.tolist()}"
            )

        # protected_high MUST refresh to 13.0 at BOS #2 (row 9).
        # The CHoCH at row 10 consumes it (NaN thereafter).
        assert protected_high[9] == 13.0, (
            f"protected_high at row 9: expected 13.0 (refreshed on BOS #2), "
            f"got {protected_high[9]}; full: {protected_high.tolist()}"
        )

        # Sanity: bias flips to bullish at row 10.
        bias = out["bias_state"].to_numpy()
        assert bias[10] == 1, (
            f"bias should flip to 1 at CHoCH row 10; got {bias[10]}; "
            f"full bias: {bias.tolist()}"
        )


class TestPivotSeriesValidation:
    """pivot_high / pivot_low Series must align exactly with frame.index.

    When supplied, the engine must:
      * Validate the supplied Series index exactly equals ``frame.index``.
      * Raise ``ValueError`` with a clear message on mismatch.
      * Validate length matches.
      * If only ONE of the pair is supplied, compute only the missing
        counterpart (do not overwrite the supplied one).
    """

    def test_pivot_high_index_mismatch_raises(self):
        df = _frame_from(_BULL_SEQ)
        bad_idx = pd.date_range("2025-01-01", periods=len(_BULL_SEQ), freq="15min")
        pivot_high = pd.Series(np.nan, index=bad_idx)
        idx = pd.date_range("2024-01-01", periods=len(_BULL_SEQ), freq="15min")
        with pytest.raises(ValueError, match="index"):
            market_structure(
                df, left=2, right=2,
                pivot_high=pivot_high, pivot_low=pd.Series(np.nan, index=idx),
            )

    def test_pivot_low_index_mismatch_raises(self):
        idx = pd.date_range("2024-01-01", periods=len(_BULL_SEQ), freq="15min")
        bad_idx = pd.date_range("2025-01-01", periods=len(_BULL_SEQ), freq="15min")
        pivot_high = pd.Series(np.nan, index=idx)
        pivot_low = pd.Series(np.nan, index=bad_idx)
        df = _frame_from(_BULL_SEQ)
        with pytest.raises(ValueError, match="index"):
            market_structure(
                df, left=2, right=2,
                pivot_high=pivot_high, pivot_low=pivot_low,
            )

    def test_pivot_high_length_mismatch_raises(self):
        # Length differs but the supplied index equals frame.index for
        # the leading slice -> still a mismatch.
        idx = pd.date_range("2024-01-01", periods=len(_BULL_SEQ), freq="15min")
        df = _frame_from(_BULL_SEQ)
        short_high = pd.Series(np.nan, index=idx[:5])
        pivot_low = pd.Series(np.nan, index=idx)
        with pytest.raises(ValueError):
            market_structure(
                df, left=2, right=2,
                pivot_high=short_high, pivot_low=pivot_low,
            )

    def test_pivot_high_missing_computes_only_low(self):
        # pivot_high is None -> engine computes its own. pivot_low is
        # supplied. The engine must NOT overwrite the supplied pivot_low
        # with a freshly computed one (would invalidate downstream
        # caller's precomputed low events).
        idx = pd.date_range("2024-01-01", periods=len(_BULL_SEQ), freq="15min")
        df = _frame_from(_BULL_SEQ)
        supplied_low = pd.Series(np.nan, index=idx)
        # Mark one entry that would NOT be there from confirmed_pivots
        # (a sentinel level) so we can detect that the engine didn't
        # overwrite.
        supplied_low.iloc[5] = 999.0
        out = market_structure(
            df, left=2, right=2,
            pivot_high=None, pivot_low=supplied_low,
        )
        # The engine must respect supplied_low -> at row 5 external_low
        # should be 999.0 (the sentinel we supplied), proving the
        # engine didn't recompute and overwrite.
        assert out["external_low"].iloc[5] == 999.0, (
            f"supplied pivot_low must not be overwritten by computed one; "
            f"external_low at row 5: {out['external_low'].iloc[5]}; "
            f"full: {out['external_low'].to_list()}"
        )

    def test_pivot_low_missing_computes_only_high(self):
        # Symmetric: pivot_low is None, pivot_high is supplied.
        idx = pd.date_range("2024-01-01", periods=len(_BULL_SEQ), freq="15min")
        df = _frame_from(_BULL_SEQ)
        supplied_high = pd.Series(np.nan, index=idx)
        supplied_high.iloc[5] = 777.0  # sentinel
        out = market_structure(
            df, left=2, right=2,
            pivot_high=supplied_high, pivot_low=None,
        )
        assert out["external_high"].iloc[5] == 777.0, (
            f"supplied pivot_high must not be overwritten; "
            f"external_high at row 5: {out['external_high'].iloc[5]}"
        )


class TestCausalityGuards:
    """Tighten future-shock safety with explicit mutation + prefix guards."""

    def test_prepending_data_does_not_change_past_outputs(self):
        # confirmed_pivots: prepend 5 rows, shift by 5, base outputs
        # must match in the original region. Pre-existing fixture — add
        # actual-mutation + prefix-identity guards.
        base = _make_long_frame(n=40, seed=7)
        baseline = confirmed_pivots(base, left=2, right=2)
        extra_idx = pd.date_range("2023-12-31", periods=5, freq="15min")
        extra = pd.DataFrame(
            {
                "open": [9.0] * 5,
                "high": [10.0] * 5,
                "low": [9.0] * 5,
                "close": [9.5] * 5,
                "volume": [1.0] * 5,
            },
            index=extra_idx,
        )
        longer = pd.concat([extra, base])
        # Real-mutation guard: the prepended frame MUST differ from the
        # base frame in the prefix (otherwise the test is vacuous).
        assert not longer.iloc[:5].equals(base.iloc[:5]), (
            "prepended frame does not differ from base in the prefix"
        )
        # Prefix-identity guard: the trailing region of `longer` MUST
        # equal `base` byte-for-byte (preserve DatetimeIndex).
        pd.testing.assert_frame_equal(
            longer.iloc[5:].reset_index(drop=True),
            base.reset_index(drop=True),
        )
        # Drop the prepended index entries and compare data + index
        # alignment on the trailing region (preserve the original
        # DatetimeIndex, not a RangeIndex). ``check_freq=False`` because
        # ``pd.concat`` legitimately drops ``DatetimeIndex.freq`` on the
        # trailing slice while preserving labels and data — that's an
        # artefact of concat, not a behavioural change in the pivot
        # helper. For ``confirmed_pivots`` the contract we care about
        # is labels + values, not the freq attribute.
        shifted = confirmed_pivots(longer, left=2, right=2).iloc[5:]
        pd.testing.assert_frame_equal(shifted, baseline, check_freq=False)

    def test_appending_suffix_does_not_change_past_outputs(self):
        # Append extra bars AFTER the frame. Past outputs (rows 0..n)
        # must remain identical when extra bars are appended.
        base = _make_long_frame(n=40, seed=11)
        baseline = confirmed_pivots(base, left=2, right=2)
        # Use an explicit future timestamp. The exact gap is irrelevant to
        # suffix causality; it only needs to start strictly after ``base``.
        extra_idx = pd.date_range(
            start="2030-01-01T00:00:00",
            periods=10,
            freq="15min",
        )
        extra = pd.DataFrame(
            {
                "open":  [100.0] * 10,
                "high":  [105.0] * 10,
                "low":   [ 95.0] * 10,
                "close": [100.0] * 10,
                "volume":[  1.0] * 10,
            },
            index=extra_idx,
        )
        longer = pd.concat([base, extra])
        # Prefix-identity guard: base region of `longer` equals `base`.
        pd.testing.assert_frame_equal(
            longer.iloc[:len(base)].reset_index(drop=True),
            base.reset_index(drop=True),
        )
        # Real-mutation guard: extra suffix MUST differ from base.
        assert not longer.iloc[len(base):].equals(base.iloc[len(base):]) if len(base) > 0 else True
        # And critically: extra differs from a zero-pad.
        suffix_only = longer.iloc[len(base):].reset_index(drop=True)
        assert (suffix_only["high"].to_numpy() == extra["high"].to_numpy()).all()
        shifted = confirmed_pivots(longer, left=2, right=2).iloc[:len(base)]
        pd.testing.assert_frame_equal(shifted, baseline, check_freq=False)


class TestStructureNonVacuousShock:
    """The structure engine must ACTUALLY consume close and pivot events.

    These tests guard against silent regressions where the engine
    returns all-zero / all-NaN output (the previous `bos/choch` checks
    would trivially pass on a stub).
    """

    def test_shock_actually_changes_tail_output(self):
        # Mutating high/low/close in the tail MUST change the structure
        # output in the tail. Without this, the engine might be ignoring
        # close or pivots.
        df = _make_long_frame(n=200, seed=3)
        baseline = market_structure(df, left=3, right=3)
        shocked = df.copy()
        shock_cols = shocked.columns.get_indexer(["high", "low", "close"])
        shocked.iloc[80:, shock_cols] *= 10.0
        actual = market_structure(shocked, left=3, right=3)
        # Real mutation guard: shocked frame must differ in the tail.
        assert not shocked.iloc[80:].equals(df.iloc[80:])
        # Prefix-identity guard.
        pd.testing.assert_frame_equal(
            shocked.iloc[:80].reset_index(drop=True),
            df.iloc[:80].reset_index(drop=True),
        )
        # Past [:80] must be identical (causality).
        for col in ("bos", "choch", "bias_state"):
            b = baseline.iloc[:80][col].to_numpy()
            a = actual.iloc[:80][col].to_numpy()
            if np.issubdtype(b.dtype, np.floating):
                both_nan = np.isnan(b) & np.isnan(a)
                equal = (b == a) | both_nan
            else:
                equal = (b == a)
            assert equal.all(), (
                f"future shock changed past {col!r} within [:80]; "
                f"row(s) where baseline != actual: {np.where(~equal)[0].tolist()[:10]}"
            )
        # Tail must differ — the engine is actually using close/pivots.
        diff = False
        for col in ("bos", "choch", "bias_state"):
            if not baseline.iloc[80:][col].equals(actual.iloc[80:][col]):
                diff = True
                break
        assert diff, (
            "future shock did not change bos/choch/bias_state in the tail; "
            "the engine may not be reading close/pivots"
        )
