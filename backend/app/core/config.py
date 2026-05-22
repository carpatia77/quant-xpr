from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_KEY: str = "quant-secret-key"
    DATABASE_URL: str = "sqlite:///./quantdb.sqlite"
    API_V1_STR: str = "/v1"

    class Config:
        env_file = ".env"

settings = Settings()
