import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from app.config import settings
from app.limiter import limiter
from app.models import HealthFactorResponse, PriceResponse
from app.services import price_client, health_factor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["price"])


@router.get("/price", response_model=PriceResponse)
@limiter.limit(settings.rate_limit_price)
async def get_price(request: Request, asset: str = "bitcoin") -> PriceResponse:
    try:
        price, source = await price_client.fetch_price(asset)
    except Exception as exc:
        logger.warning("price fetch failed for %r: %s", asset, exc)
        raise HTTPException(status_code=502, detail="Price provider unavailable") from exc

    return PriceResponse(
        price=price,
        source=source,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/health-factor", response_model=HealthFactorResponse)
async def get_health_factor(price: float) -> HealthFactorResponse:
    if not (1_000 <= price <= 10_000_000):
        raise HTTPException(status_code=422, detail="price must be between 1000 and 10000000")
    return health_factor.compute(price)


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
