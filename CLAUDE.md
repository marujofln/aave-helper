# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All backend work happens in `aave-backend/` and uses [uv](https://docs.astral.sh/uv/). pytest lives in the `dev` optional-dependency group, so test commands need `--extra dev`.

```bash
cd aave-backend
uv run dev                                        # uvicorn with reload on :8000 (app.__main__:dev)
uv run start                                      # uvicorn without reload on :8000
uv run --extra dev pytest tests/ -m "not integration"   # unit tests only, no network
uv run --extra dev pytest tests/ -m integration          # live CoinGecko tests only
uv run --extra dev pytest tests/test_api.py::test_price_success   # single test
```

No `addopts` is set, so a plain `pytest tests/` also runs the `integration`-marked tests that call CoinGecko. `asyncio_mode = "auto"` is set, so async tests need no decorator. There is no linter or formatter configured.

## Architecture

Two independent deliverables:

- **`aave-backend/`** is a FastAPI app that serves the main UI (`app/static/index.html` at `/`) plus a small `/api` router (`app/routers/price.py`).
- **`aave-widget/index.html`** is an older standalone single-file version (Portuguese README) with a hardcoded WBTC position. It fetches prices through the Anthropic API instead of the backend. It is **not** a copy of the backend's `index.html`, and the two have diverged.

### The real logic lives in the frontend

`app/static/index.html` is a single-file vanilla-JS app (Chart.js and Tabler Icons from CDN; the UI text is in Portuguese). It:

- parses the Aave Pro CSV export (`parseCSV`): the collateral is the deposited asset with the highest total USD value, and the debt is the sum of `USD Value` across all `Borrowed` rows;
- computes HF, liquidation price and the "deposit needed for HF 1.5" itself in JS (`calcHF`, `liqPrice`, with `LT = 0.78` hardcoded);
- maps symbols to CoinGecko IDs (`COINGECKO_IDS`, falling back to `symbol.toLowerCase()`) and calls the backend only for `/api/price?asset=<id>`;
- persists the position to `localStorage`.

The backend's `/api/health-factor` (`services/health_factor.py`) duplicates the HF math, but it uses the `Settings` defaults (`collateral_amount`, `debt_usd`) and is **not** used by the UI.

### Duplicated logic that must stay in sync

- **HF formula and zone thresholds** (`< 1.05` liquidation, `< 1.5` risk, otherwise safe) appear in both `services/health_factor.py` and the JS `hfColor`/`hfBadge`/`calcHF`.
- **CSV parsing:** `tests/test_pairs.py` contains `parse_csv`, a Python mirror of the JS `parseCSV`, and its own copy of `COINGECKO_IDS`. If you change the frontend parser or the ID mapping, update these tests too.

### Backend details

- `app/config.py`: a pydantic-settings `Settings` singleton that reads env vars or `aave-backend/.env`. Tests override it by patching `app.services.health_factor.settings`.
- `app/main.py`: sets up slowapi middleware, GET-only CORS from `allowed_origins`, and a strict CSP header middleware. If the frontend loads a new CDN, update `script-src`/`style-src`/`font-src` there. Docs (`/docs`, `/redoc`) are disabled.
- The rate limit on `/api/price` comes from `settings.rate_limit_price`. It is read once, when the decorator runs at import time.
- `ALLOWED_ORIGINS` is a `list[str]`, so pydantic-settings expects it as JSON in env/.env (`["http://a","http://b"]`).
- `/api/health-factor` rejects prices outside `[1_000, 10_000_000]` with a 422. `/api/price` turns any upstream exception into a 502.
- `services/price_client.py` calls the CoinGecko `simple/price` endpoint through `httpx`. API tests mock `app.routers.price.price_client.fetch_price`.
