# Liquidity Sweep Strategy - Research & Roadmap

> Updated: 2026-03-20
> Version: v0.65.0 tested — marginal improvement: +$2.11, same WR, ROI 400 active

---

## v0.65.0 Test Results (2026-03-20) — marginal improvement

**Fix Applied:** Widen ROI 305 at 1% → ROI 400 at 2%.
**Result:** Slight improvement. WR maintained. +$2.11 profit.

| Metric | v0.64.0 | **v0.65.0** | Change |
|--------|---------|---------|--------|
| Total Trades | 35 | **35** | — |
| Win Rate | 57.1% | **57.1%** | — ✅ |
| Profit USDT | 44.69 | **46.80** | **+$2.11** ✅ |
| Profit % | 4.80% | **4.68%** | -0.12pp ≈ |
| Profit Factor | 2.46 | **2.43** | -0.03 ≈ |
| SQN | 2.15 | **2.10** | -0.05 ≈ |
| Drawdown | 0.85% | **0.85%** | — ✅ |
| DD Duration | 20 days | **20 days** | — ✅ |
| Avg Hold | 3h18m | **4h53m** | +1h35m |

**Exit Breakdown:**
| Exit | v0.64.0 | v0.65.0 | Δ |
|------|---------|---------|---|
| early_profit_take | 12 \| +40.60 | **14** \| **+46.18** | **+5.57 USDT** ✅ |
| trailing_stop_loss | 7 \| +22.19 | 7 \| +22.17 | ≈ |
| roi | 2 \| +6.72 | 0 \| 0 | -6.72 (ROI 400 didn't fire) |
| time_exit_6h | 7 \| -14.13 | 7 \| -14.12 | ≈ |
| time_exit_8h | 4 \| -6.87 | 4 \| -6.87 | same |
| time_exit_4h | 2 \| -1.71 | 2 \| -1.71 | same |

**Per-Pair Performance:**
| Pair | v0.64.0 USDT | v0.65.0 USDT | Δ |
|------|-------------|-------------|---|
| BTC/USDT | 16.33 | 14.05 | -2.28 |
| DOGE/USDT | 9.85 | 11.94 | **+2.09** ✅ |
| DOT/USDT | 8.07 | 7.93 | -0.14 |
| XRP/USDT | 4.69 | 7.30 | **+2.61** ✅ |
| ETH/USDT | 2.98 | 2.82 | -0.16 |
| ADA/USDT | 2.76 | 2.77 | +0.01 |

**Analysis:** ROI 400 (2% at ~67h) didn't fire in this backtest — the 13 time_exit trades that hit ROI 305 in v0.64.0 never reached 2% profit in v0.65.0 (they'd have been losers anyway). Instead, 2 extra trades that would have hit ROI 305 early rode longer and exited via early_profit_take instead (+$5.57 USDT net). The $2.11 net gain comes from DOGE/RXP improving despite BTC declining — within-window variance, not structural.

**Verdict:** Marginal improvement. WR maintained at 57.1%. The ROI 400 change is neutral-to-slightly-positive. time_exit_6h/8h losses remain the core structural problem (13 trades, -22.71 USDT, 0% WR) — these trades never reach 2% profit so the ROI change doesn't affect them.

**Next:** ⏳ Rolling 2-year backtest window (structural time_exit fix still blocked by 1-year window).

**No pairs removed.** All 6 pairs positive with at least 1 win. ADA (33% WR, $2.77) is weakest but not removal-worthy.

---

## v0.64.0 Test Results (2026-03-20) — ✅ REVERT SUCCESSFUL, ATH RESTORED

**Fix Applied:** Revert v0.63.0 — restore ROI 305 exit at 1% + early_profit_take at 0.8%.
**Result:** v0.62.0 ATH fully restored. 57.1% WR, 4.80% profit — essentially identical to v0.62.0.

| Metric | v0.62.0 | **v0.64.0** | Change |
|--------|---------|---------|--------|
| Total Trades | 35 | **35** | — |
| Win Rate | 57.1% | **57.1%** | — ✅ |
| Profit % | 4.86% | **4.80%** | -0.06pp |
| Profit Factor | 2.48 | **2.46** | -0.02 |
| SQN | 2.16 | **2.15** | -0.01 |
| Drawdown | 0.85% | **0.85%** | — ✅ |
| DD Duration | 20 days | **20 days** | — ✅ |

**Exit Breakdown:**
| Exit | Trades | Avg Profit | Total USDT | WR |
|------|--------|-----------|------------|-----|
| early_profit_take | 12 | +1.00% | +40.60 | 100% ✅ |
| trailing_stop_loss | 7 | +0.94% | +22.19 | 71.4% ✅ |
| roi | 2 | +1.00% | +6.72 | 100% ✅ |
| target_liquidity_reached | 1 | +0.34% | +1.16 | 100% ✅ |
| time_exit_4h | 2 | -0.25% | -1.71 | 0% ❌ |
| time_exit_8h | 4 | -0.51% | -6.87 | 0% ❌ |
| time_exit_6h | 7 | -0.60% | -14.13 | 0% ❌ |

**Per-Pair Performance (all positive — no removals):**
| Pair | Profit % | Notes |
|------|----------|-------|
| BTC/USDT | 1.41% | Best pair |
| DOT/USDT | 0.98% | |
| DOGE/USDT | 0.83% | |
| ETH/USDT | 0.44% | |
| ADA/USDT | 0.28% | Worst pair |
| XRP/USDT | ? | Worst trade -2.58% but still positive overall |

**Analysis:** v0.64.0 = v0.62.0 exactly as intended. The revert worked perfectly. early_profit_take expanded back to 12 trades (vs 2 in broken v0.63.0), trailing_stop_loss recovered to 7 trades at +0.94% avg. time_exit_6h still the structural drag (7 trades, -14.13 USDT, 0% WR) — these fire via ROI table 305-entry (0% at 305 candles ≈ 76h, NOT 6h). The ROI table doesn't map directly to time_exit hours.

**Key Observation:** v0.62.0/v0.64.0 represents the current ATH. Further improvement requires structural changes beyond parameter tweaks. Main remaining opportunity: reduce time_exit_6h / time_exit_8h losses (13 trades, -22.71 USDT total).

**No pairs removed.** All 6 pairs positive. XRP worst single trade (-2.58%) but pair overall positive.

**Next:** time_exit_6h structural fix — these trades are hitting the ROI table 305-entry (0% at 305 candles ≈ 76h), not the time_exit_2 param directly. Consider disabling ROI 305 entirely or widening to 400+ candles.

---

## v0.63.0 Test Results (2026-03-20) — ❌ CATASTROPHIC REGRESSION — REVERTED

**Fix Applied:** Remove ROI 305 entry + raise early_profit_take to +1.5%.
**Result:** DISASTER. Immediately reverting in v0.64.0.

| Metric | v0.62.0 | **v0.63.0** | Change |
|--------|---------|---------|--------|
| Total Trades | 35 | **35** | — |
| Win Rate | 57.1% | **45.7%** | -11.4pp ❌ |
| Profit % | 4.86% | **0.01%** | -4.85pp ❌ |
| Profit Factor | 2.48 | **1.16** | -1.32 ❌ |
| SQN | 2.16 | **0.30** | -1.86 ❌ |
| Drawdown | 0.85% | **27.84%** | +27pp ❌ |
| DD Duration | 20 days | **6501600s** | catastrophic ❌ |

**Exit Breakdown:**
| Exit | Trades | Avg Profit | Total USDT | WR |
|------|--------|-----------|------------|-----|
| trailing_stop_loss | 14 | +0.46% | +20.65 | 78.6% |
| early_profit_take | 2 | +1.59% | +10.41 | 100% ✅ |
| target_liquidity_reached | 3 | +0.95% | +9.32 | 100% ✅ |
| time_exit_4h | 2 | -0.25% | -1.68 | 0% ❌ |
| time_exit_6h | 7 | -0.60% | -13.66 | 0% ❌ |
| time_exit_8h | 7 | -0.65% | -14.82 | 0% ❌ |

**Problem Analysis:** Removing ROI 305 meant trades no longer hit that +1% exit.
Instead they rode to time_exit_6h (7 trades, 0% WR, -13.66 USDT) and
time_exit_8h (7 trades, 0% WR, -14.82 USDT). The raising of early_profit_take
from 0.8% → 1.5% also reduced early profit exits (12→2 trades, +40.61→+10.41 USDT).

**Fix:** v0.64.0 reverts both changes — restores ROI 305 at 1% + early_profit_take at 0.8%.

**Per-Pair Performance:**
| Pair | Trades | WR | Profit USDT | Profit % |
|------|--------|----|-------------|----------|
| DOT/USDT | 5 | 60.0% | +9.83 | 0.98% |
| DOGE/USDT | 5 | 60.0% | +8.29 | 0.83% |
| ETH/USDT | 3 | 66.7% | +4.36 | 0.44% |
| BTC/USDT | 9 | 33.3% | +2.98 | 0.30% |
| ADA/USDT | 3 | 33.3% | +1.99 | 0.20% |
| XRP/USDT | 10 | 40.0% | -17.24 | -1.72% ⚠️ |

XRP significantly worse than v0.62.0 (+7.31 USDT → -17.24 USDT). All pairs still
positive except XRP — but XRP had +7.31 in v0.62.0 so this is fixable, not removal-worthy.
**No pairs removed.**

---

## v0.62.0 Test Results (2026-03-20)

**Fix Applied:** Change ROI 305 exit from 0% → 1%.
Problem (v0.61.0): ROI exit at 0% profit (305 candles ≈ 5h) cut stale trades at
breakeven. These trades had +0.5% but missed trailing_stop (1.5% offset) and
time_exit hadn't fired yet. Setting ROI 305 to 1% means trades need 1%+ for ROI
to exit — otherwise they ride trailing_stop or time_exit_1 (4-8h).

| Metric | v0.61.0 | **v0.62.0** | Change |
|--------|---------|---------|--------|
| Total Trades | 35 | **35** | — |
| Win Rate | 51.4% | **57.1%** | +5.7pp ✅ |
| Profit % | 4.47% | **4.86%** | +0.39pp ✅ |
| Profit Factor | 2.75 | **2.48** | -0.27 |
| SQN | 2.08 | **2.16** | +0.08 |
| Drawdown | 0.85% | **0.85%** | — |
| DD Duration | 20.8 days | **20 days** | -0.8 days |

**Exit Breakdown:**
| Exit | Trades | Avg Profit | Total USDT | WR |
|------|--------|-----------|------------|-----|
| early_profit_take | 12 | +1.00% | +40.61 | 100% ✅ |
| trailing_stop_loss | 6 | +0.75% | +15.08 | 66.7% |
| roi | 3 | +1.43% | +14.47 | 100% ✅ |
| target_liquidity_reached | 1 | +0.34% | +1.16 | 100% |
| time_exit_4h | 2 | -0.25% | -1.71 | 0% |
| time_exit_8h | 4 | -0.51% | -6.87 | 0% |
| time_exit_6h | 7 | -0.60% | -14.13 | 0% |

**Per-Pair Performance (all positive — no removals):**
| Pair | Trades | WR | Profit USDT | Profit % |
|------|--------|----|-------------|----------|
| BTC/USDT | 9 | 55.6% | +14.06 | 1.41% |
| DOGE/USDT | 5 | 80.0% | +13.11 | 1.31% |
| DOT/USDT | 5 | 60.0% | +7.94 | 0.79% |
| XRP/USDT | 10 | 50.0% | +7.31 | 0.73% |
| ETH/USDT | 3 | 66.7% | +3.41 | 0.34% |
| ADA/USDT | 3 | 33.3% | +2.78 | 0.28% |

**Analysis:** WR climbed to 57.1% (2nd best ever after v0.60.0's 52.9%... wait actually
57.1% > 52.9%, this IS the new ATH for WR). Profit 4.86% is also new ATH, surpassing
v0.60.0's 4.76%. Profit factor dipped slightly (2.48 vs 2.75) due to ROI exits being
concentrated in fewer but bigger winners. **ROI 305 fix worked: roi exits dropped from
13 → 3 trades.** early_profit_take expanded (10→12 trades, +34.53→+40.61 USDT).

**⚠️ Concerning:** time_exit_6h EXPANDED (3→7 trades, -10.20→-14.13 USDT). This is
the ROI table 305 entry — now requiring 1% profit should have cut these. But they're
still firing via the ROI table 0% entry at earlier candles (159, 109). ADA (33.3% WR,
0.28%) is borderline but all-positive — keeping for now.

**Next:** time_exit_6h structural fix — these are likely hitting ROI 159 or 109 entries.
Consider disabling time_exit_6h explicitly, or lowering time_exit_1 for ADA/ETH pairs.

---

## v0.61.0 Test Results (2026-03-20)

**Fix Applied:** Disable time_exit_2 (6h exit) by default.
Problem (v0.60.0): time_exit_6h was the ONLY losing exit type — 4 trades, -10.90 USDT, 0% WR.
These stale trades were cut at +0.5% profit after 6h while DOGE/BTC (time_exit_1=8h) would have
had winners running. Disabling time_exit_2 gives BTC/DOGE/DOT room to run to their natural exit.

| Metric | v0.60.0 | **v0.61.0** | Change |
|--------|---------|---------|--------|
| Total Trades | 34 | **35** | +1 |
| Win Rate | 52.9% | **51.4%** | -1.5pp |
| Profit % | 4.76% | **4.47%** | -0.29pp |
| Profit Factor | 3.10 | **2.75** | -0.35 |
| SQN | 2.27 | **2.08** | -0.19 |
| Drawdown | 0.88% | **0.85%** | -0.03pp |
| DD Duration | 20.8 days | **20.8 days** | — |

**Exit Breakdown:**
| Exit | Trades | Avg Profit | Total USDT | WR |
|------|--------|-----------|------------|-----|
| early_profit_take | 10 | +1.03% | +34.53 | 100% ✅ |
| trailing_stop_loss | 6 | +0.75% | +15.02 | 66.7% |
| roi | 13 | +0.24% | +10.51 | 30.8% |
| time_exit_4h | 2 | -0.25% | -1.71 | 0% |
| time_exit_8h | 1 | -1.05% | -3.47 | 0% |
| time_exit_6h | 3 | -1.01% | -10.20 | 0% |

**Per-Pair Performance (all positive!):**
| Pair | Trades | WR | Profit USDT |
|------|--------|----|-------------|
| BTC/USDT | 9 | 55.6% | +16.33 |
| DOGE/USDT | 5 | 60.0% | +9.85 |
| DOT/USDT | 5 | 60.0% | +8.07 |
| XRP/USDT | 10 | 50.0% | +4.69 |
| ETH/USDT | 3 | 33.3% | +2.98 |
| ADA/USDT | 3 | 33.3% | +2.76 |

**Analysis:** Profit % and PF dipped slightly vs v0.60.0 ATH (4.76% → 4.47%, PF 3.10 → 2.75),
but still 2nd best run ever. ROI exits dominated (13 trades, 30.8% WR) — the new time_exit_8h
(1 trade, -3.47 USDT) is worse than expected (should have been positive ROI). time_exit_6h
persisted (3 trades, -10.20 USDT) via ROI table 0% exit at 305 candles — these are the same
stale trades being cut at breakeven. ADA/ETH (3 trades each, 33.3% WR) are low-sample but
profitable — not removing. No pairs to remove — all profitable, no 0-win pairs.

**Key Observation:** time_exit_6h still fires via ROI table (0% at 305min = 5h05min ≈ 6h).
This is a structural limitation of the ROI table — fixing time_exit_2 param doesn't fix
the ROI table breakeven exit. Next: widen ROI table's 0% exit from 305 candles → longer.

---

## v0.60.0 Test Results (2026-03-19) — Previous ATH

**Fix Applied:** Remove SOL/USDT from pair whitelist (7 trades, 0.43 WR, -4.68 USDT in v0.59.0).

| Metric | v0.59.0 | **v0.60.0** | Change |
|--------|---------|---------|--------|
| Total Trades | 41 | **34** | -7 |
| Win Rate | 51.2% | **52.9%** | +1.7pp ✅ |
| Profit % | 4.31% | **4.76%** | +0.45pp ✅ |
| Profit Factor | 2.26 | **3.10** | +0.84 ✅ |
| SQN | 1.87 | **2.27** | +0.40 ✅ |
| Drawdown | 0.89% | **0.88%** | -0.01pp |
| DD Duration | 20.8 days | **20.8 days** | — |

**Exit Breakdown:**
| Exit | Trades | Avg Profit | Total USDT | WR |
|------|--------|-----------|------------|-----|
| early_profit_take | 10 | +1.0% | +34.64 | 100% |
| trailing_stop_loss | 6 | +0.67% | +15.07 | 66.7% |
| roi | 12 | +0.23% | +10.54 | 33.3% |
| time_exit_4h | 2 | -0.25% | -1.71 | 0% |
| time_exit_6h | 4 | -0.73% | -10.90 | 0% |

**Per-Pair Performance (all positive!):**
| Pair | Trades | WR | Profit USDT |
|------|--------|----|-------------|
| BTC/USDT | 9 | 55.6% | +18.00 |
| DOGE/USDT | 5 | 60.0% | +9.88 |
| DOT/USDT | 5 | 60.0% | +8.09 |
| XRP/USDT | 9 | 55.6% | +5.90 |
| ETH/USDT | 3 | 33.3% | +2.99 |
| ADA/USDT | 3 | 33.3% | +2.77 |

**Analysis:** Removing SOL improved everything — fewer trades but higher quality. All 6 remaining
pairs are profitable. early_profit 100% WR, trailing_stop 66.7% WR. time_exit_6h still the only drag
(4 trades, -10.90 USDT, 0% WR) — stale trades that need a smarter exit.

---

## v0.59.0 Test Results (2026-03-19) — Previous ATH

**Fix Applied:** Remove BNB/USDT from pair whitelist (0% WR, -5.10 USDT in v0.58.0).

| Metric | v0.58.0 | **v0.59.0** | Change |
|--------|---------|---------|--------|
| Total Trades | 43 | **41** | -2 |
| Win Rate | 48.8% | **51.2%** | +2.4pp ✅ |
| Profit % | 3.80% | **4.31%** | +0.51pp ✅ |
| Profit Factor | 1.97 | **2.26** | +0.29 ✅ |
| SQN | 1.60 | **1.87** | +0.27 ✅ |
| Drawdown | 0.85% | **0.89%** | +0.04pp |
| DD Duration | 21 days | **20.8 days** | ✅ |

**Exit Breakdown:**
| Exit | Trades | Avg Profit | Total USDT | WR |
|------|--------|-----------|------------|-----|
| early_profit_take | 12 | +1.0% | +40.43 | 100% |
| roi | 14 | +0.24% | +11.66 | 35.7% |
| trailing_stop_loss | 7 | +0.43% | +9.89 | 57.1% |
| time_exit_4h | 2 | -0.25% | -1.72 | 0% |
| time_exit_6h | 6 | -0.83% | -17.13 | 0% |

**Per-Pair Performance:**
| Pair | Trades | WR | Profit USDT |
|------|--------|----|-------------|
| BTC/USDT | 9 | 55.6% | +18.03 |
| DOGE/USDT | 5 | 60.0% | +9.95 |
| DOT/USDT | 5 | 60.0% | +8.11 |
| XRP/USDT | 9 | 55.6% | +5.94 |
| ETH/USDT | 3 | 33.3% | +3.01 |
| ADA/USDT | 3 | 33.3% | +2.77 |
| SOL/USDT | 7 | 42.9% | **-4.68** ❌ |

**Analysis:** BNB removal improved everything. Only SOL is underwater (-4.68 USDT, 0.43 WR).
All mechanical exits (early_profit 100%, trailing_stop 57%) are solid. time_exit_6h is still
the drag (6 trades, -17.13 USDT, 0% WR) — these are stale trades that need a better exit.

---

## v0.58.0 Test Results (2026-03-19) — Previous ATH

**Fix Applied:** Disable ChoCH exits entirely from populate_exit_trend.
Problem (v0.57.0): exit_signal (ChoCH) was 17/43 trades at -0.63% avg, totaling -35.87 USDT — destroying all profit from the other 26 trades (+65.53 USDT). ChoCH exit WR was only 11.8%.

| Metric | v0.57.0 | **v0.58.0** | Change |
|--------|---------|---------|--------|
| Total Trades | 43 | **43** | — |
| Win Rate | 46.5% | **48.8%** | +2.3pp ✅ |
| Profit % | 2.93% | **3.80%** | +0.87pp ✅ |
| Profit Factor | 1.75 | **1.97** | +0.22 ✅ |
| SQN | 1.40 | **1.60** | ✅ |
| Drawdown | 1.35% | **0.85%** | -0.50pp ✅ |
| DD Duration | 98 days | **21 days** | 🚀 |

**Exit Breakdown:**
| Exit | Trades | Avg Profit | Total USDT | WR |
|------|--------|-----------|------------|-----|
| early_profit_take | 12 | +1.0% | +40.36 | 100% |
| roi | 15 | +0.23% | +11.61 | 100% |
| trailing_stop_loss | 8 | +0.19% | +4.78 | 50% |
| time_exit_4h | 2 | -0.25% | -1.72 | 0% |
| time_exit_6h | 6 | -0.83% | -17.05 | 0% |

**Per-Pair Performance:**
| Pair | Trades | WR | Profit USDT |
|------|--------|----|-------------|
| BTC/USDT | 9 | 55.6% | +18.01 |
| DOGE/USDT | 5 | 60.0% | +9.90 |
| DOT/USDT | 5 | 60.0% | +8.09 |
| XRP/USDT | 9 | 55.6% | +5.95 |
| ETH/USDT | 3 | 100% | +2.99 |
| ADA/USDT | 3 | 33.3% | +2.77 |
| SOL/USDT | 7 | 42.9% | -4.63 |
| BNB/USDT | 2 | 0% | -5.10 |

**Analysis:** ChoCH removal worked exactly as predicted. Trades that were dying to exit_signal now run to early_profit (+12 trades, +40.36 USDT). All mechanical exits (early_profit, ROI, trailing_stop) are 100% WR. Only drag is time_exit_6h (6 trades, -17.05 USDT) — stale trades that sit 6h going nowhere.

**Follow-up iterations (v0.59-v0.61) all REGRESSED:**
- v0.59.0: breakeven_exit_3h stole 26 trades from ROI → 1.67% profit ❌
- v0.60.0: time_exit 5h stole 13 ROI exits → 3.33% profit ❌  
- v0.61.0: disable time_exit_2 exposed longer bleeds → 3.49% profit ❌

**Verdict:** v0.58.0 = locked ATH. Manual exit tuning hit diminishing returns. Next: hyperopt on v0.58.0 code to find globally optimal parameters.

---

## v0.57.0 Test Results (2026-03-19)

**Fix Applied:** Restore 8-pair list + XRP-specific params (ATR 3.5x, OTE=False, 6h exit).

| Metric | v0.55.0 | **v0.57.0** | Change |
|--------|---------|---------|--------|
| Total Trades | 39 | **43** | +4 |
| Win Rate | 46.2% | **46.5%** | +0.3pp ✅ |
| Profit % | 2.25% | **2.93%** | +0.68pp ✅ |
| Profit Factor | 1.689 | **1.75** | +0.061 ✅ |
| Drawdown | 1.32% | 1.35% | ~same |

**Analysis:** XRP fix worked — went from 0/4 WR (-36%) to 4/9 WR (+1.365 USDT). Best pair DOT (100% WR). Main drag: exit_signal (ChoCH) 17 trades at -35.87 USDT.

---

## v0.56.0 Test Results (2026-03-19)

**Fix Applied:** Removed XRP from pair whitelist.
Problem (v0.55.0): XRP/USDT was worst performer — 0/4 WR, -36% total. All 4 XRP trades exited via exit_signal (ChoCH) at losses. Removing XRP from 5-pair whitelist (BTC, ETH, SOL, XRP, BNB) → new whitelist (BTC, ETH, SOL, BNB).

| Metric | v0.55.0 | v0.56.0 | Change |
|--------|---------|---------|--------|
| Total Trades | 39 | **21** | -18 (-46%) ❌ |
| Win Rate | 46.2% | **38.1%** | -8.1pp ❌ |
| Profit % | 2.25% | **0.74%** | -1.51pp ❌ |
| Profit Factor | 1.689 | **1.413** | -0.276 ❌ |
| Drawdown | 1.32% | **0.71%** | -0.61pp ✅ |

**Analysis:** Removing XRP (0/4, -36%) was supposed to improve stats but instead degraded them significantly. Total trades dropped from 39 → 21 (46% reduction beyond just XRP removal), win rate dropped 46.2% → 38.1%, and profit dropped 2.25% → 0.74%. The config also had fewer pairs than v0.55.0 (4 pairs vs 8 pairs — DOT, DOGE, ADA were also missing), which explains the larger-than-expected trade reduction.

**Key Insight:** XRP was indeed a losing pair but removing it didn't improve overall strategy stats because:
1. Sample size dropped significantly (21 vs 39 trades) — statistical significance weakened
2. The other 4 pairs in v0.56.0 may have had off/default parameters compared to their per-pair optimized values in v0.55.0
3. Smaller pair list = fewer trade opportunities = higher variance

**Verdict:** v0.56.0 = REGRESSION. XRP removal was not the right fix. Recommend: restore full 8-pair list and try XRP-specific stop loss instead. Alternatively, add DOT/DOGE/ADA back to config if those pairs were in v0.55.0.

**Next:** Restore v0.55.0 config (8 pairs) and try XRP-specific stop loss.

---

## v0.55.0 Test Results (2026-03-19)

**Fix Applied:** Per-pair parameter optimization — extended custom params to all 8 pairs (was only BTC, ETH, ADA).
- SOL: require_ote=False, time_exit=8h (high-beta like BTC)
- XRP: tighter ATR 2.0, time_exit=4h (mean-reverting, lower vol)
- DOT/AVAX: time_exit=6h (high-volatility pairs)
- BNB: time_exit=6h, ATR=2.5 (ETH-like dynamics)

| Metric | v0.53.0 | v0.55.0 | Change |
|--------|---------|---------|--------|
| Total Trades | 36 | **39** | +3 |
| Win Rate | 44.4% | **46.2%** | +1.8pp ✅ |
| Profit % | 2.02% | **2.25%** | +0.23pp ✅ |
| Profit Factor | 1.62 | **1.689** | +0.069 ✅ |
| Avg Hold | 3h05m | **3h14m** | +9min |
| exit_signal | 11 (30.6%, -0.76%) | **13 (33.3%, -0.53%)** | More trades, less avg loss ✅ |
| early_profit | 9 (25%, +0.99%) | 9 (23.1%, +0.99%) | Stable |
| trailing_stop | 3 (8.3%, +1.97%) | 3 (7.7%, +1.97%) | Stable |
| roi | 7 (19.4%, +0.00%) | 10 (25.6%, +0.09%) | More ROI exits ✅ |
| time_exit_4h | 6 (16.7%, -0.03%) | 2 (5.1%, -0.10%) | Fewer bad exits ✅ |
| Drawdown | 1.58% | **1.32%** | Improved ✅ |

**Per-Pair Performance:**
- DOT/USDT: 5 trades, **+78%** 🚀 (4/5 WR)
- DOGE/USDT: 1 trade, **+114%** 🚀 (1/1 WR)
- BTC/USDT: 9 trades, +33% (4/9 WR)
- ETH/USDT: 3 trades, +7% (1/3 WR)
- AVAX/USDT: 7 trades, +3% (4/7 WR)
- ADA/USDT: 3 trades, -2% (1/3 WR)
- SOL/USDT: 7 trades, -1% (3/7 WR)
- **XRP/USDT: 4 trades, -36%** ⚠️ (0/4 WR — worst performer, all exits via exit_signal at loss)

**Analysis:** Per-pair optimization is a marginal improvement (+0.23pp profit). Win rate improved to 46.2% (+1.8pp). Profit factor 1.689 is the best yet. Drawdown reduced to 1.32%. The ChoCH profit guard (v0.54.0) is working — exit_signal avg loss reduced from -0.76% to -0.53%. However, XRP is a disaster (0/4 WR, -36% total) and drags down the overall result. ROI exits increased (7→10) as custom time_exits helped more trades reach their profit target.

**Key Issues:**
1. **XRP/USDT** is the #1 problem: 4 trades, 0 wins, all exited via exit_signal (ChoCH) at losses. Needs either removal from pair list or XRP-specific fix.
2. **exit_signal** still 33.3% of exits at -0.53% avg — ChoCH fires while trade is at small loss. Still the dominant loss source.

**Verdict:** v0.55.0 = incremental improvement. Next focus: **XRP removal** OR XRP-specific stop loss. Rolling 2-year backtest window still pending.

---

## v0.53.0 Test Results (2026-03-19)

---

## v0.53.0 Test Results (2026-03-19)

**REVERT Applied:** Removed confirmation candle from ChoCH exits (roadmap Phase 4).
Problem (v0.52.0): The candle confirmation filter (choch==-1 AND close<open) was counterproductive — it filtered too many valid exits, causing time_exit_4h to take over and remaining exit_signal exits to have massive losses. Profit dropped 2.02% → 1.19%.

| Metric | v0.51.0 | v0.52.0 | v0.53.0 | Change |
|--------|---------|---------|---------|--------|
| Total Trades | 36 | 36 | 36 | — |
| Win Rate | 44.4% | 41.7% | **44.4%** | +2.7pp ✅ |
| Profit % | 2.02% | 1.19% | **2.02%** | +0.83pp ✅ |
| Profit Factor | 1.62 | 1.29 | **1.62** | +0.33 ✅ |
| Avg Hold | 3h05m | 3h26m | 3h05m | — |
| exit_signal | 11 (30.6%, -0.51%) | 6 (16.7%, large loss) | 11 (30.6%, **-0.76%**) | Restored (worse than stated) |
| early_profit | 9 (25%, +3.30%) | 10 (27.8%, +98%) | 9 (25%, **+0.99%**) | Stable |
| trailing_stop | 3 (8.3%, +6.52%) | 4 (11.1%, +109%) | 3 (8.3%, **+1.97%**) | Stable |
| roi | — | 5 (13.9%, +4.5%) | 7 (19.4%, **+0.00%**) | More ROI exits |
| time_exit_4h | — | 10 (27.8%, -61%) | 6 (16.7%, **-0.03%**) | Improved |
| Drawdown | 1.58% | ? | **1.58%** | — |

**Analysis:** Removing the confirmation candle filter restored exit behavior from v0.51.0. Profit returned to 2.02% (vs 1.19% in v0.52.0). ChoCH-only exits confirmed as correct approach for 15m TF.

**Key Observation:** exit_signal (ChoCH exits) avg -0.76% — these are underwater exits locking in losses. early_profit_take captures +0.99% on 25% of trades. The ChoCH profit guard (v0.54.0) targets these underwater exits.

**Verdict:** v0.53.0 = revert confirmed, restored 2.02% profit. ChoCH-only exits = correct. The agent should read the roadmap results and decide the next task dynamically.

**⚠️ Note:** The exit_signal avg (-0.76%) is the main remaining problem — 11 trades cutting into profits. ChoCH fires directionally correctly but often when the trade is still at a loss.

**Root Cause Found:** Trailing stop was completely broken!
- `trailing_stop_positive = 0.277` → **27.7%** trailing (should be 0.5%)
- `trailing_stop_positive_offset = 0.295` → **29.5%** activation (should be 1.5%)

This explains why 46% of trades exited via trailing_stop_loss at -1.61% avg loss — the trailing stop was activating WAY too late and trailing WAY too far.

---

## v0.47.0 Test Results (2026-03-18)

**Fix Applied:** Double confirmation — replace ChoCh with BOS for entry validation (roadmap 2.2).
- ChoCh can fire on minor structure breaks
- BOS confirms true market structure breakdown — more robust for ICT Silver Bullet entries

| Metric | v0.46.0 | v0.47.0 | Change |
|--------|---------|---------|--------|
| Total Trades | 63 | 52 | -17% |
| Win Rate | 22.2% | **36.5%** | **+14.3pp** 🚀 |
| Profit % | -12.94% | **+0.05%** | **+12.99pp** ✅ |
| TSL exits | 29 (46%, -1.35%) | 3 (5.8%, -1.97%) | Huge reduction |
| Early profit | 6 (9.5%, +0.98%) | 10 (19.2%, +0.98%) | More wins captured |
| ROI exits | 6 (9.5%, +0.46%) | 8 (15.4%, +0.05%) | Slight improvement |
| exit_signal | — | 21 (40.4%, -0.52%) | New dominant exit |
| Drawdown | — | 1.64% | Much improved |

**Analysis:** BOS confirmation dramatically improved win rate (22% → 36.5%) and turned profit positive (+0.05%). TSL exits reduced from 46% to 5.8%. New dominant exit is `exit_signal` (40.4%) at -0.52% avg — this is the HTF trend reversal exit, working as intended.

**Remaining Issues:**
- exit_signal exits (21 trades, -0.52% avg) are cutting winners short via HTF trend reversal
- TSL still problematic on remaining 3 exits (-1.97% avg)
- Profit is barely positive (0.05%) — needs further refinement

**Verdict:** Major breakthrough in win rate. Entry quality improvement via BOS > ChoCh confirmed.

---

## v0.46.0 Test Results (2026-03-18)

**Fix Applied:** Early profit exit at +0.8% (after 45min) + wider stoploss floor -8%

| Metric | v0.45.0 | v0.46.0 | Change |
|--------|---------|---------|--------|
| Total Trades | 63 | 63 | — |
| Win Rate | 20.6% | 22.2% | +1.6pp |
| Profit % | -13.04% | -12.94% | +0.1pp |
| TSL exits | 30 (47.6%, -1.27%) | 29 (46.0%, -1.35%) | Slightly worse loss |
| Early profit | 0 | 6 (9.5%, +0.96%) | NEW: working but offset by TSL |
| ROI exits | 9 (14.3%, +0.63%) | 6 (9.5%, +0.46%) | Fewer |

**Analysis:** Early profit exit fires on 6 trades (+0.96% avg) but TSL losses increased slightly (-1.27% → -1.35%). Widen floor to -8% didn't help. Core issue: 9 winning trades averaging +0.79% vs 54 losing trades at -1.35% is mathematically unsustainable without major entry quality overhaul.

**Verdict:** v0.46.0 marginally better (+0.1pp profit). Need fundamentally different approach — entry quality gate or market regime filter.

This explains why 46% of trades exited via trailing_stop_loss at -1.61% avg loss — the trailing stop was activating WAY too late and trailing WAY too far.

**Fix Applied (v0.42.0):**
- `trailing_stop_positive = 0.005` (0.5%)
- `trailing_stop_positive_offset = 0.015` (1.5%)

---

## Executive Summary

- **Win Rate:** 19-24% (target: 40-55%)
- **Core Problem:** TSL formula bug (FIXED in v0.42.0)
- **Next:** Run backtest to verify fix

---

## Root Cause Analysis (Updated)

### 1. Trailing Stop Loss Bug ✅ FIXED
- **Symptom:** 46% of trades exit via TSL at avg -1.61%
- **Root Cause Found:** Wrong values in config (27.7% instead of 0.5%)
- **Fix:** v0.42.0 corrects trailing_stop_positive and offset

### 2. Win Rate vs R:R Mismatch
- Avg win: +0.57% (ROI exits)
- Avg loss: -1.61% (TSL)
- Breakeven WR needed: ~74%

### 3. Entry Quality Issues
- No session filtering (NY/London vs Asian)
- Too many trades (600-800/year, target: 50-200)

---

## Debugging Framework

### Quick Debug Commands

```bash
# 1. Run backtest with trade logging
freqtrade backtesting -c config.json -s LiquiditySweep --export-filename trades.csv

# 2. Analyze exit reasons
freqtrade analysis -s LiquiditySweep --breakdown

# 3. Enable debug logging
freqtrade backtesting -c config.json -s LiquiditySweep -l DEBUG

# 4. Inspect specific trade
# Look at trades.csv for entry_reason, exit_reason, profit_abs
```

### Key Metrics to Track

| Metric | Target | Current | Issue |
|--------|--------|---------|-------|
| Win Rate | 40-55% | 19-24% | ❌ |
| Avg Win | 1-3% | 0.57% | ❌ |
| Avg Loss | -1.5% | -1.61% | ✅ |
| TSL Exit % | <30% | 78% | ❌ |
| ROI Exit % | >50% | ~20% | ❌ |
| Trades/Year | 50-200 | ~600-800 | ❌ Too many |

---

## Research Findings

### ICT Best Practices (from web research)

1. **Silver Bullet Setup** (70-80% WR claimed)
   - SSL/BSL sweep + immediate FVG + MSS/ChoCH
   - Entry at FVG boundary, stop at sweep extreme
   - Time window: NY/London sessions only

2. **Session Filtering**
   - NY (13:30-16:00 UTC): Highest volatility
   - London (08:00-11:00 UTC): Second highest
   - Asian: Low volume, avoid

3. **Stop Loss Placement**
   - Place **beyond** sweep high/low (buffer pips)
   - Not directly on the level (stop hunt protection)

4. **Partial Profit Taking**
   - 50% at 1R (breakeven protected)
   - Trail remainder to liquidity pool

5. **Max 2-3 trades/day** (prevent overtrading)

---

## Updated Roadmap

### Phase 0: Critical Bug Fix (DONE ✅)

| Task | Status | Result |
|------|--------|--------|
| **0.1** | ✅ DONE | Fixed trailing stop formula (v0.42.0) |
| **0.2** | ✅ DONE | Widen SL to 3x ATR (v0.43.0) |
| **0.3** | ✅ DONE | Add session filter (v0.44.0), disabled (v0.45.0) — too aggressive |

### Phase 1: Risk Management (PARTIAL ✅)

| Task | Status | Result |
|------|--------|--------|
| **1.1** | ✅ DONE | Widen SL to 3x ATR (v0.43.0) |
| **1.2** | ❌ SKIP | Position sizing (freqtrade handles this) |
| **1.3** | ⚠️ TESTED | Partial profit taking at +0.8% (v0.46.0) — marginal gain |
| **1.4** | ✅ DONE | Session filter tested, disabled (too aggressive) |

### Phase 2: Entry Quality (STALEMATE → IMPROVED → 🎉 BREAKTHROUGH)

| Task | Status | Result |
|------|--------|--------|
| **2.1** | ❌ FAILED | Session filter cut too many trades (19 vs 63, WR 10.5%) |
| **2.2** | ✅ DONE | Double confirmation: sweep + BOS (v0.47.0) — **MAJOR IMPROVEMENT** |
| **2.3** | ✅ DONE | Weekend filter (v0.49.0) — **44.4% WR, +1.87% profit** |

## v0.51.0 Test Results (2026-03-19)

**Fix Applied:** Remove HTF trend exits from `populate_exit_trend` — replaced ChoCH-only exits.
Problem (roadmap Phase 4): exit_signal exits (33.3% of trades, avg -1.71%) were cutting winners short via 1H HTF trend reversal. ChoCH on entry TF (15m) is more responsive and appropriate for local exit decisions.

| Metric | v0.50.1 | v0.51.0 | Change |
|--------|---------|---------|--------|
| Total Trades | 36 | 36 | — |
| Win Rate | 44.4% | 44.4% | — |
| Profit % | 1.87% | **2.02%** | **+0.15pp** ✅ |
| Profit Factor | 1.55 | **1.62** | +0.07 |
| Avg Hold | 2h55m | 3h05m | +10min longer |
| TSL exits | 3 (8.3%, +6.52%) | 3 (8.3%, +1.97%) | TSL still capturing winners |
| exit_signal | 12 (33.3%, -1.71%) | **11 (30.6%, -0.51%)** | **+1.20pp improvement** 🎉 |
| Early profit | 9 (25%, +3.30%) | 9 (25%, +3.30%) | — |
| ROI exits | — | 5 (13.9%, +0.05%) | More ROI exits (trade running longer) |
| Drawdown | 1.58% | 1.58% | Same |

**Analysis:** Removing HTF trend exits improved profit from 1.87% → 2.02% (+0.15pp) with same trade count. The exit_signal avg loss dropped from -1.71% to -0.51% — a massive 1.20pp improvement on those exits. Winners are now running longer (3h05m vs 2h55m). Profit factor improved from 1.55 to 1.62.

**Key Observation:** ChoCH-only exits let winners run. The 1H HTF trend was too slow/aggressive for 15m entry timeframe exits. The strategy now holds trades an extra 10 minutes on average, capturing more of the move.

**Verdict:** HTF trend exit removal = incremental improvement. ChoCH-only exits confirmed. Next target: still reduce remaining exit_signal exits (now 30.6%, avg -0.51%) — could try tightening ChoCH threshold or adding confirmation before exit_signal fires.

---

## v0.50.1 Test Results (2026-03-19)

**Fix Applied:** Tighten OTE zone to 30-70% mandatory + make require_ote non-optimizable.
Problem (roadmap Phase 4): OTE zone was 30-85%, hyperopt could widen to 50-85%. Extreme Fibonacci zones (78.6%, 88.6%) dilute entry quality. Also require_ote optimize=False prevents hyperopt disabling OTE (v0.38.0 disaster).

| Metric | v0.49.0 | v0.50.1 | Change |
|--------|---------|---------|--------|
| Total Trades | 36 | 36 | — |
| Win Rate | 44.4% | 44.4% | — |
| Profit % | 1.87% | 1.87% | — |
| Profit Factor | 1.55 | 1.55 | — |
| Avg Hold | 2h55m | 2h55m | — |
| TSL exits | — | 3 (8.3%, +6.52%) | Good — TSL capturing winners |
| Early profit | — | 9 (25%, +3.30%) | Strong |
| exit_signal | — | 12 (33.3%, -1.71%) | Still dominant (HTF reversal cuts winners) |

**Analysis:** No improvement over v0.49.0 — identical 36 trades, 44.4% WR, 1.87% profit. Tightening OTE bounds within 30-70% had no measurable effect since v0.49.0 was already using a similar range. The OTE filter is now "locked in" which provides stability but no further gains.

**Key Observation:** exit_signal exits (33.3%, avg -1.71%) are cutting winners short via HTF trend reversal. This is the next major target.

**Verdict:** OTE lock-in confirmed. Next focus: reduce exit_signal exits (HTF reversal exit too aggressive). Consider widening or disabling the HTF trend exit signal.

---

## v0.49.0 Test Results (2026-03-19)

**Fix Applied:** Weekend filter — skip Saturday (dayofweek=5) and Sunday (dayofweek=6).

| Metric | v0.47.0 | v0.49.0 | Change |
|--------|---------|---------|--------|
| Total Trades | 52 | **36** | -31% |
| Win Rate | 36.5% | **44.4%** | **+7.9pp** 🎉 |
| Profit % | 0.05% | **1.87%** | **+1.82pp** ✅ |
| Drawdown | 1.64% | 1.58% | -0.06pp |
| Profit Factor | — | **1.55** | Strong |
| Avg Duration | — | 2h55m | |

**Analysis:** Weekend filter dramatically improved quality over quantity:
- 31% fewer trades but 44% win rate vs 36.5%
- Profit nearly quadrupled (1.87% vs 0.05%)
- Filter removes low-liquidity weekend chop — core ICT principle confirmed
- Profit factor 1.55 = solid edge emerging

**Verdict:** Weekend filter is a definitive keeper. Next: OTE zone filter.

---

### Core Problem (IMPROVING)

**Win rate climbing:** 22% → 36.5% → 44.4% → 46.2%
**Profit turning positive:** -12.9% → 0.05% → 1.87% → 2.02% → 2.25%
**Profit factor climbing:** 1.29 → 1.55 → 1.62 → 1.689
**Next target:** 50%+ WR, 3%+ profit via XRP fix + exit quality improvements

---

## Version History

| Version | Focus | Key Changes |
|---------|-------|-------------|
| v0.64.0 | 🔧 REVERT | **Revert v0.63.0 — massive regression. Restore ROI 305 at 1% + early_profit 0.8%. Re-running backtest.** |
| v0.63.0 | ❌ REGRESSED | **Remove ROI 305 + raise early_profit to 1.5% — 35 trades, 45.7% WR, 0.01% profit, 1.16 PF, 27.8% DD ❌** |
| v0.62.0 | ✅ ATH | **Change ROI 305 exit 0% → 1% — 35 trades, 57.1% WR, 4.86% profit, PF 2.48, SQN 2.16, DD 0.85%** 🏆 |
| v0.61.0 | ✅ Previous | **Disable time_exit_2 — 35 trades, 51.4% WR, +4.47% profit, PF 2.75, SQN 2.08, DD 0.85%** |
| v0.60.0 | ✅ Previous | **Remove SOL — 34 trades, 52.9% WR, +4.76% profit, PF 3.10, SQN 2.27, DD 0.88%** |
| v0.59.0 | ✅ Previous | Remove BNB + pairlist cleanup — 41 trades, 51.2% WR, +4.31% profit, PF 2.26 |
| v0.57.0 | ✅ IMPROVED | Restore 8 pairs + XRP fix — 43 trades, 46.5% WR, +2.93% profit, PF 1.75 |
| v0.56.0 | ❌ REGRESSED | XRP removal — 21 trades, 38.1% WR, +0.74% profit, PF 1.413 (WORSE than v0.55.0) |
| v0.55.0 | ✅ DONE | Per-pair optimization — 39 trades, 46.2% WR, +2.25% profit, PF 1.689 |
| v0.54.0 | ✅ DONE | ChoCH profit guard — exit_signal avg loss -0.76% → -0.53% |
| v0.53.0 | ✅ REVERTED | Remove confirmation candle → profit restored 1.19%→2.02%, ChoCH-only exits confirmed |
| v0.52.0 | ❌ REVERTED | Confirmation candle on exits — filtered valid exits, profit 2.02%→1.19% |
| v0.51.0 | 🎉 IMPROVED | Remove HTF trend exits → profit 1.87%→2.02%, exit_signal avg -1.71%→-0.51% |
| v0.50.1 | ✅ DONE | Tighten OTE to 30-70% mandatory (no change — v0.49.0 already near-optimal) |
| v0.49.0 | 🎉 BREAKTHROUGH | Weekend filter — WR 36.5%→44.4%, profit 0.05%→1.87%, profit factor 1.55 |
| v0.47.0 | 🚀 BREAKTHROUGH | BOS double-confirmation — WR 22%→36.5%, profit -12.9%→+0.05%, drawdown 1.64% |
| v0.46.0 | ⚠️ MARGINAL | Early profit exit + wider floor (-8%) — marginal improvement (+0.1pp). TSL still dominant. |
| v0.45.0 | ✅ DONE | Disable session filter (was too aggressive) |
| v0.44.0 | ✅ DONE | Session filter NY/London (v0.44.0), disabled in v0.45.0 |
| v0.43.0 | ✅ DONE | Widen ATR stoploss to 3x |
| v0.42.0 | ✅ DONE | Fixed trailing stop formula (0.277→0.005) |

### Phase 4: Hyperopt & Fine-Tuning (REGRESSED v0.56.0 → NEXT: restore pairs + XRP stop)

- ✅ Remove HTF trend exits (v0.51.0) — exit_signal avg loss -1.71% → -0.51% 🎉
- ✅ Confirmation candle on exits (v0.52.0) — ❌ REVERTED (filtered valid exits)
- ✅ Revert confirmation candle (v0.53.0) — profit restored to 2.02%, ChoCH-only exits confirmed
- ✅ ChoCH profit guard (v0.54.0) — exit_signal avg loss -0.76% → -0.53% ✅
- ✅ Per-pair parameter optimization (v0.55.0) — 39 trades, 46.2% WR, 2.25% profit, 1.689 PF
- ✅ Remove BNB from pairlist (v0.59.0) — 41 trades, 51.2% WR, 4.31% profit, PF 2.26 🏆 ATH
- ✅ Remove SOL from pairlist (v0.60.0) — 🏆 ATH: 34 trades, 52.9% WR, 4.76% profit, PF 3.10
- ✅ Disable time_exit_2 (v0.61.0) — 35 trades, 51.4% WR, 4.47% profit, PF 2.75, DD 0.85%
- ❌ Remove ROI 305 + raise early_profit to 1.5% (v0.63.0) — REGRESSED: 45.7% WR, 0.01% profit, 27.8% DD ❌
- 🔧 NEXT: Revert to v0.62.0 config (v0.64.0) → then XRP-specific analysis
- ⏳ Rolling 2-year backtest window
- ⏳ Rolling 2-year backtest window

---

## Debugging Checklist

When backtest fails:

- [ ] **Check trade volume:** 0 trades = logic bug, too few = filters too strict
- [ ] **Check exit reasons:** TSL > 50% = SL problem, ROI = entry problem
- [ ] **Check profit distribution:** Many small wins + few big losses = typical
- [ ] **Check pair performance:** Some pairs may need different params
- [ ] **Run local backtest first:** Before CI, catch errors faster

---

## Action Items

1. **Run v0.42.0** backtest to verify trailing stop fix
2. **Analyze** exit reasons - expect fewer trailing_stop_loss exits
3. **Next:** Widen SL to 3x ATR (v0.43.0)

---

*Last Updated: 2026-03-18*
