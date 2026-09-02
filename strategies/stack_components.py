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

__all__ = ["confirmed_pivots"]

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
