# Liquidity Sweep Freqtrade — STATUS.md

> Single source of truth for project state, open items, and decisions.

---

## Current State

- **Version:** 0.19.0
- **Status:** ❌ Negative profitability (-40.7%), but signal quality is promising
- **Branch:** `master` — latest commit: `c4935cd`
- **Last Backtest:** 2026-02-20 (CI run #22221823996)

---

## Latest Backtest Results (v0.19.0)

| Metric | Value |
|--------|-------|
| Timerange | 2024-02-22 → 2026-02-20 (~2 years) |
| Total Trades | 465 |
| Win Rate | 51.2% (238W / 116L / 111D) |
| Profit Total | -40.69% |
| Profit Mean | -0.32% per trade |
| Profit Median | +0.105% (positive — skewed by big losses) |
| Max Drawdown | 45.3% |
| Avg Duration | 11h 45m |
| Profit Factor | 0.71 |

### Exit Reason Breakdown

| Exit Reason | Trades | Avg Profit | Wins | Losses |
|-------------|--------|-----------|------|--------|
| **ROI** | 321 | **+0.98%** | 210 | 0 |
| **target_liquidity** | 28 | **+1.16%** | 28 | 0 |
| **stop_loss** | 116 | **-4.29%** | 0 | 116 |

### Key Insight
The signal quality is GOOD — 349 profitable exits (ROI + target) at ~1% avg with ZERO losses.
But 116 stop losses at -4.29% avg wipe out all gains. The loss:win amount ratio is 4.3:1.

### Per-Pair Performance
| Pair | Trades | Avg % | Win Rate | Notes |
|------|--------|-------|----------|-------|
| ADA/USDT | 48 | +0.24% | 60% | ✅ Best performer |
| DOT/USDT | 45 | -0.21% | 62% | Decent WR but losses hurt |
| SOL/USDT | 54 | -0.15% | 56% | |
| ETH/USDT | 39 | -0.25% | 54% | |
| DOGE/USDT | 45 | -0.27% | 58% | |
| XRP/USDT | 54 | -0.41% | 44% | ⚠️ Below 50% |
| AVAX/USDT | 67 | -0.19% | 54% | Most trades |
| BTC/USDT | 59 | -0.48% | 42% | ⚠️ Worst WR |
| LINK/USDT | 54 | -1.10% | 35% | ❌ Worst performer |

---

## Root Cause Analysis

**Problem:** Asymmetric risk:reward. Wins avg +1%, losses avg -4.3%.

**Why:** 
1. Static -4% SL is too wide for the signal quality
2. ROI table catches winners early (5%→3%→2%→1%→0) but can't recover from full SL hits
3. No trailing mechanism to protect partial gains before SL is hit
4. The 111 draws (break-even ROI exits at 720m) suggest trades that go nowhere are held too long

**Fix strategy (v0.20.0):**
- Tighten stoploss to -2.5% (from -4%) — cuts avg loss nearly in half
- Add a time-based exit: if trade isn't profitable after 4h, close at market
- Consider a simple trailing stop: after +1% profit, trail at +0.3% (lock in small gain)
- Drop LINK/USDT from whitelist (35% WR, -1.1% avg — consistent underperformer)

---

## Pending / Next Steps

- [ ] **v0.20.0: Tighten risk management** — SL to -2.5%, time-based exit at 4h, optional trailing after +1%
- [ ] **Drop LINK/USDT** — consistently worst performer across all metrics
- [ ] **Run hyperopt** — optimize new SL + ROI + trailing params
- [ ] **Analyze draws** — 111 draws at 0% suggest ROI table `720: 0` is catching stale trades; consider negative ROI exit
- [ ] **Re-evaluate OTE filter** — v0.19 disabled it for volume; test with loose OTE (20-90%) vs no OTE
- [ ] **Per-pair parameter optimization** — ADA has 60% WR, BTC has 42%; different params per pair?
- [ ] **Add ATR-based dynamic SL** — instead of fixed %, use 1.5x ATR for market-adaptive stops
- [ ] **Migrate hyperopt to Docker CI** — current pip-based CI had silent failures before

---

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| OTE disabled (v0.19) | Doubles trade volume without significantly hurting WR |
| Custom stoploss disabled (v0.18) | Was creating trailing effect via updating swing levels |
| Static SL only | Simplest approach after trailing/custom SL issues in v0.15-0.18 |
| 3x leverage | Conservative for swing trades; avoids liquidation on 4% SL |
| Spot mode | Safer than futures; no funding rate drag |

---

## Session Log

| Date | Version | What Changed |
|------|---------|--------------|
| 2026-02-08 | 0.1-0.9 | Initial strategy build through hyperopt optimization |
| 2026-02-12 | 0.10 | Testing looser entry (optional OTE); 811 trades but -62% profit |
| 2026-02-13 | 0.10 | Decided to re-introduce OTE filter |
| 2026-02-19 | 0.15-0.17 | Custom SL fixes, trailing stop experiments |
| 2026-02-20 | 0.18-0.19 | Disabled custom SL + trailing, tightened static SL to -4%, disabled OTE |
| 2026-02-23 | 0.20.0 | **Tighten risk: SL → -2.5%, time exit 4h, trailing after +1%, drop LINK** |
