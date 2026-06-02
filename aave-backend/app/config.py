from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    collateral_amount: float = 0.5
    debt_usd: float = 20000.0
    liquidation_threshold: float = 0.78

    allowed_origins: list[str] = ["http://localhost:8000"]
    rate_limit_price: str = "10/minute"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
