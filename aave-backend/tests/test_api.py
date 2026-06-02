from unittest.mock import AsyncMock, patch

import pytest


async def test_health_check(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_price_success(client):
    with patch("app.routers.price.price_client.fetch_price", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = (75_000.0, "CoinGecko")
        resp = await client.get("/api/price", params={"asset": "wrapped-bitcoin"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["price"] == 75_000.0
    assert body["source"] == "CoinGecko"
    assert "timestamp" in body


async def test_price_default_asset(client):
    with patch("app.routers.price.price_client.fetch_price", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = (3_000.0, "CoinGecko")
        resp = await client.get("/api/price")

    assert resp.status_code == 200
    mock_fetch.assert_called_once_with("bitcoin")


async def test_price_upstream_error_returns_502(client):
    with patch("app.routers.price.price_client.fetch_price", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = RuntimeError("CoinGecko timeout")
        resp = await client.get("/api/price")

    assert resp.status_code == 502


class TestHealthFactorEndpoint:
    async def test_valid_price_returns_200(self, client):
        resp = await client.get("/api/health-factor", params={"price": 70_000})
        assert resp.status_code == 200
        body = resp.json()
        assert "health_factor" in body
        assert "zone" in body
        assert "liquidation_price" in body
        assert "margin_pct" in body
        assert body["zone"] in {"safe", "risk", "liquidation"}

    async def test_health_factor_math(self, client):
        from unittest.mock import MagicMock, patch as _patch

        mock_cfg = MagicMock()
        mock_cfg.collateral_amount = 1.0
        mock_cfg.debt_usd = 10_000.0
        mock_cfg.liquidation_threshold = 0.78

        with _patch("app.services.health_factor.settings", mock_cfg):
            resp = await client.get("/api/health-factor", params={"price": 20_000})

        assert resp.status_code == 200
        body = resp.json()
        # HF = (1.0 * 20_000 * 0.78) / 10_000 = 1.56
        assert body["health_factor"] == pytest.approx(1.56, abs=0.001)
        assert body["zone"] == "safe"

    async def test_price_too_low_returns_422(self, client):
        resp = await client.get("/api/health-factor", params={"price": 500})
        assert resp.status_code == 422

    async def test_price_too_high_returns_422(self, client):
        resp = await client.get("/api/health-factor", params={"price": 20_000_000})
        assert resp.status_code == 422

    async def test_price_at_lower_boundary(self, client):
        resp = await client.get("/api/health-factor", params={"price": 1_000})
        assert resp.status_code == 200

    async def test_price_at_upper_boundary(self, client):
        resp = await client.get("/api/health-factor", params={"price": 10_000_000})
        assert resp.status_code == 200

    async def test_missing_price_param_returns_422(self, client):
        resp = await client.get("/api/health-factor")
        assert resp.status_code == 422
