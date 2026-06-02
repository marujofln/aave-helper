from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.limiter import limiter
from app.routers import price

_STATIC = Path(__file__).parent / "static"

app = FastAPI(
    title="Aave Health Factor Simulator",
    # Disable interactive docs in production; set to "/docs" locally if needed
    docs_url=None,
    redoc_url=None,
)

# Rate limiting
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# CORS — tighten allowed_origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "font-src https://cdn.jsdelivr.net; "
        "connect-src 'self'; "
        "img-src 'self' data:;"
    )
    return response


app.include_router(price.router)
app.mount("/static", StaticFiles(directory=_STATIC), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(_STATIC / "index.html")
