from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from app.api.v1 import endpoints
from app.db.database import engine, Base
import os

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Quant Engine API", version="1.0.0")

API_KEY = os.getenv("API_KEY", "quant-secret-key")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(status_code=403, detail="Could not validate API KEY")

app.include_router(endpoints.router, prefix="/v1", dependencies=[Depends(get_api_key)])

@app.get("/health")
def health_check():
    return {"status": "ok"}
