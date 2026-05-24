import httpx
from datetime import datetime, timedelta
import structlog

logger = structlog.get_logger(__name__)

_cache = {"value": None, "expires": datetime.min}

def get_selic_anual() -> float:
    """Retorna Selic Over anualizada (ex: 0.1325 para 13.25%)."""
    if datetime.utcnow() < _cache["expires"] and _cache["value"] is not None:
        return _cache["value"]
        
    try:
        r = httpx.get(
            "https://api.bcb.gov.br/dados/serie/bcdata.sgs.11/dados/ultimos/1",
            params={"formato": "json"},
            timeout=5.0,
        )
        r.raise_for_status()
        taxa_diaria = float(r.json()[0]["valor"]) / 100
        selic_anual = (1 + taxa_diaria) ** 252 - 1
        
        _cache["value"] = selic_anual
        _cache["expires"] = datetime.utcnow() + timedelta(hours=8)
        
        return selic_anual
    except Exception as exc:
        logger.warning("bcb_api_failed", error=str(exc), msg="Fallback to 13.25% hardcoded Selic")
        return 0.1325  # fallback hardcoded se BCB estiver fora
