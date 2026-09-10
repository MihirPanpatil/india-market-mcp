# India Market MCP

> Hermes Agent integration notes: see [`HERMES.md`](HERMES.md) for the local stdio configuration, data-source map, endpoint replacements, test commands, and maintenance checklist.

Comprehensive MCP server for the Indian stock market — **60 tools** covering NSE/BSE, F&O, Mutual Funds, Technicals, ETFs, Commodities, Currencies, Screeners, and more.

Built by combining the best features from 5 open-source Indian market MCP servers. **No API keys required.**

## Features

| Module | Tools | What It Covers |
|--------|-------|----------------|
| Stocks | 11 | Live quotes, history, financials, peers, corporate actions, peers |
| Derivatives | 15 | Option chain, Greeks, max pain, PCR, OI analysis, strategies, margin |
| Indices | 3 | All NSE indices, constituents, sector performance |
| Mutual Funds | 8 | 47,000+ AMFI schemes, NAV history, comparison, SIP/XIRR calculators |
| Market | 11 | FII/DII, IPOs, market breadth, block/bulk deals, dividends, holidays |
| Technicals | 3 | SMA, EMA, RSI, MACD, Bollinger Bands, support/resistance, candlestick |
| Additional | 9 | ETFs, commodities, currencies, sovereign gold bonds, stock screener |

## Install

```bash
cd india-market-mcp
pip install -e .
```

## Usage

### With Claude Desktop / opencode (stdio)

Add to your MCP config:

```json
{
  "mcpServers": {
    "india-market": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "D:\\Default Project\\nse-mcp-servers\\india-market-mcp"
    }
  }
}
```

### With opencode (CLI)

```bash
opencode mcp add india-market -- python -m src.server
```

### Development / Testing

```bash
mcp dev src/server.py
```

## Tool List

### Stocks
- `get_stock_quote` — Live quote with price, volume, P/E, 52-week range
- `search_stocks` — Search NSE by name or symbol
- `get_stock_history` — Historical OHLCV data (1d/1wk/1mo intervals)
- `get_top_gainers_losers` — NSE top movers with % change
- `get_52_week_high_low` — Stocks near 52-week extremes
- `get_corporate_actions` — Dividends, splits, bonuses
- `get_stock_financials` — Revenue, profit, margins, balance sheet
- `get_stock_peers` — Compare against sector peers
- `get_market_cap_ranking` — Rank stocks by market cap
- `get_stock_returns` — 1M, 3M, 6M, 1Y, 3Y, 5Y returns
- `get_delivery_volume` — Delivery vs intraday volume analysis

### Derivatives
- `get_option_chain` — Full option chain for any F&O symbol
- `get_expiry_dates` — Available expiry dates
- `get_spot_price` — Current underlying price
- `calculate_greeks` — Black-Scholes Greeks calculator
- `calculate_iv` — Implied volatility from market price
- `get_max_pain` — Max pain strike price
- `get_pcr` — Put-Call Ratio by OI and volume
- `get_oi_analysis` — Open interest build-up / unwinding
- `get_top_oi_gainers` — Largest OI change strikes
- `build_strategy` — Iron condor, straddle, strangle, butterfly, spread
- `calculate_margin` — Expected margin for F&O positions
- `get_option_premium` — Theoretical premium from Black-Scholes
- `get_atm_straddle_premium` — ATM straddle premium and IV
- `get_itm_otm_options` — Classify strikes as ITM/ATM/OTM
- `calculate_position_size` — Kelly Criterion / risk-based sizing

### Indices
- `get_all_indices` — All NSE indices with live values
- `get_index_constituents` — All stocks in an index with prices
- `get_sector_performance` — Sectoral indices ranked by performance

### Mutual Funds
- `search_mutual_funds` — Search 47,000+ AMFI schemes
- `get_mf_nav` — Latest NAV
- `get_mf_history` — Full NAV history
- `get_mf_details` — Fund house, category, AUM, expense ratio
- `compare_mf` — Side-by-side comparison of 2–4 funds
- `analyze_mf` — Risk metrics, alpha, Sharpe, Sortino
- `calculate_sip` — SIP future value calculator
- `calculate_xirr` — XIRR from irregular cashflows

### Market
- `get_market_status` — Is NSE open/closed/pre-market
- `get_fii_dii_data` — Foreign & domestic institutional flows
- `get_advances_declines` — Market breadth
- `get_upcoming_ipos` — Current & upcoming IPOs
- `get_past_ipos` — Recently listed IPO performance
- `get_market_announcements` — NSE announcements & circulars
- `get_top_market_news` — Market news headlines
- `get_block_deals` — Block deal activity
- `get_bulk_deals` — Bulk deal activity
- `get_dividend_calendar` — Upcoming ex-dividend dates
- `get_market_holidays` — NSE trading holidays

### Technicals
- `get_technical_indicators` — SMA, EMA, RSI, MACD, Bollinger Bands
- `get_support_resistance` — Pivot point S/R levels
- `detect_candlestick_patterns` — Doji, hammer, engulfing, etc.

### Additional
- `get_all_etfs` — NSE ETFs with live prices
- `get_etf_quote` — Detailed ETF quote
- `get_commodity_price` — Gold, Silver, Crude, Natural Gas
- `get_all_commodity_prices` — All commodities at once
- `get_currency_rate` — USD/INR, EUR/INR, GBP/INR, JPY/INR
- `get_all_currency_rates` — All major pairs
- `get_sgb_prices` — Sovereign Gold Bond live prices
- `get_stock_screener` — Multi-criteria stock screening
- `get_sector_stocks` — All stocks in a sector

## Data Sources

- **NSE India** — Live market data, option chains, IPOs, FII/DII, announcements
- **Yahoo Finance** — International data, technical indicators, commodities, currencies
- **AMFI** — 47,000+ mutual fund schemes and NAV history

## Caching

Results are cached to disk (`.cache/india-market-mcp/`) with TTLs ranging from 30s (live data) to 1h (static data). Cache size limit: 500MB.

## Rate Limiting

NSE API calls are rate-limited to 1 request every 350ms with automatic retry on 401/403 responses and session re-initialization.

## License

MIT
