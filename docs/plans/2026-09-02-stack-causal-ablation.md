# STACK Causal Component Ablation Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build a causal, independently configurable STACK research strategy and identify which entry, filter, exit, and risk components improve out-of-sample expectancy after costs.

**Architecture:** Preserve `strategies/LiquiditySweep.py` as a historical artifact and create `StackAblation.py` from the causal native primitives at commit `bb1de2d`, correcting their semantic gaps. Pure indicator helpers emit signals only when information becomes available; the strategy exposes pre-registered component toggles; a runner executes fixed chronological experiments and writes machine-readable results without selecting parameters on the holdout.

**Tech Stack:** Python 3.12, pandas, NumPy, TA-Lib, Freqtrade 2025.8, pytest, OKX spot OHLCV, JSON/CSV research artifacts.

---

## Preconditions and validation gates

- **Pre-flight gate:** `data/stack-ablation` must contain BTC/ETH/SOL 15m and 1h data spanning 2022-01-01 through 2026-08-30. Failure blocks experiments; repair the manifest or download.
- **Revision gate:** Every implementation task receives spec review, then code-quality review. Fix and re-review, maximum three cycles.
- **Abort gate:** Any future-shock mismatch, negative shift, centered window, retrospective signal placement, or Freqtrade lookahead finding blocks all profitability claims.
- **Escalation gate:** If fewer than 100 validation trades exist for the core trigger, widen only the pre-registered universe/time range; do not tune filters on the holdout.

### Task 1: Freeze the research dataset and chronological splits

**Objective:** Make every experiment use the same immutable candles, costs, pairs, and train/validation/holdout boundaries.

**Files:**
- Create: `research/stack/data_manifest.json`
- Create: `config_stack_ablation.json`
- Create: `tests/test_stack_data_manifest.py`

**Step 1: Write failing manifest test**

```python
def test_manifest_has_disjoint_ordered_splits(manifest):
    assert manifest["train"]["end"] < manifest["validation"]["start"]
    assert manifest["validation"]["end"] < manifest["holdout"]["start"]
    assert manifest["holdout"]["locked"] is True
```

Also assert exact pairs, timeframes, 0.15% fee per side, source file SHA-256 values, row counts, and min/max timestamps.

**Step 2: Run test to verify failure**

Run: `.venv/bin/python -m pytest tests/test_stack_data_manifest.py -v`
Expected: FAIL because the manifest does not exist.

**Step 3: Create manifest and config**

Use fixed splits:
- Train: `20220101-20241231`
- Validation: `20250101-20251231`
- Holdout: `20260101-20260831`, locked until a configuration wins validation without holdout inspection.

Set `strategy=StackAblation`, static BTC/ETH/SOL pairlist, spot mode, and explicit fee in runner commands.

**Step 4: Verify**

Run: `.venv/bin/python -m pytest tests/test_stack_data_manifest.py -v`
Expected: PASS with six OHLCV files validated.

**Step 5: Commit**

```bash
git add research/stack/data_manifest.json config_stack_ablation.json tests/test_stack_data_manifest.py
git commit -m "test: freeze STACK ablation dataset"
```

### Task 2: Recover causal native pivots as pure helpers

**Objective:** Reuse the delayed-confirmation idea from `bb1de2d` without importing `smartmoneyconcepts`.

**Files:**
- Create: `strategies/stack_components.py`
- Create: `tests/test_stack_components.py`

**Step 1: Write failing tests**

```python
def test_pivot_is_emitted_only_after_right_bars():
    out = confirmed_pivots(frame, left=2, right=2)
    assert out.loc[3, "pivot_high"] != out.loc[3, "pivot_high"]  # unavailable
    assert out.loc[5, "pivot_high"] == frame.loc[3, "high"]


def test_future_shock_does_not_change_past_pivots(frame):
    baseline = confirmed_pivots(frame, 3, 3)
    shocked = frame.copy()
    shocked.loc[80:, ["high", "low", "close"]] *= 10
    actual = confirmed_pivots(shocked, 3, 3)
    pd.testing.assert_frame_equal(baseline.loc[:79], actual.loc[:79])
```

Test ties, NaNs, flat prices, and monotonic sequences.

**Step 2: Verify failure**

Run: `.venv/bin/python -m pytest tests/test_stack_components.py -k pivot -v`
Expected: FAIL because helper is absent.

**Step 3: Implement minimal helper**

Implement trailing-window confirmation equivalent to:

```python
window = left + 1 + right
rolling_high = high.rolling(window, min_periods=window).max()
confirmed = rolling_high.eq(high.shift(right))
pivot_high = high.shift(right).where(confirmed)
```

Emit the pivot level at confirmation time only. Never backfill onto the pivot candle.

**Step 4: Verify**

Run: `.venv/bin/python -m pytest tests/test_stack_components.py -k pivot -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add strategies/stack_components.py tests/test_stack_components.py
git commit -m "feat: add causal confirmed pivots"
```

### Task 3: Implement causal structure and protected swings

**Objective:** Emit BOS/CHoCH on the candle that closes through a previously confirmed level.

**Files:**
- Modify: `strategies/stack_components.py`
- Modify: `tests/test_stack_components.py`

**Step 1: Write failing tests**

Construct explicit bullish and bearish swing sequences. Assert:
- wick-only breaks do not count;
- BOS occurs on the break candle, not the swing candle;
- the impulse origin becomes protected;
- close through protected swing emits CHoCH;
- shocking future rows changes no earlier output.

**Step 2: Verify failure**

Run: `.venv/bin/python -m pytest tests/test_stack_components.py -k "structure or protected or choch or bos" -v`
Expected: FAIL.

**Step 3: Implement state machine**

Return columns `external_high`, `external_low`, `protected_high`, `protected_low`, `bos`, `choch`, and `bias_state`. Process rows forward once; only confirmed pivots may update structure.

**Step 4: Verify**

Run the focused tests, then `.venv/bin/python -m pytest tests/test_stack_components.py -v`.
Expected: PASS.

**Step 5: Commit**

```bash
git add strategies/stack_components.py tests/test_stack_components.py
git commit -m "feat: add causal STACK structure state"
```

### Task 4: Implement independently observable setup components

**Objective:** Compute each component without immediately conjoining it into a trade signal.

**Files:**
- Modify: `strategies/stack_components.py`
- Modify: `tests/test_stack_components.py`

**Step 1: Add failing tests** for:
- three-candle FVG confirmed on candle three;
- one-time mitigation state;
- premium/discount and OTE anchored to the protected displacement leg;
- liquidity wick sweep and close-back-inside;
- sweep followed by LTF confirmation within a configurable expiry, not necessarily one candle;
- session/weekend and momentum diagnostics;
- structural R/R using frozen entry stop and target.

Each helper receives a future-shock test.

**Step 2: Verify failure**

Run: `.venv/bin/python -m pytest tests/test_stack_components.py -k "fvg or ote or sweep or sequence or reward" -v`
Expected: FAIL.

**Step 3: Implement minimal helpers**

Expose atomic booleans/levels: `htf_bias_ok`, `sweep_event`, `bos_confirmation`, `discount_ok`, `ote_ok`, `fvg_ok`, `fvg_unmitigated`, `session_ok`, `weekend_ok`, `momentum_ok`, `rr_ok`.

**Step 4: Verify**

Run complete component tests. Expected: PASS and zero future-shock mismatches.

**Step 5: Commit**

```bash
git add strategies/stack_components.py tests/test_stack_components.py
git commit -m "feat: expose causal STACK setup components"
```

### Task 5: Create the ablation strategy without changing legacy LiquiditySweep

**Objective:** Build a Freqtrade strategy whose components can be enabled independently and whose entry tags identify the experiment.

**Files:**
- Create: `strategies/StackAblation.py`
- Create: `tests/test_stack_ablation_strategy.py`

**Step 1: Write failing strategy tests**

Test the core sequence `sweep -> BOS confirmation`; each optional gate independently blocks or allows an otherwise identical fixture. Assert `enter_tag` contains the experiment ID and side. Assert no import or call to `smartmoneyconcepts`.

**Step 2: Verify failure**

Run: `.venv/bin/python -m pytest tests/test_stack_ablation_strategy.py -v`
Expected: FAIL because strategy is absent.

**Step 3: Implement strategy**

Add explicit non-hyperopt toggles loaded from environment/config:

```python
COMPONENTS = {
    "htf_bias": True,
    "discount": True,
    "ote": True,
    "fvg": False,
    "fvg_one_time": False,
    "session": False,
    "weekend": True,
    "momentum": False,
    "min_rr": True,
}
```

Core trigger is always sweep followed by causal structure confirmation. Keep exits fixed during entry/filter ablations.

**Step 4: Verify**

Run tests and:

```bash
.venv/bin/freqtrade list-strategies --strategy-path strategies -c config_stack_ablation.json
```

Expected: `StackAblation` status `OK`, no duplicate name.

**Step 5: Commit**

```bash
git add strategies/StackAblation.py tests/test_stack_ablation_strategy.py
git commit -m "feat: add configurable STACK ablation strategy"
```

### Task 6: Add attrition and experiment runners

**Objective:** Measure signal availability before interpreting PnL.

**Files:**
- Create: `scripts/diagnose_stack_attrition.py`
- Create: `scripts/run_stack_ablations.py`
- Create: `research/stack/entry_ablation_matrix.json`
- Create: `tests/test_stack_ablation_runner.py`

**Step 1: Write failing runner tests**

Use a stub Freqtrade output. Assert deterministic command generation, one changed component per leave-one-out cell, explicit `--fee 0.0015`, no holdout command unless `--unlock-holdout`, and normalized JSON/CSV output.

**Step 2: Verify failure**

Run: `.venv/bin/python -m pytest tests/test_stack_ablation_runner.py -v`
Expected: FAIL.

**Step 3: Implement pre-registered entry matrix**

Cells:
- `E00_core`: sweep + causal BOS only;
- `E01_full`: all default STACK entry gates;
- leave-one-out: HTF bias, discount, OTE, FVG, one-time FVG, session, weekend, momentum, min-R;
- single-addition cells from core for the same filters.

Capture component hit counts, conjunction attrition, trades, expectancy, PF, Sharpe, drawdown, median R, win rate, and per-pair values.

**Step 4: Verify**

Run runner tests and diagnostic on validation only. Expected: PASS; result schemas validate.

**Step 5: Commit**

```bash
git add scripts/diagnose_stack_attrition.py scripts/run_stack_ablations.py research/stack/entry_ablation_matrix.json tests/test_stack_ablation_runner.py
git commit -m "test: add STACK component ablation runner"
```

### Task 7: Run causality and entry/filter ablations

**Objective:** Identify components that improve validation expectancy while exits and risk remain fixed.

**Files:**
- Create: `research/stack/results/entry_train.json`
- Create: `research/stack/results/entry_validation.json`
- Create: `research/stack/results/entry_summary.md`

**Step 1: Pre-flight causality**

Run all tests, then:

```bash
.venv/bin/freqtrade lookahead-analysis --config config_stack_ablation.json --strategy StackAblation --strategy-path strategies --datadir data/stack-ablation --timerange 20220101-20251231 --minimum-trade-amount 20 --fee 0.0015
.venv/bin/freqtrade recursive-analysis --config config_stack_ablation.json --strategy StackAblation --strategy-path strategies --datadir data/stack-ablation --timerange 20220101-20251231 -p BTC/USDT --startup-candle 100 200 400
```

Expected: no biased indicators/signals; low enough recursive variance for all signal inputs. Failure triggers Abort gate.

**Step 2: Run train matrix**

Run: `.venv/bin/python scripts/run_stack_ablations.py --split train --matrix entry`
Expected: every registered cell completes and exports results.

**Step 3: Run validation matrix unchanged**

Run: `.venv/bin/python scripts/run_stack_ablations.py --split validation --matrix entry`
Expected: no parameter changes between train and validation.

**Step 4: Analyze conservatively**

Rank by validation expectancy and PF, with drawdown constraint. A component “works” only if its direction agrees across train and validation and it does not rely on one pair. Do not inspect holdout.

**Step 5: Commit**

```bash
git add research/stack/results/entry_train.json research/stack/results/entry_validation.json research/stack/results/entry_summary.md
git commit -m "research: measure STACK entry components"
```

### Task 8: Ablate exits and risk on the frozen winning entry model

**Objective:** Separate signal quality from money-management effects.

**Files:**
- Modify: `strategies/StackAblation.py`
- Create: `research/stack/exit_ablation_matrix.json`
- Modify: `tests/test_stack_ablation_strategy.py`
- Modify: `tests/test_stack_ablation_runner.py`

**Step 1: Write failing tests** for frozen structural stop, ATR-buffered structural stop, external-liquidity target, 2R/3R target, time exit, and no-lookahead entry-level persistence.

**Step 2: Verify failure**

Run focused tests. Expected: FAIL.

**Step 3: Implement exit modes**

Keep winning entry configuration constant. Matrix varies one dimension at a time:
- stop: protected swing, protected swing + 0.25 ATR, fixed 2%;
- target: external liquidity, 2R, 3R;
- management: none, BE at 1R;
- time exit: off, 8h.

Do not combine all levels factorially until single-variable effects are known.

**Step 4: Verify and run train/validation**

Run tests, then runner for `exit` matrix on train and validation. Expected: complete machine-readable results; no holdout access.

**Step 5: Commit**

```bash
git add strategies/StackAblation.py research/stack/exit_ablation_matrix.json tests/test_stack_ablation_strategy.py tests/test_stack_ablation_runner.py research/stack/results
git commit -m "research: measure STACK exit and risk components"
```

### Task 9: Final untouched holdout and review

**Objective:** Evaluate exactly one pre-selected configuration once.

**Files:**
- Create: `research/stack/results/holdout.json`
- Create: `research/stack/results/final_report.md`

**Step 1: Spec revision gate**

Reviewer verifies causal timing, one-component experiment deltas, locked holdout, explicit costs, and no pair filtering based on results.

**Step 2: Quality revision gate**

Reviewer checks numerical safety, state persistence, tags, schema, test adequacy, and reproducibility.

**Step 3: Full verification**

```bash
git diff --check main...HEAD
.venv/bin/python -m pytest -q
.venv/bin/freqtrade lookahead-analysis --config config_stack_ablation.json --strategy StackAblation --strategy-path strategies --datadir data/stack-ablation --timerange 20220101-20251231 --minimum-trade-amount 20 --fee 0.0015
```

Expected: all green.

**Step 4: Unlock and run holdout once**

Run: `.venv/bin/python scripts/run_stack_ablations.py --split holdout --winner <preselected-id> --unlock-holdout`
Expected: exactly one strategy cell executed.

**Step 5: Write final report and commit**

Report train, validation, and holdout separately; list each component as supported, harmful, neutral, or inconclusive. Never call the strategy profitable unless net holdout expectancy is positive after fees with an adequate trade count and tolerable drawdown.

```bash
git add research/stack/results/holdout.json research/stack/results/final_report.md
git commit -m "research: validate causal STACK strategy"
```

Do not push without Marco's explicit permission.
