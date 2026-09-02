"""Contract tests for the pre-registered STACK experiment tooling."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts import run_stack_ablations as runner


COMPONENTS = [
    "htf_bias", "discount", "ote", "fvg", "fvg_one_time",
    "session", "weekend", "momentum", "min_rr",
]


@pytest.fixture
def matrix():
    return json.loads(
        (Path(__file__).parents[1] / "research/stack/entry_ablation_matrix.json").read_text()
    )


def test_matrix_has_core_full_loo_and_single_additions(matrix):
    experiments = matrix["experiments"]
    ids = [item["id"] for item in experiments]
    assert ids[0:2] == ["E00_core", "E01_full"]
    assert len(experiments) == 20
    assert {item["kind"] for item in experiments} == {"core", "full", "leave_one_out", "single_addition"}
    for item in experiments:
        assert set(item["components"]) == set(COMPONENTS)


def test_matrix_deltas_change_exactly_one_component(matrix):
    experiments = {item["id"]: item for item in matrix["experiments"]}
    core = experiments["E00_core"]["components"]
    full = experiments["E01_full"]["components"]
    assert all(value is False for value in core.values())
    for item in matrix["experiments"][2:11]:
        changed = [name for name in COMPONENTS if item["components"][name] != full[name]]
        assert changed == [item["component"]], item["id"]
    for item in matrix["experiments"][11:]:
        changed = [name for name in COMPONENTS if item["components"][name] != core[name]]
        assert changed == [item["component"]], item["id"]


def test_command_is_deterministic_and_explicit(tmp_path):
    experiment = {"id": "E00_core", "components": {name: False for name in COMPONENTS}}
    command = runner.build_command(
        freqtrade="/usr/local/bin/freqtrade",
        config=tmp_path / "cell.config.json",
        strategy_path=Path("strategies"),
        datadir=Path("data/stack-ablation"),
        pair_list=["BTC/USDT", "ETH/USDT", "SOL/USDT"],
        timerange="20220101-20250101",
        export_path=tmp_path / "E00_core.json",
    )
    assert command == runner.build_command(
        freqtrade="/usr/local/bin/freqtrade",
        config=tmp_path / "cell.config.json",
        strategy_path=Path("strategies"),
        datadir=Path("data/stack-ablation"),
        pair_list=["BTC/USDT", "ETH/USDT", "SOL/USDT"],
        timerange="20220101-20250101",
        export_path=tmp_path / "E00_core.json",
    )
    assert command[:2] == ["/usr/local/bin/freqtrade", "backtesting"]
    for flag, value in (
        ("--fee", "0.0015"), ("--cache", "none"), ("--datadir", "data/stack-ablation"),
        ("--timerange", "20220101-20250101"), ("--backtest-directory", str(tmp_path / "E00_core.json")),
    ):
        assert command[command.index(flag) + 1] == value
    assert command[command.index("--export") + 1] == "trades"
    assert command[command.index("--pairs") + 1:command.index("--export")] == [
        "BTC/USDT", "ETH/USDT", "SOL/USDT"
    ]


def test_holdout_requires_unlock_and_exactly_one_winner(tmp_path, monkeypatch):
    manifest = {
        "holdout": {"start_inclusive": "2026-01-01T00:00:00+00:00", "end_exclusive": "2026-08-31T00:00:00+00:00", "locked": True},
        "pairs": ["BTC/USDT"], "fee": 0.0015,
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    monkeypatch.setattr(runner, "resolve_freqtrade", lambda _: "/bin/true")
    with pytest.raises(SystemExit):
        runner.main(["--split", "holdout", "--manifest", str(path), "--dry-run"])
    with pytest.raises(SystemExit):
        runner.main(["--split", "holdout", "--manifest", str(path), "--unlock-holdout", "--dry-run"])
    with pytest.raises(SystemExit):
        runner.main(["--split", "holdout", "--manifest", str(path), "--unlock-holdout", "--winner", "E00_core", "--winner", "E01_full", "--dry-run"])


def test_normalize_result_artifact_and_csv(tmp_path):
    artifact = tmp_path / "export.json"
    artifact.write_text(json.dumps({
        "strategy": {"E00_core": {"trades": 4, "expectancy_ratio": 99, "profit_factor": 1.4, "sharpe": 0.8, "max_drawdown": 0.11, "winrate": 0.5}},
        "trades": [
            {"pair": "BTC/USDT", "profit_ratio": 0.02},
            {"pair": "BTC/USDT", "profit_ratio": -0.01},
            {"pair": "ETH/USDT", "profit_ratio": 0.01},
            {"pair": "ETH/USDT", "profit_ratio": -0.005},
        ],
    }))
    result = runner.parse_result_artifact(artifact)
    assert result["trades"] == 4
    assert result["mean_profit_ratio"] == pytest.approx(0.00375)
    assert result["per_pair"]["BTC/USDT"]["trades"] == 2
    output = tmp_path / "results.json"
    runner.write_results([{"experiment_id": "E00_core", "metrics": result}], output, tmp_path / "results.csv")
    assert json.loads(output.read_text())["results"][0]["experiment_id"] == "E00_core"
    assert "experiment_id" in (tmp_path / "results.csv").read_text()


def test_execute_experiment_creates_backtest_directory(monkeypatch, tmp_path):
    export_dir = tmp_path / "missing" / "E00_core"

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(command, **kwargs):
        assert export_dir.is_dir()
        return Completed()

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    result = runner.execute_experiment(
        experiment={"id": "E00_core", "components": {name: False for name in runner.COMPONENTS}},
        split="train",
        manifest={"fee": 0.0015, "pairs": ["BTC/USDT"]},
        freqtrade="/usr/local/bin/freqtrade",
        config=tmp_path / "config.json",
        strategy_path=Path("strategies"),
        datadir=Path("data/stack-ablation"),
        timerange="20220101-20250101",
        export_path=export_dir,
    )
    assert result["exit_code"] == 0


def test_subprocess_exit_code_and_artifact_are_recorded(tmp_path, monkeypatch):
    export = tmp_path / "export"
    completed = subprocess.CompletedProcess(["fake"], 3, stdout="ignored", stderr="failure")
    monkeypatch.setattr(runner.subprocess, "run", lambda *args, **kwargs: completed)
    experiment = {"id": "E00_core", "components": {name: False for name in COMPONENTS}}
    result = runner.execute_experiment(
        experiment=experiment,
        split="train",
        manifest={"fee": 0.0015, "pairs": ["BTC/USDT"]},
        freqtrade="fake",
        config=tmp_path / "config.json",
        strategy_path=Path("strategies"), datadir=Path("data/stack-ablation"),
        timerange="20220101-20250101", export_path=export,
    )
    assert result["exit_code"] == 3
    assert result["experiment_toggles"] == experiment["components"]
    assert result["metrics"]["trades"] == 0
    assert result["stderr"] == "failure"
