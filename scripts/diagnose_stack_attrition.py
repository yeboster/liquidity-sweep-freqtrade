#!/usr/bin/env python3
"""Report causal STACK signal attrition, without looking at PnL.

For each pair and requested chronological split this runs the same
``StackAblation.build_stack_indicators`` pipeline used by Freqtrade, then
counts each atomic gate and the cumulative conjunction.  Counts are based on
15-minute rows whose timestamps fall in the manifest's half-open interval.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from strategies.StackAblation import StackAblation

COMPONENTS = (
    "htf_bias", "discount", "ote", "fvg", "fvg_one_time",
    "session", "weekend", "momentum", "min_rr",
)
GATE_COLUMNS = {
    "htf_bias": "htf_bias_ok", "discount": "discount_ok", "ote": "ote_ok",
    "fvg": "fvg_ok", "fvg_one_time": "fvg_one_time_ok", "session": "session_ok",
    "weekend": "weekend_ok", "momentum": "momentum_ok", "min_rr": "rr_ok",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _timestamp(value: str) -> pd.Timestamp:
    return pd.Timestamp(value).tz_convert("UTC") if pd.Timestamp(value).tzinfo else pd.Timestamp(value, tz="UTC")


def _frame_utc(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    if "date" in result.columns:
        dates = pd.to_datetime(result["date"], utc=True)
    else:
        dates = pd.to_datetime(result.index, utc=True)
        result["date"] = dates
    result.index = dates
    return result.sort_index()


def _file_key(pair: str, timeframe: str) -> str:
    return f"{pair.replace('/', '_')}_{timeframe}"


def _count(value: pd.Series) -> int:
    return int(value.fillna(False).astype(bool).sum())


def _diagnose_frame(frame: pd.DataFrame) -> dict[str, Any]:
    """Count raw atomic events and left-to-right conjunction attrition."""
    raw = {
        "rows": int(len(frame)),
        "sweep": _count(frame.get("sweep_event", pd.Series(False, index=frame.index))),
        "bos_confirmation": _count(frame.get("sequence_confirmed", pd.Series(False, index=frame.index))),
    }
    for component, column in GATE_COLUMNS.items():
        raw[component] = _count(frame[column])
    # Core is sweep + causal confirmation; the strategy's sequence column is
    # already the event-level conjunction, while retaining both raw counts is
    # useful for diagnosing where the core disappears.
    conjunction = frame.get("sequence_confirmed", pd.Series(False, index=frame.index)).fillna(False).astype(bool)
    cumulative = [{"stage": "core", "components": [], "count": int(conjunction.sum())}]
    enabled: list[str] = []
    for component in COMPONENTS:
        enabled.append(component)
        conjunction = conjunction & frame[GATE_COLUMNS[component]].fillna(False).astype(bool)
        cumulative.append({"stage": component, "components": list(enabled), "count": int(conjunction.sum())})
    return {"raw_counts": raw, "cumulative_conjunction": cumulative}


def diagnose_pair_split(
    *, manifest: dict[str, Any], pair: str, split: str, datadir: Path,
) -> dict[str, Any]:
    split_spec = manifest[split]
    start, end = _timestamp(split_spec["start_inclusive"]), _timestamp(split_spec["end_exclusive"])
    entry_path = repo_root() / datadir / f"{pair.replace('/', '_')}-15m.feather" if not datadir.is_absolute() else datadir / f"{pair.replace('/', '_')}-15m.feather"
    context_path = repo_root() / datadir / f"{pair.replace('/', '_')}-1h.feather" if not datadir.is_absolute() else datadir / f"{pair.replace('/', '_')}-1h.feather"
    entry = _frame_utc(pd.read_feather(entry_path))
    context = _frame_utc(pd.read_feather(context_path))
    # Include pre-split history for causal warm-up, then count only the target
    # half-open interval. This avoids resetting confirmed state at split start.
    strategy = StackAblation({})
    # Freqtrade's merge helper expects ``date`` to be a column, not also an
    # index level. Keep the UTC date column and use a simple positional index
    # for this offline diagnostic.
    entry_for_pipeline = entry.loc[entry.index < end].reset_index(drop=True)
    context_for_pipeline = context.loc[context.index < end].reset_index(drop=True)
    indicators = strategy.build_stack_indicators(entry_for_pipeline, context_for_pipeline)
    indicator_dates = pd.to_datetime(indicators["date"], utc=True)
    selected = indicators.loc[(indicator_dates >= start) & (indicator_dates < end)]
    counts = _diagnose_frame(selected)
    return {
        "pair": pair, "split": split,
        "start_inclusive": split_spec["start_inclusive"],
        "end_exclusive": split_spec["end_exclusive"],
        **counts,
    }


def write_report(rows: list[dict[str, Any]], json_path: Path, csv_path: Path) -> None:
    rows = sorted(rows, key=lambda row: (row["split"], row["pair"]))
    payload = {"schema_version": "1.0.0", "purpose": "signal-availability-only", "results": rows}
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["split", "pair", "rows", "sweep", "bos_confirmation", *COMPONENTS]
    with csv_path.open("w", newline="") as handle:
        handle.write(",".join(fields) + "\n")
        for row in rows:
            raw = row["raw_counts"]
            handle.write(",".join(str(row.get("split", "")) if field == "split" else str(row.get("pair", "")) if field == "pair" else str(raw.get(field, "")) for field in fields) + "\n")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", action="append", choices=("train", "validation", "holdout"), default=["train", "validation"])
    parser.add_argument("--pair", action="append")
    parser.add_argument("--manifest", type=Path, default=repo_root() / "research/stack/data_manifest.json")
    parser.add_argument("--datadir", type=Path, default=repo_root() / "data/stack-ablation")
    parser.add_argument("--output", type=Path, default=repo_root() / "research/stack/results/stack_attrition.json")
    parser.add_argument("--csv", type=Path, default=repo_root() / "research/stack/results/stack_attrition.csv")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    manifest = json.loads(args.manifest.read_text())
    pairs = args.pair or manifest["pairs"]
    splits = list(dict.fromkeys(args.split))
    if "holdout" in splits:
        raise SystemExit("holdout is locked for attrition diagnostics; pass no holdout split")
    rows = [diagnose_pair_split(manifest=manifest, pair=pair, split=split, datadir=args.datadir) for split in splits for pair in pairs]
    write_report(rows, args.output, args.csv)
    print(json.dumps({"results": len(rows), "output": str(args.output), "csv": str(args.csv)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
