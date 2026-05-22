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

### 1. Backend Setup & Supabase

```bash
cd backend
uv pip install -r requirements.txt
```

**Supabase (Cloud DB):** 
The ingestion pipeline runs on GitHub Actions and connects to a Supabase PostgreSQL database. To enable this:
1. Create a free project on [Supabase](https://supabase.com/).
2. Get your connection string (e.g. `postgresql://postgres.[YOUR_PROJECT]:[PASSWORD]@aws-0-sa-east-1.pooler.supabase.com:6543/postgres`).
3. In your GitHub repository, go to **Settings > Secrets and variables > Actions**.
4. Add a New Repository Secret: `DATABASE_URL` and paste the connection string.

By default, local development uses SQLite (in the `backend/` directory). To test with Supabase locally, create a `.env` file in the `backend/` directory with `DATABASE_URL=sua_url_aqui`.

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
