# Liquidity Sweep Freqtrade Strategy

A Freqtrade implementation of the **Liquidity Sweep Reversal Strategy** based on [Daily Price Action](https://dailypriceaction.com/blog/liquidity-sweep-reversals/).

## Strategy Overview

This strategy trades reversals after liquidity grabs in OTE (Optimal Trade Entry) zones.

### Core Logic

1. **HTF Trend Analysis (1H)**: Only trade with the higher timeframe trend
2. **OTE Zone Detection**: Wait for price to retrace into 0.62-0.79 Fibonacci zone
3. **Liquidity Sweep**: Detect when price wicks beyond recent swing high/low
4. **Confirmation**: Enter when price closes back beyond triggering swing level

### Features

- Multi-timeframe analysis (15m entry, 1H context)
- Dynamic swing detection for liquidity pools
- Custom stoploss based on sweep levels + buffer
- Hyperoptable parameters (OTE levels, lookback periods, R:R)
- Futures trading with configurable leverage

## Setup

### Prerequisites

```bash
# Install Freqtrade
pip install freqtrade

# Or use Docker
docker pull freqtradeorg/freqtrade:stable
```

### Configuration

1. Copy your API keys to `config.json`:
```json
{
    "exchange": {
        "key": "YOUR_API_KEY",
        "secret": "YOUR_API_SECRET"
    }
}
```

2. Adjust pair whitelist as needed

### Download Data

```bash
# Download historical data for backtesting
freqtrade download-data --config config.json --timeframe 15m 1h --days 365
```

## Backtesting

### Basic Backtest

```bash
freqtrade backtesting \
    --config config.json \
    --strategy LiquiditySweep \
    --timeframe 15m \
    --timerange 20240101-20250201
```

### With Detailed Output

```bash
freqtrade backtesting \
    --config config.json \
    --strategy LiquiditySweep \
    --timeframe 15m \
    --timerange 20240101-20250201 \
    --export trades \
    --export-filename backtest_results.json
```

### Hyperopt (Parameter Optimization)

```bash
freqtrade hyperopt \
    --config config.json \
    --strategy LiquiditySweep \
    --hyperopt-loss SharpeHyperOptLoss \
    --spaces buy \
    --epochs 500 \
    --timerange 20240101-20250101
```

## Strategy Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `ote_lower` | 0.62 | 0.55-0.65 | Lower OTE boundary (Fib level) |
| `ote_upper` | 0.79 | 0.75-0.85 | Upper OTE boundary (Fib level) |
| `swing_lookback` | 20 | 10-30 | Candles to look back for swings |
| `buffer_pips` | 0.0005 | 0.0002-0.001 | SL buffer beyond sweep |
| `min_rr` | 2.0 | 1.5-3.0 | Minimum reward-to-risk ratio |

## Development Roadmap

### v0.1.0 (Current)
- [x] Basic strategy structure
- [x] HTF trend detection
- [x] OTE zone calculation
- [x] Swing detection
- [x] Sweep detection
- [x] Entry signals
- [x] Custom stoploss

### v0.2.0 (Planned)
- [ ] FVG (Fair Value Gap) detection for refined entries
- [ ] Take profit at external swing levels
- [ ] Improve triggering swing detection accuracy
- [ ] Add "flat top" liquidity pool pattern detection

### v0.3.0 (Planned)
- [ ] Structure-based trend detection (BoS markers)
- [ ] Multiple TF confirmation
- [ ] Backtesting reports with trade analysis
- [ ] Live trading optimizations

## Backtest Results

*Results will be appended here after each iteration.*

---

## Iteration Log

| Date | Version | Changes | Performance |
|------|---------|---------|-------------|
| 2026-02-07 | 0.1.0 | Initial implementation | TBD |

---

## License

MIT License - Use at your own risk.

## Disclaimer

This strategy is for educational purposes only. Trading cryptocurrencies and forex carries significant risk. Past performance does not guarantee future results. Always use proper risk management.
