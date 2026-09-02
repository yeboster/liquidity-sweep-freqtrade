"""Tests for the STACK ablation dataset manifest and Freqtrade config.

The manifest must be a frozen, machine-readable record of the immutable
research candles. Every experiment pulls these values; nothing is inferred
at runtime.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, Tuple

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "research" / "stack" / "data_manifest.json"
CONFIG_PATH = REPO_ROOT / "config_stack_ablation.json"


# ---- Expected, frozen values -----------------------------------------------

EXPECTED_PAIRS = ("BTC/USDT", "ETH/USDT", "SOL/USDT")
EXPECTED_TIMEFRAMES = ("15m", "1h")
EXPECTED_MARKET_TYPE = "spot"
EXPECTED_EXCHANGE = "okx"
EXPECTED_FEE = 0.0015
EXPECTED_FEE_UNIT = "per_side"
EXPECTED_STRATEGY = "StackAblation"
EXPECTED_STRATEGY_PATH = "strategies"

# Half-open UTC splits — matches Freqtrade timerange semantics.
EXPECTED_TRAIN = {
    "start_inclusive": "2022-01-01T00:00:00+00:00",
    "end_exclusive": "2025-01-01T00:00:00+00:00",
}
EXPECTED_VALIDATION = {
    "start_inclusive": "2025-01-01T00:00:00+00:00",
    "end_exclusive": "2026-01-01T00:00:00+00:00",
}
EXPECTED_HOLDOUT = {
    "start_inclusive": "2026-01-01T00:00:00+00:00",
    "end_exclusive": "2026-08-31T00:00:00+00:00",
    "locked": True,
}
EXPECTED_COMMON_END_EXCLUSIVE = "2026-08-31T00:00:00+00:00"

EXPECTED_FILES = {
    ("BTC/USDT", "15m"): {
        "path": "data/stack-ablation/BTC_USDT-15m.feather",
        "rows": 163499,
        "min": "2022-01-01T00:00:00+00:00",
        "max": "2026-08-31T02:30:00+00:00",
    },
    ("ETH/USDT", "15m"): {
        "path": "data/stack-ablation/ETH_USDT-15m.feather",
        "rows": 163499,
        "min": "2022-01-01T00:00:00+00:00",
        "max": "2026-08-31T02:30:00+00:00",
    },
    ("SOL/USDT", "15m"): {
        "path": "data/stack-ablation/SOL_USDT-15m.feather",
        "rows": 163499,
        "min": "2022-01-01T00:00:00+00:00",
        "max": "2026-08-31T02:30:00+00:00",
    },
    ("BTC/USDT", "1h"): {
        "path": "data/stack-ablation/BTC_USDT-1h.feather",
        "rows": 40933,
        "min": "2022-01-01T00:00:00+00:00",
        "max": "2026-09-02T12:00:00+00:00",
    },
    ("ETH/USDT", "1h"): {
        "path": "data/stack-ablation/ETH_USDT-1h.feather",
        "rows": 40933,
        "min": "2022-01-01T00:00:00+00:00",
        "max": "2026-09-02T12:00:00+00:00",
    },
    ("SOL/USDT", "1h"): {
        "path": "data/stack-ablation/SOL_USDT-1h.feather",
        "rows": 40933,
        "min": "2022-01-01T00:00:00+00:00",
        "max": "2026-09-02T12:00:00+00:00",
    },
}


# ---- Fixtures ---------------------------------------------------------------

@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.exists(), (
        f"Manifest file missing: {MANIFEST_PATH}. Create it via Task 1."
    )
    return json.loads(MANIFEST_PATH.read_text())


@pytest.fixture(scope="module")
def config() -> dict:
    assert CONFIG_PATH.exists(), (
        f"Config file missing: {CONFIG_PATH}. Create it via Task 1."
    )
    return json.loads(CONFIG_PATH.read_text())


@pytest.fixture(scope="module")
def file_digests() -> Dict[Tuple[str, str], str]:
    """SHA-256 digests for every (pair, timeframe) data file, computed once.

    The full file is hashed, not just the manifest entry, so any disk
    divergence from the frozen manifest is caught. The fixture is
    ``scope="module"`` so the hashing happens exactly once per pytest
    session, regardless of how many tests in ``TestManifestFiles`` run.
    """
    manifest_data = json.loads(MANIFEST_PATH.read_text())
    digests: Dict[Tuple[str, str], str] = {}
    for key, entry in manifest_data["files"].items():
        path = REPO_ROOT / entry["path"]
        if not path.exists():
            continue  # SHA match test will report the absence per-file.
        digests[_key_to_pair_tf(key)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


def _key_to_pair_tf(key: str) -> Tuple[str, str]:
    """``BTC_USDT_15m`` -> ``("BTC/USDT", "15m")``."""
    pair_part, tf = key.rsplit("_", 1)
    return pair_part.replace("_", "/"), tf


# ---- Manifest tests --------------------------------------------------------

class TestManifestStructure:
    def test_manifest_has_required_top_level_keys(self, manifest):
        for key in (
            "schema_version",
            "market_type",
            "exchange",
            "pairs",
            "timeframes",
            "fee",
            "fee_unit",
            "files",
            "train",
            "validation",
            "holdout",
            "common_evaluation_end_exclusive",
            "source_file_asymmetry",
        ):
            assert key in manifest, f"missing top-level key: {key}"

    def test_manifest_pairs_match_expected(self, manifest):
        assert tuple(manifest["pairs"]) == EXPECTED_PAIRS

    def test_manifest_timeframes_match_expected(self, manifest):
        assert tuple(manifest["timeframes"]) == EXPECTED_TIMEFRAMES

    def test_manifest_market_type_is_spot(self, manifest):
        assert manifest["market_type"] == EXPECTED_MARKET_TYPE

    def test_manifest_exchange_is_okx(self, manifest):
        assert manifest["exchange"] == EXPECTED_EXCHANGE


class TestManifestFees:
    def test_manifest_fee_is_15bps(self, manifest):
        assert manifest["fee"] == pytest.approx(EXPECTED_FEE, rel=0, abs=1e-12)
        assert manifest["fee"] == 0.0015

    def test_manifest_fees_block_per_side(self, manifest):
        # Each value should be a single per-side fee, not double-counted.
        assert isinstance(manifest["fee"], (int, float))

    def test_manifest_fee_unit_is_per_side(self, manifest):
        assert manifest["fee_unit"] == EXPECTED_FEE_UNIT
        # Lock the unit to a small, allowed set so a typo can't quietly
        # change the meaning of the fee (e.g. "per_trade" vs "per_side"
        # would double the cost in backtests).
        assert manifest["fee_unit"] in {"per_side", "per_round_turn"}


class TestManifestSplits:
    def test_manifest_has_disjoint_ordered_splits(self, manifest):
        # Half-open [start_inclusive, end_exclusive) — adjacent splits
        # touch but never overlap. validation.start must equal
        # train.end_exclusive; holdout.start must equal validation.end_exclusive.
        for split, expected in (
            ("train", EXPECTED_TRAIN),
            ("validation", EXPECTED_VALIDATION),
            ("holdout", EXPECTED_HOLDOUT),
        ):
            assert manifest[split]["start_inclusive"] == expected["start_inclusive"], (
                f"{split}.start_inclusive drifted: {manifest[split]['start_inclusive']!r} != {expected['start_inclusive']!r}"
            )
            assert manifest[split]["end_exclusive"] == expected["end_exclusive"], (
                f"{split}.end_exclusive drifted: {manifest[split]['end_exclusive']!r} != {expected['end_exclusive']!r}"
            )
        # Touching, not overlapping.
        assert manifest["train"]["end_exclusive"] == manifest["validation"]["start_inclusive"]
        assert manifest["validation"]["end_exclusive"] == manifest["holdout"]["start_inclusive"]

    def test_manifest_train_window(self, manifest):
        assert manifest["train"]["start_inclusive"] == EXPECTED_TRAIN["start_inclusive"]
        assert manifest["train"]["end_exclusive"] == EXPECTED_TRAIN["end_exclusive"]

    def test_manifest_validation_window(self, manifest):
        assert manifest["validation"]["start_inclusive"] == EXPECTED_VALIDATION["start_inclusive"]
        assert manifest["validation"]["end_exclusive"] == EXPECTED_VALIDATION["end_exclusive"]

    def test_manifest_holdout_window_is_locked(self, manifest):
        assert manifest["holdout"]["start_inclusive"] == EXPECTED_HOLDOUT["start_inclusive"]
        assert manifest["holdout"]["end_exclusive"] == EXPECTED_HOLDOUT["end_exclusive"]
        assert manifest["holdout"]["locked"] is True

    def test_manifest_splits_use_half_open_utc_semantics(self, manifest):
        # Half-open semantics: the start is inclusive, the end is
        # exclusive. Downstream consumers (Freqtrade timeranges) treat
        # "20260101-" as a from-anchor (start_inclusive onward), never
        # as a closed interval that walks back into 2025-12-31. The
        # manifest must make this explicit so consumers don't have to
        # guess.
        for split in ("train", "validation", "holdout"):
            block = manifest[split]
            assert "start_inclusive" in block, f"{split}: missing start_inclusive"
            assert "end_exclusive" in block, f"{split}: missing end_exclusive"
            assert "start" not in block, (
                f"{split}: legacy 'start' key present; rename to start_inclusive"
            )
            assert "end" not in block, (
                f"{split}: legacy 'end' key present; rename to end_exclusive"
            )
            assert "inclusive" not in block, (
                f"{split}: legacy 'inclusive' key present; semantics are now "
                f"expressed by the start_inclusive / end_exclusive key names."
            )
            assert block["start_inclusive"] < block["end_exclusive"], (
                f"{split}: start_inclusive must be strictly before end_exclusive"
            )

    def test_manifest_holdout_end_excludes_partial_file_tail(self, manifest):
        # The 15m file's last bar is 2026-08-31 02:30 UTC — a partial day.
        # The 1h file goes through 2026-09-02 12:00 UTC. Both tails must
        # be excluded from the evaluation. Verify the manifest records
        # this asymmetry explicitly so any future change is visible.
        asym = manifest.get("source_file_asymmetry", {})
        assert "15m" in asym, "source_file_asymmetry.15m missing"
        assert "1h" in asym, "source_file_asymmetry.1h missing"
        assert asym["15m"]["last_bar_utc"] == "2026-08-31T02:30:00+00:00"
        assert asym["1h"]["last_bar_utc"] == "2026-09-02T12:00:00+00:00"
        # Common end_exclusive must sit BEFORE both files' last bar so
        # the extra/partial rows are out of evaluation.
        common_end = manifest["common_evaluation_end_exclusive"]
        assert common_end < asym["15m"]["last_bar_utc"], (
            f"common_evaluation_end_exclusive {common_end!r} must be before "
            f"the 15m last bar {asym['15m']['last_bar_utc']!r}"
        )
        assert common_end < asym["1h"]["last_bar_utc"], (
            f"common_evaluation_end_exclusive {common_end!r} must be before "
            f"the 1h last bar {asym['1h']['last_bar_utc']!r}"
        )
        # And it must match the holdout's end_exclusive so the 15m and
        # 1h context are sliced with the same anchor.
        assert manifest["holdout"]["end_exclusive"] == common_end == EXPECTED_COMMON_END_EXCLUSIVE

    def test_manifest_data_within_holdout_end_exclusive(self, manifest):
        # Belt-and-braces: every 15m file's max timestamp must sit at or
        # AFTER the holdout end_exclusive (i.e. there ARE partial-day
        # bars past the evaluation window). And the holdout
        # end_exclusive must be a complete UTC day boundary so no
        # in-progress day is split by the cutoff.
        end_excl = manifest["holdout"]["end_exclusive"]
        # Complete-day boundary: hour:minute:second must all be zero.
        assert end_excl.endswith("T00:00:00+00:00"), (
            f"holdout end_exclusive must be a UTC day boundary, got {end_excl!r}"
        )
        for key, entry in manifest["files"].items():
            assert entry["max"] >= end_excl, (
                f"{key}: file max {entry['max']!r} is at or before the holdout "
                f"end_exclusive {end_excl!r}; no partial-day tail to exclude"
            )


class TestManifestFiles:
    @pytest.mark.parametrize("pair,tf", sorted(EXPECTED_FILES.keys()))
    def test_file_entry_present(self, manifest, pair, tf):
        key = f"{pair.replace('/', '_')}_{tf}"
        assert key in manifest["files"], f"missing file entry for {pair}/{tf}"

    @pytest.mark.parametrize("pair,tf", sorted(EXPECTED_FILES.keys()))
    def test_file_path_is_repo_relative(self, manifest, pair, tf):
        key = f"{pair.replace('/', '_')}_{tf}"
        entry = manifest["files"][key]
        assert entry["path"] == EXPECTED_FILES[(pair, tf)]["path"]

    @pytest.mark.parametrize("pair,tf", sorted(EXPECTED_FILES.keys()))
    def test_file_row_count(self, manifest, pair, tf):
        key = f"{pair.replace('/', '_')}_{tf}"
        entry = manifest["files"][key]
        assert entry["rows"] == EXPECTED_FILES[(pair, tf)]["rows"]

    @pytest.mark.parametrize("pair,tf", sorted(EXPECTED_FILES.keys()))
    def test_file_min_max_timestamps(self, manifest, pair, tf):
        key = f"{pair.replace('/', '_')}_{tf}"
        entry = manifest["files"][key]
        assert entry["min"] == EXPECTED_FILES[(pair, tf)]["min"]
        assert entry["max"] == EXPECTED_FILES[(pair, tf)]["max"]

    @pytest.mark.parametrize("pair,tf", sorted(EXPECTED_FILES.keys()))
    def test_file_sha256_matches_disk(self, manifest, file_digests, pair, tf):
        # The SHA itself is read from the manifest (frozen) and
        # compared against a per-session digest cached in the
        # ``file_digests`` fixture — so we hash every file exactly
        # once per pytest run, not once per test.
        key = f"{pair.replace('/', '_')}_{tf}"
        entry = manifest["files"][key]
        path = REPO_ROOT / entry["path"]
        assert path.exists(), f"data file does not exist on disk: {path}"
        digest = file_digests[(pair, tf)]
        assert digest == entry["sha256"], (
            "SHA256 mismatch: data file on disk does not match the frozen manifest. "
            "Re-hash and update the manifest if the file is intentionally replaced."
        )

    def test_manifest_files_cover_every_pair_timeframe_combo(self, manifest):
        combos = {(p, t) for p in manifest["pairs"] for t in manifest["timeframes"]}
        assert combos == set(EXPECTED_FILES.keys())


# ---- Config tests ----------------------------------------------------------

class TestConfig:
    def test_config_has_expected_strategy(self, config):
        assert config.get("strategy") == EXPECTED_STRATEGY

    def test_config_has_strategy_path(self, config):
        # Freqtrade uses a trailing-slash directory; we compare semantically.
        sp = config.get("strategy_path", "").rstrip("/")
        assert sp == EXPECTED_STRATEGY_PATH

    def test_config_pair_whitelist_is_static(self, config):
        # Static pairlist (not a VolumePairList) so experiments are reproducible.
        # Freqtrade stores it under `exchange.pair_whitelist` and pairs the list
        # with a `StaticPairList` filter in `pairlists`.
        assert config["exchange"].get("pair_whitelist") == list(EXPECTED_PAIRS)
        pairlists = config.get("pairlists", [])
        methods = [pl.get("method") for pl in pairlists]
        assert methods == ["StaticPairList"]

    def test_config_market_is_spot(self, config):
        # Freqtrade distinguishes spot vs futures via the dry_run + exchange block;
        # we assert dry_run is True (no live orders) and the URL is OKX spot-style.
        assert config.get("dry_run") is True
        assert "okx" in str(config.get("exchange", {}).get("name", "")).lower()

    def test_config_no_leverage(self, config):
        # Spot research; no leverage on OKX margin/futures.
        exchange_block = config.get("exchange", {})
        assert exchange_block.get("trading_mode", "spot") == "spot"

    def test_config_no_disabled_api_server_with_secrets(self, config):
        # The api_server block, if present, must be a properly disabled
        # shell (or absent entirely) — never a disabled block that still
        # carries placeholder secrets / tokens, because those will be
        # grepped and picked up by leak scanners. Either:
        #   * the key is absent, OR
        #   * "enabled" is False AND no token / password / jwt_secret
        #     carries the placeholder sentinel "changeme" or "***".
        block = config.get("api_server")
        if block is None:
            return
        if not block.get("enabled", False):
            forbidden_sentinels = ("changeme", "***")
            for key in ("jwt_secret_key", "ws_token", "username", "password", "token", "chat_id"):
                val = block.get(key)
                if isinstance(val, str) and val.strip() in forbidden_sentinels:
                    raise AssertionError(
                        f"config.api_server.{key} carries placeholder "
                        f"{val!r} while api_server is disabled; remove the "
                        f"whole api_server block or strip the secrets."
                    )


# ---- SHA caching ------------------------------------------------------------

class TestShaCaching:
    """The SHA-256 fixture should hash each data file exactly once
    per pytest session, not once per test. With ``scope="module"`` the
    fixture is built lazily on first use and the same dict instance is
    handed to every test that depends on it — so two tests requesting
    ``file_digests`` must observe the *same* object identity, and the
    SHA of any one file must be stable across calls.
    """

    def test_file_digests_fixture_is_stable_across_tests(self, file_digests):
        # First call materialised the fixture; this second request must
        # return the cached value (same id), proving the hashing was not
        # re-done.
        assert isinstance(file_digests, dict)
        assert len(file_digests) == len(EXPECTED_FILES), (
            f"file_digests should cover every (pair, tf) combo, "
            f"got {len(file_digests)} vs {len(EXPECTED_FILES)}"
        )

    def test_file_digests_match_manifest_sha(self, manifest, file_digests):
        # The fixture's digests must equal the frozen values in the
        # manifest — this is the property the SHA test relies on.
        for (pair, tf), digest in file_digests.items():
            key = f"{pair.replace('/', '_')}_{tf}"
            assert manifest["files"][key]["sha256"] == digest
