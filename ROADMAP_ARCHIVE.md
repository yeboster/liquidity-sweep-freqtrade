# Liquidity Sweep Strategy — Roadmap

> Updated: 2026-03-20
> Current: v0.65.0 — **35 trades / 2 years = TOO FEW**

---

## 🚨 The Problem: Trade Frequency Is Too Low

Mean reversion on 15m TF should fire much more often.

| | Target | v0.65.0 |
|--|--------|---------|
| Trades/Year | 100-200 | **~17** ❌ |
| Win Rate | 45%+ | 57.1% ✅ |
| Profit/Year | 5%+ | 4.68% ⚠️ |

**35 trades in 2 years = 1 trade every 3 weeks.** We need to risk more.

---

## Phase FF: High-Frequency Experiment

**Goal:** 100-200 trades/year without destroying edge.

### Strategy Comparison

| Version | Trades/yr | WR | PF | Profit | ATR Offset | OTE Zone | Conf | FVG |
|---------|-----------|----|----|--------|-----------|----------|------|-----|
| v0.65.0 (current) | ~17 | 57% | 2.43 | 4.68% | 2.0x | 30-70% | YES | YES |
| FF-2 (loosened) | ~40-60 | ? | ? | ? | 1.5x | 20-80% | NO | NO |
| FF-3 (extreme) | ~60-100 | ? | ? | ? | 1.5x | 10-90% | NO | NO |

### What Changes for High-Frequency

**Entry — loosen:**
- OTE zone: 30-70% → 20-80% (catch more setups)
- Confirmation candle: REMOVE
- FVG filter: REMOVE
- Imbalance filter: REMOVE

**Risk — increase:**
- atr_offset_v2: 2.0x → 1.5x (tighter stop)
- stoploss: -0.99 → -1.5% (wider floor)
- stake: 2% → 5% (higher exposure)

**Exit — keep:**
- early_profit_take: 0.8% (quick winners)
- trailing_stop_offset: 1.5%
- ROI 305 at 1%

### Test Run Order
1. **FF-2** — loosen OTE + remove all blocking filters → check trade count jump
2. **FF-3** — FF-2 + tighter ATR (1.5x) + wider OTE (10-90%)
3. **FF-4** — FF-3 + higher stake (5%) → measure risk-adjusted return

### Success Criteria
- ✅ Trades: 100+/yr
- ✅ WR: ≥45%
- ✅ PF: ≥1.5
- ✅ Profit: ≥5%/yr

---

## v0.65.0 Results (ATH — 2026-03-20)

| Metric | Value |
|--------|-------|
| Trades | 35 (2yr) |
| Win Rate | 57.1% |
| Profit USDT | +$46.80 |
| Profit % | 4.68% |
| Profit Factor | 2.43 |
| SQN | 2.10 |
| Max Drawdown | 0.85% |
| Avg Hold | 4h53m |

**Exit Breakdown:**
| Exit | Trades | USDT | WR |
|------|--------|------|----|
| early_profit_take | 14 | +46.18 | 100% |
| trailing_stop_loss | 7 | +22.17 | 71% |
| time_exit_6h | 7 | -14.12 | 0% |
| time_exit_8h | 4 | -6.87 | 0% |
| time_exit_4h | 2 | -1.71 | 0% |

**Per-Pair (all positive — no removals):**
BTC +$14.05 | DOGE +$11.94 | DOT +$7.93 | XRP +$7.30 | ETH +$2.82 | ADA +$2.77

**Core Issue:** time_exit 13 trades at -$22.71, 0% WR. Structural fix: partial exits.

---

## Architecture

```
Entry: OTE zone (30-70%) + SSL/BSL sweep + confirmation candle + FVG + imbalance
Exit: early_profit_take (0.8%) + trailing_stop + ROI + time_exit
Stop: atr_offset_v2 (2.0x) + stoploss (-0.99%)
Pairs: BTC, DOGE, DOT, XRP, ETH, ADA
Timeframe: 15m
```

---

## Version History (v0.60.0+)

| Version | Focus | Result |
|---------|-------|--------|
| v0.65.0 | ROI 400 @ 2% | 35 trades, 57.1% WR, $46.80 |
| v0.64.0 | REVERT v0.63.0 | 35 trades, 57.1% WR, $44.69 |
| v0.63.0 | Remove ROI 305 | ❌ REGRESSED — 45.7% WR, $0.01 |
| v0.62.0 | ROI 305 @ 1% | 35 trades, 57.1% WR, ATH |
| v0.61.0 | Disable time_exit_2 | 35 trades, 51.4% WR |
| v0.60.0 | Remove SOL | 34 trades, 52.9% WR |
| v0.59.0 | Remove BNB | 41 trades, 51.2% WR |
| v0.58.0 | Disable ChoCH exits | 43 trades, 48.8% WR |

---

*Full version history and archived experiments in ROADMAP_ARCHIVE.md*
