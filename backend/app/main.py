from fastapi import FastAPI, Depends, HTTPException, Security, Request
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import time

from app.api.v1 import endpoints
from app.api.v1 import upload
from app.core.config import settings
from app.core.logger import logger
from app.core.rate_limit import limiter

app = FastAPI(title="Quant Engine API", version="1.1.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://carpatia77.github.io"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        process_time_ms=f"{process_time:.2f}"
    )
    return response

API_KEY = settings.API_KEY
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_api_key(api_key_header: str = Security(api_key_header)):
    if api_key_header == API_KEY:
        return api_key_header
    raise HTTPException(status_code=403, detail="Could not validate API KEY")

# Análise e histórico (autenticados)
app.include_router(
    endpoints.router,
    prefix=settings.API_V1_STR,
    dependencies=[Depends(get_api_key)]
)

# Upload manual de dados (autenticado)
app.include_router(
    upload.router,
    prefix=settings.API_V1_STR,
    dependencies=[Depends(get_api_key)]
)

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.1.0"}
