"""
upload.py
---------
Endpoints para upload manual de dados de mercado.

POST /v1/upload/options/{ticker}   → grade de opções (xlsx/csv)
POST /v1/upload/ohlcv/{ticker}     → histórico OHLCV (xlsx/csv)
GET  /v1/upload/status/{ticker}    → verifica quais arquivos existem
DELETE /v1/upload/{type}/{ticker}  → remove arquivo
"""
import os
import io
import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from app.core.rate_limit import limiter
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/tmp/quant_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

REQUIRED_OPTIONS_COLS = {"ticker", "type", "strike", "iv", "delta", "last_price", "dist_pct", "moneyness", "expiry_date"}
REQUIRED_OHLCV_COLS  = {"Date", "Close"}

OPTIONS_DISPLAY_COLS = ["ticker","type","strike","iv","delta","gamma",
                         "theta_brl","theta_pct","vega","last_price",
                         "dist_pct","moneyness","expiry_date"]


def _read_upload(file: UploadFile) -> pd.DataFrame:
    content = file.file.read()
    name = file.filename.lower()
    if name.endswith(".csv"):
        return pd.read_csv(io.BytesIO(content))
    elif name.endswith((".xlsx", ".xls")):
        # Tenta ler primeira aba que contém as colunas necessárias
        xf = pd.ExcelFile(io.BytesIO(content))
        for sheet in xf.sheet_names:
            df = xf.parse(sheet)
            df.columns = [str(c).strip() for c in df.columns]
            if len(df.columns) >= 3:
                return df
        raise ValueError("Nenhuma aba válida encontrada no Excel")
    else:
        raise ValueError("Formato não suportado. Use .csv, .xlsx ou .xls")


def _options_path(ticker: str) -> str:
    clean = ticker.upper().replace(".SA", "")
    return os.path.join(UPLOAD_DIR, f"{clean}_options.csv")


def _ohlcv_path(ticker: str) -> str:
    clean = ticker.upper().replace(".SA", "")
    return os.path.join(UPLOAD_DIR, f"{clean}_ohlcv.csv")


@router.post("/upload/options/{ticker}")
@limiter.limit("10/minute")
async def upload_options(request: Request, ticker: str, file: UploadFile = File(...)):
    """
    Recebe grade de opções (xlsx ou csv).
    Aceita o formato do template PETR4_VALE3_opcoes_grade.xlsx.
    Detecta automaticamente a aba correta pelo ticker.
    """
    clean = ticker.upper().replace(".SA", "")
    try:
        df = _read_upload(file)
    except Exception as e:
        raise HTTPException(400, f"Erro ao ler arquivo: {e}")

    # Normaliza colunas — aceita nomes em português do template B3
    col_map = {
        "Ticker": "ticker", "TICKER": "ticker",
        "Tipo":   "type",   "TIPO":   "type",   "TYPE": "type",
        "Strike": "strike", "STRIKE": "strike",
        "IV (%)": "iv",     "Vol. Impl. (%)": "iv",  "IV": "iv",
        "Delta":  "delta",  "DELTA":  "delta",
        "Gamma":  "gamma",  "GAMMA":  "gamma",
        "Theta (R$)": "theta_brl", "Theta ($)": "theta_brl",
        "Theta (%)": "theta_pct",
        "Vega":   "vega",   "VEGA": "vega",
        "Último": "last_price", "Last": "last_price",
        "Dist. (%)": "dist_pct", "Dist_pct": "dist_pct",
        "Moeda":  "moneyness", "A/I/OTM": "moneyness",
        "Vencimento": "expiry_date", "Data/Hora": "expiry_date",
    }
    df = df.rename(columns=col_map)
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Filtra linhas do ticker correto (se coluna existir e for mista)
    if "ticker" in df.columns:
        mask = df["ticker"].astype(str).str.upper().str.startswith(clean[:4])
        df = df[mask]

    # Valida colunas mínimas
    missing = REQUIRED_OPTIONS_COLS - set(df.columns)
    if missing:
        # Tenta aceitar mesmo sem colunas opcionais
        hard_missing = {"strike", "iv", "type"} - set(df.columns)
        if hard_missing:
            raise HTTPException(400, f"Colunas obrigatórias faltando: {hard_missing}. Colunas encontradas: {list(df.columns)}")

    # Garante iv em decimal (se veio como 35.1 em vez de 0.351)
    if "iv" in df.columns:
        df["iv"] = pd.to_numeric(df["iv"], errors="coerce")
        if df["iv"].dropna().mean() > 2.0:  # veio em %, converte
            df["iv"] = df["iv"] / 100.0

    if "strike" in df.columns:
        df["strike"] = pd.to_numeric(df["strike"], errors="coerce")

    if df.empty:
        raise HTTPException(400, f"Nenhum dado encontrado para o ticker {clean}")

    path = _options_path(ticker)
    df.to_csv(path, index=False)
    logger.info("options_uploaded", ticker=clean, rows=len(df), path=path)

    return {
        "status": "success",
        "ticker": clean,
        "rows": len(df),
        "contracts_call": int((df["type"].str.upper() == "CALL").sum()) if "type" in df.columns else None,
        "contracts_put":  int((df["type"].str.upper() == "PUT").sum())  if "type" in df.columns else None,
        "path": path,
    }


@router.post("/upload/ohlcv/{ticker}")
@limiter.limit("10/minute")
async def upload_ohlcv(request: Request, ticker: str, file: UploadFile = File(...)):
    """
    Recebe histórico OHLCV (xlsx ou csv).
    Colunas mínimas: Date, Close.
    Colunas completas: Date, Open, High, Low, Close, Volume.
    """
    clean = ticker.upper().replace(".SA", "")
    try:
        df = _read_upload(file)
    except Exception as e:
        raise HTTPException(400, f"Erro ao ler arquivo: {e}")

    df.columns = [str(c).strip() for c in df.columns]

    # Normaliza nomes
    col_map = {
        "date": "Date", "DATA": "Date", "Fecha": "Date",
        "close": "Close", "CLOSE": "Close", "Fechamento": "Close",
        "open": "Open", "OPEN": "Open", "Abertura": "Open",
        "high": "High",  "HIGH": "High",  "Máxima": "High",
        "low": "Low",   "LOW": "Low",   "Mínima": "Low",
        "volume": "Volume", "VOLUME": "Volume", "Vol": "Volume",
    }
    df = df.rename(columns=col_map)

    missing = REQUIRED_OHLCV_COLS - set(df.columns)
    if missing:
        raise HTTPException(400, f"Colunas obrigatórias faltando: {missing}. Encontradas: {list(df.columns)}")

    df["Date"]  = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
    df = df.dropna(subset=["Date", "Close"]).sort_values("Date")

    if df.empty:
        raise HTTPException(400, "Arquivo sem dados válidos de data/preço.")

    path = _ohlcv_path(ticker)
    df.to_csv(path, index=False)
    logger.info("ohlcv_uploaded", ticker=clean, rows=len(df), path=path)

    return {
        "status": "success",
        "ticker": clean,
        "rows": len(df),
        "date_start": str(df["Date"].min().date()),
        "date_end":   str(df["Date"].max().date()),
        "path": path,
    }


@router.get("/upload/status/{ticker}")
@limiter.limit("30/minute")
async def upload_status(request: Request, ticker: str):
    clean = ticker.upper().replace(".SA", "")
    opts_path  = _options_path(ticker)
    ohlcv_path = _ohlcv_path(ticker)

    opts_info  = None
    ohlcv_info = None

    if os.path.exists(opts_path):
        df = pd.read_csv(opts_path)
        opts_info = {"rows": len(df), "file": opts_path}

    if os.path.exists(ohlcv_path):
        df = pd.read_csv(ohlcv_path)
        ohlcv_info = {
            "rows": len(df),
            "date_start": df["Date"].iloc[0] if "Date" in df else None,
            "date_end":   df["Date"].iloc[-1] if "Date" in df else None,
            "file": ohlcv_path,
        }

    return {
        "ticker": clean,
        "options_chain": opts_info,
        "ohlcv_history": ohlcv_info,
        "ready_for_analysis": opts_info is not None and ohlcv_info is not None,
    }


@router.delete("/upload/{upload_type}/{ticker}")
@limiter.limit("10/minute")
async def delete_upload(request: Request, upload_type: str, ticker: str):
    if upload_type == "options":
        path = _options_path(ticker)
    elif upload_type == "ohlcv":
        path = _ohlcv_path(ticker)
    else:
        raise HTTPException(400, "Tipo inválido. Use 'options' ou 'ohlcv'")

    if os.path.exists(path):
        os.remove(path)
        return {"status": "deleted", "path": path}
    return {"status": "not_found", "path": path}
