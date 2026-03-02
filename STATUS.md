# Liquidity Sweep Freqtrade — STATUS.md

> Single source of truth for project state, open items, and decisions.

---

## Current State

- **Version:** 0.38.0 (Hyperopt Results Applied)
- **Status:** Iterating based on 2026-02-27 Hyperopt run (results-122).
- **Branch:** `main`

---

## Latest Backtest Results (v0.38.0 - Hyperopt Estimation)

| Metric | Value | Notes |
|--------|-------|-------|
| Total Trades | **15** | 📉 Significantly lower volume (2-year backtest?). |
| Win Rate | **33.3%** (5W / 10L) | 📈 Improved WR over v0.35.0. |
| Profit Total | **+1.96%** | ✅ Back to profitability in simulation. |
| Avg Profit | +0.40% | |
| Strategy Logic | Relaxed Confluence | Hyperopt disabled `require_ote` and `require_fvg`. |

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

- [ ] **Analyze v0.36.0 backtest results** — expect 60-100 trades with improved quality. Magnet logic fix should significantly reduce stop-outs at liquidity magnets. Enhanced FVG check should improve entry timing.
- [ ] **Run hyperopt on v0.37.0 space** — focus on `atr_multiplier` (1.5-3.0) and `ote_lower/upper` (30-85).
- [ ] **Consider trailing entry** — Wait for price to start moving in our direction after hitting the FVG zone before entering.

---

## Session Log

| Date | Version | What Changed |
|------|---------|--------------|
| 2026-03-01 | 0.35.0 | Fixed FVG active zone detection bug. Volume recovered to 116 trades. |
| 2026-03-01 | 0.36.0 | Fixed Magnet Filter (inverted logic since v0.28). Enhanced FVG confluence (Price inside zone). Delayed ROI stale exits to improve avg win. |
| 2026-03-02 | 0.37.0 | Re-expanded OTE hyperopt bounds (30-85%) and ATR multiplier (1.0-3.0) to allow optimizer more room. |
