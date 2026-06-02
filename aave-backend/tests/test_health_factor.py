from unittest.mock import MagicMock, patch

import pytest

from app.services import health_factor


def make_settings(collateral: float, debt: float, lt: float = 0.78) -> MagicMock:
    s = MagicMock()
    s.collateral_amount = collateral
    s.debt_usd = debt
    s.liquidation_threshold = lt
    return s


def compute(collateral: float, debt: float, price: float, lt: float = 0.78):
    with patch("app.services.health_factor.settings", make_settings(collateral, debt, lt)):
        return health_factor.compute(price)


class TestHealthFactorValue:
    def test_known_values(self):
        result = compute(collateral=0.5, debt=20000.0, price=67813.40)
        assert result.health_factor == pytest.approx(1.322, abs=0.001)

    def test_higher_price_raises_hf(self):
        low  = compute(collateral=1.0, debt=10_000.0, price=50_000.0)
        high = compute(collateral=1.0, debt=10_000.0, price=100_000.0)
        assert high.health_factor > low.health_factor

    def test_higher_debt_lowers_hf(self):
        low_debt  = compute(collateral=1.0, debt=10_000.0, price=50_000.0)
        high_debt = compute(collateral=1.0, debt=20_000.0, price=50_000.0)
        assert high_debt.health_factor < low_debt.health_factor

    def test_collateral_usd(self):
        result = compute(collateral=2.0, debt=10_000.0, price=30_000.0)
        assert result.collateral_usd == pytest.approx(60_000.0)

    def test_debt_usd_passthrough(self):
        result = compute(collateral=1.0, debt=12_345.67, price=50_000.0)
        assert result.debt_usd == pytest.approx(12_345.67)


class TestZoneClassification:
    def test_zone_safe(self):
        # HF = (1 * 100_000 * 0.78) / 10_000 = 7.8
        result = compute(collateral=1.0, debt=10_000.0, price=100_000.0)
        assert result.zone == "safe"

    def test_zone_risk_lower_boundary(self):
        debt, col, lt = 10_000.0, 1.0, 0.78
        price = debt * 1.06 / (col * lt)
        result = compute(collateral=col, debt=debt, price=price, lt=lt)
        assert result.zone == "risk"

    def test_zone_risk_upper_boundary(self):
        debt, col, lt = 10_000.0, 1.0, 0.78
        price = debt * 1.49 / (col * lt)
        result = compute(collateral=col, debt=debt, price=price, lt=lt)
        assert result.zone == "risk"

    def test_zone_liquidation(self):
        debt, col, lt = 10_000.0, 1.0, 0.78
        price = debt * 1.04 / (col * lt)
        result = compute(collateral=col, debt=debt, price=price, lt=lt)
        assert result.zone == "liquidation"


class TestLiquidationPrice:
    def test_liquidation_price_formula(self):
        col, debt, lt = 0.5, 20_000.0, 0.78
        result = compute(collateral=col, debt=debt, price=80_000.0, lt=lt)
        expected = debt / (col * lt)
        assert result.liquidation_price == pytest.approx(expected, rel=1e-4)

    def test_margin_positive_above_liq(self):
        result = compute(collateral=1.0, debt=10_000.0, price=100_000.0)
        assert result.margin_pct > 0

    def test_margin_negative_below_liq(self):
        debt, col, lt = 10_000.0, 1.0, 0.78
        liq = debt / (col * lt)
        result = compute(collateral=col, debt=debt, price=liq * 0.9, lt=lt)
        assert result.margin_pct < 0
