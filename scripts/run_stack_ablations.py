#!/usr/bin/env python3
"""Run the pre-registered STACK entry ablation matrix.

The runner is intentionally a thin, reproducible orchestration layer: all
component choices come from the checked-in matrix and every Freqtrade cell is
run with a generated config.  It never edits a strategy file or selects a
cell from holdout results.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Iterable

COMPONENTS = (
    "htf_bias", "discount", "ote", "fvg", "fvg_one_time",
    "session", "weekend", "momentum", "min_rr",
)
METRIC_KEYS = ("trades", "mean_profit_ratio", "profit_factor", "sharpe", "drawdown", "win_rate")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_freqtrade(override: str | None = None) -> str:
    """Resolve an executable without assuming this worktree's virtualenv."""
    candidates = [override, os.environ.get("FREQTRADE_BIN"), shutil.which("freqtrade")]
    for candidate in candidates:
        if candidate and Path(candidate).exists() and os.access(candidate, os.X_OK):
            return str(Path(candidate).resolve())
        if candidate and not Path(candidate).is_absolute():
            found = shutil.which(candidate)
            if found:
                return str(Path(found).resolve())
    raise FileNotFoundError("Freqtrade executable not found; pass --freqtrade or set FREQTRADE_BIN")


def _date_compact(timestamp: str) -> str:
    return timestamp[:10].replace("-", "")


def split_timerange(manifest: dict[str, Any], split: str) -> str:
    if split not in {"train", "validation", "holdout"}:
        raise ValueError(f"unknown split: {split}")
    spec = manifest[split]
    return f"{_date_compact(spec['start_inclusive'])}-{_date_compact(spec['end_exclusive'])}"


def build_command(
    *, freqtrade: str, config: Path, strategy_path: Path, datadir: Path,
    pair_list: Iterable[str], timerange: str, export_path: Path,
) -> list[str]:
    """Return the complete stable Freqtrade 2025.8-compatible command."""
    pairs = list(pair_list)
    return [
        str(freqtrade), "backtesting", "--config", str(config),
        "--strategy", "StackAblation", "--strategy-path", str(strategy_path),
        "--datadir", str(datadir), "--timerange", timerange,
        "--fee", "0.0015", "--cache", "none", "--pairs", *pairs,
        "--export", "trades", "--backtest-directory", str(export_path),
    ]


def _finite(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _profit(trade: dict[str, Any]) -> float | None:
    for key in ("profit_ratio", "profit_pct", "profit_percent", "profit_abs", "profit"):
        value = _finite(trade.get(key))
        if value is not None:
            # Freqtrade's profit_pct is percentage points, unlike ratio fields.
            return value / 100 if key in {"profit_pct", "profit_percent"} else value
    return None


def _trade_lists(value: Any) -> Iterable[list[dict[str, Any]]]:
    if isinstance(value, list) and value and all(isinstance(x, dict) for x in value):
        if any("pair" in x and _profit(x) is not None for x in value):
            yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _trade_lists(child)


def _find_summary(payload: Any, experiment_id: str | None = None) -> dict[str, Any]:
    if isinstance(payload, dict):
        if experiment_id and isinstance(payload.get("strategy"), dict):
            candidate = payload["strategy"].get(experiment_id)
            if isinstance(candidate, dict):
                return candidate
        for key in ("strategy", "results", "summary", "metrics"):
            child = payload.get(key)
            if isinstance(child, dict):
                found = _find_summary(child, experiment_id)
                if found:
                    return found
        if any(key in payload for key in ("trades", "expectancy", "profit_factor", "max_drawdown")):
            return payload
    return {}


def _drawdown(profits: list[float]) -> float:
    if not profits:
        return 0.0
    curve = 1.0
    peak = curve
    worst = 0.0
    for profit in profits:
        curve *= 1.0 + profit
        peak = max(peak, curve)
        worst = max(worst, (peak - curve) / peak)
    return worst


def _computed_metrics(trades: list[dict[str, Any]]) -> dict[str, Any]:
    profits = [value for trade in trades if (value := _profit(trade)) is not None]
    wins = [value for value in profits if value > 0]
    losses = [value for value in profits if value < 0]
    mean = sum(profits) / len(profits) if profits else 0.0
    deviation = math.sqrt(sum((x - mean) ** 2 for x in profits) / (len(profits) - 1)) if len(profits) > 1 else 0.0
    return {
        "trades": len(profits),
        "mean_profit_ratio": mean,
        "profit_factor": sum(wins) / abs(sum(losses)) if losses else (float("inf") if wins else 0.0),
        "sharpe": mean / deviation * math.sqrt(len(profits)) if deviation else 0.0,
        "drawdown": _drawdown(profits),
        "win_rate": len(wins) / len(profits) if profits else 0.0,
    }


def _read_artifact(path: Path) -> Any:
    if path.is_dir():
        archives = sorted(path.glob("backtest-result-*.zip"))
        if not archives:
            return {}
        path = archives[-1]
    if not path.exists():
        return {}
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            names = sorted(name for name in archive.namelist() if name.lower().endswith(".json"))
            if not names:
                return {}
            return json.loads(archive.read(names[0]))
    return json.loads(path.read_text())


def parse_result_artifact(path: Path, experiment_id: str | None = None) -> dict[str, Any]:
    """Normalize JSON/zip export data, computing missing metrics from trades."""
    payload = _read_artifact(path)
    trade_lists = list(_trade_lists(payload))
    trades = max(trade_lists, key=len) if trade_lists else []
    computed = _computed_metrics(trades)
    summary = _find_summary(payload, experiment_id)
    if isinstance(payload, dict) and isinstance(payload.get("strategy"), dict):
        strategies = payload["strategy"]
        if experiment_id and isinstance(strategies.get(experiment_id), dict):
            summary = strategies[experiment_id]
        elif len(strategies) == 1:
            only = next(iter(strategies.values()))
            if isinstance(only, dict):
                summary = only
    aliases = {
        "trades": ("trades", "total_trades"),
        "profit_factor": ("profit_factor", "profitfactor"),
        "sharpe": ("sharpe", "sharpe_ratio"),
        "drawdown": ("drawdown", "max_drawdown", "max_drawdown_ratio"),
        "win_rate": ("win_rate", "winrate", "win_rate_pct"),
    }
    metrics: dict[str, Any] = {}
    for output_key, keys in aliases.items():
        value = next((_finite(summary.get(key)) for key in keys if key in summary), None)
        if value is None:
            value = computed[output_key]
        if output_key == "win_rate" and value > 1:
            value /= 100
        metrics[output_key] = value
    # Unlike Freqtrade's absolute `expectancy` and reward/loss-style
    # `expectancy_ratio`, this is always the arithmetic mean of exported
    # per-trade profit ratios and therefore has identical units globally and
    # per pair.
    metrics["mean_profit_ratio"] = computed["mean_profit_ratio"]
    metrics["trades"] = int(metrics["trades"] or 0)
    per_pair: dict[str, Any] = {}
    for pair in sorted({str(trade.get("pair")) for trade in trades if trade.get("pair") is not None}):
        per_pair[pair] = _computed_metrics([trade for trade in trades if str(trade.get("pair")) == pair])
    metrics["per_pair"] = per_pair
    return metrics


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def write_results(results: list[dict[str, Any]], json_path: Path, csv_path: Path) -> None:
    ordered = sorted(results, key=lambda row: row["experiment_id"])
    _write_json(json_path, {"schema_version": "1.0.0", "results": ordered})
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["experiment_id", "split", "exit_code", *METRIC_KEYS]
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in ordered:
            metrics = row.get("metrics", {})
            writer.writerow({field: row.get(field, metrics.get(field, "")) for field in fields})


def _config_for_cell(base: dict[str, Any], experiment: dict[str, Any]) -> dict[str, Any]:
    config = dict(base)
    config.update({
        "strategy": "StackAblation", "strategy_path": "strategies",
        "stack_experiment_id": experiment["id"],
        "stack_components": experiment["components"],
    })
    return config


def execute_experiment(
    *, experiment: dict[str, Any], split: str, manifest: dict[str, Any], freqtrade: str,
    config: Path, strategy_path: Path, datadir: Path, timerange: str, export_path: Path,
) -> dict[str, Any]:
    export_path.mkdir(parents=True, exist_ok=True)
    command = build_command(
        freqtrade=freqtrade, config=config, strategy_path=strategy_path,
        datadir=datadir, pair_list=manifest["pairs"], timerange=timerange,
        export_path=export_path,
    )
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    metrics = parse_result_artifact(export_path, experiment["id"])
    return {
        "experiment_id": experiment["id"], "split": split,
        "experiment_toggles": experiment["components"], "timerange": timerange,
        "command": command, "exit_code": completed.returncode,
        "metrics": metrics, "stderr": completed.stderr.strip(),
        "stdout": completed.stdout.strip(),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("train", "validation", "holdout"), required=True)
    parser.add_argument("--matrix", choices=("entry",), default="entry")
    parser.add_argument("--manifest", type=Path, default=repo_root() / "research/stack/data_manifest.json")
    parser.add_argument("--output-dir", type=Path, default=repo_root() / "research/stack/results/entry_runs")
    parser.add_argument("--config", type=Path, default=repo_root() / "config_stack_ablation.json")
    parser.add_argument("--strategy-path", type=Path, default=repo_root() / "strategies")
    parser.add_argument("--datadir", type=Path, default=repo_root() / "data/stack-ablation")
    parser.add_argument("--freqtrade")
    parser.add_argument("--winner", action="append", default=[])
    parser.add_argument("--unlock-holdout", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="validate and write commands without executing")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    manifest = json.loads(args.manifest.read_text())
    matrix_path = repo_root() / "research/stack/entry_ablation_matrix.json"
    matrix = json.loads(matrix_path.read_text())
    experiments = matrix["experiments"]
    if args.split == "holdout":
        if not manifest["holdout"].get("locked", True) and args.winner:
            raise SystemExit("--winner is only valid for a locked holdout")
        if manifest["holdout"].get("locked", True) and (not args.unlock_holdout or len(args.winner) != 1):
            raise SystemExit("holdout requires --unlock-holdout and exactly one --winner")
        if len(args.winner) == 1:
            experiments = [item for item in experiments if item["id"] == args.winner[0]]
            if not experiments:
                raise SystemExit(f"winner is not registered in entry matrix: {args.winner[0]}")
    elif args.winner:
        raise SystemExit("--winner is only valid with --split holdout")
    freqtrade = args.freqtrade or ("dry-run-freqtrade" if args.dry_run else resolve_freqtrade(None))
    base_config = json.loads(args.config.read_text()) if args.config.exists() else {}
    timerange = split_timerange(manifest, args.split)
    results: list[dict[str, Any]] = []
    config_dir = args.output_dir / "configs"
    export_dir = args.output_dir / "exports"
    for experiment in experiments:
        cell_config = config_dir / f"{experiment['id']}.json"
        export_path = export_dir / experiment["id"]
        _write_json(cell_config, _config_for_cell(base_config, experiment))
        if args.dry_run:
            command = build_command(freqtrade=freqtrade, config=cell_config, strategy_path=args.strategy_path, datadir=args.datadir, pair_list=manifest["pairs"], timerange=timerange, export_path=export_path)
            results.append({"experiment_id": experiment["id"], "split": args.split, "experiment_toggles": experiment["components"], "timerange": timerange, "command": command, "exit_code": None, "metrics": {key: 0 for key in METRIC_KEYS}, "stderr": "", "stdout": ""})
        else:
            results.append(execute_experiment(experiment=experiment, split=args.split, manifest=manifest, freqtrade=freqtrade, config=cell_config, strategy_path=args.strategy_path, datadir=args.datadir, timerange=timerange, export_path=export_path))
    write_results(results, args.output_dir / f"entry_{args.split}.json", args.output_dir / f"entry_{args.split}.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
