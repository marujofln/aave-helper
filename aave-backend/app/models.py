from pydantic import BaseModel, Field


class PriceResponse(BaseModel):
    price: float = Field(..., gt=0, description="BTC price in USD")
    source: str
    timestamp: str


class HealthFactorResponse(BaseModel):
    health_factor: float
    collateral_usd: float
    debt_usd: float
    liquidation_price: float
    margin_pct: float
    zone: str  # "safe" | "risk" | "liquidation"
