"""
Tests for collateral/debt pair support.

Covers:
- CSV parsing for every pair (Python mirror of the JS parseCSV logic)
- Health factor math for every pair
- Live CoinGecko price fetch for each collateral asset (integration marker)
"""

import math
import textwrap
from unittest.mock import MagicMock, patch

import pytest

from app.services import health_factor
from app.services.price_client import fetch_price, fetch_prices

# ─── COINGECKO IDs (must match the frontend mapping) ─────────────────────────

COINGECKO_IDS = {
    "WBTC": "wrapped-bitcoin",
    "ETH":  "ethereum",
}

# Expected CoinGecko price ranges for sanity checks
PRICE_RANGES = {
    "wrapped-bitcoin": (1_000,   10_000_000),
    "ethereum":        (100,     1_000_000),
}

# ─── CSV helper ───────────────────────────────────────────────────────────────

def make_csv(collateral_asset: str, collateral_amount: float,
             collateral_usd: float, debt_asset: str, debt_usd: float) -> str:
    """Minimal Aave-Pro-style CSV with one deposit and one borrow row."""
    return textwrap.dedent(f"""
        Date,Action,Asset,Amount,USD Value,Exchange Rate (USD),Hub,Spoke,Transaction Hash
        2026-01-01T00:00:00.000Z,Deposited,{collateral_asset},{collateral_amount},{collateral_usd},1.0,Core,Main,https://etherscan.io/tx/0x1
        2026-01-02T00:00:00.000Z,Borrowed,{debt_asset},{debt_usd},{debt_usd},1.0,Core,Main,https://etherscan.io/tx/0x2
    """).strip()


def parse_csv(text: str) -> dict:
    """Python mirror of the frontend JS parseCSV function."""
    lines = [l.strip() for l in text.strip().split("\n")]
    header = [h.strip() for h in lines[0].split(",")]

    def col(name: str) -> int:
        return header.index(name)

    deposits: dict[str, dict] = {}
    total_debt = 0.0

    for line in lines[1:]:
        row = [c.strip() for c in line.split(",")]
        if len(row) < len(header):
            continue

        action  = row[col("Action")]
        asset   = row[col("Asset")]
        try:    amount  = float(row[col("Amount")])
        except  ValueError: amount = math.nan
        try:    usd_val = float(row[col("USD Value")])
        except  ValueError: usd_val = math.nan

        if action == "Deposited" and asset and not math.isnan(amount):
            if asset not in deposits:
                deposits[asset] = {"amount": 0.0, "usd": 0.0}
            deposits[asset]["amount"] += amount
            if not math.isnan(usd_val):
                deposits[asset]["usd"] += usd_val

        elif action == "Borrowed" and not math.isnan(usd_val):
            total_debt += usd_val

    if not deposits:
        raise ValueError("No deposits found")
    if total_debt == 0:
        raise ValueError("No borrows found")

    # Primary collateral = highest total deposit USD value (mirrors JS sort)
    primary_asset, primary_data = max(deposits.items(), key=lambda x: x[1]["usd"])
    return {
        "asset":              primary_asset,
        "collateral_amount":  primary_data["amount"],
        "total_debt":         total_debt,
    }


# ─── Fixtures / helpers ───────────────────────────────────────────────────────

def make_settings(collateral: float, debt: float, lt: float = 0.78) -> MagicMock:
    s = MagicMock()
    s.collateral_amount    = collateral
    s.debt_usd             = debt
    s.liquidation_threshold = lt
    return s


def compute_hf(collateral: float, debt: float, price: float, lt: float = 0.78):
    with patch("app.services.health_factor.settings", make_settings(collateral, debt, lt)):
        return health_factor.compute(price)


# ─── Parametrize across all 6 pairs ──────────────────────────────────────────

PAIRS = [
    # (collateral, debt_token, col_amount, col_price, debt_usd)
    ("WBTC", "USDT", 0.5,  67_000.0, 20_000.0),
    ("WBTC", "USDC", 0.5,  67_000.0, 20_000.0),
    ("WBTC", "USDG", 0.5,  67_000.0, 20_000.0),
    ("ETH",  "USDT", 5.0,   2_000.0,  5_000.0),
    ("ETH",  "USDC", 5.0,   2_000.0,  5_000.0),
    ("ETH",  "USDG", 5.0,   2_000.0,  5_000.0),
]

PAIR_IDS = [f"{c}/{d}" for c, d, *_ in PAIRS]


# ─── CSV parsing tests ────────────────────────────────────────────────────────

class TestCSVParsing:
    @pytest.mark.parametrize("collateral,debt_token,col_amount,col_price,debt_usd", PAIRS, ids=PAIR_IDS)
    def test_detects_correct_collateral_asset(self, collateral, debt_token, col_amount, col_price, debt_usd):
        csv = make_csv(collateral, col_amount, col_amount * col_price, debt_token, debt_usd)
        result = parse_csv(csv)
        assert result["asset"] == collateral

    @pytest.mark.parametrize("collateral,debt_token,col_amount,col_price,debt_usd", PAIRS, ids=PAIR_IDS)
    def test_sums_collateral_amount(self, collateral, debt_token, col_amount, col_price, debt_usd):
        csv = make_csv(collateral, col_amount, col_amount * col_price, debt_token, debt_usd)
        result = parse_csv(csv)
        assert result["collateral_amount"] == pytest.approx(col_amount)

    @pytest.mark.parametrize("collateral,debt_token,col_amount,col_price,debt_usd", PAIRS, ids=PAIR_IDS)
    def test_sums_debt_usd(self, collateral, debt_token, col_amount, col_price, debt_usd):
        csv = make_csv(collateral, col_amount, col_amount * col_price, debt_token, debt_usd)
        result = parse_csv(csv)
        assert result["total_debt"] == pytest.approx(debt_usd)

    @pytest.mark.parametrize("debt_token", ["USDT", "USDC", "USDG"])
    def test_debt_token_does_not_affect_result(self, debt_token):
        """All three stablecoins produce identical collateral/debt totals."""
        csv = make_csv("WBTC", 0.5, 33_500.0, debt_token, 20_000.0)
        result = parse_csv(csv)
        assert result["collateral_amount"] == pytest.approx(0.5)
        assert result["total_debt"]        == pytest.approx(20_000.0)

    def test_primary_collateral_chosen_by_usd_value(self):
        """If two assets are deposited, the one with higher USD value wins."""
        csv = textwrap.dedent("""
            Date,Action,Asset,Amount,USD Value,Exchange Rate (USD),Hub,Spoke,Transaction Hash
            2026-01-01T00:00:00.000Z,Deposited,ETH,1.0,2000.0,2000.0,Core,Main,https://etherscan.io/tx/0x1
            2026-01-02T00:00:00.000Z,Deposited,WBTC,0.5,33500.0,67000.0,Core,Main,https://etherscan.io/tx/0x2
            2026-01-03T00:00:00.000Z,Borrowed,USDT,10000.0,10000.0,1.0,Core,Main,https://etherscan.io/tx/0x3
        """).strip()
        result = parse_csv(csv)
        assert result["asset"] == "WBTC"

    def test_multiple_deposit_rows_same_asset(self):
        """Multiple deposit rows for the same asset are summed."""
        csv = textwrap.dedent("""
            Date,Action,Asset,Amount,USD Value,Exchange Rate (USD),Hub,Spoke,Transaction Hash
            2026-01-01T00:00:00.000Z,Deposited,WBTC,0.3,20100.0,67000.0,Core,Main,https://etherscan.io/tx/0x1
            2026-01-02T00:00:00.000Z,Deposited,WBTC,0.2,13400.0,67000.0,Core,Main,https://etherscan.io/tx/0x2
            2026-01-03T00:00:00.000Z,Borrowed,USDT,15000.0,15000.0,1.0,Core,Main,https://etherscan.io/tx/0x3
        """).strip()
        result = parse_csv(csv)
        assert result["collateral_amount"] == pytest.approx(0.5)

    def test_multiple_borrow_rows_different_stablecoins(self):
        """Multiple borrow rows across different stablecoins are summed."""
        csv = textwrap.dedent("""
            Date,Action,Asset,Amount,USD Value,Exchange Rate (USD),Hub,Spoke,Transaction Hash
            2026-01-01T00:00:00.000Z,Deposited,WBTC,0.5,33500.0,67000.0,Core,Main,https://etherscan.io/tx/0x1
            2026-01-02T00:00:00.000Z,Borrowed,USDT,5000.0,5000.0,1.0,Core,Main,https://etherscan.io/tx/0x2
            2026-01-03T00:00:00.000Z,Borrowed,USDC,3000.0,3000.0,1.0,Core,Main,https://etherscan.io/tx/0x3
            2026-01-04T00:00:00.000Z,Borrowed,USDG,2000.0,2000.0,1.0,Core,Main,https://etherscan.io/tx/0x4
        """).strip()
        result = parse_csv(csv)
        assert result["total_debt"] == pytest.approx(10_000.0)

    def test_enabled_as_collateral_rows_are_ignored(self):
        """'Enabled as collateral' rows (Amount=—) do not affect totals."""
        csv = textwrap.dedent("""
            Date,Action,Asset,Amount,USD Value,Exchange Rate (USD),Hub,Spoke,Transaction Hash
            2026-01-01T00:00:00.000Z,Enabled as collateral,WBTC,—,—,—,Core,Main,https://etherscan.io/tx/0x0
            2026-01-02T00:00:00.000Z,Deposited,WBTC,0.5,33500.0,67000.0,Core,Main,https://etherscan.io/tx/0x1
            2026-01-03T00:00:00.000Z,Borrowed,USDT,10000.0,10000.0,1.0,Core,Main,https://etherscan.io/tx/0x2
        """).strip()
        result = parse_csv(csv)
        assert result["collateral_amount"] == pytest.approx(0.5)
        assert result["total_debt"]        == pytest.approx(10_000.0)


# ─── Health factor math tests ─────────────────────────────────────────────────

class TestHealthFactorPairs:
    @pytest.mark.parametrize("collateral,debt_token,col_amount,col_price,debt_usd", PAIRS, ids=PAIR_IDS)
    def test_hf_is_positive(self, collateral, debt_token, col_amount, col_price, debt_usd):
        result = compute_hf(col_amount, debt_usd, col_price)
        assert result.health_factor > 0

    @pytest.mark.parametrize("collateral,debt_token,col_amount,col_price,debt_usd", PAIRS, ids=PAIR_IDS)
    def test_hf_formula(self, collateral, debt_token, col_amount, col_price, debt_usd):
        # HF = (collateral * price * LT) / debt
        expected = (col_amount * col_price * 0.78) / debt_usd
        result = compute_hf(col_amount, debt_usd, col_price)
        assert result.health_factor == pytest.approx(expected, rel=1e-3)

    @pytest.mark.parametrize("debt_token", ["USDT", "USDC", "USDG"])
    def test_same_usd_debt_same_hf_regardless_of_token(self, debt_token):
        """Stablecoin choice is irrelevant — only the USD value matters."""
        # All three should produce exactly the same health factor
        result = compute_hf(collateral=0.5, debt=20_000.0, price=67_000.0)
        assert result.health_factor == pytest.approx((0.5 * 67_000.0 * 0.78) / 20_000.0, rel=1e-4)

    def test_wbtc_position_zone(self):
        # HF = (0.5 * 67000 * 0.78) / 20000 = 1.3065 → risk zone
        result = compute_hf(collateral=0.5, debt=20_000.0, price=67_000.0)
        assert result.zone == "risk"

    def test_eth_position_zone(self):
        # HF = (5 * 2000 * 0.78) / 5000 = 1.56 → safe zone
        result = compute_hf(collateral=5.0, debt=5_000.0, price=2_000.0)
        assert result.zone == "safe"


# ─── CoinGecko integration ────────────────────────────────────────────────────
# All tests share a single batched request to avoid rate-limiting.

@pytest.fixture(scope="session")
def live_prices():
    """One CoinGecko call for the whole test session."""
    import asyncio
    try:
        return asyncio.run(fetch_prices(["wrapped-bitcoin", "ethereum", "bitcoin"]))
    except Exception as exc:
        pytest.skip(f"CoinGecko unavailable: {exc}")


@pytest.mark.integration
class TestCoinGeckoIntegration:
    def test_coingecko_ids_mapping_is_correct(self):
        assert COINGECKO_IDS["WBTC"] == "wrapped-bitcoin"
        assert COINGECKO_IDS["ETH"]  == "ethereum"

    def test_wbtc_price_returned(self, live_prices):
        assert "wrapped-bitcoin" in live_prices
        assert isinstance(live_prices["wrapped-bitcoin"], float)

    def test_eth_price_returned(self, live_prices):
        assert "ethereum" in live_prices
        assert isinstance(live_prices["ethereum"], float)

    def test_wbtc_price_in_range(self, live_prices):
        price = live_prices["wrapped-bitcoin"]
        low, high = PRICE_RANGES["wrapped-bitcoin"]
        assert low < price < high, f"WBTC ${price:,.2f} outside ${low:,}–${high:,}"

    def test_eth_price_in_range(self, live_prices):
        price = live_prices["ethereum"]
        low, high = PRICE_RANGES["ethereum"]
        assert low < price < high, f"ETH ${price:,.2f} outside ${low:,}–${high:,}"

    def test_wbtc_tracks_bitcoin_peg(self, live_prices):
        """WBTC should trade within 2% of BTC."""
        wbtc = live_prices["wrapped-bitcoin"]
        btc  = live_prices["bitcoin"]
        diff_pct = abs(wbtc - btc) / btc * 100
        assert diff_pct < 2.0, (
            f"WBTC (${wbtc:,.2f}) deviates {diff_pct:.2f}% from "
            f"BTC (${btc:,.2f}) — peg may be broken"
        )
