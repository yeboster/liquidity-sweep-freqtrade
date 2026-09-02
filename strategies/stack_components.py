"""Causal STACK component primitives.

Pure indicator helpers that emit signals only when information becomes
available. Each helper accepts a ``pandas.DataFrame`` with columns
``high``, ``low`` (and any other context) and returns a new
``DataFrame`` whose outputs are **strictly forward-only**:

    For every row ``i``, the value at row ``i`` depends only on rows
    ``<= i``. No present value can ever change because a future value
    changes.

This module deliberately avoids third-party libraries such as
``smartmoneyconcepts``. The reference semantics live at git commit
``bb1de2d`` (``strategies/LiquiditySweep.py``); this module preserves
the delayed-confirmation idea and intentionally separates two concerns
that the legacy implementation conflated:

1. **Confirmation vs. propagation.** The legacy ``_compute_swings``
   shifts the pivot forward by ``pivot_len`` (placing it at the
   confirmation bar) and *then* ``.ffill()``s it onto every subsequent
   row. That ``.ffill`` is **causal propagation after confirmation**:
   it never writes a pivot before the right-side bars have closed, so
   it is not a future leak. It is, however, a *state-maintenance*
   decision baked into the indicator. ``confirmed_pivots`` deliberately
   returns **event-only** output — a pivot is reported at the single
   confirmation bar and never carried forward. Downstream code that
   needs the "most recent confirmed swing" can call ``.ffill()`` itself
   and decide its own reset policy. The event/output split is a design
   choice, not a leakage fix.
2. **Strict ties.** The legacy code dropped ties silently. Here, a
   pivot is emitted only if the centre bar is *strictly* greater
   (high) or *strictly* less (low) than every other bar in the
   ``left + 1 + right`` window. Tied centres produce no pivot, which
   is deterministic and avoids ambiguous "first vs last tied bar"
   choices.

The helper is intentionally side-effect free, allocation-light, and
safe to call inside Freqtrade's ``populate_indicators`` (vectorised,
no Python-level row loops).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = [
    "confirmed_pivots",
    "market_structure",
    "fair_value_gap",
    "fvg_lifecycle",
    "location",
    "liquidity_sweep",
    "sweep_to_structure",
    "structural_rr",
]

# Practical safety cap on the pivot window width
# ``left + 1 + right``. The implementation builds a dense (n, window)
# ``np.lib.stride_tricks.as_strided`` matrix; without an upper bound,
# a fat-finger call (e.g. ``left=10000``) would silently allocate
# ``n * window`` doubles and torch the process. 401 is well above any
# realistic pivot lookback in this stack (current default is 3 + 1 + 3
# = 7) and small enough that even on the largest frame we touch (a few
# hundred thousand 15m bars) the matrix stays cheap.
MAX_PIVOT_WINDOW = 401


def _require_columns(frame: pd.DataFrame, *names: str) -> None:
    missing = [n for n in names if n not in frame.columns]
    if missing:
        raise KeyError(
            f"confirmed_pivots: missing required column(s): {missing}. "
            f"Available: {list(frame.columns)}"
        )


def _validate_window(left: int, right: int) -> None:
    if not isinstance(left, int) or not isinstance(right, int):
        raise TypeError("left and right must be ints")
    if left < 1 or right < 1:
        raise ValueError(
            f"left and right must both be >= 1; got left={left}, right={right}. "
            "Use left=1 / right=1 for a 3-bar confirmation window."
        )
    window = left + 1 + right
    if window > MAX_PIVOT_WINDOW:
        raise ValueError(
            f"pivot window left + 1 + right = {window} exceeds the practical "
            f"cap of {MAX_PIVOT_WINDOW}. Larger windows build an O(n * window) "
            f"matrix and are almost certainly a bug — split the lookback into "
            f"multiple smaller confirmed_pivots calls instead."
        )


def _validate_numeric_series(series: pd.Series, name: str) -> None:
    """Reject non-numeric ``high`` / ``low`` columns up front.

    The pivot logic compares values with ``>`` / ``<`` and depends on
    NaN semantics that only hold for floating-point columns. Object /
    string columns would either blow up downstream with a confusing
    TypeError, or — worse — silently compare lexicographically and
    emit bogus pivots. Bool columns are technically "numeric" in
    pandas' typing, but are categorically wrong for a price series
    (True/False would compare fine and emit a "pivot" of 0/1). Fail
    loudly with a precise message instead of letting the silent
    nonsense through.
    """
    dtype = series.dtype
    if dtype == object or not pd.api.types.is_numeric_dtype(dtype) or dtype == bool:
        raise TypeError(
            f"confirmed_pivots: column {name!r} must be a numeric price "
            f"series (e.g. float64), got dtype {dtype!r}. Convert with "
            f"``pd.to_numeric(series, errors='coerce')`` before calling."
        )


def _validate_pivot_series(
    series: pd.Series, frame_index: pd.Index, name: str
) -> None:
    """Validate that ``series`` is a sparse event column aligned to ``frame_index``.

    The market-structure engine treats ``pivot_high`` / ``pivot_low``
    arguments as precomputed event Series: every finite entry is a
    pivot that has just been confirmed at that row. Misaligned
    indexes (length mismatch, wrong timestamps, even a leading-slice
    coincidence) silently shift every signal, so we fail loudly with
    a clear message.

    The check is exact: the supplied index must EQUAL ``frame_index``.
    Any difference — including type (RangeIndex vs DatetimeIndex) or
    length — raises ``ValueError``.
    """
    if not isinstance(series, pd.Series):
        raise TypeError(
            f"market_structure: {name!r} must be a pandas.Series, "
            f"got {type(series).__name__}"
        )
    if len(series) != len(frame_index):
        raise ValueError(
            f"market_structure: {name!r} length {len(series)} does not "
            f"match frame length {len(frame_index)}; the supplied "
            f"event Series must be aligned exactly to frame.index."
        )
    if not series.index.equals(frame_index):
        raise ValueError(
            f"market_structure: {name!r}.index does not match frame.index. "
            f"Lengths match but the labels differ (e.g. RangeIndex vs "
            f"DatetimeIndex, or shifted timestamps). Reindex with "
            f"``series.reindex(frame.index)`` before passing."
        )


def _validate_aligned_series(
    series: pd.Series, frame_index: pd.Index, name: str, caller: str
) -> None:
    """Validate that ``series`` is a ``pandas.Series`` exactly aligned to
    ``frame_index``.

    Shared by every Task 4 helper that accepts a precomputed event/level
    Series (an FVG frame, a sweep level, a leg boundary, a bos/choch
    column, ...). Mirrors :func:`_validate_pivot_series` but is written
    once, generically, and parameterised by the caller's name so error
    messages stay precise without duplicating the check six times.
    """
    if not isinstance(series, pd.Series):
        raise TypeError(
            f"{caller}: {name!r} must be a pandas.Series, "
            f"got {type(series).__name__}"
        )
    if len(series) != len(frame_index):
        raise ValueError(
            f"{caller}: {name!r} length {len(series)} does not match "
            f"frame length {len(frame_index)}; the supplied Series must "
            f"be aligned exactly to frame.index."
        )
    if not series.index.equals(frame_index):
        raise ValueError(
            f"{caller}: {name!r}.index does not match frame.index. "
            f"Lengths match but the labels differ. Reindex with "
            f"``series.reindex(frame.index)`` before calling."
        )


def _as_level_series(
    level, frame_index: pd.Index, name: str, caller: str
) -> pd.Series:
    """Coerce ``level`` (scalar or Series) into a float Series aligned to
    ``frame_index``.

    A bare scalar is broadcast to every row (a single fixed level). A
    ``pandas.Series`` must already be aligned to ``frame_index`` — this
    function never infers or recomputes the level (e.g. via a rolling
    extremum); the caller must supply it explicitly, which is the whole
    point of keeping these helpers causal and independently testable.
    """
    if isinstance(level, pd.Series):
        _validate_aligned_series(level, frame_index, name, caller)
        _validate_numeric_series(level, name)
        return level.astype(float)
    if isinstance(level, bool) or not isinstance(level, (int, float, np.integer, np.floating)):
        raise TypeError(
            f"{caller}: {name!r} must be a numeric scalar or a "
            f"pandas.Series aligned to frame.index, got {type(level).__name__}"
        )
    if not np.isfinite(level):
        raise ValueError(f"{caller}: {name!r} scalar must be finite, got {level!r}")
    return pd.Series(float(level), index=frame_index)


def _candidate_pivots(
    series: pd.Series, left: int, right: int, mode: str
) -> pd.Series:
    """Return a boolean Series where row ``i`` is ``True`` iff row ``i``
    is the **unique** extreme of the window
    ``[i - left, i + right]``.

    This mask is aligned with the candidate pivot bar, **not** the
    confirmation bar. Emission happens after a ``.shift(right)`` so
    that the level only becomes available once the right-side bars
    have been observed.
    """
    n = len(series)
    window = left + 1 + right
    if n < window:
        return pd.Series(False, index=series.index)

    arr = series.to_numpy(dtype=float, copy=False)
    if np.isnan(arr).all():
        return pd.Series(False, index=series.index)

    # Build a padded array: leading ``left`` NaNs, then the series,
    # then trailing ``right`` NaNs. The window for candidate ``c`` is
    # therefore padded_arr[c : c + window].
    pad = np.full(left, np.nan, dtype=float)
    tail = np.full(right, np.nan, dtype=float)
    padded = np.concatenate([pad, arr, tail])
    shape = (n, window)
    strides = padded.strides + (padded.strides[-1],)
    matrix = np.lib.stride_tricks.as_strided(padded, shape=shape, strides=strides)

    centre = arr

    if mode == "max":
        with np.errstate(invalid="ignore"):
            extreme = np.max(matrix, axis=1)
    elif mode == "min":
        with np.errstate(invalid="ignore"):
            extreme = np.min(matrix, axis=1)
    else:
        raise ValueError(f"mode must be 'max' or 'min'; got {mode!r}")

    # Strict-tie-break: count finite entries equal to the centre value.
    # NaN positions compare unequal, so they contribute 0.
    eq_centre = (matrix == centre[:, None])
    n_eq = np.nansum(eq_centre, axis=1).astype(int)

    # A candidate is a pivot iff:
    #   * the window is fully populated (every value in the window
    #     [i - left, i + right] is finite — not just the centre or
    #     the extreme, but every slot). This is the explicit
    #     ``np.isfinite(matrix).all(axis=1)`` check the spec asks for,
    #     and it is strictly stronger than the earlier
    #     ``np.isfinite(extreme) & np.isfinite(centre)`` because the
    #     extreme of a partially-NaN window is itself NaN, so the old
    #     expression was a proxy rather than the real requirement.
    #   * the centre equals the window extreme, AND
    #   * no other bar in the window equals the centre.
    has_full_window = np.isfinite(matrix).all(axis=1)
    return pd.Series(
        has_full_window & (extreme == centre) & (n_eq == 1),
        index=series.index,
    )


def confirmed_pivots(
    frame: pd.DataFrame,
    left: int = 3,
    right: int = 3,
) -> pd.DataFrame:
    """Detect causal pivot highs and pivot lows.

    A pivot high at row ``i`` means ``frame['high'][i]`` is strictly
    greater than every other ``high`` in the window
    ``[i - left, i + right]``. The pivot level is emitted at row
    ``i + right`` (the confirmation bar) — never at ``i``, never
    fanned forward. Until that row, the pivot column is ``NaN``.

    Ties at the centre bar produce no pivot (deterministic).

    Parameters
    ----------
    frame:
        Input OHLCV frame. Must contain ``high`` and ``low`` columns.
    left:
        Number of bars to the left of the candidate pivot that must
        have a strictly smaller (for high) or strictly greater (for
        low) value. Must be ``>= 1``.
    right:
        Number of bars to the right of the candidate pivot that must
        close (be observed) before the pivot is emitted. Must be
        ``>= 1``.

    Returns
    -------
    pd.DataFrame
        Same index as ``frame`` with two new columns:
        ``pivot_high`` (the level of a confirmed pivot high, else
        ``NaN``) and ``pivot_low`` (same for pivot lows).
    """
    _validate_window(left, right)
    _require_columns(frame, "high", "low")
    _validate_numeric_series(frame["high"], "high")
    _validate_numeric_series(frame["low"], "low")

    is_high = _candidate_pivots(frame["high"], left, right, mode="max")
    is_low = _candidate_pivots(frame["low"], left, right, mode="min")

    # Emit at the confirmation bar (centre + right). No backfill, no
    # ffill: each row carries at most one confirmed pivot value.
    pivot_high = frame["high"].where(is_high).shift(right)
    pivot_low = frame["low"].where(is_low).shift(right)

    return pd.DataFrame(
        {"pivot_high": pivot_high, "pivot_low": pivot_low},
        index=frame.index,
    )


def market_structure(
    frame: pd.DataFrame,
    *,
    left: int = 3,
    right: int = 3,
    pivot_high: pd.Series | None = None,
    pivot_low: pd.Series | None = None,
) -> pd.DataFrame:
    """Causal BOS/CHoCH structure engine over confirmed pivot events.

    Consumes a frame containing ``high``, ``low`` and ``close`` columns
    (plus optional ``pivot_high`` / ``pivot_low`` event columns from
    :func:`confirmed_pivots`) and returns a state machine summary:

    ==================  ==========================================
    external_high       most recent confirmed pivot high (state)
    external_low        most recent confirmed pivot low  (state)
    protected_high      impulse-origin swing high (state)
    protected_low       impulse-origin swing low  (state)
    bos                 +1 bullish BOS, -1 bearish BOS, else 0
    choch               +1 bullish CHoCH, -1 bearish CHoCH, else 0
    bias_state          +1 bullish, -1 bearish, NaN until first event
    ==================  ==========================================

    Design notes
    ------------

    * **Causal.** Every value at row ``i`` depends only on rows
      ``<= i``. Shocking future rows never changes past outputs.
    * **Close-based.** Only the candle *body close* crosses a level;
      wick excursions through ``high`` / ``low`` do not fire signals.
    * **Equal close = no cross.** A candle that closes exactly on the
      level is treated as a touch, not a break, so signals do not spam
      on every re-touch.
    * **No-repeat.** A given external level, once consumed by a BOS,
      does not re-fire on subsequent candles until a *new* pivot
      strictly beyond it has been confirmed.
    * **Same-candle non-break.** A pivot confirmed at row ``i`` is
      emitted into ``external_high`` / ``external_low`` on row ``i``
      (visible in state columns) but is NOT eligible to be CROSSED on
      row ``i``. Cross evaluation runs against the structure state
      carried from row ``i - 1``; the row ``i`` pivot is committed to
      state for row ``i + 1`` onward.
    * **Protected-swing refresh.** Every continuation BOS refreshes the
      *opposite-side* protected swing to the most recent confirmed
      opposite-side pivot that existed BEFORE the BOS candle. The
      protected level is the impulse origin of the new displacement.
    * **Event vs state.** ``bos`` and ``choch`` are sparse event
      columns (``0`` everywhere except the break candle); the other
      columns are forward-running state.
    * **O(n) forward loop.** State is tracked incrementally: a single
      ``for i in range(n)`` pass with running ``last_external_high`` /
      ``last_external_low`` / ``last_known_pivot_high`` / ``last_known_pivot_low``
      variables. No ``pl_arr[:i + 1]`` scans.
    * **NaN handling.** A ``close`` of NaN never fires any signal and
      does not update external/protected levels.

    Parameters
    ----------
    frame:
        OHLC frame. Must contain ``high``, ``low``, ``close`` columns.
        May also already contain ``pivot_high`` / ``pivot_low`` event
        columns (e.g. from :func:`confirmed_pivots`); if absent, the
        engine runs its own pivot detection with the given ``left`` /
        ``right`` window.
    left, right:
        Pivot window width. Passed through to
        :func:`confirmed_pivots` when pivot columns are not supplied.
    pivot_high, pivot_low:
        Optional precomputed confirmed pivot event columns. Must be
        sparse series aligned to ``frame.index`` with NaN everywhere
        except the confirmation bar. The supplied Series must have an
        index that EQUALS ``frame.index`` and a matching length;
        mismatches raise ``ValueError``. When only one of the pair is
        supplied, the missing counterpart is computed via
        :func:`confirmed_pivots`; the supplied one is preserved as-is
        (not overwritten).

    Returns
    -------
    pd.DataFrame
        Same index as ``frame`` with the seven structure columns
        described above.
    """
    _require_columns(frame, "high", "low", "close")
    _validate_numeric_series(frame["high"], "high")
    _validate_numeric_series(frame["low"], "low")
    _validate_numeric_series(frame["close"], "close")

    frame_index = frame.index
    n = len(frame)
    if n == 0:
        # Empty frame: every state column is NaN; every event column
        # is empty. The bias_state sentinel must be translated to NaN
        # for the public API.
        empty = pd.DataFrame(
            {
                "external_high": np.array([], dtype=float),
                "external_low": np.array([], dtype=float),
                "protected_high": np.array([], dtype=float),
                "protected_low": np.array([], dtype=float),
                "bos": np.array([], dtype=np.int64),
                "choch": np.array([], dtype=np.int64),
                "bias_state": np.array([], dtype=np.float64),
            },
            index=frame_index,
        )
        return empty

    if pivot_high is not None:
        _validate_pivot_series(pivot_high, frame_index, "pivot_high")
    if pivot_low is not None:
        _validate_pivot_series(pivot_low, frame_index, "pivot_low")

    if pivot_high is None or pivot_low is None:
        _validate_window(left, right)
        events = confirmed_pivots(frame, left=left, right=right)
        if pivot_high is None:
            pivot_high = events["pivot_high"]
        if pivot_low is None:
            pivot_low = events["pivot_low"]
    else:
        # Reuse the provided event columns. Re-validate window
        # parameters only if the caller didn't pre-supply events.
        _validate_window(left, right)

    index = frame_index
    high_arr = frame["high"].to_numpy(dtype=float)
    low_arr = frame["low"].to_numpy(dtype=float)
    close_arr = frame["close"].to_numpy(dtype=float)
    ph_arr = pivot_high.to_numpy(dtype=float)
    pl_arr = pivot_low.to_numpy(dtype=float)

    # Output arrays — float for level columns (NaN-cleanable), int for
    # the event/bias columns (sparse, never NaN except bias_state).
    external_high = np.full(n, np.nan, dtype=float)
    external_low = np.full(n, np.nan, dtype=float)
    protected_high = np.full(n, np.nan, dtype=float)
    protected_low = np.full(n, np.nan, dtype=float)
    bos = np.zeros(n, dtype=np.int64)
    choch = np.zeros(n, dtype=np.int64)
    # bias_state uses a sentinel (-128) so we can keep ``np.nan`` for
    # the head (pre-event) and still pack the array as int64.
    BIAS_UNDEFINED = -128
    bias = np.full(n, BIAS_UNDEFINED, dtype=np.int64)

    # State carried forward.
    last_external_high: float | None = None  # last confirmed pivot high
    last_external_low: float | None = None   # last confirmed pivot low
    last_bos_high: float | None = None  # last external_high consumed by bullish BOS
    last_bos_low: float | None = None   # last external_low consumed by bearish BOS
    protected_high_level: float | None = None  # impulse-origin swing high
    protected_low_level: float | None = None   # impulse-origin swing low
    current_bias = BIAS_UNDEFINED  # -1 / +1 / BIAS_UNDEFINED
    # Incremental trackers for the most recent confirmed pivot HIGH/LOW
    # (used to refresh protected swings on every continuation BOS).
    # These track pivots committed on previous rows only — they are
    # updated AFTER cross evaluation, so a pivot emitted on row ``i``
    # does not become the BOS origin on the same row.
    last_known_pivot_high: float | None = None
    last_known_pivot_low: float | None = None

    def _strictly_above(close: float, level: float) -> bool:
        return not np.isnan(close) and not np.isnan(level) and close > level

    def _strictly_below(close: float, level: float) -> bool:
        return not np.isnan(close) and not np.isnan(level) and close < level

    for i in range(n):
        ph = ph_arr[i]
        pl = pl_arr[i]
        c = close_arr[i]

        # --- 1. Output the CURRENT external state (carried from prior
        # iterations plus this row's newly confirmed pivot for display).
        # The state USED for cross evaluation on this row is
        # ``last_external_high`` / ``last_external_low`` as they were
        # BEFORE this row — i.e. state from the prior iteration. The
        # pivot emitted on this row is reported in external_* on this
        # row but is NOT eligible to be crossable here; it becomes
        # eligible starting on the next row.
        if not np.isnan(ph):
            # Newly confirmed pivot high: output its level on this row,
            # but do NOT update ``last_external_high`` until AFTER cross
            # evaluation.
            external_high[i] = float(ph)
        else:
            external_high[i] = last_external_high if last_external_high is not None else np.nan

        if not np.isnan(pl):
            external_low[i] = float(pl)
        else:
            external_low[i] = last_external_low if last_external_low is not None else np.nan

        # --- 2. Cross evaluation against PRIOR-iteration state.
        # ``last_external_high`` / ``last_external_low`` here do NOT yet
        # include the pivot confirmed on row ``i`` (that commit happens
        # below in step 4). So a freshly-confirmed pivot on row ``i``
        # cannot be broken by row ``i``'s close.
        fired_bullish_bos = False
        fired_bearish_bos = False
        fired_bullish_choch = False
        fired_bearish_choch = False

        # --- CHoCH candidates (priority over BOS once bias exists) ---
        if current_bias == 1 and protected_low_level is not None and _strictly_below(c, protected_low_level):
            fired_bearish_choch = True
            current_bias = -1
            # Consume the protected level so it does not re-fire.
            protected_low_level = None
            # The external_low bookkeeping (last_bos_low) is left as
            # is; if external_low has not been refreshed, a new
            # bearish BOS would require a NEW pivot low to fire.
        elif current_bias == -1 and protected_high_level is not None and _strictly_above(c, protected_high_level):
            fired_bullish_choch = True
            current_bias = 1
            protected_high_level = None

        # --- BOS candidates (only when no CHoCH fired this candle) ---
        if not fired_bullish_choch and not fired_bearish_choch:
            # Bullish BOS: close strictly above an external_high that
            # has NOT yet been consumed by a bullish BOS.  A new
            # pivot high strictly higher than last_bos_high refreshes
            # the external level, allowing the next close above it to
            # re-fire.
            bull_eligible = (
                last_external_high is not None
                and (last_bos_high is None or last_external_high > last_bos_high)
                and _strictly_above(c, last_external_high)
            )
            if bull_eligible:
                fired_bullish_bos = True
                last_bos_high = last_external_high
                # Refresh protected_low to the most recent confirmed
                # pivot low that existed BEFORE this BOS candle (the
                # impulse origin of this new bullish leg). Using
                # ``last_known_pivot_low`` (incremental tracker, O(1))
                # means a pivot low confirmed on the SAME row cannot
                # become the BOS origin — same-row non-break semantics.
                protected_low_level = last_known_pivot_low
                current_bias = 1

            # Bearish BOS — symmetric.
            bear_eligible = (
                last_external_low is not None
                and (last_bos_low is None or last_external_low < last_bos_low)
                and _strictly_below(c, last_external_low)
            )
            if bear_eligible:
                fired_bearish_bos = True
                last_bos_low = last_external_low
                protected_high_level = last_known_pivot_high
                current_bias = -1

        bos[i] = 1 if fired_bullish_bos else (-1 if fired_bearish_bos else 0)
        choch[i] = 1 if fired_bullish_choch else (-1 if fired_bearish_choch else 0)
        bias[i] = current_bias

        protected_high[i] = protected_high_level if protected_high_level is not None else np.nan
        protected_low[i] = protected_low_level if protected_low_level is not None else np.nan

        # --- 4. Commit this row's pivot events to state for the NEXT
        # row's cross evaluation. Order matters: the new external level
        # (and the running pivot trackers used for the next protected-
        # swing refresh) update AFTER cross evaluation so that
        # pivot-on-row-``i`` cannot be broken by row ``i``'s close.
        if not np.isnan(ph):
            last_external_high = float(ph)
            last_known_pivot_high = float(ph)
        if not np.isnan(pl):
            last_external_low = float(pl)
            last_known_pivot_low = float(pl)

    out = pd.DataFrame(
        {
            "external_high": external_high,
            "external_low": external_low,
            "protected_high": protected_high,
            "protected_low": protected_low,
            "bos": bos,
            "choch": choch,
            "bias_state": bias,
        },
        index=index,
    )
    # Translate the BIAS_UNDEFINED sentinel to NaN for the public API.
    out["bias_state"] = out["bias_state"].replace(BIAS_UNDEFINED, np.nan)
    # Cast bias_state to float so empty / all-NaN columns are float NaN
    # rather than the int sentinel type.
    out["bias_state"] = out["bias_state"].astype(float)
    return out


# =============================================================================
# Task 4: independently observable setup components
# =============================================================================
#
# Every helper below is a *pure*, causal function: row ``i`` of the output
# depends only on rows ``<= i`` of the input. None of them conjoin into a
# trade signal — that composition belongs to the strategy layer (Task 5).
# Several of them deliberately accept an already-known level/leg/event
# Series (a confirmed pivot, a protected swing, a prior sweep) rather than
# recomputing a rolling extremum internally, so that the causal boundary
# lives in one place (``market_structure`` / ``confirmed_pivots``) and is
# not silently re-derived — and potentially re-broken — downstream.


def fair_value_gap(frame: pd.DataFrame) -> pd.DataFrame:
    """Three-candle Fair Value Gap (FVG) event.

    A bullish FVG is confirmed on candle ``i`` (the third candle of the
    pattern) when ``frame['low'][i] > frame['high'][i - 2]``: candle
    ``i - 1``'s body never traded into the range
    ``[high[i - 2], low[i]]``, leaving an untraded imbalance. A bearish
    FVG is confirmed when ``frame['high'][i] < frame['low'][i - 2]``,
    leaving the range ``[high[i], low[i - 2]]`` untraded.

    The event is emitted strictly on the third candle: row ``i`` uses
    only rows ``i - 2 .. i``, so no future data is ever read and no
    earlier row is ever backfilled. Equality (``low[i] == high[i - 2]``
    or ``high[i] == low[i - 2]``) is a touch, not a gap, and does not
    fire — this is the same strict, deterministic tie convention used
    by :func:`confirmed_pivots` and :func:`market_structure`.

    Parameters
    ----------
    frame:
        Input OHLC frame. Must contain ``high`` and ``low`` columns.

    Returns
    -------
    pd.DataFrame
        Same index as ``frame`` with four columns:

        ``fvg_bullish`` / ``fvg_bearish``
            Boolean event columns, ``True`` only on the confirming
            (third) candle.
        ``fvg_top`` / ``fvg_bottom``
            The gap's zone boundaries, populated only on event rows
            (``NaN`` elsewhere). For a bullish gap, ``top = low[i]``
            and ``bottom = high[i - 2]``. For a bearish gap,
            ``top = low[i - 2]`` and ``bottom = high[i]``. In both
            cases ``top > bottom`` by construction.
    """
    _require_columns(frame, "high", "low")
    _validate_numeric_series(frame["high"], "high")
    _validate_numeric_series(frame["low"], "low")

    high = frame["high"]
    low = frame["low"]
    prior_high = high.shift(2)
    prior_low = low.shift(2)

    # NaN comparisons (head-of-frame, or NaN OHLC) evaluate to False
    # under pandas/NumPy semantics, so no explicit NaN masking is
    # needed here: a NaN prior_high/prior_low simply cannot confirm a
    # gap.
    bullish = (low > prior_high).fillna(False)
    bearish = (high < prior_low).fillna(False)

    fvg_top = pd.Series(np.nan, index=frame.index, dtype=float)
    fvg_bottom = pd.Series(np.nan, index=frame.index, dtype=float)
    fvg_top[bullish] = low[bullish]
    fvg_bottom[bullish] = prior_high[bullish]
    fvg_top[bearish] = prior_low[bearish]
    fvg_bottom[bearish] = high[bearish]

    return pd.DataFrame(
        {
            "fvg_bullish": bullish,
            "fvg_bearish": bearish,
            "fvg_top": fvg_top,
            "fvg_bottom": fvg_bottom,
        },
        index=frame.index,
    )


def fvg_lifecycle(frame: pd.DataFrame, fvg: pd.DataFrame) -> pd.DataFrame:
    """One-time FVG mitigation lifecycle, using only current/past prices.

    Tracks, independently per side, the single most recently confirmed
    *unexpired* gap — "latest active gap per side" — and its
    active / tapped / consumed state as price is observed candle by
    candle. This is a deliberate simplification: if a new gap on the
    same side is confirmed while the previous one is still
    active/tapped, the new gap silently replaces it as the tracked
    gap (the old one is simply no longer watched). A production system
    that must track many simultaneously open gaps per side would need
    a list-based variant of this state machine; this helper trades
    that completeness for a small, auditable, O(n) state machine that
    matches the "latest gap" behaviour most SMC indicators use.

    States (per side): ``0`` no gap tracked, ``1`` active (untouched),
    ``2`` tapped (price wicked into the zone but has not fully traded
    through it), ``3`` consumed (price traded all the way through the
    zone — mitigated, locked, never re-activates).

    Deterministic same-row / new-gap ordering
    ------------------------------------------
    On every row, price-action state transitions for the *currently
    tracked* gap are evaluated first, using that row's high/low
    against the *old* gap's boundaries. Only after that does a new
    gap confirmed on this row (from ``fvg``) replace the tracked gap.
    This ordering matters: a bullish gap's ``top`` is by construction
    equal to that same row's ``low`` (``top = low[i]``), so if the new
    gap were evaluated against its own creation row's price it would
    trivially "tap" itself the instant it is born. Evaluating the OLD
    gap first, then replacing, avoids that self-tap and keeps the
    lifecycle causal (only current/past prices are used — no future
    row is ever read to decide the state of a gap opened at or before
    it).

    A gap that both tap- and fully-consumes on the very same
    subsequent candle (a large wick that trades clean through the
    zone) fires both ``*_tap_event`` and ``*_consumed_event`` on that
    row — the tap is a real, if instantaneous, precursor to the fill.

    Parameters
    ----------
    frame:
        OHLC frame. Must contain ``high`` and ``low`` columns.
    fvg:
        Output of :func:`fair_value_gap`, or any frame with the same
        four columns (``fvg_bullish``, ``fvg_bearish``, ``fvg_top``,
        ``fvg_bottom``) aligned exactly to ``frame.index``.

    Returns
    -------
    pd.DataFrame
        Same index as ``frame`` with, per side (``bullish`` /
        ``bearish``):

        ``{side}_fvg_state``
            Int state code (0/1/2/3) described above.
        ``{side}_fvg_top`` / ``{side}_fvg_bottom``
            The currently tracked gap's zone boundaries (``NaN`` when
            state is ``0``).
        ``{side}_fvg_unmitigated``
            Convenience boolean: ``True`` iff state is ``1`` or ``2``
            (a gap is tracked and not yet fully consumed).
        ``{side}_fvg_new_event`` / ``{side}_fvg_tap_event`` /
        ``{side}_fvg_consumed_event``
            Sparse boolean event columns, one-shot per transition.
    """
    _require_columns(frame, "high", "low")
    _validate_numeric_series(frame["high"], "high")
    _validate_numeric_series(frame["low"], "low")

    required_fvg_cols = ("fvg_bullish", "fvg_bearish", "fvg_top", "fvg_bottom")
    missing = [c for c in required_fvg_cols if c not in fvg.columns]
    if missing:
        raise KeyError(
            f"fvg_lifecycle: fvg frame missing required column(s): {missing}. "
            f"Pass the output of fair_value_gap()."
        )
    for col in required_fvg_cols:
        _validate_aligned_series(fvg[col], frame.index, col, "fvg_lifecycle")
    for col in ("fvg_bullish", "fvg_bearish"):
        if fvg[col].dtype != bool:
            raise TypeError(
                f"fvg_lifecycle: {col!r} must be a boolean Series, "
                f"got dtype {fvg[col].dtype!r}"
            )
    for col in ("fvg_top", "fvg_bottom"):
        _validate_numeric_series(fvg[col], col)
    event = fvg["fvg_bullish"] | fvg["fvg_bearish"]
    finite_zone = np.isfinite(fvg["fvg_top"]) & np.isfinite(fvg["fvg_bottom"])
    invalid_zone = event & (
        ~finite_zone
        | (fvg["fvg_top"] <= fvg["fvg_bottom"])
    )
    if bool(invalid_zone.any()):
        bad = frame.index[invalid_zone][0]
        raise ValueError(
            "fvg_lifecycle: event rows require finite zone bounds with "
            f"fvg_top > fvg_bottom; violated at index {bad!r}"
        )
    if bool((fvg["fvg_bullish"] & fvg["fvg_bearish"]).any()):
        raise ValueError("fvg_lifecycle: a row cannot open both FVG sides")

    index = frame.index
    n = len(frame)
    high_arr = frame["high"].to_numpy(dtype=float)
    low_arr = frame["low"].to_numpy(dtype=float)
    new_bull_arr = fvg["fvg_bullish"].to_numpy(dtype=bool)
    new_bear_arr = fvg["fvg_bearish"].to_numpy(dtype=bool)
    new_bull_top = fvg["fvg_top"].to_numpy(dtype=float)
    new_bull_bottom = fvg["fvg_bottom"].to_numpy(dtype=float)
    new_bear_top = fvg["fvg_top"].to_numpy(dtype=float)
    new_bear_bottom = fvg["fvg_bottom"].to_numpy(dtype=float)

    out = {
        "bullish_fvg_state": np.zeros(n, dtype=np.int64),
        "bullish_fvg_top": np.full(n, np.nan, dtype=float),
        "bullish_fvg_bottom": np.full(n, np.nan, dtype=float),
        "bullish_fvg_new_event": np.zeros(n, dtype=bool),
        "bullish_fvg_tap_event": np.zeros(n, dtype=bool),
        "bullish_fvg_consumed_event": np.zeros(n, dtype=bool),
        "bearish_fvg_state": np.zeros(n, dtype=np.int64),
        "bearish_fvg_top": np.full(n, np.nan, dtype=float),
        "bearish_fvg_bottom": np.full(n, np.nan, dtype=float),
        "bearish_fvg_new_event": np.zeros(n, dtype=bool),
        "bearish_fvg_tap_event": np.zeros(n, dtype=bool),
        "bearish_fvg_consumed_event": np.zeros(n, dtype=bool),
    }

    bull_state = 0
    bull_top = np.nan
    bull_bottom = np.nan
    bear_state = 0
    bear_top = np.nan
    bear_bottom = np.nan

    for i in range(n):
        lo = low_arr[i]
        hi = high_arr[i]

        # --- bullish side: price approaches the gap from above -------
        tap_evt = False
        consumed_evt = False
        if bull_state in (1, 2) and not np.isnan(lo):
            if lo <= bull_bottom:
                tap_evt = bull_state == 1
                consumed_evt = True
                bull_state = 3
            elif lo <= bull_top:
                tap_evt = bull_state == 1
                bull_state = 2
        new_evt = False
        if new_bull_arr[i]:
            bull_top = new_bull_top[i]
            bull_bottom = new_bull_bottom[i]
            bull_state = 1
            new_evt = True
        out["bullish_fvg_state"][i] = bull_state
        out["bullish_fvg_top"][i] = bull_top
        out["bullish_fvg_bottom"][i] = bull_bottom
        out["bullish_fvg_new_event"][i] = new_evt
        out["bullish_fvg_tap_event"][i] = tap_evt
        out["bullish_fvg_consumed_event"][i] = consumed_evt

        # --- bearish side: price approaches the gap from below -------
        tap_evt = False
        consumed_evt = False
        if bear_state in (1, 2) and not np.isnan(hi):
            if hi >= bear_top:
                tap_evt = bear_state == 1
                consumed_evt = True
                bear_state = 3
            elif hi >= bear_bottom:
                tap_evt = bear_state == 1
                bear_state = 2
        new_evt = False
        if new_bear_arr[i]:
            bear_top = new_bear_top[i]
            bear_bottom = new_bear_bottom[i]
            bear_state = 1
            new_evt = True
        out["bearish_fvg_state"][i] = bear_state
        out["bearish_fvg_top"][i] = bear_top
        out["bearish_fvg_bottom"][i] = bear_bottom
        out["bearish_fvg_new_event"][i] = new_evt
        out["bearish_fvg_tap_event"][i] = tap_evt
        out["bearish_fvg_consumed_event"][i] = consumed_evt

    result = pd.DataFrame(out, index=index)
    result["bullish_fvg_unmitigated"] = result["bullish_fvg_state"].isin([1, 2])
    result["bearish_fvg_unmitigated"] = result["bearish_fvg_state"].isin([1, 2])
    return result


_VALID_LOCATION_SIDES = ("long", "short")


def location(
    frame: pd.DataFrame,
    leg_low,
    leg_high,
    side: str,
    *,
    ote_lower: float = 0.62,
    ote_upper: float = 0.79,
    price_col: str = "close",
) -> pd.DataFrame:
    """Premium/discount location and OTE (optimal-trade-entry) metrics
    for a *known* displacement leg.

    This helper never infers a leg from rolling extrema — ``leg_low``
    and ``leg_high`` must be supplied explicitly, either as fixed
    scalars (a single known displacement) or as a ``pandas.Series``
    aligned to ``frame.index`` (e.g. ``protected_low`` /
    ``protected_high`` from :func:`market_structure`, so the leg can
    legitimately evolve candle by candle). Keeping leg discovery out of
    this function means the causal boundary for "when did we learn
    this leg" lives in exactly one place upstream.

    Parameters
    ----------
    frame:
        Must contain ``price_col`` (default ``"close"``).
    leg_low, leg_high:
        The displacement leg boundaries. Scalar or Series. Wherever
        both are finite, ``leg_high`` must be strictly greater than
        ``leg_low`` — an inverted or zero-width leg raises
        ``ValueError`` (a degenerate leg is a caller bug, not a
        situation to silently paper over with NaN). Rows where either
        boundary is ``NaN`` are allowed and simply produce ``NaN``
        outputs (the leg is not known yet).
    side:
        ``"long"``: the leg is a bullish (low -> high) displacement;
        retracement is measured as the fraction price has pulled back
        from ``leg_high`` toward ``leg_low``.
        ``"short"``: the leg is a bearish (high -> low) displacement;
        retracement is measured as the fraction price has pulled back
        from ``leg_low`` toward ``leg_high``.
    ote_lower, ote_upper:
        OTE retracement band, inclusive on both ends. Must satisfy
        ``0 <= ote_lower < ote_upper <= 1``.
    price_col:
        Column of ``frame`` used as the observed price. Defaults to
        ``"close"``.

    Returns
    -------
    pd.DataFrame
        Same index as ``frame`` with:

        ``retracement``
            Fraction (can exceed ``[0, 1]`` if price trades beyond the
            leg) of how far price has retraced into the leg, per
            ``side``'s convention above. ``NaN`` where undefined.
        ``premium`` / ``discount``
            Boolean: price strictly above / below the leg midpoint.
            Both ``False`` on an exact midpoint touch or when
            undefined (deterministic — no signal on a tie).
        ``ote``
            Boolean: ``ote_lower <= retracement <= ote_upper``.
    """
    if side not in _VALID_LOCATION_SIDES:
        raise ValueError(
            f"location: side must be one of {_VALID_LOCATION_SIDES}, got {side!r}"
        )
    if not all(np.isfinite(value) for value in (ote_lower, ote_upper)) or not (
        0 <= ote_lower < ote_upper <= 1
    ):
        raise ValueError(
            f"location: require 0 <= ote_lower < ote_upper <= 1; "
            f"got ote_lower={ote_lower}, ote_upper={ote_upper}"
        )
    _require_columns(frame, price_col)
    _validate_numeric_series(frame[price_col], price_col)

    leg_low_s = _as_level_series(leg_low, frame.index, "leg_low", "location")
    leg_high_s = _as_level_series(leg_high, frame.index, "leg_high", "location")

    both_finite = leg_low_s.notna() & leg_high_s.notna()
    if bool((both_finite & (leg_high_s <= leg_low_s)).any()):
        bad = frame.index[both_finite & (leg_high_s <= leg_low_s)][0]
        raise ValueError(
            f"location: leg_high must be strictly greater than leg_low "
            f"wherever both are known; violated at index {bad!r} "
            f"(leg_low={leg_low_s.loc[bad]}, leg_high={leg_high_s.loc[bad]})"
        )

    price = frame[price_col].astype(float)
    rng = leg_high_s - leg_low_s
    with np.errstate(invalid="ignore", divide="ignore"):
        if side == "long":
            retracement = (leg_high_s - price) / rng
        else:
            retracement = (price - leg_low_s) / rng

    midpoint = (leg_high_s + leg_low_s) / 2.0
    premium = (price > midpoint).fillna(False) & both_finite
    discount = (price < midpoint).fillna(False) & both_finite
    ote = ((retracement >= ote_lower) & (retracement <= ote_upper)).fillna(False)

    return pd.DataFrame(
        {
            "retracement": retracement,
            "premium": premium,
            "discount": discount,
            "ote": ote,
        },
        index=frame.index,
    )


_VALID_SWEEP_SIDES = ("high", "low")


def liquidity_sweep(frame: pd.DataFrame, level, side: str) -> pd.DataFrame:
    """Liquidity sweep: a wick trades across a previously known level
    and the candle closes back inside.

    ``side="high"``: a buy-side liquidity sweep. Fires when
    ``high[i] > level[i]`` (the wick trades strictly beyond the level)
    AND ``close[i] < level[i]`` (the candle closes back strictly
    below it). This is the classic "stop hunt above a swing high,
    then reject" setup.

    ``side="low"``: the symmetric sell-side sweep. Fires when
    ``low[i] < level[i]`` AND ``close[i] > level[i]``.

    Equality is deterministic and never counts as a sweep on either
    side of the comparison: a wick that only *touches* the level
    (``high == level``) is not a breach, and a close that lands
    exactly *on* the level (``close == level``) is not "back inside"
    — it's a touch, matching the strict-cross convention used
    throughout this module (:func:`market_structure`'s "equal close =
    no cross").

    ``level`` is a previously known level — a confirmed pivot, an
    ``external_high`` / ``external_low`` from :func:`market_structure`,
    or any other externally supplied value. This helper never computes
    a rolling extremum itself; it only tests whether price swept a
    level the caller already knows about. ``level`` may be a fixed
    scalar or a ``pandas.Series`` aligned to ``frame.index`` (so the
    watched level can legitimately change over time). Scalar levels are
    fixed and therefore already known. Series levels are shifted by one
    row internally: a level first emitted at candle ``i`` may only be
    swept from candle ``i + 1`` onward. This prevents a confirmation
    candle from sweeping a level that did not exist before its close.
    A ``NaN`` level
    on a given row means "no known level yet" and can never produce a
    sweep on that row.

    Parameters
    ----------
    frame:
        Must contain ``high``, ``low``, ``close``.
    level:
        Scalar or aligned Series — the level being watched.
    side:
        ``"high"`` or ``"low"``.

    Returns
    -------
    pd.DataFrame
        Same index as ``frame`` with:

        ``sweep_event``
            Boolean, ``True`` on the candle the sweep fires.
        ``sweep_level``
            The level value on event rows (``NaN`` elsewhere) — a
            frozen record of exactly what was swept, useful as a
            downstream stop/reference level.
    """
    if side not in _VALID_SWEEP_SIDES:
        raise ValueError(
            f"liquidity_sweep: side must be one of {_VALID_SWEEP_SIDES}, got {side!r}"
        )
    _require_columns(frame, "high", "low", "close")
    _validate_numeric_series(frame["high"], "high")
    _validate_numeric_series(frame["low"], "low")
    _validate_numeric_series(frame["close"], "close")

    level_s = _as_level_series(level, frame.index, "level", "liquidity_sweep")
    if isinstance(level, pd.Series):
        level_s = level_s.shift(1)

    high = frame["high"]
    low = frame["low"]
    close = frame["close"]

    if side == "high":
        event = ((high > level_s) & (close < level_s)).fillna(False)
    else:
        event = ((low < level_s) & (close > level_s)).fillna(False)

    sweep_level = pd.Series(np.nan, index=frame.index, dtype=float)
    sweep_level[event] = level_s[event]

    return pd.DataFrame(
        {"sweep_event": event, "sweep_level": sweep_level},
        index=frame.index,
    )


def sweep_to_structure(
    sweep_high: pd.Series,
    sweep_low: pd.Series,
    bos: pd.Series,
    choch: pd.Series,
    max_bars: int,
) -> pd.DataFrame:
    """Bounded sweep -> structure-confirmation sequence.

    A sweep of a high level (``sweep_high``, e.g. from
    :func:`liquidity_sweep` with ``side="high"``) is a bearish setup:
    it is "confirmed" if a bearish BOS or CHoCH (``bos == -1`` or
    ``choch == -1``) fires within the ``max_bars`` bars *following*
    the sweep. Symmetrically, a sweep of a low level is a bullish
    setup confirmed by a bullish BOS/CHoCH (``== 1``).

    Only current/past rows are ever consulted — there is no scan
    forward to "look for" a confirmation. Instead, on every sweep the
    helper opens a bounded pending window (a deadline
    ``sweep_row + max_bars``) and, on each subsequent row as it is
    processed, checks whether *that row's* bos/choch matches. This is
    forward iteration, not lookahead: the confirmation is recognised
    exactly when it happens, never earlier.

    Same-row ordering: the sweep candle's own bos/choch never confirms
    its own sweep — "subsequently processed bars" excludes the sweep
    row itself. On any row, a pre-existing pending window is checked
    against that row's bos/choch *before* a brand-new sweep on that
    same row opens its own (fresh) pending window.

    Only the most recently opened pending window per direction is
    tracked (a new sweep on the same side replaces an unresolved
    pending window, matching the "latest gap" simplification of
    :func:`fvg_lifecycle`).

    A pending window resolves exactly once: either it is confirmed (a
    match occurs on some row within the window, inclusive of the
    deadline row) or it expires (the deadline row passes with no
    match). Confirmation takes priority over expiry when both would
    apply on the deadline row itself.

    Parameters
    ----------
    sweep_high, sweep_low:
        Boolean event Series (e.g. ``liquidity_sweep(...)["sweep_event"]``
        for ``side="high"`` / ``side="low"`` respectively), aligned to a
        common index.
    bos, choch:
        Integer event Series with values in ``{-1, 0, 1}`` (e.g. from
        :func:`market_structure`), aligned to the same index.
    max_bars:
        Number of bars, strictly after the sweep bar, in which a
        matching confirmation is accepted. Must be an ``int >= 1``.

    Returns
    -------
    pd.DataFrame
        Same index as the inputs with:

        ``sweep_confirmed``
            Event column: ``+1`` on the row a bullish confirmation
            resolves a pending low-sweep, ``-1`` for a bearish
            confirmation of a pending high-sweep, ``0`` otherwise.
        ``sweep_expired``
            Event column: ``+1`` when a pending bullish (low-sweep)
            window expires unconfirmed, ``-1`` for a pending bearish
            (high-sweep) window, ``0`` otherwise.
        ``sweep_pending_bullish`` / ``sweep_pending_bearish``
            Independent boolean state for each pending direction. Both
            can be true when the market swept both sides before either
            sequence resolved.
        ``sweep_pending``
            State column: ``+1`` while a bullish confirmation is
            outstanding, ``-1`` while a bearish confirmation is
            outstanding, ``0`` when nothing is pending.
    """
    if not isinstance(max_bars, (int, np.integer)) or isinstance(max_bars, bool):
        raise TypeError(f"sweep_to_structure: max_bars must be an int, got {type(max_bars).__name__}")
    if max_bars < 1:
        raise ValueError(f"sweep_to_structure: max_bars must be >= 1, got {max_bars}")

    index = sweep_high.index
    for series, name in (
        (sweep_high, "sweep_high"),
        (sweep_low, "sweep_low"),
        (bos, "bos"),
        (choch, "choch"),
    ):
        _validate_aligned_series(series, index, name, "sweep_to_structure")

    for series, name in ((sweep_high, "sweep_high"), (sweep_low, "sweep_low")):
        if series.dtype != bool:
            raise TypeError(
                f"sweep_to_structure: {name!r} must be a boolean Series, "
                f"got dtype {series.dtype!r}"
            )

    for series, name in ((bos, "bos"), (choch, "choch")):
        if not pd.api.types.is_integer_dtype(series.dtype):
            raise TypeError(
                f"sweep_to_structure: {name!r} must be an integer Series "
                f"with values in {{-1, 0, 1}}, got dtype {series.dtype!r}"
            )
        bad_values = set(series.unique().tolist()) - {-1, 0, 1}
        if bad_values:
            raise ValueError(
                f"sweep_to_structure: {name!r} must only contain values "
                f"in {{-1, 0, 1}}; found {sorted(bad_values)}"
            )

    n = len(index)
    sweep_high_arr = sweep_high.to_numpy(dtype=bool)
    sweep_low_arr = sweep_low.to_numpy(dtype=bool)
    bos_arr = bos.to_numpy(dtype=np.int64)
    choch_arr = choch.to_numpy(dtype=np.int64)

    confirmed = np.zeros(n, dtype=np.int64)
    expired = np.zeros(n, dtype=np.int64)
    pending_out = np.zeros(n, dtype=np.int64)
    pending_bullish = np.zeros(n, dtype=bool)
    pending_bearish = np.zeros(n, dtype=bool)

    bull_deadline = None  # awaiting bullish confirmation (from a low sweep)
    bear_deadline = None  # awaiting bearish confirmation (from a high sweep)

    for i in range(n):
        # --- resolve any pre-existing pending window against THIS row's
        # structure signal (this row is "subsequent" to whatever sweep
        # opened the window, since the window is only opened after this
        # check runs).
        if bull_deadline is not None:
            if bos_arr[i] == 1 or choch_arr[i] == 1:
                confirmed[i] = 1
                bull_deadline = None
            elif i == bull_deadline:
                expired[i] = 1
                bull_deadline = None

        if bear_deadline is not None:
            if bos_arr[i] == -1 or choch_arr[i] == -1:
                confirmed[i] = -1
                bear_deadline = None
            elif i == bear_deadline:
                expired[i] = -1
                bear_deadline = None

        # --- open a new pending window for a sweep on THIS row. Opened
        # after the resolution check above, so this row's own bos/choch
        # cannot confirm its own freshly-opened window.
        if sweep_low_arr[i]:
            bull_deadline = i + max_bars
        if sweep_high_arr[i]:
            bear_deadline = i + max_bars

        pending_bullish[i] = bull_deadline is not None
        pending_bearish[i] = bear_deadline is not None
        if pending_bullish[i] and not pending_bearish[i]:
            pending_out[i] = 1
        elif pending_bearish[i] and not pending_bullish[i]:
            pending_out[i] = -1
        # Both pending is intentionally represented as 0 in the legacy
        # signed summary; callers needing the complete state use the two
        # independent boolean columns above.

    return pd.DataFrame(
        {
            "sweep_confirmed": confirmed,
            "sweep_expired": expired,
            "sweep_pending_bullish": pending_bullish,
            "sweep_pending_bearish": pending_bearish,
            "sweep_pending": pending_out,
        },
        index=index,
    )


def structural_rr(entry, stop, target):
    """Structural reward/risk ratio from a frozen entry, stop and target.

    ``risk = |entry - stop|`` and ``reward = |target - entry|``; the
    result is ``reward / risk``. This is a magnitude ratio: it does
    not validate that ``stop`` and ``target`` sit on the structurally
    correct sides of ``entry`` for a given trade direction — that is a
    side-aware concern for the caller (e.g. the strategy layer, which
    knows whether the trade is long or short). Keeping this helper
    direction-agnostic keeps it trivially pure and safe to reuse for
    both sides.

    Safety:

    * ``risk <= 0`` (i.e. ``entry == stop`` — the abs() makes risk
      strictly non-negative, so the only "nonpositive" case is exactly
      zero) returns ``NaN`` rather than raising or producing ``inf``.
    * Any ``NaN`` in ``entry`` / ``stop`` / ``target`` propagates to a
      ``NaN`` result, never an exception.

    Parameters
    ----------
    entry, stop, target:
        Scalars, or aligned ``pandas.Series`` (any mix — a Series
        input determines the return type and index; multiple Series
        arguments must share an identical index).

    Returns
    -------
    float or pd.Series
        A ``float`` (``NaN``-safe) if every argument is a scalar,
        otherwise a ``pandas.Series`` aligned to the common index.
    """
    series_inputs = [
        (name, val)
        for name, val in (("entry", entry), ("stop", stop), ("target", target))
        if isinstance(val, pd.Series)
    ]
    index = None
    if series_inputs:
        index = series_inputs[0][1].index
        for name, val in series_inputs[1:]:
            if not val.index.equals(index):
                raise ValueError(
                    f"structural_rr: {name!r} index does not match "
                    f"{series_inputs[0][0]!r} index; all Series arguments "
                    f"must share an identical index."
                )

    def _to_array(val, name):
        if isinstance(val, pd.Series):
            _validate_numeric_series(val, name)
            return val.to_numpy(dtype=float)
        if isinstance(val, bool) or not isinstance(val, (int, float, np.integer, np.floating)):
            raise TypeError(
                f"structural_rr: {name!r} must be a numeric scalar or "
                f"pandas.Series, got {type(val).__name__}"
            )
        return np.float64(val)

    entry_arr = _to_array(entry, "entry")
    stop_arr = _to_array(stop, "stop")
    target_arr = _to_array(target, "target")

    risk = np.abs(entry_arr - stop_arr)
    reward = np.abs(target_arr - entry_arr)
    with np.errstate(invalid="ignore", divide="ignore"):
        rr = np.where(risk > 0, reward / risk, np.nan)

    if index is not None:
        return pd.Series(rr, index=index)
    return float(rr)
