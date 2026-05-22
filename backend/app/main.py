from fastapi import FastAPI
from app.api.v1 import endpoints

app = FastAPI(title="Quant Engine API", version="1.0.0")

app.include_router(endpoints.router, prefix="/v1")

@app.get("/health")
def health_check():
    return {"status": "ok"}
