import httpx
from functools import lru_cache
import structlog

logger = structlog.get_logger(__name__)

@lru_cache(maxsize=1)
def get_selic_anual() -> float:
    """Retorna Selic Over anualizada (ex: 0.1325 para 13.25%)."""
    try:
        r = httpx.get(
            "https://api.bcb.gov.br/dados/serie/bcdata.sgs.11/dados/ultimos/1",
            params={"formato": "json"},
            timeout=5.0,
        )
        r.raise_for_status()
        taxa_diaria = float(r.json()[0]["valor"]) / 100
        selic_anual = (1 + taxa_diaria) ** 252 - 1
        return selic_anual
    except Exception as exc:
        logger.warning("bcb_api_failed", error=str(exc), msg="Fallback to 13.25% hardcoded Selic")
        return 0.1325  # fallback hardcoded se BCB estiver fora
