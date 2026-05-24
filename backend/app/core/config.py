from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    API_KEY: str = "quant-secret-key"
    DATABASE_URL: str = "sqlite:///./quantdb.sqlite"
    API_V1_STR: str = "/v1"
    HG_BRASIL_API_KEY: str = "8e65eb97"
    
    # Strategy Parameters
    BULL_THRESHOLD: float = 0.5
    IV_MAX_CHEAP: float = 0.35
    SKEW_MIN_REVERSAL: float = 0.02

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
