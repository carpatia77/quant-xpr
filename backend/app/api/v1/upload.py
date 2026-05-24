"""
upload.py
---------
Endpoints para upload manual de dados de mercado.

POST /v1/upload/options/{ticker}   -> grade de opcoes (xlsx/csv exportado da B3)
POST /v1/upload/ohlcv/{ticker}     -> historico OHLCV (xlsx/csv)
GET  /v1/upload/status/{ticker}    -> verifica quais arquivos existem
DELETE /v1/upload/{type}/{ticker}  -> remove arquivo

Formato B3 aceito:
  - Linha 0: titulo (ignorado)
  - Linha 1: cabecalhos com possivel \xa0 (non-breaking space)
  - Linha 2+: dados com valores inteiros codificados:
      Strike: int / 100   (ex: 4319 -> 43.19)
      Vol. Impl. (%): int / 1000  (ex: 351 -> 0.351)
      Delta: int / 10000  (ex: 6757 -> 0.6757)
      Dist. (%): int / 100  (ex: -290 -> -2.90)
      Ultimo: int / 100   (ex: 267 -> 2.67)
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


def _options_path(ticker: str) -> str:
    clean = ticker.upper().replace(".SA", "")
    return os.path.join(UPLOAD_DIR, f"{clean}_options.csv")


def _ohlcv_path(ticker: str) -> str:
    clean = ticker.upper().replace(".SA", "")
    return os.path.join(UPLOAD_DIR, f"{clean}_ohlcv.csv")


def _clean_col(c) -> str:
    """Remove non-breaking spaces e espacos extras dos nomes de coluna."""
    return str(c).strip().replace('\xa0', '').replace('\u00a0', '')


def _parse_options_b3(content: bytes, filename: str) -> pd.DataFrame:
    """
    Parser dedicado ao formato de exportacao B3.
    Detecta automaticamente se o cabecalho esta na linha 0 ou 1.
    Normaliza valores inteiros codificados para decimais reais.
    """
    if filename.endswith('.csv'):
        raw = pd.read_csv(io.BytesIO(content), header=None)
    else:
        raw = pd.read_excel(io.BytesIO(content), header=None)

    if raw.shape[0] < 2:
        raise ValueError("Arquivo sem dados suficientes")

    # Detecta linha do cabecalho: procura a linha que contem 'Ticker' ou 'Strike'
    header_row = 0
    for i in range(min(3, len(raw))):
        row_vals = [_clean_col(v) for v in raw.iloc[i].tolist()]
        if any(v in ('Ticker', 'Strike', 'Tipo', 'TYPE') for v in row_vals):
            header_row = i
            break

    # Monta DataFrame com cabecalho correto
    headers = [_clean_col(v) for v in raw.iloc[header_row].tolist()]
    df = raw.iloc[header_row + 1:].copy()
    df.columns = headers
    df = df.reset_index(drop=True)

    # Remove linhas completamente vazias
    df = df.dropna(how='all')

    # ---- Mapeamento de colunas B3 -> padrao interno ----
    col_map = {
        # Ticker
        'Ticker': 'ticker',
        # Tipo
        'Tipo': 'type',
        # Strike (B3 exporta sem decimal: 4319 = 43.19)
        'Strike': '_strike_raw',
        # Moneyness
        'A/I/OTM': 'moneyness',
        # Distancia do strike (B3: -290 = -2.90%)
        'Dist. (%) do Strike': '_dist_raw',
        # Volatilidade implicita (B3: 351 = 35.1% = 0.351 em decimal)
        'Vol. Impl. (%)': '_iv_raw',
        # Ultimo preco (B3: 267 = 2.67)
        'Ultimo': '_last_raw',
        'Ultimo': '_last_raw',
        # Greeks (B3 multiplica por 10000)
        'Delta':    '_delta_raw',
        'Gamma':    '_gamma_raw',
        'Theta ($)':'_theta_brl_raw',
        'Theta (%)':'_theta_pct_raw',
        'Vega':     '_vega_raw',
        # Data
        'Data/Hora': 'expiry_date',
        # Ja no padrao correto (se vier de template interno)
        'ticker':      'ticker',
        'type':        'type',
        'strike':      'strike',
        'iv':          'iv',
        'delta':       'delta',
        'gamma':       'gamma',
        'theta_brl':   'theta_brl',
        'theta_pct':   'theta_pct',
        'vega':        'vega',
        'last_price':  'last_price',
        'dist_pct':    'dist_pct',
        'expiry_date': 'expiry_date',
    }

    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # ---- Normaliza valores B3 inteiros -> decimais reais ----
    def to_num(series):
        return pd.to_numeric(series, errors='coerce')

    # Strike: verifica se precisa dividir (se medio > 1000, esta em centesimos)
    if '_strike_raw' in df.columns:
        raw_s = to_num(df['_strike_raw'])
        df['strike'] = raw_s / 100 if raw_s.dropna().mean() > 500 else raw_s

    # IV: se medio > 2, esta em decimos de porcento (351 = 35.1% = 0.351)
    if '_iv_raw' in df.columns:
        raw_iv = to_num(df['_iv_raw'])
        mean_iv = raw_iv.dropna().mean()
        if mean_iv > 100:
            df['iv'] = raw_iv / 1000   # 351 -> 0.351
        elif mean_iv > 2:
            df['iv'] = raw_iv / 100    # 35.1 -> 0.351
        else:
            df['iv'] = raw_iv          # ja em decimal

    # Delta (B3: 6757 -> 0.6757)
    if '_delta_raw' in df.columns:
        raw_d = to_num(df['_delta_raw'])
        df['delta'] = raw_d / 10000 if raw_d.dropna().abs().mean() > 2 else raw_d

    # Gamma
    if '_gamma_raw' in df.columns:
        raw_g = to_num(df['_gamma_raw'])
        df['gamma'] = raw_g / 10000 if raw_g.dropna().mean() > 0.5 else raw_g

    # Theta BRL
    if '_theta_brl_raw' in df.columns:
        raw_t = to_num(df['_theta_brl_raw'])
        df['theta_brl'] = raw_t / 10000 if raw_t.dropna().abs().mean() > 1 else raw_t

    # Theta %
    if '_theta_pct_raw' in df.columns:
        raw_tp = to_num(df['_theta_pct_raw'])
        df['theta_pct'] = raw_tp / 10000 if raw_tp.dropna().abs().mean() > 1 else raw_tp

    # Vega
    if '_vega_raw' in df.columns:
        raw_v = to_num(df['_vega_raw'])
        df['vega'] = raw_v / 10000 if raw_v.dropna().mean() > 10 else raw_v

    # Ultimo preco
    if '_last_raw' in df.columns:
        raw_l = to_num(df['_last_raw'])
        df['last_price'] = raw_l / 100 if raw_l.dropna().mean() > 20 else raw_l

    # Dist %
    if '_dist_raw' in df.columns:
        raw_dist = to_num(df['_dist_raw'])
        df['dist_pct'] = raw_dist / 100 if raw_dist.dropna().abs().mean() > 5 else raw_dist

    # Expiry: normaliza data
    if 'expiry_date' in df.columns:
        df['expiry_date'] = pd.to_datetime(
            df['expiry_date'], dayfirst=True, errors='coerce'
        ).dt.strftime('%Y-%m-%d')

    # Normaliza ticker e type
    if 'ticker' in df.columns:
        df['ticker'] = df['ticker'].astype(str).str.strip()
    if 'type' in df.columns:
        df['type'] = df['type'].astype(str).str.strip().str.upper()

    # Remove colunas temporarias _raw
    drop_cols = [c for c in df.columns if c.startswith('_')]
    df = df.drop(columns=drop_cols, errors='ignore')

    # Mantem apenas colunas uteis
    keep = ['ticker','type','strike','iv','delta','gamma',
            'theta_brl','theta_pct','vega','last_price','dist_pct','moneyness','expiry_date']
    df = df[[c for c in keep if c in df.columns]]
    df = df.dropna(subset=['strike', 'iv'])

    return df


@router.post("/upload/options/{ticker}")
@limiter.limit("10/minute")
async def upload_options(request: Request, ticker: str, file: UploadFile = File(...)):
    """
    Recebe grade de opcoes exportada da B3 ou template interno.
    Aceita .xlsx e .csv. Detecta formato automaticamente.
    """
    clean = ticker.upper().replace(".SA", "")
    content = await file.read()

    try:
        df = _parse_options_b3(content, file.filename)
    except Exception as e:
        logger.error("options_parse_error", ticker=clean, error=str(e))
        raise HTTPException(400, f"Erro ao processar arquivo: {e}")

    # Filtra pelo ticker se a coluna existir e o arquivo tiver multiplos tickers
    if 'ticker' in df.columns:
        mask = df['ticker'].astype(str).str.upper().str.startswith(clean[:4])
        filtered = df[mask]
        # So filtra se encontrar algo; caso contrario usa tudo
        if not filtered.empty:
            df = filtered

    if df.empty:
        raise HTTPException(400, f"Nenhum dado encontrado para {clean} no arquivo enviado.")

    path = _options_path(ticker)
    df.to_csv(path, index=False)
    logger.info("options_uploaded", ticker=clean, rows=len(df), path=path)

    calls = int((df['type'].str.upper() == 'CALL').sum()) if 'type' in df.columns else None
    puts  = int((df['type'].str.upper() == 'PUT').sum())  if 'type' in df.columns else None

    return {
        "status": "success",
        "ticker": clean,
        "rows": len(df),
        "contracts_call": calls,
        "contracts_put": puts,
        "iv_sample": round(float(df['iv'].mean()), 4) if 'iv' in df.columns else None,
        "strike_range": [round(float(df['strike'].min()), 2), round(float(df['strike'].max()), 2)] if 'strike' in df.columns else None,
    }


@router.post("/upload/ohlcv/{ticker}")
@limiter.limit("10/minute")
async def upload_ohlcv(request: Request, ticker: str, file: UploadFile = File(...)):
    """
    Recebe historico OHLCV. Colunas minimas: Date, Close.
    """
    clean = ticker.upper().replace(".SA", "")
    content = await file.read()
    name = file.filename.lower()

    try:
        if name.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(400, f"Erro ao ler arquivo: {e}")

    df.columns = [_clean_col(c) for c in df.columns]

    # Normaliza nomes
    col_map = {
        'date': 'Date', 'DATA': 'Date', 'data': 'Date',
        'close': 'Close', 'CLOSE': 'Close', 'fechamento': 'Close', 'Fechamento': 'Close',
        'open': 'Open', 'abertura': 'Open',
        'high': 'High', 'maxima': 'High', 'Maxima': 'High',
        'low': 'Low', 'minima': 'Low', 'Minima': 'Low',
        'volume': 'Volume', 'Volume': 'Volume',
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    if 'Date' not in df.columns or 'Close' not in df.columns:
        raise HTTPException(400, f"Colunas obrigatorias faltando. Necessario: Date, Close. Encontrado: {list(df.columns)}")

    df['Date']  = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
    df = df.dropna(subset=['Date', 'Close']).sort_values('Date')

    if df.empty:
        raise HTTPException(400, "Arquivo sem dados validos de data/preco.")

    path = _ohlcv_path(ticker)
    df.to_csv(path, index=False)
    logger.info("ohlcv_uploaded", ticker=clean, rows=len(df), path=path)

    return {
        "status": "success",
        "ticker": clean,
        "rows": len(df),
        "date_start": str(df['Date'].min().date()),
        "date_end":   str(df['Date'].max().date()),
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
        opts_info = {
            "rows": len(df),
            "file": opts_path,
            "iv_atm_sample": round(float(df['iv'].mean()), 4) if 'iv' in df.columns else None,
        }
    if os.path.exists(ohlcv_path):
        df = pd.read_csv(ohlcv_path)
        ohlcv_info = {
            "rows": len(df),
            "date_start": str(df['Date'].iloc[0])[:10] if 'Date' in df else None,
            "date_end":   str(df['Date'].iloc[-1])[:10] if 'Date' in df else None,
        }

    return {
        "ticker": clean,
        "options_chain": opts_info,
        "ohlcv_history": ohlcv_info,
        "ready_for_analysis": opts_info is not None,  # OHLCV eh opcional se Brapi funcionar
    }


@router.delete("/upload/{upload_type}/{ticker}")
@limiter.limit("10/minute")
async def delete_upload(request: Request, upload_type: str, ticker: str):
    if upload_type == 'options':
        path = _options_path(ticker)
    elif upload_type == 'ohlcv':
        path = _ohlcv_path(ticker)
    else:
        raise HTTPException(400, "Tipo invalido. Use 'options' ou 'ohlcv'")
    if os.path.exists(path):
        os.remove(path)
        return {"status": "deleted", "path": path}
    return {"status": "not_found", "path": path}
