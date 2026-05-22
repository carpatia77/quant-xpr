from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_KEY: str = "quant-secret-key"
    DATABASE_URL: str = "sqlite:///./quantdb.sqlite"
    API_V1_STR: str = "/v1"
    
    # Strategy Parameters
    BULL_THRESHOLD: float = 0.5
    IV_MAX_CHEAP: float = 0.35
    SKEW_MIN_REVERSAL: float = 0.02

    class Config:
        env_file = ".env"

settings = Settings()
