"""
upload.py
---------
Endpoints para upload manual de dados de mercado.

POST /v1/upload/options/{ticker}
POST /v1/upload/ohlcv/{ticker}
GET  /v1/upload/status/{ticker}
DELETE /v1/upload/{type}/{ticker}

Ticker aceito com ou sem .SA (ex: PETR4 ou PETR4.SA).

Formato B3 aceito (exportacao direta do site):
  - Linha 0: titulo (ignorado)
  - Linha 1: cabecalhos com \xa0 (non-breaking space)
  - Linha 2+: valores inteiros codificados:
      Strike       / 100    (ex: 4319   -> 43.19)
      Vol. Impl.   / 1000   (ex: 351    -> 0.351)
      Delta/Gamma  / 10000  (ex: 6757   -> 0.6757)
      Ultimo       / 100    (ex: 267    -> 2.67)
      Dist.(%)     / 100    (ex: -290   -> -2.90)
"""
import os
import io
import pandas as pd
from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Path
from app.core.rate_limit import limiter
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/tmp/quant_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


import re

def _clean_ticker(ticker: str) -> str:
    """Remove .SA e converte para maiúsculas, sanitizando path traversal"""
    raw = ticker.upper().replace(".SA", "")
    clean = re.sub(r'[^A-Z0-9.]', '', raw)
    return clean.strip()


def _options_path(ticker: str) -> str:
    clean = os.path.basename(_clean_ticker(ticker))
    return os.path.join(UPLOAD_DIR, f"{clean}_options.csv")


def _ohlcv_path(ticker: str) -> str:
    clean = os.path.basename(_clean_ticker(ticker))
    return os.path.join(UPLOAD_DIR, f"{clean}_ohlcv.csv")


def _clean_col(c) -> str:
    return str(c).strip().replace('\xa0', '').replace('\u00a0', '')


def _parse_options_b3(content: bytes, filename: str) -> pd.DataFrame:
    """
    Parser dedicado ao formato de exportacao B3.
    Detecta header_row automaticamente (linha que contem 'Ticker' ou 'Strike').
    Normaliza valores inteiros codificados para decimais reais.
    """
    fname = (filename or '').lower()
    if fname.endswith('.csv'):
        raw = pd.read_csv(io.BytesIO(content), header=None)
    else:
        raw = pd.read_excel(io.BytesIO(content), header=None)

    if raw.shape[0] < 2:
        raise ValueError("Arquivo sem dados suficientes (menos de 2 linhas)")

    # Detecta linha do cabecalho
    header_row = 0
    for i in range(min(4, len(raw))):
        row_vals = [_clean_col(v) for v in raw.iloc[i].tolist()]
        if any(v in ('Ticker', 'Strike', 'Tipo', 'TYPE', 'type') for v in row_vals):
            header_row = i
            break

    headers = [_clean_col(v) for v in raw.iloc[header_row].tolist()]
    df = raw.iloc[header_row + 1:].copy()
    df.columns = headers
    df = df.reset_index(drop=True).dropna(how='all')

    # Mapeamento B3 -> interno
    col_map = {
        'Ticker': 'ticker', 'TICKER': 'ticker',
        'Tipo':   'type',   'TIPO':   'type',
        'Strike': '_strike_raw',
        'A/I/OTM': 'moneyness',
        'Dist. (%) do Strike': '_dist_raw',
        'Vol. Impl. (%)': '_iv_raw',
        'Ultimo':    '_last_raw',
        'Delta':     '_delta_raw',
        'Gamma':     '_gamma_raw',
        'Theta ($)': '_theta_brl_raw',
        'Theta (%)': '_theta_pct_raw',
        'Vega':      '_vega_raw',
        'Data/Hora': 'expiry_date',
        # colunas ja normalizadas (template interno)
        'strike': 'strike', 'iv': 'iv', 'delta': 'delta',
        'gamma': 'gamma', 'theta_brl': 'theta_brl', 'theta_pct': 'theta_pct',
        'vega': 'vega', 'last_price': 'last_price', 'dist_pct': 'dist_pct',
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    def to_num(s): return pd.to_numeric(s, errors='coerce')
    def auto_div(s, threshold, divisor):
        n = to_num(s)
        return n / divisor if n.dropna().abs().mean() > threshold else n

    if '_strike_raw'    in df.columns: df['strike']    = auto_div(df['_strike_raw'],    500,  100)
    if '_iv_raw'        in df.columns:
        n = to_num(df['_iv_raw'])
        m = n.dropna().mean()
        df['iv'] = n/1000 if m > 100 else (n/100 if m > 2 else n)
    if '_delta_raw'     in df.columns: df['delta']     = auto_div(df['_delta_raw'],     2,    10000)
    if '_gamma_raw'     in df.columns: df['gamma']     = auto_div(df['_gamma_raw'],     0.5,  10000)
    if '_theta_brl_raw' in df.columns: df['theta_brl'] = auto_div(df['_theta_brl_raw'], 1,    10000)
    if '_theta_pct_raw' in df.columns: df['theta_pct'] = auto_div(df['_theta_pct_raw'], 1,    10000)
    if '_vega_raw'      in df.columns: df['vega']      = auto_div(df['_vega_raw'],      10,   10000)
    if '_last_raw'      in df.columns: df['last_price']= auto_div(df['_last_raw'],      20,   100)
    if '_dist_raw'      in df.columns: df['dist_pct']  = auto_div(df['_dist_raw'],      5,    100)

    if 'expiry_date' in df.columns:
        df['expiry_date'] = pd.to_datetime(
            df['expiry_date'], dayfirst=True, errors='coerce'
        ).dt.strftime('%Y-%m-%d')

    if 'ticker' in df.columns:
        df['ticker'] = df['ticker'].astype(str).str.strip()
    if 'type' in df.columns:
        df['type'] = df['type'].astype(str).str.strip().str.upper()

    df = df.drop(columns=[c for c in df.columns if c.startswith('_')], errors='ignore')

    keep = ['ticker','type','strike','iv','delta','gamma',
            'theta_brl','theta_pct','vega','last_price','dist_pct','moneyness','expiry_date']
    df = df[[c for c in keep if c in df.columns]]
    df = df.dropna(subset=['strike', 'iv'])
    return df


# ---- Endpoints -------------------------------------------------------

@router.post("/upload/options/{ticker:path}")
@limiter.limit("10/minute")
async def upload_options(
    request: Request,
    ticker: str = Path(...),
    file: UploadFile = File(...)
):
    clean = _clean_ticker(ticker)
    
    fname = (file.filename or '').lower()
    if not fname.endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(400, "Formato não suportado. Apenas .csv, .xlsx, .xls")

    content = await file.read()
    MAX_FILE_SIZE = 10 * 1024 * 1024 # 10MB
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, "Arquivo muito grande (limite 10MB)")
    try:
        df = _parse_options_b3(content, file.filename)
    except Exception as e:
        logger.error("options_parse_error", ticker=clean, error=str(e))
        raise HTTPException(400, f"Erro ao processar arquivo: {e}")

    if 'ticker' in df.columns:
        mask = df['ticker'].astype(str).str.upper().str.startswith(clean[:4])
        filtered = df[mask]
        if not filtered.empty:
            df = filtered

    if df.empty:
        raise HTTPException(400, f"Nenhum dado encontrado para {clean}.")

    df.to_csv(_options_path(ticker), index=False)
    logger.info("options_uploaded", ticker=clean, rows=len(df))

    return {
        "status": "success",
        "ticker": clean,
        "rows": len(df),
        "contracts_call": int((df['type'].str.upper()=='CALL').sum()) if 'type' in df.columns else None,
        "contracts_put":  int((df['type'].str.upper()=='PUT').sum())  if 'type' in df.columns else None,
        "iv_atm_sample":  round(float(df['iv'].mean()), 4) if 'iv' in df.columns else None,
        "strike_range":   [round(float(df['strike'].min()),2), round(float(df['strike'].max()),2)],
    }


@router.post("/upload/ohlcv/{ticker:path}")
@limiter.limit("10/minute")
async def upload_ohlcv(
    request: Request,
    ticker: str = Path(...),
    file: UploadFile = File(...)
):
    clean = _clean_ticker(ticker)
    
    fname = (file.filename or '').lower()
    if not fname.endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(400, "Formato não suportado. Apenas .csv, .xlsx, .xls")

    content = await file.read()
    MAX_FILE_SIZE = 10 * 1024 * 1024 # 10MB
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, "Arquivo muito grande (limite 10MB)")
    try:
        df = pd.read_csv(io.BytesIO(content)) if fname.endswith('.csv') \
             else pd.read_excel(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(400, f"Erro ao ler arquivo: {e}")

    df.columns = [_clean_col(c) for c in df.columns]
    col_map = {
        'date':'Date','data':'Date','DATA':'Date',
        'close':'Close','CLOSE':'Close','fechamento':'Close','Fechamento':'Close',
        'open':'Open','high':'High','low':'Low','volume':'Volume',
    }
    df = df.rename(columns={k:v for k,v in col_map.items() if k in df.columns})

    if 'Date' not in df.columns or 'Close' not in df.columns:
        raise HTTPException(400, f"Colunas Date e Close sao obrigatorias. Encontradas: {list(df.columns)}")

    df['Date']  = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    df = df.dropna(subset=['Date','Close']).sort_values('Date')

    if df.empty:
        raise HTTPException(400, "Arquivo sem dados validos.")

    df.to_csv(_ohlcv_path(ticker), index=False)
    logger.info("ohlcv_uploaded", ticker=clean, rows=len(df))

    return {
        "status": "success",
        "ticker": clean,
        "rows": len(df),
        "date_start": str(df['Date'].min().date()),
        "date_end":   str(df['Date'].max().date()),
    }


@router.get("/upload/status/{ticker:path}")
@limiter.limit("30/minute")
async def upload_status(request: Request, ticker: str = Path(...)):
    opts_path  = _options_path(ticker)
    ohlcv_path = _ohlcv_path(ticker)
    opts_info  = None
    ohlcv_info = None

    if os.path.exists(opts_path):
        d = pd.read_csv(opts_path)
        opts_info = {
            "rows": len(d),
            "iv_atm_sample": round(float(d['iv'].mean()), 4) if 'iv' in d.columns else None,
        }
    if os.path.exists(ohlcv_path):
        d = pd.read_csv(ohlcv_path)
        ohlcv_info = {
            "rows": len(d),
            "date_start": str(d['Date'].iloc[0])[:10]  if 'Date' in d.columns else None,
            "date_end":   str(d['Date'].iloc[-1])[:10] if 'Date' in d.columns else None,
        }

    return {
        "ticker": _clean_ticker(ticker),
        "options_chain": opts_info,
        "ohlcv_history": ohlcv_info,
        "ready_for_analysis": opts_info is not None,
    }


@router.delete("/upload/{upload_type}/{ticker:path}")
@limiter.limit("10/minute")
async def delete_upload(request: Request, upload_type: str, ticker: str = Path(...)):
    if upload_type == 'options':
        path = _options_path(ticker)
    elif upload_type == 'ohlcv':
        path = _ohlcv_path(ticker)
    else:
        raise HTTPException(400, "Tipo invalido. Use 'options' ou 'ohlcv'")
    if os.path.exists(path):
        os.remove(path)
        return {"status": "deleted"}
    return {"status": "not_found"}
