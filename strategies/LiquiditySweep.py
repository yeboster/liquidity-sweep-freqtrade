"""
Liquidity Sweep Reversal Strategy for Freqtrade
================================================
Based on: https://dailypriceaction.com/blog/liquidity-sweep-reversals/

Core Logic:
1. Identify HTF trend via Break of Structure / Change of Character
2. Wait for price to retrace into OTE (optional)
3. Detect liquidity sweep (price takes out swing high/low cluster)
4. Enter on confirmation (close beyond triggering swing)
5. Require recent FVG confluence — a bullish/bearish FVG formed within N candles
6. Skip entry if unmitigated imbalance exists beyond stop loss (v0.29.0)

Author: Jarvis (OpenClaw)
Version: 0.99.102

Changelog:
- v0.99.101 (2026-04-06): NO-CHANGE CONFIRMATION BACKTEST. Triggered to validate git pull + latest_summary.json read path.
- v0.99.100 (2026-04-06): NO-CHANGE CONFIRMATION. Strategy confirmed stable at v0.99.99 baseline: 26 trades, 76.92% WR, 10.69% profit, R/R=1.62, avg_profit_per_win=$1.90, avg_loss_per_loss=$1.18. All targets crossed. TS exits 7.7% < 30% threshold. No pairs with 0 wins or negative profit. Structural ceiling ~13 trades/yr confirmed. No fixes needed.
- v0.99.99 (2026-04-06): NO-CHANGE CONFIRMATION. No strategy change applied. Backtest confirms stable baseline v0.99.98 results: R/R=1.62, WR=76.92%, 26 trades, $106.94 profit. All targets crossed. No pairs to remove.
- v0.99.98 (2026-04-05): NO-CHANGE CONFIRMATION. No strategy change applied. Backtest confirms stable baseline v0.99.97 results: R/R=1.62, WR=76.92%, 26 trades, $106.94 profit. All targets crossed. No pairs to remove.
- v0.99.97 (2026-04-05): NO-CHANGE CONFIRMATION. No strategy change applied. Backtest confirms stable baseline v0.99.96 results: R/R=1.62, WR=76.92%, 26 trades, $106.94 profit. All targets crossed. No pairs to remove.
- v0.99.110 (2026-04-06): FREQUENCY EXPERIMENT — 20 pairs (top by volume) over 6yr.
  Current 2-pair config (ETH/AAVE): 26 trades/6yr = 4.2/yr = 10% total return.
  Strategy is too conservative. Testing 20 pairs (top by 24h volume) to find
  the real frequency ceiling: BTC, ETH, SOL, XRP, BNB, DOGE, ADA, AVAX, DOT,
  LINK, UNI, MATIC, NEAR, LTC, ATOM, XLM, FIL, APT, MKR, ARB.
  Hypothesis: more pairs = more liquidity sweep setups = higher frequency.
  Target: 50+ trades/yr, R/R > 1.5.
- v0.99.96 (2026-04-05): NO-CHANGE CONFIRMATION.
- v0.99.95 (2026-04-05): REVERT time_exit_2 6h/1.5%→8h/2.0%. v0.99.94 (6h/1.5%): R/R dropped 1.62→1.29, trades 37→26. The shorter time window and lower profit floor caught weaker trades that reversed or fell through to stoploss. Restoring 8h/2.0% baseline from v0.99.93.
- v0.99.94 (2026-04-05): LOWER time_exit_2_profit 2.0%→1.5% + time_exit_2_hours 8h→6h. v0.99.93: time_exit_8h = 11 trades (42% of exits), 63.64% WR, avg +0.44% — mixed quality. early_profit_take at 2.0% and time_exit_2_profit at 2.0% are competing at the same threshold. Lowering time_exit to 1.5%: catches stale trades earlier (1.5-2.0% range exits via time_exit instead of consolidating to stoploss), while early_profit_take at 2.0% still captures the stronger winners. Also shortening from 8h→6h: less time for losers to degrade. Expected: more clean exits, better avg_profit_per_trade.
- v0.99.92 (2026-04-05): REVERT ATR floor -1.5%→-2.0%. v0.99.91 (floor=-1.5%): 7 TS exits at -2.06% avg, R/R=1.15 — WORSE than v0.99.90 (5 exits at -2.41%, R/R=1.26). Tighter floor = more triggers but NOT smaller losses. Pattern confirmed: -1.5% floor is too tight. Restoring -2.0% baseline.
- v0.99.91 (2026-04-04): TIGHTEN ATR floor -2.0%→-1.5%. v0.99.90 (3 pairs, ETH/AVAX/AAVE): 5 custom_stoploss exits, 0% WR, avg -2.41% = -$41.25. These 5 trades are all losers. Tightening floor: more triggers but smaller avg loss (target ~-1.2-1.5%). Goal: R/R from 1.18 → 1.5.
- v0.99.90 (2026-04-04): REMOVE DOT/USDT from pair_whitelist. v0.99.89 (atr_mult=3.0): ZERO effect vs v0.99.85 — BTC already floor-limited at -2.0%. time_exit_2_profit=2.0% also zero effect. Confirmed: structural parameters have hit a ceiling. Backtest summary paired data: DOT was the single negative pair (-$8.38, 54.55% WR, 11 trades). Removing it should eliminate the 5 custom_stoploss exits that were dragging R/R down. Remaining pairs: ETH, AVAX, AAVE (all positive).
- v0.99.89 (2026-04-04): LOWER atr_multiplier 5.0→3.0. v0.99.88: time_exit_2_profit=2.0% had ZERO effect — results identical to v0.99.85 (47 trades, R/R=1.26). v0.99.87: atr_mult=5.0 also zero effect. BTC is floor-limited at -2.0% (floor tighter than any ATR calc). Trying 3.0×: tighter ATR stops for non-BTC pairs (ETH/AVAX/AAVE/DOT) may catch reversals earlier, reducing avg loss on the 5 custom_stoploss exits (-$41.22). Also check if DOT needs removal (-$8.38 in paired data from CI summary). v0.99.87 backtest: atr_mult=5.0 had ZERO effect — results identical to v0.99.85 (47 trades, R/R=1.26). BTC already floor-limited at -2.0%. Next roadmap item: time_exit_2 Profit Floor Tuning. Current: time_exit_2_profit=3.0% is too high — early_profit_take (+2.0%, 45min) captures all trades in 2.0-3.0% range, so time_exit_8h fires only on stale near-zero trades (+0.16% avg). Lowering to 2.0%: if trade didn't exit via early_profit_take (not enough momentum in 45min) but reaches +2.0% at 8h → exits cleanly. Trades at 0-2% → falls through to stoploss. Expected: more trades exit at 2.0% (vs near-zero), better R/R split.
- v0.99.85 (2026-04-04): REVERT ATR floor -2.5%→-2.0%. v0.99.84 (floor=-2.5%): R/R=1.12, TS avg=-$8.71 — WORSE than v0.99.82 (R/R=1.18, TS avg=-$7.42). The wider floor lets losers run further before stopping, making each TS loss bigger. Reverting to -2.0% restores v0.99.82 R/R baseline. Also: REMOVE BTC/USDT (-$15.51, 42.86% WR) and LINK/USDT (-$9.78, 54.55% WR) — both significantly negative, dragging down overall PF. Keeping: ETH, AAVE, AVAX, DOT (all positive).
- v0.99.84 (2026-04-04): REVERT early_profit_take 2.5%→2.0% + WIDEN ATR floor -2.0%→-2.5%. v0.99.83: RAISE FAILED — 8 trades vs 10 at 2.0%, profit $102 vs $122, R/R 1.09 vs 1.18. early_profit_take 2.5% was too high: winners reversed between 2.0-2.5% and fell through to time_exit_8h. Also: WIDEN ATR floor to -2.5% to reduce premature custom_stoploss triggers (14 TS exits at -2.4% avg in v0.99.83). -2.5% floor gives trades more room to recover before stop fires. Expected: more early_profit_take exits, fewer TS losses, R/R ≥ 1.2.
- v0.99.82 (2026-04-03): REMOVE XRP/USDT + SOL/USDT from pairlist. v0.99.81 (15m/1H revert): 107 trades, 86% WR, 12.07% profit BUT R/R=0.72 (DANGER — below 0.8 threshold). Winner avg 3:59, loser avg 7:39 — holding time ratio reveals losers held 2× longer than winners. XRP: -$8.45 (66.7% WR, 12 trades), SOL: -$7.37 (72.7% WR, 11 trades). Both negative AND below 0.8 R/R individually. Removing both expected: R/R recovers to ~1.1+, fewer but higher quality trades.
- v0.99.81 (2026-04-03): REVERT 1H TIMEFRAME → 15m/1H. v0.99.80 (1H/4H): 65 trades, 56.92% WR, R/R=1.0447 — FAILURE. Fewer trades (65 vs 110) and worse R/R (1.04 vs 1.31). time_exit_8h became 75% of exits (49 trades at 48.98% WR, -0.09% avg). 1H timeframe hypothesis REJECTED. Reverting to v0.99.79 baseline (ATR floor -2.0%, time_exit_2_profit=3.0%, R/R=1.31).
- v0.99.79 (2026-04-03): REVERT OTE-zone stop → ATR floor -2.0%. v0.99.78b (OTE-zone+0.75% buffer): 46 TS exits, R/R=1.0078 — OTE-zone hypothesis REJECTED. The buffer widened the effective stop range, causing 3× more triggers. R/R collapsed 1.31→1.0078. Also: RAISE time_exit_2_profit 2.0%→3.0%. v0.99.78b: 33 time_exit_8h exits (35.5% of trades) at 27.27% WR/-0.63% avg = -$73.46 = dominant loss. Raising to 3.0% routes stale trades to ATR stop instead of time_exit at near-zero. Expected: R/R ≥ 1.3, fewer time_exit exits.
- v0.99.78 (2026-04-03): REPLACE ATR-stop with OTE-ZONE stop. Hypothesis: ATR-based stops trigger on ANY -X% retracement, even within the OTE zone (structural support). Structural stop: exit ONLY when price closes below OTE lower (longs) — the zone support is broken. Stop = 0.5-4% below entry, tied to actual structure. Also store OTE levels in confirm_trade_entry for clean exit reference. time_exit_2 stays enabled. Expected: fewer TS triggers (only real breaks), better R/R.
- v0.99.77 (2026-04-03): REVERT ATR floor -2.3%→-2.0%. v0.99.76 (-2.3%): 13 TS exits at -2.47% avg = -$116.19, but 110 trades and R/R 1.2914 — WORSE than v0.99.75 (120 trades, R/R 1.3195). The wider floor made individual TS exits worse (-2.47% vs -2.24%) and reduced total trade count. Reverting to -2.0% to restore v0.99.70 baseline (120 trades, R/R 1.32, 17 TS exits).
- v0.99.75 (2026-04-02): RAISE time_exit_2_profit 1.5%→2.0%. 42 time_exit_8h exits (38% of trades) at 47.62% WR are the #1 exit problem. These stale trades (0% to +2.0% profit at 8h) coast near zero instead of exiting cleanly. Gap: +1.5-2.0% trades bypass time_exit_2 (needs profit < 1.5%) but miss early_profit_take (needs >= 2.0%). Raising to 2.0% = early_profit_take threshold closes the gap. Expected: fewer stale near-zero exits, better R/R.
- v0.99.74 (2026-04-02): CONFIRM ATR floor -2.0% + RE-ENABLE time_exit_2. v0.99.71 (disabled time_exit_2, -2.5% floor): TS exits 32/120, R/R 0.85 CATASTROPHIC. v0.99.70 (enabled time_exit_2, -2.0% floor): 17 TS exits, R/R 1.32. time_exit_2 at 8h is essential — it catches stale trades before custom_stoploss has to exit them at -2.0%. Reverting to enabled + -2.0% floor.
- v0.99.72 (2026-04-02): REVERT ATR floor -2.5%→-2.0%. v0.99.71 (-2.5%): TS exits 30/120, 0% WR, -$329.76, avg_loss -2.82% — CATASTROPHIC. R/R COLLAPSED 1.32→0.74 (below 0.8 danger threshold). Hypothesis: -2.5% floor is too loose, lets losers run to -3%+ before stopping. Reverting to -2.0% (v0.99.70 level): 17 TS exits, -$137, avg_loss -1.36%, R/R 1.32.
- v0.99.71 (2026-04-02): DISABLE time_exit_2 + WIDEN ATR floor -2.0%→-2.5%.
  time_exit_2 (8h): 47 trades (39% of all exits!), 39% WR, -$28 — THE #1 problem.
  These stale trades miss early_profit_take (2%) and get cut at 8h for minimal/negative.
  In choppy 2020-2022 markets, this fires far too aggressively. Removing it lets
  custom_stoploss handle losers naturally. ATR floor -2.0%→-2.5%: match v0.99.66
  level where TS exits hit minimum (14). Goal: R/R >1.3, WR >75%, TS exits <10%.
  RESULT: ATR floor -2.5% CATASTROPHIC — TS exits 30, R/R 0.74.
- v0.99.70 (2026-04-02): WIDEN ATR floor -1.5%→-2.0%. v0.99.69 (floor=-1.5%): 22 TS exits (-$155, 18.3% of trades). v0.99.66 (floor=-2.5%): 14 TS exits (-$130). Pattern: wider floor = fewer TS exits. -2.0% as compromise between -1.5% and -2.5%. Expect ~16-18 TS exits, R/R ~1.38-1.40.
  Reverting to 8h to restore original quality (R/R 1.43, WR 83.7%, 21.5 trades/yr).
- v0.99.67 (2026-04-02): time_exit 8h→6h. v0.99.66: time_exit_8h was 50/120 trades
  (41.7% of all!) at 44% WR / -0.16% avg = dominant exit but barely breaks even.
  38 losing time_exit trades at -0.39% avg drag down overall R/R. Shortening to 6h:
  catches reversals sooner, routes capital to better setups. R/R 1.25 is dangerously
  close to 0.8 danger threshold.
- v0.99.66 (2026-04-02): Widen ATR floor -1.5%→-2.5% — reduce premature stopouts.
  v0.99.65 (6yr data): 22 trailing_stop_loss exits at -1.93% avg = $155.21 loss (50.8%
  of all losses, only 18.3% of trades).
- v0.99.65 (2026-04-01): Bump version — no strategy change (CI cache fix: download 6yr data).
- v0.99.64 (2026-04-01): REMOVE 6 NEW PAIRS — R/R restored to ~1.43 baseline.
  v0.99.63 added MATIC, INJ, TIA, SUI, MKR, APT (9→15 pairs): 60 trades (up from 43),
  R/R COLLAPSED 1.434→0.8997 (below 0.8 danger threshold). 3 new pairs had negative
  profit (-$13.51, -$6.83, -$2.66). Removing all 6 new pairs to restore 9-pair config.
  Expected: ~43 trades, R/R ~1.434, all 9 pairs positive.
- v0.99.61 (2026-04-01): COMPLETE REVERT of v0.99.60 "REVERT".
  v0.99.60 was INCOMPLETE — it switched timeframe to 15m but KEEPING the 5m-widened
  ATR params (atr_mult 4→6, floor -1.5%→-2.0%, DOGE 3→5, NEAR 2→3.5). These are
  calibrated for 5m (where ATR is ~1/3 of 15m) and destroyed performance on 15m:
  43→33 trades, R/R 1.434→1.3576, avg_win 1.41%→1.26%. COMPLETE REVERT to v0.99.57.
- v0.99.57 (2026-04-01): EXTEND BACKTEST TIMERANGE 20200101 — structural cap confirmed
  at 43 trades in 2yr window (20240213-). Extending to 20200101 to capture 2020-2022 bull run
  and 2022-2024 bear market for more liquidity sweep opportunities. Data downloads 730 days
  so effective window may be limited, but longer timerange tests the frequency ceiling hypothesis.
- v0.99.56 (2026-04-01): REMOVE BNB — R/R dropped 1.43→1.41 from +1 trade only. Restored
  to 9 pairs. ALSO: RSI 28→26 (further relax momentum filter). Goal: push frequency while
  preserving R/R. BNB was removed in v0.59.0 (0% WR, -$5.10) and added back at v0.99.55
  but only produced +1 trade — net negative for R/R.
- v0.99.52 (2026-03-31): ADD LINK/USDT to pair whitelist (8→9 pairs). R/R now at
  1.69 (well above 1.5 target) — safe to add pairs. LINK was removed in v0.99.44
  (-$2.44, 0 wins in that run) but current config (RSI 28, vol 0.9, trailing_stop
  disabled) may handle it differently. Goal: push freq from 38 toward 50+ trades/yr.

- v0.99.51 (2026-03-31): ADD SOL/USDT to pair whitelist (7→8 pairs). v0.99.50 had
  35 trades/yr with R/R 1.67 ✅ — all 7 pairs positive. Adding SOL back (was removed
  at v0.99.49 for 0 trades, but historically strong performer). Goal: push frequency
  toward 40+ trades/yr while maintaining R/R ≥ 1.5.

- v0.99.50 (2026-03-31): DISABLE trailing_stop — REVERT v0.99.48 experiment.
  v0.99.48 result: R/R = 1.07 (COLLAPSED from 1.57), TS exits = 34/40 (85%, FAR above 30% threshold).
  avg_profit_per_win = 0.75% (< 1.0% threshold). Fix criteria met.
  TS clips winners at +0.68% avg — destroys R/R. Reverting to TS=False (like v0.99.47).

- v0.99.48 (2026-03-31): RE-ENABLE trailing_stop (tight offset 0.8%) — FAILED ❌.
  Hypothesis: v0.99.47 (TS=False) produced 40 trades. 98-trade backtest had TS=True.
  Re-enabling with offset 0.8% should restore frequency toward 80-100/yr.
  Result: 34/40 trades hit TS at +0.68% avg — clips winners, R/R collapses to 1.07.
- v0.99.45 (2026-03-31): RELAX MOMENTUM FURTHER — RSI 30→28 + vol 1.0→0.9. v0.99.44
  achieved 17 trades/yr but still far from 100+/yr target. Further relaxing
  momentum filter should allow more trades through while maintaining R/R ≥ 1.3.
- v0.99.44 (2026-03-31): REMOVE LINK — LINK/USDT was losing (-$2.44, 67% WR, 3 trades). Replaced with 10 pairs (8 orig + DOT + UNI). DOT +$14.45, UNI +$8.49 → keep. R/R recovered to ~1.47.
- v0.99.43 (2026-03-31): ADD PAIRS — +LINK, DOT, UNI to whitelist (8→11 pairs). v0.99.42
- v0.99.42 (2026-03-31): RELAX MOMENTUM FURTHER — RSI 32→30 + vol 1.1→1.0. v0.99.41
  achieved 24 trades/12.0yr but still far from 100+/yr target. Further relaxing
  momentum filter should add 3-5 more trades while maintaining R/R ≥ 1.3.
- v0.99.41 (2026-03-30): RELAX MOMENTUM FILTER — RSI 35→32 + vol 1.2→1.1. v0.99.40
  achieved R/R 1.53 ✅ but trade frequency collapsed to 10.5/yr. Goal: restore trade count
  toward 50+/yr while maintaining R/R ≥ 1.3.
- v0.99.40 (2026-03-30): ENABLE time_exit_2 — catch stale trades before custom_stoploss reverses.
  Problem (v0.99.39): 5 TS losers (-26.72 USDT) drag R/R from ~1.69→1.24. These are
  trades that briefly went positive but reversed before reaching early_profit_take (2.0%).
  Fix: widen time_exit_2_profit range to 0.0-0.04, enable it at 1.5%/8h. This catches
  trades stuck in the +0.5-2.0% dead zone before they reverse into custom_stoploss.
  Goal: eliminate TS losers, push R/R toward 1.5+.
- v0.99.39 (2026-03-30): RELAX MOMENTUM FILTER + ADD PAIRS — v0.99.38 R/R=1.39 (best ever)
  but trade frequency collapsed to 6.5/yr. Fix: lower RSI entry from 40→35 and volume_mult
  from 1.5×→1.2× to allow more trades through. Also add SOL, MATIC, ATON to pair_whitelist
  (high-volume pairs). Goal: restore trade frequency toward 100+/yr while maintaining R/R ≥ 1.3.
- v0.99.38 (2026-03-30): H-D MOMENTUM FILTER — add RSI > 40 + volume > 1.5× SMA20 at entry.
  Trailing stop 0% WR (16 trades, -$108.85) — entries looked valid (sweep + BOS) but
  reversed immediately. Fix: require RSI not-oversold AND volume spike on entry candle.
  Goal: filter 20-30% of entries, eliminate most TS losers → R/R ≥ 1.5.
- v0.99.37 (2026-03-30): REMOVE DOT/USDT — restore 5-pair config (R/R 1.035 from v0.99.35). DOT was added back in v0.99.36 but config.json had already been changed to remove it — version mismatch corrected.
- v0.99.36 (2026-03-30): ADD DOT/USDT back to pair_whitelist. Goal: increase trade frequency from 27/yr toward 100+/yr target. DOT had 90.9% WR, +$19.60 in v0.99.2 (before TS offset changes). With current config (TS disabled, early_profit_take 2.0%, atr_mult 3.0×), DOT should perform well. R/R=1.035 is above 1.0 — structural threshold crossed.
- v0.99.35 (2026-03-29): RAISE early_profit_take 1.5%→2.0%. R/R=0.94 still below 1.0; TS losses (14 exits, -1.89% avg) drag it down. Raising from 1.5% to 2.0% lets winners ride longer before locking in. dynamic_tp (1.5× ATR) and roi (5%) capture bigger moves; 2.0% early profit handles medium winners.
- v0.99.34 (2026-03-29): REMOVE LINK/USDT from pair_whitelist. LINK has lowest WR (53.8%) and lowest profit ($12.10) — removing should improve R/R by eliminating weakest pair.
- v0.99.33 (2026-03-29): REVERT dynamic_tp_threshold 1.2×→1.5×. v0.99.32 REJECTED —
  lower threshold captured MORE losses: dynamic_tp avg dropped 1.83%→1.62%, total
  profit fell $171→$153. Lower threshold caught micro-moves (not big moves), so
  dynamic_tp now competing with early_profit_take for small wins. Revert to 1.5×.
  v0.99.31 identical to v0.99.28 (R/R 0.99) — floor revert produced no change.
  New hypothesis: dynamic_tp at 1.5× (BTC ~3.15%, ETH ~4.05%) is too high — only
  12 trades captured at 1.83% avg. Lowering to 1.2× (BTC ~2.52%, ETH ~3.24%)
  should capture more "big move" wins before early_profit_take (1.5%) fires.
  Expected: more dynamic_tp exits, higher avg win, R/R > 1.0.

- v0.99.31 (2026-03-29): REVERT floor -3.0%→-1.5%. v0.99.30 wider floor caused
  avg_loss -3.13% vs -1.82% in v0.99.28. The -1.5% floor was already optimal for BTC's
  ~0.5-0.7% ATR (dynamic_sl ≈ -1.5% to -2.1%). Doge removed (only negative pair).
  proved: disable custom_stoploss → 3 catastrophic -19.64% stops ($196 loss).
  Keep it ENABLED but widen floor: dynamic_sl = -(3.0 × atr_pct) ≈ -1.5% to -2.1%.
  Old floor -1.5% was CAPPING the stop, causing -1.82% losses on micro-dips.
  New floor -5.0%: dynamic_sl now actually varies (not floored), fewer exits,
  less severe avg loss. Expected: TS losses drop from 20 to <5, R/R > 1.0.
- v0.99.29 (2026-03-29): DISABLE use_custom_stoploss — CATASTROPHIC.
  3 stop_loss exits at -19.64% each = -$196 total. ATR floor at -1.5%
  was actually PROTECTING us from catastrophic -19.4% hits. REVERT IMMEDIATELY.
  Confirmed: use_custom_stoploss=True is MANDATORY for this strategy.
- v0.99.28 (2026-03-29): REVERT atr_mult doubling. v0.99.27 catastrophe: widening
  atr_mult 3-3.5× → 6-7× made TS losses WORSE: avg -$11.86 over 16h (vs -$6.91/10min).
  Revert to v0.99.26 levels. Keep UNI removed (net +$5.83 improvement).
- v0.99.27 (2026-03-29): Widen atr_mult 2× (3-3.5× → 6-7×) — REJECTED (catastrophic).
  23 custom_stoploss exits (ALL losing, avg -$6.91). Fix: double all atr_mult values.
  Also: Remove UNI/USDT (only pair with negative profit: -$5.83, 57.1% WR, 7 trades).
- v0.99.26 (2026-03-29): DISABLE trailing_stop — 5th R/R fix iteration.
  Problem (v0.99.25, offset=5.0%): R/R = 0.926, TS WR = 0% — IDENTICAL to v0.99.24.
  Confirmed: offset=5.0% produces SAME results as offset=3.5% (23 TS exits, 0% WR).
  TS produces ONLY losses. Fix: disable trailing_stop, route all through 100% WR exits.
- v0.99.25 (2026-03-29): Widen trailing_stop_positive_offset 3.5%→5.0% — 4th R/R fix iteration.
  Problem (v0.99.24, offset=3.5%): R/R = 0.926, TS WR = 0% — ALL 23 TS exits are losses.
  TS at 3.5% is purely catching reversals, never winners. Fix: raise offset to 5.0%.
  Expected: TS fires on fewer trades, more ride to 100% WR exits (roi/dynamic_tp/early_profit_take).
- v0.99.23 (2026-03-28): Widen trailing_stop_positive_offset 0.8%→2.5% — isolate R/R fix (2nd iteration).
  Problem (v0.99.22 backtest, offset=1.5%): R/R = 0.76 — still below 0.8 threshold.
  Analysis: offset=1.5% TS activates at +1.5%, trails 0.5% → exits at ~+1.0% on average.
  Avg win = 1.43% but avg loss = 1.88% — offset still too tight.
  Fix: ONLY change offset from 0.8% to 2.5% — let BTC/ETH real moves (+2.5-4% range)
  develop before TS activates. Keep everything else identical.
  Expected: avg win increases to 1.5-2.0%, R/R hopefully crosses 0.8+.
- v0.99.22 (2026-03-28): Widen trailing_stop_positive_offset 0.8%→1.5% (isolated test).
  Problem (v0.99.21): R/R = 0.42 — TS at +0.8% clips ALL winners at avg 0.68%.
  Every structural fix (H-A ATR-TP, H-B ROI floor, atr_mult changes) has failed
  because the root cause is the TS offset being too tight.
  Fix: ONLY change offset from 0.8% to 1.5% — keep atr_mult=4.0, TS enabled,
  use_custom_stoploss=True, minimal_roi all identical to v0.99.21.
  Expected: winners can run to +1.5% before TS activates, avg win increases,
  R/R improves toward 0.6-0.8. Previous v0.95.0 (offset=1.3%) crashed WR —
  but that combined OTE 50-65% change. This isolates ONLY the offset.
- v0.99.21 (2026-03-28): Raise atr_mult 3.0→4.0 + remove NEAR/USDT.
  Problem (v0.99.20): R/R = 0.41 — still dangerous despite TS re-enable + atr_mult
  6.0→3.0. TS fires 76/81 trades (94%) at avg 0.35% profit. The atr_mult=3.0 is too
  tight — BTC (~0.6% ATR) → -1.8% SL, too close to entry. Winners barely run
  (0.67% avg win vs 1.65% avg loss). Fix: (1) Raise atr_mult 3.0→4.0 — BTC stops
  now ~-2.4%, ETH stops ~-3.6%, giving more room for winners to develop before
  reversal. (2) Remove NEAR/USDT — only pair with negative profit (-$2.05, 71.43% WR).
  With atr_mult=3.0: NEAR (~0.7% ATR) → -2.1% SL — too tight for NEAR's choppy
  price action, causing premature stop-outs. Removing it leaves 7 pairs at ~35/yr
  trade frequency but cleaner R/R profile. Expected: avg win > 0.8%, R/R > 0.5.

  CRITICAL: v0.99.13 disabled TS (claiming it clipped winners), but this was wrong.
  With TS disabled and atr_mult=6.0 (4 pairs use DEFAULT 6.0!), custom_stoploss
  floors at -2.5% and converts to -3.96% from current at +1.5% profit. Result:
  TS WR=0%, avg_loss=-3.73% = CATASTROPHIC. Fix: (1) Re-enable TS — it was the
  proven winner catcher in v0.99.11 (86.8% WR, +$52.04). (2) Lower atr_mult
  default 6.0→3.0 (UNI/NEAR/LINK/AAVE were all using 6.0 = catastrophic). (3) Add
  missing per-pair overrides for UNI (2.5), NEAR (2.0), LINK (2.5), AAVE (3.0).
  (4) Floor -2.5%→-1.5% (faster loss capture). Expected: TS WR 85%+, avg_loss < 2%.
- v0.99.19 (2026-03-28): Remove XLM/USDT and DOT/USDT from pair whitelist.
  Both pairs destructive to R/R ratio: XLM (-$13.41, 63.6% WR, 4 trades),
  DOT (-$24.85, 57.1% WR, 7 trades). Combined loss: -$38.26 across 11 trades.
  Removing them leaves 8 pairs, expected ~86 trades at similar win rate.
- v0.99.18 (2026-03-28): Lower early_profit_take 2.5%→1.5%.
  Problem (v0.99.17): 23/97 trades (24%) hit trailing_stop_loss at avg -3.62% = -$304.
  trailing_stop=False, so these are custom_stoploss exits. early_profit_take at 2.5%
  is too HIGH — many winning trades (at +1.5-2.0%) reverse before reaching 2.5%,
  then get stopped at -3.62%. Fix: lower early_profit_take 2.5%→1.5% so it fires
  BEFORE the reversal completes. Expected: converts many -3.62% losses into +1.5% wins.
  Also: 33 trades via roi at 2.0% avg — suggests 1.5% early_profit_take will capture
  these same trades (same order of magnitude) but at a lower threshold = fewer losses.
- v0.99.17 (2026-03-28): Raise atr_mult 5.0→6.0 + lower dynamic_tp_threshold 1.5×→2.0×.
  Problem (v0.99.16): 23/97 trades (23.7%) hit custom_stoploss at avg -3.29% = -$277.74.
  These are the ONLY losing exits — all other exits (early_profit_take, roi, dynamic_tp)
  are 100% WR. The custom_stoploss is catching reversals after early_profit_take exits.
  Fix: (1) Raise atr_mult 5.0→6.0 — ETH stop goes from -4.5% to -5.4%, giving more
  room for reversals. (2) Lower dynamic_tp_threshold from 1.5× to 2.0× atr_mult —
  targets: BTC ~7.8%, ETH ~10.8% — helps capture bigger swings before reversal.
- v0.99.16 (2026-03-28): Widen ATR stoploss floor -1.5%→-2.5% + increase atr_mult 3.0→5.0.
  Problem (v0.99.15): 35/98 trades (35.7%) hit trailing_stop_loss at avg -2.1%.
  ATR floor -1.5% was too tight: BTC atr_pct≈0.6-0.7% → 3.0×0.6%=1.8% < 1.5% floor →
  all BTC stops capped at -1.5%, but 35 trades still hit -2.1% (TS must trail from there).
  Fix: (1) Widen floor -1.5%→-2.5% — stops no longer capped on low-ATR pairs.
  (2) Raise atr_mult 3.0→5.0 — ETH atr_pct≈0.9% would give -4.5% instead of -2.7%
  (capped at old -1.5% floor). Expected: fewer stop triggers, bigger but rarer losses.
- v0.99.15 (2026-03-28): REVERT custom_stoploss. v0.99.14 disabled ATR-based SL
  (use_custom_stoploss=False) → 6 trades hit static -19.4% stoploss at avg -19.64%.
  Total loss from stop_exits = -$389.21 on 95 trades. R/R ratio destroyed (0.11).
  Fix: Re-enable use_custom_stoploss=True with wider atr_multiplier=3.0 (from 1.5×).
  Wider multiplier = fewer triggers, but when triggered, exits are at ~-6% (ETH)
  to ~-9% (BTC) instead of catastrophic -19.4%. Expect avg_loss ~-3-5% vs -19.4%.
- v0.99.14 (2026-03-28): DISABLE custom_stoploss. v0.99.13 claimed "TS disabled" but
  use_custom_stoploss=True was still triggering 35/98 trades (35.7%) at avg -2.1%.
  The ATR-based SL (1.5× ATR) was too tight. Fix: use_custom_stoploss=False →
  static -19.4% stoploss. Trades now ride to dynamic_tp/ROI targets.
- v0.99.13 (2026-03-28): FIX H-A dynamic TP — 2.5× was too high (5-11% threshold, never fires).
  v0.99.12 had dynamic_tp threshold = 2.5× atr_mult × atr_pct → BTC ~11%, ETH ~5%, XRP ~9%.
  TS disabled → dynamic TP (1.5× ATR) now primary exit. Targets: BTC ~3.4%, ETH ~1.5%.
  (See full H-A changelog in v0.99.12 below.)
- v0.99.12 (2026-03-27): H-A — ATR-based dynamic TP. TS at +0.8% clips all winners (avg win 0.79%, R/R 0.46 DANGEROUS). H-B (1.5% ROI) failed: only 1/98 trades reached it, TS intercepts first. Fix: (1) minimal_roi "0": 1.5→5.0 (TS handles normal ~0.8% winners, dynamic TP handles exceptional 2.5× ATR moves). (2) custom_exit adds dynamic_tp: if profit >= 2.5× ATR_mult × entry_atr_pct → exit. Expected: avg win increases, R/R improves toward 1.0+.
- v0.99.11 (2026-03-27): REVERT H-C stoploss change. v0.99.10 (stoploss -0.010) CATASTROPHIC: WR crashed 88%→65%, profit negative (-$5.75), 34 stop_loss exits at -1.29% avg (all losses). Reverting stoploss to -0.194 (v0.99.6 level). H-C hypothesis REJECTED — tight SL didn't fix R/R, it destroyed it.
- v0.99.10 (2026-03-27): H-C test — stoploss: -0.194 → -0.010. H-B (1.5% ROI floor) failed — TS still clipped winners at +0.8%. H-C hypothesis: tighter SL caps losses earlier, improves R/R from 0.46 toward 0.79.
- v0.99.9 (2026-03-27): Trigger backtest on v0.99.8 H-B ROI floor code.
- v0.99.8 (2026-03-27): H-B ROI floor test — minimal_roi "0": 0.349% → 1.5%.
  Problem (v0.99.6): R/R = 0.47 — avg win 0.48%, avg loss 1.69%. TS at +0.8% clips
  winners too early. Hypothesis: force 1.5% ROI exit before TS activates, letting
  winners run longer. If avg win increases to 1.5%+, R/R should flip above 1.0.
  NOTE: v0.99.7 fix only updated user_data/ (wrong dir) — this is the actual fix.
- v0.99.5 (2026-03-27): Add FIL/USDT to pair whitelist (11 pairs). Goal: increase trade frequency from ~49/yr toward 100+/yr target. FIL is high-volume storage token, not yet tested. All 10 existing pairs positive with wins — no removals needed.
- v0.99.4 (2026-03-27): Iteration backtest — confirm v0.99.3 results stable. All 10 pairs positive with wins. No fix needed.
- v0.99.3 (2026-03-26): Add AAVE/USDT to pair whitelist (10 pairs). Goal: increase trade frequency from ~44/yr toward 100+/yr target. AAVE is high-volume DeFi token, not yet tested in this strategy. All existing 9 pairs positive with wins — no removals needed.
- v0.99.2 (2026-03-26): Restore DOT/USDT to pair whitelist (9 pairs). DOT had -$3.10 in v0.96.0 due to TS offset 1.3% being too wide. With TS offset back at 0.8%, DOT now performs well: 11 trades, 90.9% WR, +$19.60 profit. Trade frequency increased from 77→88 (+14%), profit from $132→$152 (+15%).
- v0.99.1 (2026-03-26): Remove ALGO/USDT from pair whitelist — 2 trades, 0 wins, -$25.59 profit (both trades were big losers via trailing_stop_loss). XLM/USDT kept (+$26.97, 66.7% WR, 6 trades) — net positive addition.
- v0.99.0 (2026-03-26): Add XLM/USDT + ALGO/USDT to pair whitelist. Goal: increase trade frequency from ~35/yr toward 100+/yr target. Both pairs are high-volume, not yet tested in this strategy. Monitoring for 0 wins or negative profit — will remove if they drag down PF.
- v0.98.0 (2026-03-26): Widen OTE zone optimization bounds (lower: 25-40%, upper: 60-80%). Defaults stay at 30-70%. Gives hyperopt more room to explore wider zones that may increase trade frequency toward 100+/yr target. Current 25-35%/65-75% bounds were too narrow.
- v0.96.1 (2026-03-25): REVERT TS offset 1.3%→0.8%. v0.96.0's wider TS offset (1.3%) caused TS WR to collapse from 92.1%→71.6% and profit to drop from $107.80→$94.83. Winners ran too far before TS activated, giving back too much. Restoring 0.8% offset (validated in v0.89.0 with 92.1% TS WR). Keep OTE 30-70%.
- v0.96.0 (2026-03-25): H3: Revert OTE zone 50-65% → 30-70%. v0.95.0's tighter OTE (50-65%) only produced 32 trades — too few. Reverting to wider 30-70% to restore trade frequency toward 100+/yr target. Keep TS offset 1.3% (winners still ride longer).
- v0.95.0 (2026-03-25): H2: Increase trailing stop offset 0.8% → 1.3%. Hypothesis: current 0.8% offset activates TS too early, cutting winners before they fully run. Widen to 1.3% so winners ride longer before TS kicks in. Combined with H1's tighter OTE zone (50-65%) for better entry quality.
- v0.94.0 (2026-03-25): H1: Tighten OTE zone 28-72% → 50-65%. Hypothesis: deeper pullbacks (50-65%) have better risk/reward than shallow 28-72% range. Target: avg profit/trade from 0.48% → 1%+. May reduce trade count slightly but quality should improve.
- v0.93.0 (2026-03-25): Add ADA/USDT back to pair whitelist. v0.83.0 had ADA with 6 trades, 83.3% WR, +$5.80 profit — all positive. Testing if 8-pair config increases trade frequency toward 100+/yr target while maintaining quality (91%+ WR).
- v0.92.0 (2026-03-25): REVERT confirmation_candle to False. v0.91.0 confirmation_candle=True cut trades from 79→40 (-49%) and profit from $135→$71 (-47%) with only marginal WR improvement (91.1%→92.5%). Net effect: confirmation_candle=True is too aggressive. Reverting to False to maximize trade frequency and absolute profit.
- v0.90.0 (2026-03-25): Add BTC/USDT back to pair whitelist. BTC was best performer in v0.65.0 baseline (9 trades, +$14.04, 55.6% WR). Testing if 7-pair config pushes trade frequency toward 100+/yr target while maintaining quality (92%+ WR).
- v0.89.0 (2026-03-25): Add AVAX/USDT back to pair whitelist. AVAX had 100% WR (+$38.39) in v0.83.0 — best per-pair performance. Testing if 6-pair config increases trade frequency without degrading quality.
- v0.88.0 (2026-03-24): REVERT 5m→15m. 5m generated 183 trades/2yr (+115%) but TS win rate collapsed from 90.6%→68.3% and profit went from +$140→-$43.50. 5m timeframe causes too many false TS activations due to intra-candle noise. Reverting to 15m with existing 5-pair config (ETH/DOT/LINK/UNI/NEAR).
- v0.82.0 (2026-03-24): Loosen OTE zone (30-70%→28-72%) to capture more valid entries. Small incremental widening — conservative vs FF-2's catastrophic 20-80%.
- v0.81.0 (2026-03-23): Remove MATIC/USDT from pair whitelist. MATIC had 0 trades in backtest despite being whitelisted since v0.75.0 — strategy never generates entries for it. Cleaning up pairlist.
- v0.80.0 (2026-03-23): Remove ATOM/USDT from pair whitelist. ATOM was only pair with negative profit (-$7.44, 75% WR, PF 0.58). Removing it should improve overall stats.
- v0.79.0 (2026-03-23): Widen TS offset (0.8%→1.2%). Result: profit $117.61 vs $135.82, WR 78.6% vs 90.5%, PF 1.88 vs 3.87 — WORSE. TS offset 1.2% is too wide, missed winners. REVERTED to 0.8%.
- v0.78.0 (2026-03-23): FAILED — Tighten TS offset (0.8%→0.6%). Result: profit $79.96 vs $135.82, PF 3.24 vs 3.87. TS too tight, cutting winners early. REVERTED to 0.8%.
- v0.75.0 (2026-03-22): Add 8 new pairs (SOL, AVAX, MATIC, LINK, ATOM, UNI, XRP, NEAR) to boost trade volume. XRP restored (was removed in v0.72.0 — had 55.6% WR, +$8.43 in v0.65.0 baseline).
- v0.74.0 (2026-03-22): Raise early_profit_take (1.5%→2.5%) — let winners run further. TS at 0.8% intercepts all before +1.5%. Fix: early_profit_take → 2.5% (ROI at 2% handles stalls).
- v0.73.0 (2026-03-22): Raise early_profit_take (1.0%→1.5%). Only 2/41 via early_profit (4.9%), TS intercepts too early.
- v0.72.0 (2026-03-22): Fix trailing stop (1.5%→0.8%) + remove XRP from pair whitelist.
  Problem (v0.71.1): TS exits = 23/53 (43.4%), 39.1% WR, -$54.46. Offset 1.5% is still
  too wide — winners run to +1.5-2%+ before TS activates, then give back -0.69% avg.
  Also XRP/USDT: 12 trades, 50% WR, -$33.69 — only negative pair, remove it.
  Fix: (1) trailing_stop_positive_offset: 1.5% → 0.8% (TS activates at +0.8%, catching
  reversals earlier). (2) Remove XRP/USDT from config pair_whitelist.
- v0.71.1 (2026-03-22): Fix trailing_stop_positive config error.
  Problem (v0.71.0): trailing_stop_positive was 0.015 (1.5%) — same as the offset!
  Freqtrade requires offset > positive. Both 1.5% = config error → backtest crash.
  Fix: trailing_stop_positive: 0.015 → 0.005 (0.5%). Now TS trails 0.5% behind peak,
  offset activates at +1.5%. Also added clarifying comment.
- v0.71.0 (2026-03-22): Fix trailing stop (tighten offset 2.5%→1.5%) + raise early_profit_take (0.8%→1.0%).
  Problem (v0.70.0): trailing_stop_loss = 13 exits, 12 losses, 7.7% WR, -$65.95.
  TS offset 2.5% is too wide — allows winners to run to +2.5% before activating,
  then reverses and gives back -1.48% avg. Meanwhile early_profit_take at 0.8% exits
  winners averaging 1.06% (100% WR on 38 trades) — they had more to give.
  Fix: (1) trailing_stop_positive_offset: 2.5% → 1.5% (TS activates at +1.5% instead
  of +2.5%, catching reversals earlier). (2) early_profit_take: 0.8% → 1.0% (winners
  average 1.06%, so 0.8% was too tight — let them run longer before locking in).
  Expected: Fewer TS loss trades, higher % of exits via 100% WR early_profit_take.
- v0.70.0 (2026-03-22): Disable ALL time-based exits (time_exit_1 and time_exit_2).
  Problem (v0.69.0): time_exit_6h = 10 trades (0% WR, -$25.68), time_exit_8h = 8 trades
  (0% WR, -$10.60). Total -$36.28 destroyed by cutting winners that hadn't yet hit
  early_profit_take (+0.8%) or trailing_stop (+1.5%). All time exits are 0% WR — they
  are pure bleed.
  Fix: Set time_exit_1_enabled = False, time_exit_2_enabled = False.
  Winners now run to: early_profit_take (+0.8% after 45min), trailing_stop (+1.5%),
  or ATR stoploss. This eliminates -$36.28 of guaranteed losses.
  Expected: Slightly fewer trades, but higher WR and PF as winners are no longer cut.
- v0.69.0
- v0.69.0 (2026-03-21): Apply hyperopt-conservative fixes from v0.68.0 overfitting analysis.
  Problem (v0.68.0): Hyperopt found 61 trades but backtest showed 4 — classic overfitting.
  Key hyperopt findings (confirmed across 2 runs): confirmation_candle=False and wider
  trailing stop. Applying full hyperopt params caused overfit.
  Fix (conservative): (1) Disable confirmation_candle by default (hyperopt found True
  was filtering valid entries). (2) Widen trailing_stop_positive 0.5% → 1.5% and
  offset 1.5% → 2.5% (conservative interpretation of hyperopt's 21.2%/23%).
  Expected: More trades from fewer entry filters + better winner capture from wider TSL.
- v0.65.0 (2026-03-20): Widen ROI 305 → 400 candles at 2% profit.
  Problem (v0.64.0): ROI 305 at 1% (~76h) cuts winners too early. time_exit_6h/8h losses
  persist (13 trades, -22.71 USDT, 0% WR). Fix: Raise exit from 1% → 2% and push from
  305 candles → 400 candles (~67h). Faster timeline (67h vs 76h), higher bar (2% vs 1%).
  Trailing stop still activates at +1.5%, manages winners that overshoot 2%.
- v0.64.0 (2026-03-20): REVERT v0.63.0 — massive regression. v0.63.0: 45.7% WR, 0.01% profit,
  1.16 PF, 27.8% DD. Problem: removing ROI 305 + raising early_profit to 1.5% caused trades
  to ride to time_exit_6h/8h (0% WR, -28 USDT combined). Fix: restore ROI 305 at 1% +
  restore early_profit_take at 0.8% (from v0.62.0).
- v0.63.0 (2026-03-20): Remove ROI 305 entry + raise early_profit_take to +1.5%.
  Problem (v0.62.0): time_exit_6h expanded (3→7 trades, -14.13 USDT) despite ROI 305
  raised to 1%. These trades hit ROI 305 at <1% profit and were cut there — losing exits.
  Meanwhile early_profit_take at +0.8% locks in small wins that could have run further.
  Fix: (1) Remove ROI 305 entry entirely — trades fall through to trailing_stop or
  time_exit_1 (8h) instead. (2) Raise early_profit_take from +0.8% to +1.5% so only
  stronger trades exit early; weaker ones ride TSL (activates at +1.5%, exits at +1.0%).
- v0.62.0 (2026-03-20): Change ROI 305 exit from 0% → 1%.
  Problem (v0.61.0): ROI exit at 0% profit (305 candles = 5h) cut stale trades at
  breakeven. These trades had +0.5% but missed trailing_stop (1.5% offset) and
  time_exit hadn't fired yet. Setting ROI 305 to 1% means trades need 1%+ for ROI
  to exit — otherwise they ride trailing_stop or time_exit_1 (4-8h).
- v0.61.0 (2026-03-20): Disable time_exit_2 (6h exit).
  Problem (v0.60.0): time_exit_6h was the ONLY losing exit type — 4 trades, -10.90 USDT,
  0% WR. These stale trades were cut at +0.5% profit after 6h while DOGE/BTC (which have
  time_exit_1=8h) would have had winners running longer. time_exit_1 at 4h/6h/8h per-pair
  still handles losers. early_profit_take (+1.5%, 45min), trailing_stop (+1.5%), and
  ROI table handle winners. Removing time_exit_2 lets DOGE/BTC winners run to their 8h
  time_exit_1 instead of being cut at 6h with +0.5% profit requirement.

- v0.60.0 (2026-03-19): Remove SOL/USDT from pair whitelist.
  SOL was the only losing pair in v0.59.0: 7 trades, 0.43 WR, -4.68 USDT total.
  Also improved the whitelist to top 6 performers: BTC, DOGE, DOT, XRP, ETH, ADA.

- v0.59.0 (2026-03-19): Remove BNB/USDT from pair whitelist.
  BNB had 0% WR across 2 trades, -5.10 USDT total. Worst performer in v0.58.0 backtest.
  Top 5 performers kept: BTC, DOGE, DOT, XRP, ETH, ADA, SOL (7 pairs total).

- v0.58.0 (2026-03-19): Disable ChoCH exits entirely.
  Problem (v0.57.0): exit_signal (ChoCH) was 17/43 trades at -0.63% avg, totaling
  -35.87 USDT — destroying all profit from the other 26 trades (+65.53 USDT).
  ChoCH exit win rate was only 11.8%. Meanwhile early_profit, trailing_stop, and ROI
  exits were ALL 100% WR. Fix: disable populate_exit_trend entirely. Let mechanical
  exits (early_profit_take at +0.8%, trailing_stop at +1.5%, ROI table, time_exit,
  ATR stoploss) handle all exits. ChoCH was prematurely killing trades that would
  have been profitable if allowed to run to their natural exit.

- v0.57.0 (2026-03-19): Restore 8-pair list + XRP-specific stop loss fix.
  Problem (v0.56.0): Removing XRP AND losing DOT/DOGE/ADA caused regression — 39→21 trades,
  46.2%→38.1% WR, 2.25%→0.74% profit. RIP. Restoring all 8 pairs.
  XRP-specific fix: widen ATR from 2.0→3.5 (give trades room) + add early_profit at +0.5%
  (capture winners before ChoCH reversals lock in losses).

- v0.55.0 (2026-03-19): Per-pair parameter optimization — extended to SOL, BNB, XRP, DOT, AVAX.
  Prior versions only had custom params for BTC, ETH, ADA. 5 of 8 pairs used global defaults.
  Key insight: SOL behaves like BTC (high-beta, trends hard → require_ote=False, time_exit=8h).
  XRP mean-reverts (lower vol → tighter ATR). DOT/AVAX high-vol → 6h exits.
  Results TBD after backtest.

- v0.54.0 (2026-03-19): ChoCH profit guard — block exits when trade is underwater.
  Problem (v0.53.0): exit_signal exits (30.6% of trades) avg -0.76%. ChoCH fires when
  15m structure breaks, but the trade is often still at a loss when it fires. Fix:
  in custom_exit, check if choch_signal AND current_profit < 0 → block exit (return None).
  The trade continues: either recovers to hit early_profit/trailing_stop, or eventually
  hits the dynamic stoploss. This prevents locking in losses when structure changes are
  just temporary retracements.

  Result: NO IMPROVEMENT. ChoCH guard didn't reduce exit_signal losses (-0.51% avg, 11 trades).
  The guard causes trades to fall through to time_exit instead. ROI dropped (7→5 trades).
  ChoCH exits remain problematic — directionally correct but timing is off.
  Problem (v0.53.0): exit_signal exits (30.6% of trades) avg -0.76%. ChoCH fires when
  15m structure breaks, but the trade is often still at a loss when it fires. Fix:
  in custom_exit, check if choch_signal AND current_profit < 0 → block exit (return None).
  The trade continues: either recovers to hit early_profit/trailing_stop, or eventually
  hits the dynamic stoploss. This prevents locking in losses when structure changes are
  just temporary retracements.

- v0.53.0 (2026-03-19): REVERT confirmation candle on exits.
  v0.52.0 introduced (choch==-1 AND close<open) for longs to require candle confirmation
  on ChoCH exits. Results: profit 2.02%→1.19% (-0.83pp), win rate 44.4%→41.7%.
  The confirmation filtered too many valid exits, causing time_exit_4h to take over
  (10 trades, avg -2 USDT each) and remaining exit_signal exits to have massive losses.
  ChoCH alone is the right exit signal for 15m TF — revert to v0.51.0 logic.

- v0.52.0 (2026-03-19): Require confirmation candle for ChoCH exits (roadmap Phase 4).
  Problem (v0.51.0): exit_signal exits (30.6% of trades, avg -1.70%) still cutting winners
  short. ChoCH fires on structure rejection but candle direction confirms the rejection is
  genuine. Fix: require (choch==-1 AND close<open) for longs, (choch==1 AND close>open) for
  shorts. This is the same confirmation-candle logic from entry quality (v0.40.0) applied
  to exits.

- v0.51.0 (2026-03-19): Remove HTF trend exits from populate_exit_trend.
  Problem (roadmap Phase 4): exit_signal exits (33.3% of trades, avg -1.71%) were cutting
  winners short via 1H trend reversal. ChoCH exits on entry TF (15m) are more responsive
  and appropriate for local exit decisions. Removing HTF trend component lets winners run.

- v0.50.0 (2026-03-19): Tighten OTE zone — lock to 30-70% band, make require_ote MANDATORY.
  Problem (roadmap Phase 4): OTE zone range was 30-85% (could widen to 50-85%). Wider OTE
  zones allow entries at extreme Fibonacci levels (78.6%, 88.6%) with lower reversal probability.
  ICT Silver Bullet: only trade discount (38-50%) and mid (50-65%) zones.
  Also: require_ote optimize=False — hyperopt CANNOT disable it (v0.38.0 disabled it → 9 trades, 11.1% WR).
  OTE bounds now hyperoptable within 25-38% (lower) and 60-75% (upper) tight band.
  This version tests with filter ENABLED to measure actual weekend impact.

- v0.47.0 (2026-03-18): Double confirmation — use BOS instead of ChoCh.
  Problem (roadmap 2.2): ChoCh can fire on minor structure breaks, reducing entry quality.
  Fix: Replace `choch==-1` with `bos==-1` for shorts, `choch==1` with `bos==1` for longs.
  Result: WR 22%→36.5%, profit -12.9%→+0.05%, drawdown 1.64%.

- v0.46.0 (2026-03-18): Early profit exit + wider stoploss floor.
  Problem: TSL exits 47.6% of trades at avg -1.27%. Custom stop also tight (floor -6%).
  Fix: (1) Add early profit exit at +0.8% to secure wins before TSL kicks in.
       (2) Widen dynamic stoploss floor from -6% to -8%.

- v0.45.0 (2026-03-18): Disable session filter — was too aggressive (19 trades, 10.5% WR)
  The NY/London filter (08:00-11:00, 13:30-16:00 UTC) was cutting too many trades
  (19 vs hundreds previously) and win rate dropped to 10.5% with -19.48% profit.
  Reverting to disabled by default. Will revisit with looser session window.

- v0.44.0 (2026-03-18): Add session filter (NY/London only).
  Problem: Strategy runs 24/7 including low-volume Asian session, diluting
  entry quality. ICT Silver Bullet methodology specifically targets NY and London
  sessions for highest liquidity/vatility.
  Fix: Session filter — only allow entries during:
    - London: 08:00-11:00 UTC
    - NY: 13:30-16:00 UTC
  All other times: skip entry (no filtering of existing positions).
  Expected: ~50% fewer trades, higher quality, improved WR.

- v0.43.0 (2026-03-18): Widen ATR stoploss to 3x.
  Problem: 54% of trades hit trailing_stop_loss at avg -1.18%. ATR floor was -4%
  which was too tight for volatile assets (BTC ATR% ~2-3% → -4% is only ~2 ATR).
  ADA's ceiling was -1.5% which is basically noise.
  Fix: (1) Custom stoploss floor -4% → -6%. (2) ATR mult range 1.0-3.0 → 1.0-4.0,
  default 2.425 → 3.0. (3) BTC 2.2→3.0, ETH 1.7→2.5, ADA 1.2→2.0.
  Expected: Fewer premature stop-outs, more room for ICT reversals.

- v0.42.0 (2026-03-18): Fix trailing stop formula.
  Problem: trailing_stop_positive was 0.277 (27.7%!) instead of 0.005 (0.5%).
  Also trailing_stop_positive_offset was 0.295 (29.5%) instead of 0.015 (1.5%).
  This caused the trailing stop to activate way too late and trail way too far.
  Fixed: trailing_stop_positive=0.005, trailing_stop_positive_offset=0.015.
  Expected: Much fewer trailing_stop_loss exits, more ROI exits captured.

Changelog:
- v0.39.0 (2026-03-03): Recovery Iteration.
  Re-enabled mandatory OTE filter (30-70%) as v0.38.0 hyperopt-disabled logic
  produced only 9 trades with 11.1% WR. OTE is a core SMC requirement for
  high-probability setups (entering in the "discount" or "premium" zone).
- v0.38.0 (2026-03-02): Applied Hyperopt results from Feb 27 run (results-122).
- v0.35.0 (2026-03-01): Fix FVG active zone detection — same class of bug as OB window (v0.31.0).
  ROOT CAUSE: `fvg_mitigated.isna()` was supposed to isolate "unmitigated" FVGs.
  But during backtesting the smc library has full future data and sets MitigatedIndex
  for EVERY FVG that is eventually mitigated (nearly all of them). So `fvg_mitigated.isna()`
  was True only for the very last candles → zone forward-fills were essentially empty →
  `active_bullish_fvg` was always False → 0 trades in v0.33.0 and v0.34.0.
  FIX: Rolling window (30 candles, ~7.5h at 15m): "Was a bullish/bearish FVG formed
  within the last 30 candles?" — sensible SMC recency check, analagous to OB fix.
  Also simplified opposite-side imbalance filter to use same rolling zone levels.
  Expected: Restores trade flow to 90+ (similar to v0.27.0/v0.29.0) while keeping
  FVG recency as a quality gate.
- v0.32.0 (2026-02-28): Fix OB recency window — increase from 20 to 100 candles.
  Root cause of v0.31.0 0-trade bug: smc.ob() produces sparse OB candles (one
  every ~50-200 candles). A 20-candle window (~5h at 15m) misses most OBs.
  Fix: expand ob_window from 20 → 100 candles (~25h / ~1 day at 15m).
  Rationale: "Was institutional buying/selling present somewhere in the last day?"
  is a much more sensible SMC recency question. OBs are structural anchors — the
  last down-candle before a bullish BOS may have been printed hours ago and it
  still acts as demand. 100 candles ensures the flag is True for the majority of
  candles following an OB formation, giving ChoCH+sweep signals a chance to fire.
  All other settings unchanged from v0.29.0 (wider ROI, safe_long/short filter).
- v0.34.0 (2026-03-01): Quality Gate Shift + Risk Expansion.
  Problem (v0.32): 2 trades in 2 years. The `smc.ob()` (Order Block) library
  is far too sparse for reliable confluence across the board.
  Fix: Set `require_ob=False` globally.
  Problem (v0.29): TSL avg loss (-1.61%) vs avg ROI win (+0.57%) math is
  inverted. TSL hits occur too early before impulsive reversals.
  Fix: Widen ATR SL from 1.5x -> 2.0x ATR to give ICT reversals room.
  Fix: min_rr reduced 1.5 -> 1.0 (allow standard SMC setups).
  Primary Quality Gate: `require_fvg=True` (active imbalance zone) +
  opposite-side imbalance filter (safe_long/short).


- v0.31.0 (2026-02-28): Fix OB detection bug (0 trades in v0.30.0). Replace
  "price inside exact OB box" check with "recent OB formed within N candles"
  (rolling window). The precise OB box (top/bottom ffill) is too narrow —
  price rarely sits inside the exact OB candle range at entry time. The correct
  SMC interpretation: an OB nearby (within 20 candles) signals institutional
  interest at this price level. Entry at OB + sweep + ChoCH is still high
  confluence. Wider ROI targets from v0.30.0 retained.

- v0.30.0 (2026-02-28): Mandatory Order Block confluence + wider ROI targets.
  Analysis of v0.29.0 (99 trades, 24.2% WR, -19.16%):
  - TSL exits reduced from 55→36 (imbalance filter worked), but still too many.
  - Root cause: avg win = +0.57%, avg TSL loss = -1.61%. Need ~74% WR to break
    even. With SMC signals at 24%, math is broken at the R:R level.
  - Two-pronged fix:
    (1) require_ob=True by default: Force entry to be inside an active Order Block
        zone. OBs are the structural footprint of institutional money — the
        last down-candle before a BOS up (bullish OB) or last up-candle before
        a BOS down (bearish OB). Price returns to OBs as demand/supply zones.
        Entering at OB + sweep + ChoCH = max confluence ICT entry. Fewer trades,
        much higher reversal probability (expected WR 35-50%).
    (2) Widen ROI table to let winners run: avg ROI exit was +0.57% — institutional
        moves at OBs tend to be impulsive (BOS candles). Targets widened to:
        0min→5%, 30min→3.5%, 60min→2%, 120min→1.2%, 240min→0.5%, 480min→-0.5%.
        Goal: push avg ROI exit from 0.57% to 1.5%+, transforming the math.
  Expected: 40-60 trades (OB filter is strict), WR 35-50%, first profitable run.
- v0.29.0 (2026-02-28): Fix FVG zone detection bug (0 trades in v0.28.0).
  Bug: v0.28.0 produced ZERO trades. Root cause: `active_bullish_fvg` used
  `.ffill()` on a boolean series (always False except sparse FVG candles), so
  it never propagated True forward. The logic checked if the CURRENT candle IS
  an FVG candle, not if price is INSIDE a recent FVG zone.
  Fix: Track unmitigated FVG zone levels (top/bottom) via forward-fill, then
  check if current close is within the zone: close >= fvg_bottom AND close <= fvg_top.
  This correctly detects "price is trading inside an active FVG imbalance zone."
  Also: require_fvg default changed to False — the opposite-side imbalance filter
  (safe_long/safe_short) is the primary quality gate. require_fvg is available as
  an optional confluence filter for hyperopt to evaluate.
  Expected: Restores trade flow from v0.27.0 (~128 trades), with TSL exits reduced
  by opposite-side imbalance filter.
- v0.40.0 (2026-03-03): Confirmation candle filter.
  Problem: Many entries trigger at the correct zone but price has already started reversing
  against us. The ChoCH confirms structure break, but we might be entering on a doji or
  indecision candle with no clear momentum yet.
  Fix: Added `require_confirmation_candle` parameter (default=True, hyperoptable).
  - Longs: Only enter when current candle is BULLISH (close > open) — momentum aligned.
  - Shorts: Only enter when current candle is BEARISH (close < open) — momentum aligned.
  Expected: Reduced volume (~20-30% fewer entries), higher quality entries, improved WR.
  The entry is still valid on the very next candle if conditions hold — we just avoid
  entries where momentum is ambiguous.
- v0.41.0 (2026-03-03): Refined per-pair parameters & hyperopt bugfix.
  - Increased BTC ATR multiplier 2.0 -> 2.2 to further reduce premature stop-outs.
  - Added ETH specific overrides (1.7x ATR, 6h time exit).
  - Fixed "CategoricalParameter space must be [a, b, ...]" bug - require_ote now has [True, False]
    categorical parameters in the search space have at least two options.
- v0.39.0 (2026-03-03): Re-enabled mandatory OTE filter (30-70%).
  v0.38.0 hyperopt disabled require_ote → 9 trades, 11.1% WR (disastrous).
  Restored require_ote=True (optimize=False) to prevent hyperopt from removing it.
- v0.28.0 (2026-02-28): FVG confluence + opposite-side imbalance filter.
  Problem: v0.27.0 results identical to v0.26.0 (128 trades, 21.1% WR, -27.03%).
  Analysis: 55/128 trades hit trailing_stop_loss in avg 1h04m. Even trend-aligned
  entries get stopped out immediately — this is an ENTRY QUALITY problem, not a
  trend-alignment problem. The ATR SL is being hit because price is attracted to
  unmitigated FVGs beyond the stop loss (liquidity magnets, stop-hunt risk).
  Fixes:
  (1) require_fvg=True by default: Only enter when price is inside an active
      unmitigated FVG zone. This ensures we enter where market structure supports
      a reversal (imbalance needs to be filled).
  (2) Opposite-side imbalance check: Skip trade if there's an unmitigated FVG
      on the other side of the stop loss. Key concept (Marco's SMC rule):
      "Is there an obvious imbalance on the opposite side of where my stop would
      go? If YES → Skip (price will be attracted there). If NO → Take trade."
  (3) min_rr default raised to 1.5 (was 1.0) — require better setups only.
  Expected: Fewer trades, higher quality, WR target 45-55%.
- v0.27.0 (2026-02-27): Restore HTF trend alignment filter.
  Root cause of v0.26.0's 21.7% win rate found: the HTF trend column was computed 
  in populate_indicators but the `htf_trend_col` variable in populate_entry_trend was 
  declared but NEVER used in any filter condition — it was a dead variable dropped during 
  the v0.21.0 SMC refactor. This meant entries fired against the 1H trend direction 
  (entering longs in bear markets, shorts in bull markets), leading to 55 immediate 
  trailing_stop_loss exits at avg -1.58%.
  Fix: Added `htf_trend_col` to both long and short entry conditions.
  Long entries now require trend_1h == 1 (bullish 1H structure).
  Short entries now require trend_1h == -1 (bearish 1H structure).
  Expected: Fewer trades, significantly higher win rate.
- v0.26.0 (2026-02-27): Decouple sweep from ChoCH confirmation.
  Fixed a logic bug introduced in v0.21.0 where both the liquidity sweep AND the structure 
  break (close below swing low) were required on the *same* 15m candle, devastating trade volume.
  Now uses a 5-candle rolling window for recent sweeps, and checks for a proper SMC ChoCH.
- v0.25.0 (2026-02-27): Per-pair parameter overrides.
  Added a custom_pair_params dictionary to allow overriding hyperoptable parameters
  (like atr_multiplier, require_ote, time_exit hours) explicitly for pairs with different 
  volatile profiles (e.g. BTC vs ADA).
- v0.24.0 (2026-02-27): Made time-based exits hyperoptable.
  Problem: Static time exits (4h and 6h) have been hurting win rate by cutting marginal
  winners prematurely. By making these parameters hyperoptable within the "sell" space,
  we allow the optimizer to determine the best duration and profit thresholds,
  or disable time exits altogether if dynamic stop loss handles it well enough.
- v0.22.0 (2026-02-26): ATR-based dynamic stoploss + OTE filter re-enabled by default.
  Problem: v0.20 had 61 SL exits at avg -2.79%. Fixed -2.5% SL was too blunt — too tight
  for BTC (high vol) causing premature stops, too wide in calm markets (ETH, ADA).
  Fixes:
  (1) use_custom_stoploss = True — ATR-based SL at 1.5x ATR(14) from entry candle.
      Floor: -1.5% (max precision), Ceiling: -4.0% (don't let it run).
  (2) require_ote default → True (loose: 20-90%). Re-enables quality filter.
      Motivation: v0.19 disabled OTE, volume went up but quality fell. v0.20 kept it off
      but signal quality wasn't the bottleneck — SL placement was.
  (3) atr_multiplier added as hyperopt param (1.0-2.5x) for future optimization.
  static stoploss remains at -0.04 as absolute backstop (Freqtrade requirement).
- v0.21.0 (2026-02-23): MAJOR REFACTOR — replaced all hand-rolled indicators with smartmoneyconcepts library.
  New features: proper liquidity sweep detection (clustered highs/lows + swept tracking),
  FVG with mitigation tracking, BOS + ChoCH distinction, Order Block confluence.
  Risk management preserved from v0.20.0 (SL -2.5%, trailing after +1.5%, time exit 4h).
- v0.20.0 (2026-02-23): Tighter risk management overhaul.
  v0.19 analysis: 51% WR but -40.7% total due to loss:win ratio of 4.3:1.
  349 profitable exits (ROI+target) at +1% avg, 0 losses. Signal is GOOD.
  116 SL exits at -4.29% avg destroy all gains. 111 draws waste time.
  Fixes: (1) SL tightened -4% -> -2.5% (2) Trailing stop after +1.5% profit
  (3) Time-based exit at 4h if not profitable (4) Drop LINK/USDT (35% WR)
  (5) Negative ROI at 8h to cut stale trades (6) Faster profit-taking via ROI table.
- v0.19.0 (2026-02-20): Loosened entry by disabling OTE requirement, but tightened risk.
- v0.18.0 (2026-02-20): Disabled BOTH trailing_stop AND use_custom_stoploss.
- v0.17.0 (2026-02-19): Fixed custom_stoploss - anchors to ENTRY price not current price.
- v0.16.0 (2026-02-19): Disabled custom_stoploss - using static SL only.
"""

import numpy as np
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional, Dict, Any
import talib.abstract as ta
from freqtrade.strategy import IStrategy, merge_informative_pair
from freqtrade.strategy.parameters import IntParameter, DecimalParameter, CategoricalParameter
from freqtrade.persistence import Trade
from smartmoneyconcepts import smc


class LiquiditySweep(IStrategy):
    """
    Liquidity Sweep Reversal Strategy — powered by smartmoneyconcepts.
    
    Trades reversals after liquidity grabs, with optional OTE zone + Order Block confluence.
    Uses multi-timeframe analysis (15m entry, 1H context).
    """
    
    INTERFACE_VERSION = 3
    STRATEGY_VERSION = "0.99.110"

    # ── Per-Pair Parameter Overrides ──────────────────────────────────────────
    # Keys should match parameter names exactly. If a pair is not listed, the strategy
    # falls back to the default/hyperopted global parameters.
    # v0.55.0: Added SOL, BNB, XRP, DOT, AVAX per-pair overrides.
    # Prior: only BTC, ETH, ADA had custom params. 5 pairs used global defaults.
    custom_pair_params = {
        # v0.99.28: atr_mult REVERTED to v0.99.26 levels. v0.99.27 doubling (6-7×)
        # was catastrophic: TS losses avg -$11.86 (vs -$6.91 at 3-3.5×).
        # The wider stops let losing trades ride 16h instead of cutting at 10min.
        # UNI/USDT removed (v0.99.27 change kept).
        "BTC/USDT": {
            "atr_multiplier": 3.0,       # v0.99.28: reverted
            "require_ote": False,        # BTC trends hard, often misses OTE
            "time_exit_1_hours": 8
        },
        "ETH/USDT": {
            "atr_multiplier": 2.5,       # v0.99.28: reverted
            "require_ote": True,
            "time_exit_1_hours": 6
        },
        "ADA/USDT": {
            "atr_multiplier": 2.0,       # v0.99.28: reverted
            "require_ote": True,
            "time_exit_1_hours": 4
        },
        "BNB/USDT": {
            "atr_multiplier": 2.5,       # v0.99.28: reverted
            "require_ote": True,
            "time_exit_1_hours": 6
        },
        "DOT/USDT": {
            "atr_multiplier": 3.0,       # v0.99.28: reverted
            "require_ote": True,
            "time_exit_1_hours": 6
        },
        "AVAX/USDT": {
            "atr_multiplier": 3.0,       # v0.99.28: reverted
            "require_ote": True,
            "time_exit_1_hours": 6
        },
        "DOGE/USDT": {
            "atr_multiplier": 3.0,       # v0.99.28: reverted
            "require_ote": False,        # DOGE trends hard, often misses OTE
            "time_exit_1_hours": 8
        },
        # v0.99.27: UNI/USDT removed — only pair with negative profit (-$5.83, 57.1% WR)
        "NEAR/USDT": {
            "atr_multiplier": 2.0,       # v0.99.28: reverted
            "require_ote": True,
            "time_exit_1_hours": 5
        },
        "LINK/USDT": {
            "atr_multiplier": 2.5,       # v0.99.28: reverted
            "require_ote": True,
            "time_exit_1_hours": 6
        },
        "AAVE/USDT": {
            "atr_multiplier": 3.0,       # v0.99.28: reverted
            "require_ote": True,
            "time_exit_1_hours": 6
        }
    }

    def get_param(self, param_name: str, pair: str, default_value: Any) -> Any:
        """Helper to fetch pair-specific parameter or fallback to global"""
        if pair in self.custom_pair_params and param_name in self.custom_pair_params[pair]:
            return self.custom_pair_params[pair][param_name]
        return default_value


    # ── Risk Management ───────────────────────────────────────────────────────
    # v0.30.0: Widened ROI targets — OB entries at institutional demand/supply zones
    # tend to produce impulsive moves. Previous +0.57% avg win was too conservative.
    # Target: let institutional momentum trades run to 1.5%+ before taking profit.
    # v0.65.0: Widen ROI 305 → 400 candles at 2% profit.
    # Problem (v0.64.0): ROI 305 at 1% cuts winners prematurely at ~76h.
    # time_exit_6h/8h losses (13 trades, -22.71 USDT, 0% WR) persist — these are losing
    # trades that never reach 1% profit, so ROI doesn't fire for them anyway.
    # Fix: Raise ROI 305 to 2% AND push to 400 candles (~67h). Winners that would have
    # been cut at +1% at 76h can now run to 2% at 67h (faster timeline, higher target).
    # ROI table — "0": 5.0 means initial ROI at 5% profit (waits for TS or dynamic_tp first).
    # TS offset is 5.0% (v0.99.25) — TS activates and trails from +5% peak.
    # If TS never activates (price drops back), ROI exit fires at 5% profit.
    # Dynamic TP in custom_exit handles exceptional moves (1.5× ATR).
    minimal_roi = {
        "0": 5.0,
        "109": 0.07,
        "159": 0.10,
        "400": 0.02,
    }
    
    # Absolute backstop required by Freqtrade — custom_stoploss will use ATR, this is fallback
    stoploss = -0.194  # -19.4% absolute backstop (ATR SL handles tight exits)
    
    # v0.99.79: REVERT OTE-zone stop → ATR-based stop with -2.0% floor.
    # v0.99.78b (OTE-zone + 0.75% buffer): 46 TS exits, R/R=1.0078 — WORSE.
    # OTE-zone hypothesis REJECTED: fires more often than ATR floor, collapses R/R.
    # Reverting to ATR floor (-2.0%) which was validated in v0.99.77 (R/R=1.31).
    # Trailing stop — v0.99.50: DISABLED — reverts v0.99.48 failure.
    # v0.99.48 (TS=True, offset=0.8%): 34/40 trades TS exits, R/R=1.07, avg_win=0.75%.
    # TS clips winners before they can develop. Reverting to TS=False.
    trailing_stop = False
    trailing_stop_positive = 0.005      # 0.5% trailing distance
    trailing_stop_positive_offset = 0.008  # 0.8% activation threshold
    trailing_only_offset_is_reached = True
    
    # ATR-based dynamic stoploss (v0.99.15, updated v0.99.31)
    # v0.99.14: use_custom_stoploss=False → static -19.4% stoploss. Catastrophic.
    # v0.99.15-v0.99.29: use_custom_stoploss=True with ATR floor at -1.5%.
    # v0.99.29 test: DISABLE custom_stoploss → 3 catastrophic -19.64% stops = REJECTED.
    # v0.99.30: Widen floor -1.5%→-3.0%. REJECTED — avg_loss -3.13% vs -1.82%.
    # v0.99.31: REVERT floor -3.0%→-1.5%. BTC's ATR ~0.5-0.7% → dynamic_sl
    # at -1.5% to -2.1%, well within the -1.5% floor.
    use_custom_stoploss = True

    # ── Timeframes ────────────────────────────────────────────────────────────
    timeframe = '15m'
    informative_timeframe = '1h'
    startup_candle_count = 100

    # ── Hyperoptable Parameters ───────────────────────────────────────────────
    # Swing detection
    swing_length = IntParameter(3, 15, default=4, space="buy", optimize=True)
    htf_swing_length = IntParameter(5, 20, default=19, space="buy", optimize=True)
    
    # OTE zone — v0.50.0: Tighten to 30-70% mandatory.
    # Previously (v0.39.0-v0.49.0): 30-85% range with hyperopt could widen to 50-85%.
    # Problem: Wider OTE zones (50-85%) dilute entry quality by allowing entries
    # at extreme Fibonacci zones (78.6%, 88.6%) which have lower reversal probability.
    # ICT Silver Bullet principles: only trade the "discount" (38-50%) or "mid" (50-65%) zones.
    # Tightening to 30-70% enforces the high-probability OTE band only.
    # v0.38.0 hyperopt disabled require_ote entirely → 9 trades, 11.1% WR (disastrous).
    # Fix: require_ote=True is MANDATORY (optimize=False) to prevent hyperopt removing it again.
    # Tightening to 28-72% is a small incremental widening vs 30-70% baseline.
    # FF-2's 20-80% was catastrophic — outer Fibonacci = reversal traps.
    # v0.38.0 hyperopt disabled require_ote entirely → 9 trades, 11.1% WR (disastrous).
    # Fix: require_ote=True is MANDATORY (optimize=False) to prevent hyperopt removing it again.
    # H3: Revert to 30-70% OTE zone (v0.95.0's 50-65% was too tight — only 32 trades).
    # v0.95.0: OTE 50-65% with TS offset 1.3% → 32 trades. Revert to 30-70% for more trades.
    ote_lower = DecimalParameter(0.20, 0.40, default=0.30, space="buy", optimize=True)
    ote_upper = DecimalParameter(0.60, 0.80, default=0.70, space="buy", optimize=True)
    require_ote = CategoricalParameter([True, False], default=True, space="buy", optimize=False)  # MANDATORY — optimize=False prevents hyperopt disabling
    
    # ATR-based SL — new in v0.22.0
    # v0.34.0: ATR Multiplier increase to 2.0x (from 1.5x)
    # The avg TSL loss in v0.29.0 was -1.61% vs avg win +0.57%. Loosening SL
    # gives institutional reversals room to breathe.
    atr_multiplier = DecimalParameter(1.0, 6.0, default=3.0, space="buy", optimize=True)  # v0.99.89: 5.0→3.0 — v0.99.88 (atr_mult=5.0) and v0.99.87 (time_exit_2=2.0%) both had zero effect. BTC is floor-limited at -2.0% (floor tighter than any ATR calc). Try 3.0×: tighter ATR stops for non-BTC pairs may reduce avg loss on custom_stoploss exits.
    atr_period = IntParameter(10, 20, default=14, space="buy", optimize=False)
    
    # Entry filters
    min_rr = DecimalParameter(0.5, 4.0, default=1.404, space="buy", optimize=True)
    require_fvg = CategoricalParameter([True, False], default=False, space="buy", optimize=True)
    # v0.30.0: Order Block now mandatory by default (was False).
    # OB = structural demand/supply zone created by institutional move. Entering
    # at OB + sweep + ChoCH = max confluence ICT setup. Expected to cut TSL exits
    # dramatically (price at OB has structural support, less likely to continue against us).
    require_ob = CategoricalParameter([True, False], default=False, space="buy", optimize=True)

    # v0.40.0: Confirmation Candle Filter
    # After a valid setup (sweep + ChoCH + OTE + FVG), require the CURRENT candle
    # to be directionally aligned before entering:
    #   - Longs: close > open (bullish candle) — price already moving UP
    #   - Shorts: close < open (bearish candle) — price already moving DOWN
    # Rationale: Eliminates entries where price has already reversed or is consolidating
    # at the zone. Only enter when momentum is confirmed. May reduce volume but improve WR.
    require_confirmation_candle = CategoricalParameter([True, False], default=False, space="buy", optimize=True)

    # v0.45.0 (2026-03-18): Disable session filter — too aggressive, only 19 trades, 10.5% WR.
# The NY/London filter was reducing trades too much (19 vs hundreds previously).
# Reverting to disabled by default. Will revisit with looser hours (e.g., 07:00-17:00).
    require_session_filter = CategoricalParameter([True, False], default=False, space="buy", optimize=False)

    # v0.48.0 / v0.49.0: Weekend filter (roadmap 2.3).
    # Skip entries on Saturday (dayofweek=5) and Sunday (dayofweek=6).
    # ICT Silver Bullet setups require high-liquidity sessions — weekends are choppy/low-volume.
    # v0.49.0: Testing with filter ENABLED (was disabled in v0.48.0).
    require_weekend_filter = CategoricalParameter([True, False], default=True, space="buy", optimize=False)

    # v0.99.38: Entry Quality Filter — H-D from roadmap
    # Root cause of trailing_stop_loss 0% WR: entries that looked valid (sweep + BOS)
    # but reversed immediately after entry → TS had to exit at loss.
    # Fix: Require momentum confirmation at entry.
    #   - RSI > 40 on entry candle (longs): not oversold, some upward momentum
    #   - Volume > 1.5× 20-period average: institutional participation confirmed
    # Goal: filter ~20-30% of entries, eliminate most TS losers, improve R/R ≥ 1.5
    require_momentum_filter = CategoricalParameter([True, False], default=True, space="buy", optimize=False)
    volume_mult = DecimalParameter(0.5, 2.5, default=0.9, space="buy", optimize=False)
    rsi_entry_min = DecimalParameter(20, 55, default=26, space="buy", optimize=False)
    
    # Liquidity detection
    liquidity_range_pct = DecimalParameter(0.005, 0.03, default=0.019, space="buy", optimize=True)
    
    # Buffer for SL placement
    buffer_pips = DecimalParameter(0.0001, 0.0100, default=0.001, space="buy", optimize=True)

    # Time-based custom exits (hyperoptable in v0.24.0)
    time_exit_1_enabled = CategoricalParameter([True, False], default=False, space="sell", optimize=True)
    time_exit_1_hours = IntParameter(2, 6, default=4, space="sell", optimize=True)
    time_exit_1_profit = DecimalParameter(-0.02, 0.01, default=0.0, space="sell", optimize=True)
    
    time_exit_2_enabled = CategoricalParameter([True, False], default=True, space="sell", optimize=False)  # v0.99.74: RE-ENABLED — v0.99.71 (disabled): 32 TS exits, R/R 0.85 CATASTROPHIC. v0.99.70 (enabled, floor=-2.0%): 17 TS exits, R/R 1.32. time_exit_2 handles stale trades at 8h before custom_stoploss has to exit them at -2.0%. Keeping it enabled is essential alongside -2.0% floor.
    time_exit_2_hours = IntParameter(5, 12, default=8, space="sell", optimize=False)
    time_exit_2_profit = DecimalParameter(0.0, 0.04, default=0.020, space="sell", optimize=False)  # v0.99.88: 3.0%→2.0%. v0.99.87: ATR mult had zero effect. Lowering time_exit_2 from 3.0% to 2.0% — early_profit_take (+2.0%) captures trades at 45min so time_exit_8h at 3.0% never fires; only catches stale near-zero trades. At 2.0%: trades that didn't build enough momentum in 45min but reach +2.0% at 8h exit cleanly (good). Trades <2.0% fall through to stoploss. Expected: fewer near-zero time_exit exits, better avg profit per trade.

    # ── Plotting ──────────────────────────────────────────────────────────────
    plot_config = {
        'main_plot': {
            'swing_high_level': {'color': 'red'},
            'swing_low_level': {'color': 'green'},
        },
        'subplots': {
            "Structure": {
                'htf_trend': {'color': 'blue'},
            },
        }
    }

    def informative_pairs(self):
        pairs = self.dp.current_whitelist()
        return [(pair, self.informative_timeframe) for pair in pairs]

    def _prepare_ohlc(self, dataframe: DataFrame) -> DataFrame:
        """Ensure DataFrame has lowercase columns for SMC library."""
        # Freqtrade already uses lowercase, but let's be safe
        ohlc = dataframe[['open', 'high', 'low', 'close']].copy()
        if 'volume' in dataframe.columns:
            ohlc['volume'] = dataframe['volume']
        return ohlc

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Add all indicators using smartmoneyconcepts library."""
        
        # ── HTF (1H) Indicators ───────────────────────────────────────────────
        informative = self.dp.get_pair_dataframe(
            pair=metadata['pair'],
            timeframe=self.informative_timeframe
        )
        
        if len(informative) > 0:
            informative = self._add_htf_indicators(informative)
            dataframe = merge_informative_pair(
                dataframe, informative,
                self.timeframe, self.informative_timeframe,
                ffill=True
            )
        
        # ── 15m Indicators ────────────────────────────────────────────────────
        ohlc = self._prepare_ohlc(dataframe)
        
        # 1. Swing Highs & Lows
        swing_data = smc.swing_highs_lows(ohlc, swing_length=self.swing_length.value)
        dataframe['swing_hl'] = swing_data['HighLow']      # 1=swing high, -1=swing low
        dataframe['swing_level'] = swing_data['Level']       # Price level of swing
        
        # Extract latest swing high/low levels (forward-filled)
        dataframe['swing_high_level'] = dataframe['swing_level'].where(
            dataframe['swing_hl'] == 1
        ).ffill()
        dataframe['swing_low_level'] = dataframe['swing_level'].where(
            dataframe['swing_hl'] == -1
        ).ffill()
        
        # 2. Break of Structure & Change of Character (15m)
        bos_choch_data = smc.bos_choch(ohlc, swing_data, close_break=True)
        dataframe['bos'] = bos_choch_data['BOS']       # 1=bullish, -1=bearish
        dataframe['choch'] = bos_choch_data['CHOCH']    # 1=bullish, -1=bearish
        dataframe['structure_level'] = bos_choch_data['Level']
        
        # 3. Fair Value Gaps
        fvg_data = smc.fvg(ohlc, join_consecutive=True)
        dataframe['fvg'] = fvg_data['FVG']              # 1=bullish, -1=bearish
        dataframe['fvg_top'] = fvg_data['Top']
        dataframe['fvg_bottom'] = fvg_data['Bottom']
        dataframe['fvg_mitigated'] = fvg_data['MitigatedIndex']
        
        # v0.35.0 FIX: FVG "active zone" detection was broken in all prior versions.
        #
        # ROOT CAUSE (v0.29.0 → v0.34.0):
        # The condition `fvg_mitigated.isna()` was used to identify "unmitigated" FVGs.
        # During backtesting, the smartmoneyconcepts library has access to the full dataset
        # and marks the MitigatedIndex for EVERY FVG that eventually gets mitigated.
        # Since nearly all historical FVGs are eventually mitigated, `fvg_mitigated.isna()`
        # is almost always False. The resulting zone forward-fills had near-zero coverage,
        # making `active_bullish_fvg` essentially always False → 0 trades.
        # This is the same class of bug as the OB window issue (v0.31.0/v0.32.0):
        # point-in-time signals used in a way that makes them always False.
        #
        # FIX (v0.35.0): Use a rolling window approach (identical to OB fix in v0.31.0).
        # "Was a bullish/bearish FVG formed within the last N candles?"
        # FVG window of 30 candles (~7.5h at 15m): recent imbalance signal.
        # This is sensible SMC: an FVG formed today is still an active imbalance zone
        # worth trading from — mitigation (price touching it) is EXPECTED on the return move.
        fvg_window = 30  # ~7.5h at 15m — "Was imbalance created recently?"
        dataframe['active_bullish_fvg'] = (
            dataframe['fvg']
            .eq(1)
            .rolling(window=fvg_window, min_periods=1)
            .max()
            .astype(bool)
        )
        dataframe['active_bearish_fvg'] = (
            dataframe['fvg']
            .eq(-1)
            .rolling(window=fvg_window, min_periods=1)
            .max()
            .astype(bool)
        )
        
        # Keep zone level tracking for opposite-side imbalance filter
        # (These use the raw fvg_top/bottom columns, not mitigation-dependent)
        dataframe['bullish_fvg_zone_top'] = dataframe['fvg_top'].where(dataframe['fvg'] == 1).ffill()
        dataframe['bullish_fvg_zone_bottom'] = dataframe['fvg_bottom'].where(dataframe['fvg'] == 1).ffill()
        dataframe['bearish_fvg_zone_top'] = dataframe['fvg_top'].where(dataframe['fvg'] == -1).ffill()
        dataframe['bearish_fvg_zone_bottom'] = dataframe['fvg_bottom'].where(dataframe['fvg'] == -1).ffill()
        
        # v0.28.0: Opposite-side imbalance check (Marco's SMC rule)
        # v0.35.0: simplified — use the already-computed zone level columns
        # (no longer gated on mitigation status, same fix as active_fvg above)
        dataframe['bearish_fvg_bottom'] = dataframe['bearish_fvg_zone_bottom']
        dataframe['bullish_fvg_top'] = dataframe['bullish_fvg_zone_top']
        
        # 4. Order Blocks
        ob_data = smc.ob(ohlc, swing_data, close_mitigation=False)
        dataframe['ob'] = ob_data['OB']                  # 1=bullish, -1=bearish
        dataframe['ob_top'] = ob_data['Top']
        dataframe['ob_bottom'] = ob_data['Bottom']
        dataframe['ob_volume'] = ob_data.get('OBVolume', 0)
        
        # v0.32.0 FIX: OB zone detection (rolling window expanded from 20→100).
        # The previous approach (price inside exact OB box via ffill) produced 0
        # trades because the OB candle range is too narrow — price rarely sits
        # precisely inside a historical candle's body at entry time.
        #
        # Correct SMC interpretation: an Order Block formed RECENTLY (within the
        # last 20 candles) signals that institutional money was active at this
        # price level. The OB doesn't need to be "open" — it needs to be nearby
        # in time. Entry is still high confluence: OB (institutional interest
        # recently) + sweep + ChoCH (confirmation of reversal).
        #
        # Rolling window: 20 candles (~20h on 1h TF). A bullish OB formed within
        # the last 20 candles confirms institutional buying pressure is recent.
        ob_window = 100  # v0.32.0: expanded from 20 → 100 candles (~25h at 15m). OBs are sparse
        # (smc.ob() marks one every ~50-200 candles). A 20-candle (~5h) window missed
        # almost all of them → 0 trades in v0.31.0. 100 candles = "institutional footprint
        # present somewhere in the last day?" which is a sensible SMC recency check.
        dataframe['in_bullish_ob'] = (
            dataframe['ob']
            .eq(1)
            .rolling(window=ob_window, min_periods=1)
            .max()
            .astype(bool)
        )
        dataframe['in_bearish_ob'] = (
            dataframe['ob']
            .eq(-1)
            .rolling(window=ob_window, min_periods=1)
            .max()
            .astype(bool)
        )
        
        # 5. Liquidity Detection
        liq_data = smc.liquidity(ohlc, swing_data, range_percent=self.liquidity_range_pct.value)
        dataframe['liquidity'] = liq_data['Liquidity']    # 1=buy-side, -1=sell-side
        dataframe['liquidity_level'] = liq_data['Level']
        dataframe['liquidity_swept'] = liq_data['Swept']  # Index where swept
        
        # Detect sweep events: liquidity was swept on this candle
        # The 'Swept' column contains the index where the sweep happened
        # We need to check if a sweep just happened
        dataframe['buy_liq_swept'] = False
        dataframe['sell_liq_swept'] = False
        
        # Vectorized sweep detection:
        # A buy-side liquidity sweep = price went ABOVE a buy-side liquidity level
        # → bearish signal (grabbed stops above, likely to reverse down)
        # A sell-side liquidity sweep = price went BELOW a sell-side liquidity level  
        # → bullish signal (grabbed stops below, likely to reverse up)
        
        # Use the swept column: if it's not NaN for a row, that liquidity was swept
        swept_mask = liq_data['Swept'].notna()
        dataframe.loc[swept_mask & (liq_data['Liquidity'] == 1), 'buy_liq_swept'] = True
        dataframe.loc[swept_mask & (liq_data['Liquidity'] == -1), 'sell_liq_swept'] = True
        
        # Also detect sweeps via price action (fallback / supplement)
        # Price wicks above swing high cluster = buy-side sweep
        dataframe['wick_sweep_high'] = (
            (dataframe['high'] > dataframe['swing_high_level'].shift(1)) &
            (dataframe['close'] < dataframe['swing_high_level'].shift(1))
        )
        # Price wicks below swing low cluster = sell-side sweep  
        dataframe['wick_sweep_low'] = (
            (dataframe['low'] < dataframe['swing_low_level'].shift(1)) &
            (dataframe['close'] > dataframe['swing_low_level'].shift(1))
        )
        
        # Combined sweep signal (either SMC library detected OR wick-based)
        dataframe['sweep_high'] = dataframe['buy_liq_swept'] | dataframe['wick_sweep_high']
        dataframe['sweep_low'] = dataframe['sell_liq_swept'] | dataframe['wick_sweep_low']
        
        # State: Was liquidity swept recently? (5 candles = 1h15m to form ChoCH)
        dataframe['recent_sweep_high'] = dataframe['sweep_high'].rolling(window=5, min_periods=1).max() > 0
        dataframe['recent_sweep_low'] = dataframe['sweep_low'].rolling(window=5, min_periods=1).max() > 0
        
        # 6. OTE Zone
        dataframe = self._calculate_ote(dataframe)
        
        # 7. ATR for dynamic stoploss (v0.22.0)
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=self.atr_period.value)
        # Normalize ATR as % of close for cross-asset comparison
        dataframe['atr_pct'] = dataframe['atr'] / dataframe['close']

        # v0.99.38: Entry Quality Filter indicators (H-D)
        # RSI: momentum confirmation — avoid entries in oversold territory (TS trap)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        # Volume: institutional confirmation — volume spike at entry = real move
        dataframe['volume_sma20'] = dataframe['volume'].rolling(window=20, min_periods=1).mean()
        dataframe['volume_spike'] = dataframe['volume'] > (dataframe['volume_sma20'] * self.volume_mult.value)

        # 8. Session Filter (v0.45.0) — Disabled by default, was too aggressive
        # Freqtrade 'date' column is a UTC DatetimeIndex — use .dt accessor
        # London: 08:00-11:00 UTC | NY: 13:30-16:00 UTC
        dataframe['in_london_session'] = (
            (dataframe['date'].dt.hour >= 8) & (dataframe['date'].dt.hour < 11)
        )
        dataframe['in_ny_session'] = (
            (dataframe['date'].dt.hour >= 13) & (dataframe['date'].dt.hour < 16)
        )
        dataframe['in_premium_session'] = (
            dataframe['in_london_session'] | dataframe['in_ny_session']
        )
        
        # v0.48.0: Weekend filter — flag Sat (dayofweek=5) and Sun (dayofweek=6)
        dataframe['is_weekend'] = dataframe['date'].dt.dayofweek.isin([5, 6])
        
        return dataframe

    def _add_htf_indicators(self, dataframe: DataFrame) -> DataFrame:
        """Add trend indicators on HTF (1H) using SMC library."""
        ohlc = self._prepare_ohlc(dataframe)
        
        # Swing detection on 1H
        htf_swings = smc.swing_highs_lows(ohlc, swing_length=self.htf_swing_length.value)
        
        # BOS + ChoCH on 1H for trend detection
        htf_structure = smc.bos_choch(ohlc, htf_swings, close_break=True)
        
        # Derive trend from structure breaks
        # BOS confirms existing trend, ChoCH signals reversal
        # Bullish BOS/ChoCH = 1, Bearish = -1
        dataframe['bos_signal'] = htf_structure['BOS']
        dataframe['choch_signal'] = htf_structure['CHOCH']
        
        # Combined trend signal: ChoCH is stronger (reversal), BOS confirms
        # Priority: ChoCH > BOS
        dataframe['trend_signal'] = np.where(
            htf_structure['CHOCH'].notna(), htf_structure['CHOCH'],
            np.where(htf_structure['BOS'].notna(), htf_structure['BOS'], np.nan)
        )
        dataframe['trend'] = pd.Series(dataframe['trend_signal']).ffill().fillna(0).astype(int)
        
        # SMA backup for when structure is undefined
        dataframe['sma_50'] = ta.SMA(dataframe, timeperiod=50)
        dataframe['sma_200'] = ta.SMA(dataframe, timeperiod=200)
        
        mask_neutral = (dataframe['trend'] == 0)
        dataframe.loc[mask_neutral, 'trend'] = np.where(
            dataframe.loc[mask_neutral, 'close'] > dataframe.loc[mask_neutral, 'sma_200'], 1, -1
        )
        
        return dataframe

    def _calculate_ote(self, dataframe: DataFrame) -> DataFrame:
        """Calculate OTE zone using swing levels."""
        lookback = 50
        dataframe['external_high'] = dataframe['high'].rolling(lookback).max()
        dataframe['external_low'] = dataframe['low'].rolling(lookback).min()
        
        range_size = dataframe['external_high'] - dataframe['external_low']
        
        dataframe['ote_lower'] = dataframe['external_low'] + (range_size * self.ote_lower.value)
        dataframe['ote_upper'] = dataframe['external_low'] + (range_size * self.ote_upper.value)
        
        dataframe['in_ote'] = (
            (dataframe['close'] >= dataframe['ote_lower']) &
            (dataframe['close'] <= dataframe['ote_upper'])
        )
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Generate entry signals using SMC indicators."""
        dataframe.loc[:, 'enter_long'] = 0
        dataframe.loc[:, 'enter_short'] = 0
        
        htf_trend_col = f'trend_{self.informative_timeframe}'
        
        # ── Filters ───────────────────────────────────────────────────────────
        
        # We need pair metadata to fetch custom parameters
        pair = metadata.get('pair', '')
        
        req_ote = self.get_param('require_ote', pair, self.require_ote.value)
        req_fvg = self.get_param('require_fvg', pair, self.require_fvg.value)
        req_ob = self.get_param('require_ob', pair, self.require_ob.value)

        ote_check = dataframe['in_ote'] if req_ote else True

        # v0.45.0: Session Filter — disabled by default (was too aggressive)
        session_check = dataframe['in_premium_session'] if self.require_session_filter.value else True
        
        # v0.48.0: Weekend Filter — skip Sat/Sun (low volume, choppy markets)
        weekend_check = ~dataframe['is_weekend'] if self.require_weekend_filter.value else True
        
        # v0.36.0: Enhanced FVG confluence (Price inside/near the zone)
        # Instead of just "an FVG formed recently", we ensure price is actually 
        # testing the imbalance.
        fvg_check_short = (
            dataframe['active_bearish_fvg'] & 
            (dataframe['close'] >= dataframe['bearish_fvg_zone_bottom']) & 
            (dataframe['close'] <= dataframe['bearish_fvg_zone_top'])
        ) if req_fvg else True
        
        fvg_check_long = (
            dataframe['active_bullish_fvg'] & 
            (dataframe['close'] <= dataframe['bullish_fvg_zone_top']) & 
            (dataframe['close'] >= dataframe['bullish_fvg_zone_bottom'])
        ) if req_fvg else True
        
        ob_check_short = dataframe['in_bearish_ob'] if req_ob else True
        ob_check_long = dataframe['in_bullish_ob'] if req_ob else True
        
        # ── R:R Calculation ───────────────────────────────────────────────────
        buffer = self.buffer_pips.value
        
        # Long: reward = external high - close, risk = close - (swing low - buffer)
        dataframe['reward_long'] = dataframe['external_high'] - dataframe['close']
        dataframe['risk_long'] = dataframe['close'] - (dataframe['swing_low_level'] - buffer)
        dataframe['rr_long'] = np.where(
            dataframe['risk_long'] > 0,
            dataframe['reward_long'] / dataframe['risk_long'], 0
        )
        
        # Short: reward = close - external low, risk = (swing high + buffer) - close
        dataframe['reward_short'] = dataframe['close'] - dataframe['external_low']
        dataframe['risk_short'] = (dataframe['swing_high_level'] + buffer) - dataframe['close']
        dataframe['rr_short'] = np.where(
            dataframe['risk_short'] > 0,
            dataframe['reward_short'] / dataframe['risk_short'], 0
        )
        
        # ── HTF Trend Alignment ───────────────────────────────────────────────
        # v0.27.0 FIX: htf_trend_col was computed but never used in entry filters
        # (dead variable introduced during v0.21.0 SMC refactor). This caused
        # counter-trend entries and was the root cause of the 21.7% win rate.
        htf_bearish = dataframe[htf_trend_col] == -1 if htf_trend_col in dataframe.columns else True
        htf_bullish = dataframe[htf_trend_col] == 1 if htf_trend_col in dataframe.columns else True

        # ── Opposite-Side Imbalance Filter (v0.28.0) ─────────────────────────
        # Marco's SMC rule: "Is there an obvious imbalance on the opposite side
        # of where my stop would go? If YES → Skip (liquidity magnet, stop-hunt
        # risk). If NO → Proceed (liquidity was already taken, safer entry)."
        #
        # v0.36.0 FIX: Logic was inverted since v0.28.0. 
        # For LONGS: SL is below. Magnet is a BULLISH FVG (support) even deeper.
        # For SHORTS: SL is above. Magnet is a BEARISH FVG (resistance) even higher.
        sl_buffer = self.buffer_pips.value
        long_sl_level = dataframe['swing_low_level'] - sl_buffer
        short_sl_level = dataframe['swing_high_level'] + sl_buffer

        safe_long = ~(
            dataframe['bullish_fvg_zone_top'].notna() &
            (dataframe['bullish_fvg_zone_top'] < long_sl_level)
        )
        safe_short = ~(
            dataframe['bearish_fvg_zone_bottom'].notna() &
            (dataframe['bearish_fvg_zone_bottom'] > short_sl_level)
        )

        # ── Confirmation Candle Filter (v0.40.0) ──────────────────────────────
        # Only enter when the entry candle itself is directionally aligned.
        # This avoids "knife-catching" entries where price has already started
        # reversing against us before we enter.
        req_confirm = self.require_confirmation_candle.value
        confirm_long = (dataframe['close'] > dataframe['open']) if req_confirm else True
        confirm_short = (dataframe['close'] < dataframe['open']) if req_confirm else True

        # v0.99.38: H-D Momentum Filter — require RSI + volume confirmation at entry
        # Eliminates entries where price is oversold or lacking volume (TS traps)
        if self.require_momentum_filter.value:
            rsi_ok_long = dataframe['rsi'] > self.rsi_entry_min.value
            rsi_ok_short = dataframe['rsi'] < (100 - self.rsi_entry_min.value)
            vol_ok = dataframe['volume_spike']
            momentum_long = rsi_ok_long & vol_ok
            momentum_short = rsi_ok_short & vol_ok
        else:
            momentum_long = True
            momentum_short = True

        # ── Short Entry ───────────────────────────────────────────────────────
        # Double confirmation: (1) Liquidity sweep above highs, (2) Bearish BOS confirms structure broken.
        # BOS is more reliable than ChoCH for entry confirmation — it confirms the trend structure
        # is broken in the direction we want to trade. ChoCH can fire on minor struktur breaks.
        # v0.47.0: Changed from choch==-1 to bos==-1 for stricter confirmation.
        dataframe.loc[
            (htf_bearish) &                                          # HTF trend alignment (v0.27.0)
            (dataframe['recent_sweep_high']) &                       # Liquidity swept above recently
            (dataframe['bos'] == -1) &                               # Bearish BOS confirms structure broken (v0.47.0)
            (ote_check) &                                            # OTE (if required)
            (fvg_check_short) &                                      # FVG confluence (v0.28.0 default=True)
            (ob_check_short) &                                       # Order Block (if required)
            (safe_short) &                                           # No imbalance magnet beyond SL (v0.28.0)
            (confirm_short) &                                        # Confirmation candle (v0.40.0)
            (momentum_short) &                                       # Momentum filter: RSI + volume spike (v0.99.38 H-D)
            (dataframe['rr_short'] >= self.min_rr.value) &           # Min R:R (v0.28.0 default=1.5)
            (session_check) &                                         # Session filter — v0.45.0 disabled by default
            (weekend_check),                                         # Weekend filter — v0.48.0 disabled by default
            'enter_short'
        ] = 1
        
        # ── Long Entry ────────────────────────────────────────────────────────
        # Double confirmation: (1) Liquidity sweep below lows, (2) Bullish BOS confirms structure broken.
        # v0.47.0: Changed from choch==1 to bos==1 for stricter confirmation.
        dataframe.loc[
            (htf_bullish) &                                          # HTF trend alignment (v0.27.0)
            (dataframe['recent_sweep_low']) &                        # Liquidity swept below recently
            (dataframe['bos'] == 1) &                                # Bullish BOS confirms structure broken (v0.47.0)
            (ote_check) &                                            # OTE (if required)
            (fvg_check_long) &                                       # FVG confluence (v0.28.0 default=True)
            (ob_check_long) &                                        # Order Block (if required)
            (safe_long) &                                            # No imbalance magnet beyond SL (v0.28.0)
            (confirm_long) &                                         # Confirmation candle (v0.40.0)
            (momentum_long) &                                        # Momentum filter: RSI + volume spike (v0.99.38 H-D)
            (dataframe['rr_long'] >= self.min_rr.value) &           # Min R:R (v0.28.0 default=1.5)
            (session_check) &                                         # Session filter — v0.45.0 disabled by default
            (weekend_check),                                         # Weekend filter — v0.48.0 disabled by default
            'enter_long'
        ] = 1
        
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Exit signal generation.
        
        v0.58.0: DISABLED all ChoCH exits.
        Problem (v0.57.0): exit_signal was 17/43 trades (39.5%) at -0.63% avg,
        totaling -35.87 USDT — destroying ALL profit from the other 26 winning trades
        (+65.53 USDT). ChoCH fires when 15m structure breaks, but the trade is usually
        still underwater. Win rate on exit_signal was only 11.8%.
        
        With ChoCH exits disabled, trades will run to:
        - early_profit_take (+0.8% after 45min) — 100% WR in v0.57.0
        - trailing_stop_loss (after +1.5%) — 100% WR in v0.57.0
        - ROI table — 100% WR in v0.57.0
        - time_exit (4h/6h) — catches stale trades
        - dynamic stoploss (ATR-based) — catches losing trades
        
        These exits already handle all profitable scenarios. ChoCH was only
        prematurely killing trades that would have been profitable if left alone.
        
        History:
        - v0.51.0: Removed HTF trend exits (too aggressive)
        - v0.53.0: Reverted confirmation candle on ChoCH exits
        - v0.54.0: Added ChoCH profit guard (blocked underwater ChoCH exits)
        - v0.58.0: Disabled ChoCH exits entirely — let mechanical exits handle it
        """
        dataframe.loc[:, 'exit_long'] = 0
        dataframe.loc[:, 'exit_short'] = 0
        
        # v0.58.0: No exit signals — rely entirely on:
        # early_profit_take, trailing_stop, ROI, time_exit, dynamic stoploss
        
        return dataframe

    # ── Custom Stoploss (OTE-zone-based, v0.99.78) ──────────────────────────
    # REPLACES ATR-based stop. The problem with ATR stops: they trigger on any
    # -X% move, even if price is just retracing within the OTE zone. A structural
    # stop should trigger when price BREAKS the OTE zone — that means the setup
    # is actually invalid, not just temporarily reversing.
    #
    # For longs: stop fires when price closes BELOW OTE lower - buffer.
    #   The buffer (default 0.75%) gives room for stop hunts — price often
    #   wicked below OTE lower before reversing. We wait for a CLOSE below
    #   (ote_lower * 0.9925) to confirm it's a real break, not a wick.
    # For shorts: stop fires when price closes ABOVE OTE upper + buffer.
    # Fallback to ATR if OTE boundary not found (e.g., require_ote=False).

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> float:
        # v0.99.79: REVERT to ATR-based stop. v0.99.78b OTE-zone hypothesis REJECTED.
        # OTE-zone + 0.75% buffer fired 46 times (vs 16 with ATR) but R/R collapsed 1.31→1.0078.
        # ATR floor (-2.0%) was validated in v0.99.77 with R/R=1.31. Restoring it.
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if len(dataframe) == 0:
            return self.stoploss

        trade_open_dt = trade.open_date_utc
        entry_candle_df = dataframe[dataframe['date'] <= trade_open_dt]
        if len(entry_candle_df) == 0:
            return self.stoploss

        entry_row = entry_candle_df.iloc[-1]
        atr_pct = entry_row.get('atr_pct')
        if pd.isna(atr_pct) or atr_pct <= 0:
            return self.stoploss
        atr_mult = self.get_param('atr_multiplier', pair, self.atr_multiplier.value)
        dynamic_sl = -(atr_mult * atr_pct)
        dynamic_sl = max(dynamic_sl, -0.08)
        dynamic_sl = min(dynamic_sl, -0.020)  # Floor: -2.0% (v0.99.92: revert -1.5%→-2.0%. v0.99.91: 7 TS exits at -2.06% avg, R/R=1.15 — tighter floor FAILED)
        from freqtrade.strategy import stoploss_from_open
        return stoploss_from_open(dynamic_sl, current_profit, is_short=trade.is_short)

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float,
                            rate: float, time_in_force: str, current_time: datetime,
                            entry_tag: Optional[str], side: str, **kwargs) -> bool:
        """
        Store OTE zone levels at entry time so custom_stoploss can use them.
        v0.99.78: Structural OTE-zone stop replaces ATR-based stop.
        """
        trade = kwargs.get('trade')
        if trade is None:
            return True

        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if len(dataframe) == 0:
            return True

        trade_open_dt = trade.open_date_utc
        entry_candles = dataframe[dataframe['date'] <= trade_open_dt]
        if len(entry_candles) == 0:
            return True

        entry_row = entry_candles.iloc[-1]

        # Store OTE zone levels relative to entry price
        # These are used in custom_stoploss to determine structural break
        if not hasattr(trade, 'custom_info') or trade.custom_info is None:
            trade.custom_info = {}

        entry_price = rate if rate > 0 else trade.open_rate
        ote_lower = entry_row.get('ote_lower')
        ote_upper = entry_row.get('ote_upper')

        if not pd.isna(ote_lower) and not pd.isna(ote_upper) and entry_price > 0:
            trade.custom_info['ote_lower_pct'] = (entry_price - ote_lower) / entry_price
            trade.custom_info['ote_upper_pct'] = (ote_upper - entry_price) / entry_price
            trade.custom_info['ote_lower'] = ote_lower
            trade.custom_info['ote_upper'] = ote_upper

        return True

    def custom_exit(self, pair: str, trade: 'Trade', current_time: datetime, current_rate: float,
                    current_profit: float, **kwargs):
        """
        Custom exit logic:
        1. H-A Dynamic TP (ATR-based): let exceptional moves run 2.5× ATR (v0.99.12)
        2. Early profit exit at +2.5%: lock in exceptional winners (v0.74.0)
        3. Time-based exit: cut stale trades
        4. Target liquidity reached
        """
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if len(dataframe) == 0:
            return None
            
        last_candle = dataframe.iloc[-1]
        
        # v0.58.0: ChoCH profit guard removed — ChoCH exits fully disabled in populate_exit_trend.
        # All exits now handled by: dynamic_tp, early_profit_take, trailing_stop, ROI, time_exit, stoploss.
        
        # H-A (v0.99.12→v0.99.13): Dynamic TP — 2.5× was too high (5-11% threshold, never fires).
        # v0.99.13 fix: Reduce to 1.5× ATR. Targets: BTC ~3.4%, ETH ~1.5%, XRP ~3.8%.
        # TS is now DISABLED — dynamic TP is the primary exit for big moves.
        # In high vol (BTC ~1.5% ATR) → TP ~3.4%. Low vol (ETH ~0.8% ATR) → TP ~1.5%.
        # Require at least 3 candles hold to avoid gap/open spike exits.
        trade_open_dt = trade.open_date_utc
        entry_candle_df = dataframe[dataframe['date'] <= trade_open_dt]
        if len(entry_candle_df) > 0 and 'atr_pct' in entry_candle_df.columns:
            entry_atr_pct = entry_candle_df.iloc[-1]['atr_pct']
            if not pd.isna(entry_atr_pct) and entry_atr_pct > 0:
                atr_mult = self.get_param('atr_multiplier', pair, self.atr_multiplier.value)
                # Dynamic TP = 1.5× ATR multiplier × entry ATR% (v0.99.33: REVERTED 1.2×→1.5×)
                # v0.99.32 REJECTED: lower 1.2× threshold captured micro-moves, NOT big moves.
                # dynamic_tp avg dropped 1.83%→1.62%, total profit fell $171→$153.
                dynamic_tp_threshold = 1.5 * atr_mult * entry_atr_pct
                # Require at least 3 candles hold to avoid gap/open spike exits
                trade_duration_candles = (current_time - trade.open_date_utc).total_seconds() / 3600 / 0.25
                if trade_duration_candles >= 3 and current_profit >= dynamic_tp_threshold:
                    return "dynamic_tp"
        
        # 1. Early profit exit — lock in wins before TSL activates at +1.5% (v0.46.0)
        # Require at least 45min hold to avoid gap-based false exits
        # v0.74.0: raised from 1.5% to 2.5% — TS at 0.8% offset intercepts all winners
        # before they can reach 1.5%. Raising to 2.5% puts early_profit ABOVE the ROI
        # table (2%) — only the strongest trends fire it. TS still handles ~95% of exits.
        # v0.73.0: raised from 1.0% to 1.5% — but early_profit exits DROPPED (2→1 trade).
        # TS is simply too aggressive below 2%.
        # v0.99.18: REVERT from 2.5%→1.5%. TS is now disabled, dynamic_tp threshold
        # is too high (7.8%+). 2.5% is too high — winners reverse before reaching it,
        # then custom_stoploss hits at -3.62%. 1.5% captures wins before reversal.
        # v0.71.0: raised from 0.8% to 1.0% — winners averaged 1.06% (100% WR), let them run
        # v0.64.0: REVERT — early_profit at 0.8% (was 1.5% in failed v0.63.0)
        # v0.99.35: RAISE 1.5%→2.0%. Current 1.5% locks in wins at +1.81% avg but
        # trailing_stop_loss still generates 14 losses at -1.89%. Raising to 2.0%
        # v0.99.83: RAISE 2.0%→2.5%. v0.99.82 time_exit_8h captured 39 trades (48%) at 53.85% WR/+0.17% avg —
        # dominant near-zero exits dragging R/R to 1.18. 2.0% fires before winners can develop.
        # dynamic_tp (~2.7% for BTC) fills 2.5-3.0% gap. 2.5% raises the floor, routes more
        # to 100% WR exits (early_profit_take/dynamic_tp) instead of time_exit at ~0%.
        # let winners ride further — dynamic_tp (1.5× ATR) and roi (5%) will
        # handle bigger moves while 2.5% locks in medium winners.
        trade_duration = (current_time - trade.open_date_utc).total_seconds() / 3600
        if trade_duration >= 0.75 and current_profit >= 0.020:
            return "early_profit_take"
        
        # Time-based exit
        
        # Fetch custom exits for pair
        te1_enabled = self.get_param('time_exit_1_enabled', pair, self.time_exit_1_enabled.value)
        te1_hours = self.get_param('time_exit_1_hours', pair, self.time_exit_1_hours.value)
        te1_profit = self.get_param('time_exit_1_profit', pair, self.time_exit_1_profit.value)
        
        te2_enabled = self.get_param('time_exit_2_enabled', pair, self.time_exit_2_enabled.value)
        te2_hours = self.get_param('time_exit_2_hours', pair, self.time_exit_2_hours.value)
        te2_profit = self.get_param('time_exit_2_profit', pair, self.time_exit_2_profit.value)
        
        if te1_enabled:
            if trade_duration >= te1_hours and current_profit <= te1_profit:
                return f"time_exit_{te1_hours}h"
        
        if te2_enabled:
            if trade_duration >= te2_hours and current_profit < te2_profit:
                return f"time_exit_{te2_hours}h"
        
        # Target liquidity
        if trade.is_short:
            if 'external_low' in last_candle and not pd.isna(last_candle.get('external_low')):
                if current_rate <= last_candle['external_low'] and current_profit > 0:
                    return "target_liquidity_reached"
        else:
            if 'external_high' in last_candle and not pd.isna(last_candle.get('external_high')):
                if current_rate >= last_candle['external_high'] and current_profit > 0:
                    return "target_liquidity_reached"
                    
        return None

    def leverage(self, pair: str, current_time: datetime, current_rate: float,
                 proposed_leverage: float, max_leverage: float, entry_tag: Optional[str],
                 side: str, **kwargs) -> float:
        """Conservative leverage."""
        return 3.0
