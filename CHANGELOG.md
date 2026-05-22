# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Commit Convention
We follow the **Semantic Commits** convention:
- `feat:` A new feature.
- `fix:` A bug fix.
- `docs:` Documentation only changes.
- `style:` Changes that do not affect the meaning of the code.
- `refactor:` A code change that neither fixes a bug nor adds a feature.
- `perf:` A code change that improves performance.
- `test:` Adding missing tests or correcting existing tests.
- `chore:` Changes to the build process or auxiliary tools.

---

## [1.0.0] - 2026-05-22

### Added
- `feat`: Institutional Dashboard with Chart.js integration (Markov regime time-series & Volatility Smile).
- `feat`: Asynchronous FastAPI backend to prevent blocking on data fetching.
- `feat`: Cross analysis endpoints (`/summary/{ticker}`) extracting logic from Markov and Volatility engines.
- `feat`: Database persistence for analysis history using SQLAlchemy and SQLite.
- `feat`: Alembic migrations for database schema management.
- `feat`: API Key authentication dependency.
- `feat`: Automated testing pipeline via GitHub Actions using Pytest.
- `feat`: Structured JSON Logging using `structlog`.
- `feat`: Global and route-specific Rate Limiting via `slowapi` to prevent API abuse.
- `docs`: Extensive README and CHANGELOG to guide open-source and institutional contributors.

### Refactored
- `refactor`: Extracted Yahoo Finance fetching logic to `services/data_fetcher.py`.
- `refactor`: Converted endpoints to `async def` and offloaded blocking computations to threads using `asyncio.to_thread`.
- `refactor`: Monorepo structure unifying `backend`, `frontend`, `ingestion` and `contracts`.

### Fixed
- `fix`: Timezone issues by replacing `datetime.utcnow()` with `datetime.now(timezone.utc)`.
- `fix`: Pydantic settings loading from `.env` instead of unsafe `os.getenv` fallbacks.
