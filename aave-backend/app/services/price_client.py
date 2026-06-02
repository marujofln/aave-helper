import httpx

_COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"


async def fetch_prices(coingecko_ids: list[str]) -> dict[str, float]:
    """Fetch multiple asset prices in a single request."""
    params = {"ids": ",".join(coingecko_ids), "vs_currencies": "usd"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(_COINGECKO_URL, params=params)
        response.raise_for_status()
        data = response.json()
    return {cg_id: float(data[cg_id]["usd"]) for cg_id in coingecko_ids}


async def fetch_price(coingecko_id: str) -> tuple[float, str]:
    prices = await fetch_prices([coingecko_id])
    return prices[coingecko_id], "CoinGecko"
