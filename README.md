# Quant XPR 🚀

A full-stack, production-grade Quantitative Analysis Platform for Institutional Research.
This monorepo contains the Backend API, the Frontend Dashboard, and the Ingestion pipeline.

## 🏛️ Architecture

- **Backend:** FastAPI, SQLAlchemy, Alembic, Structlog, SlowAPI (Rate Limiter).
- **Frontend:** Vanilla JS, HTML, CSS, Chart.js.
- **Ingestion:** Python scripts for CRON-based weekly market data ingestion.
- **Database:** SQLite (dev) / Ready for Postgres.
- **Engines:** Markov Regime Switching models (Hidden Markov Models / Observable) and Volatility Surface (Smile/Skew).

## 🚀 Getting Started (Local Development)

### Prerequisites
- Python 3.11+
- `uv` package manager (`pip install uv`)

### 1. Backend Setup

```bash
cd backend
uv pip install -r requirements.txt
```

### 2. Database Migrations

The database schema is managed by **Alembic**. To apply the migrations and create the local SQLite database:

```bash
cd backend
uv run alembic upgrade head
```

### 3. Running the API

```bash
cd backend
uv run uvicorn app.main:app --reload
```
The API will be available at: http://127.0.0.1:8000
Swagger Docs: http://127.0.0.1:8000/docs

### 4. Running the Dashboard

Simply open `frontend/index.html` in your web browser. 
Configure your API Base URL (e.g., `http://127.0.0.1:8000`) and the API Key (`quant-secret-key` by default) in the UI.

## 🐳 Running via Docker

To run the entire stack using Docker Compose:

```bash
docker-compose up --build
```

## 🧪 Running Tests

We use `pytest` for unit testing the API.

```bash
cd backend
PYTHONPATH=. uv run pytest tests/
```
