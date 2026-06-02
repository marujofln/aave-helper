from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.price_client import fetch_price


def _mock_response(payload: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = payload
    resp.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("err", request=MagicMock(), response=resp)
        if status_code >= 400 else None
    )
    return resp


def _patch_client(response: MagicMock):
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return patch("app.services.price_client.httpx.AsyncClient", return_value=mock_client)


async def test_returns_price_and_source():
    resp = _mock_response({"wrapped-bitcoin": {"usd": 95000.50}})
    with _patch_client(resp):
        price, source = await fetch_price("wrapped-bitcoin")
    assert price == pytest.approx(95000.50)
    assert source == "CoinGecko"


async def test_price_is_float():
    resp = _mock_response({"ethereum": {"usd": 3000}})
    with _patch_client(resp):
        price, _ = await fetch_price("ethereum")
    assert isinstance(price, float)


async def test_works_for_any_asset():
    resp = _mock_response({"chainlink": {"usd": 14.75}})
    with _patch_client(resp):
        price, source = await fetch_price("chainlink")
    assert price == pytest.approx(14.75)
    assert source == "CoinGecko"


async def test_http_error_propagates():
    resp = _mock_response({}, status_code=429)
    with _patch_client(resp):
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_price("wrapped-bitcoin")


async def test_missing_key_raises():
    resp = _mock_response({"wrapped-bitcoin": {}})  # no "usd" key
    with _patch_client(resp):
        with pytest.raises(KeyError):
            await fetch_price("wrapped-bitcoin")
