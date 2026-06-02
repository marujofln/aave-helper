# Aave Health Factor Simulator

Simulates the health factor of any Aave V4 position — any collateral asset against any stablecoin debt.

Import your transaction history CSV from Aave Pro to populate your real position, then drag the price slider to see how different prices affect your health factor, liquidation price, and how much collateral you would need to deposit to reach HF 1.5. Values are saved in browser `localStorage` and restored on every visit.

## Structure

```
aave-helper/
├── aave-backend/   FastAPI backend — serves the UI and API endpoints
└── aave-widget/    Standalone HTML widget (no server required)
```

## Requirements

- [uv](https://docs.astral.sh/uv/) — Python package manager

## Getting started

```bash
cd aave-backend
uv run dev        # development server with auto-reload on :8000
uv run start      # production server on :8000
```

Open http://localhost:8000 in your browser.

## Importing your position

Click **Importar histórico** and select the CSV exported from Aave Pro. The app will:

1. Detect the collateral asset automatically (the deposited asset with the highest total USD value)
2. Sum all `Deposited` rows for that asset into the collateral amount
3. Sum the `USD Value` of all `Borrowed` rows into the total debt
4. Save the position to browser `localStorage` — no need to re-import on the next visit

Expected CSV columns: `Date`, `Action`, `Asset`, `Amount`, `USD Value`.

Supported collateral/debt pairs include WBTC/USDT, WBTC/USDC, WBTC/USDG, ETH/USDT, ETH/USDC, ETH/USDG, and any other asset available on CoinGecko. The debt token only contributes its USD value — it is never priced separately.

### CoinGecko asset mapping

The frontend maps CSV asset symbols to CoinGecko IDs for live price fetching:

| Symbol | CoinGecko ID |
|--------|-------------|
| WBTC | `wrapped-bitcoin` |
| cbBTC | `coinbase-wrapped-btc` |
| ETH / WETH | `ethereum` / `weth` |
| LINK | `chainlink` |
| AAVE | `aave` |
| UNI | `uniswap` |

Assets not in the table fall back to `symbol.toLowerCase()` as the CoinGecko ID.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/price?asset={coingecko_id}` | Current price from CoinGecko (`asset` defaults to `bitcoin`) |
| `GET` | `/api/health-factor?price={n}` | Health factor for a given collateral price |
| `GET` | `/api/health` | Health check |

Rate limit: 10 requests/minute on `/api/price`.

## Configuration

All settings have defaults and can be overridden via environment variables or a `.env` file in `aave-backend/`:

| Variable | Default | Description |
|----------|---------|-------------|
| `COLLATERAL_AMOUNT` | `0.5` | Collateral amount (backend default only) |
| `DEBT_USD` | `20000.0` | Total debt in USD (backend default only) |
| `LIQUIDATION_THRESHOLD` | `0.78` | Aave liquidation threshold (78%) |
| `ALLOWED_ORIGINS` | `http://localhost:8000` | CORS allowed origins |
| `RATE_LIMIT_PRICE` | `10/minute` | Rate limit for the price endpoint |

> The collateral and debt values come from the imported CSV in the browser. The backend defaults are only used by the `/api/health-factor` endpoint when called directly.

```bash
cp .env.example .env
# edit .env as needed
```

## Running tests

```bash
cd aave-backend
uv run pytest tests/ -v                 # 70 unit tests (no network)
uv run pytest tests/ -v -m integration  # + 6 live CoinGecko tests
```

### Test coverage

| File | What it covers |
|------|---------------|
| `test_health_factor.py` | HF formula, zone boundaries, liquidation price, margin sign |
| `test_price_client.py` | CoinGecko client — response parsing, HTTP errors, missing keys |
| `test_api.py` | All endpoints — happy paths, upstream 502, price boundary 422s |
| `test_pairs.py` | CSV parsing and HF math for all 6 pairs (WBTC/USDT, WBTC/USDC, WBTC/USDG, ETH/USDT, ETH/USDC, ETH/USDG); live CoinGecko price checks for WBTC and ETH |
