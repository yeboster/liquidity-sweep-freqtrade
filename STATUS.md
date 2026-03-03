# Liquidity Sweep Freqtrade — STATUS.md

> Single source of truth for project state, open items, and decisions.

---

## Current State

- **Version:** 0.40.0 (Confirmation Candle Filter)
- **Status:** Added `require_confirmation_candle` parameter (default=True, hyperoptable). Requires entry candle to be directionally aligned before entering. OTE 30-70% remains mandatory.
- **Branch:** `main`

---

## Latest Backtest Results (v0.38.0 - Reality)

| Metric | Value | Notes |
|--------|-------|-------|
| Total Trades | **9** | 📉 Volume ultra-low. |
| Win Rate | **11.1%** (1W / 8L) | ❌ Disastrous quality without OTE/FVG confluence. |
| Profit Total | **-2.61%** | ❌ Back to losses. |
| Avg Profit | -0.89% | |
| Strategy Logic | No Confluence | Hyperopt disabled `require_ote` and `require_fvg`. |

---

## Latest Backtest Results (v0.35.0)

| Metric | Value | Notes |
|--------|-------|-------|
| Total Trades | **116** | ✅ Volume recovered (FVG rolling window fix worked). |
| Win Rate | **19.0%** (22W / 94L) | ❌ Very poor. Strategy losing money (-24.6% profit). |
| Avg Win | +0.9% | Target was 1.5%. Most wins hit lower ROI tiers early. |
| Avg Loss | -1.6% | TSL (ATR-based) hits often after reversals fail. |
| Root Cause | Inverted Magnet logic | Detected v0.35.0 logic was checking the wrong FVG type for magnets. |

*Fixed in v0.36.0: (1) Corrected Magnet logic (Long skips if Bullish FVG below SL). (2) Enhanced FVG confluence (Price inside zone). (3) ROI tuned to push avg win higher.*

---

## Previous Backtest Results (v0.32.0)

| Metric | Value | Notes |
|--------|-------|-------|
| Total Trades | **2** | ❌ Bug/Tuning — `smc.ob()` is still too sparse, even with a 100-candle window. |
| Root Cause | Strict OB criteria | Order blocks are rarely identified by the library in a way that aligns with sweeps and ChoCH. Drops volume to near-zero. |

*Fixed in v0.33.0: `require_ob` set to False. Entry filtering now relies on `require_fvg=True` (active imbalance zone) and the opposite-side imbalance checker.*

---

## Previous Backtest Results (v0.29.0)

| Metric | Value | Change vs v0.27.0 |
|--------|-------|-------------------|
| Timerange | 2024-03-01 → 2026-02-28 | |
| Total Trades | **99** | 📉 -29 (was 128) |
| Win Rate | **24.2%** (24W / 75L) | 📈 +3.1% |
| Profit Total | **-19.16%** | 📈 +7.87% |
| Avg Duration | 2h 33m | ~Same |

### Exit Reason Breakdown
| Exit Reason | Trades | Avg Profit | Wins |
|-------------|--------|-----------|------|
| **roi** | 22 | +0.57% | 100% |
| **time_exit_6h** | 8 | -0.25% | 12.5% |
| **time_exit_4h** | 14 | -0.45% | 0% |
| **trailing_stop_loss** | 36 | -1.61% | 0% |

---

## Pending / Next Steps

- [ ] **Run hyperopt on v0.40.0** — `require_confirmation_candle` is now hyperoptable. Let optimizer decide if it helps.
- [ ] **Analyze trade volume** — if confirmation candle drops trades <30, disable it or loosen to allow doji entries.
- [ ] **Migrate Hyperopt to Docker-based CI** — eliminate silent failures and dependencies mismatch on host.
- [x] ~~**Consider trailing entry**~~ → Implemented as `require_confirmation_candle` in v0.40.0.

---

## Session Log

| Date | Version | What Changed |
|------|---------|--------------|
| 2026-03-03 | 0.40.0 | Added confirmation candle filter: entry candle must be directionally aligned (bullish for longs, bearish for shorts). Hyperoptable. Expected: fewer but higher-quality entries. |
| 2026-03-03 | 0.39.0 | Recovery Iteration: Re-enabled mandatory OTE filter (30-70%) after v0.38.0 hyperopt-disabled logic failed (11.1% WR). |
| 2026-03-02 | 0.38.0 | Applied Hyperopt results from Feb 27 run (results-122). Resulted in disastrous 11.1% WR. |
