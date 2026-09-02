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

__all__ = ["confirmed_pivots", "market_structure"]

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
