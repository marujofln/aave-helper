from app.config import settings
from app.models import HealthFactorResponse


def compute(price: float) -> HealthFactorResponse:
    collateral_usd = settings.collateral_amount * price
    health_factor = (collateral_usd * settings.liquidation_threshold) / settings.debt_usd
    liquidation_price = settings.debt_usd / (settings.collateral_amount * settings.liquidation_threshold)
    margin_pct = ((price - liquidation_price) / price) * 100

    if health_factor < 1.05:
        zone = "liquidation"
    elif health_factor < 1.5:
        zone = "risk"
    else:
        zone = "safe"

    return HealthFactorResponse(
        health_factor=round(health_factor, 4),
        collateral_usd=round(collateral_usd, 2),
        debt_usd=settings.debt_usd,
        liquidation_price=round(liquidation_price, 2),
        margin_pct=round(margin_pct, 2),
        zone=zone,
    )
