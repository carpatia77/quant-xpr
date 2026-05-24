import { useState, useRef, useEffect } from 'react'

interface UploadStatus {
  options_chain: { rows: number; file: string } | null
  ohlcv_history: { rows: number; date_start: string; date_end: string } | null
  ready_for_analysis: boolean
}

interface Props {
  apiBase: string
  apiKey: string
}

const TICKERS = ['PETR4.SA', 'VALE3.SA', 'ITUB4.SA', 'BBDC4.SA', 'BBAS3.SA', 'B3SA3.SA', 'ABEV3.SA', 'WEGE3.SA']

export default function DataSources({ apiBase, apiKey }: Props) {
  const [activeTicker, setActiveTicker] = useState('PETR4.SA')
  const [status, setStatus] = useState<Record<string, UploadStatus>>({})
  const [uploading, setUploading] = useState<Record<string, boolean>>({})
  const [feedback, setFeedback] = useState<Record<string, string>>({})
  const [brapiKey, setBrapiKey]   = useState(import.meta.env.VITE_BRAPI_TOKEN || '')
  const [hgKey, setHgKey]         = useState(import.meta.env.VITE_HG_KEY || '')
  const [keySaved, setKeySaved]   = useState(false)

  const optionsRef = useRef<HTMLInputElement>(null)
  const ohlcvRef   = useRef<HTMLInputElement>(null)

  const headers = { 'X-API-Key': apiKey }

  const fetchStatus = async (ticker: string) => {
    try {
      const res = await fetch(`${apiBase}/v1/upload/status/${ticker}`, { headers })
      if (res.ok) {
        const json = await res.json()
        setStatus(prev => ({ ...prev, [ticker]: json }))
      }
    } catch {}
  }

  useEffect(() => {
    TICKERS.forEach(fetchStatus)
  }, [])

  useEffect(() => {
    fetchStatus(activeTicker)
  }, [activeTicker])

  const handleUpload = async (type: 'options' | 'ohlcv', file: File) => {
    const key = `${activeTicker}_${type}`
    setUploading(prev => ({ ...prev, [key]: true }))
    setFeedback(prev => ({ ...prev, [key]: '' }))
    const form = new FormData()
    form.append('file', file)
    try {
      const res = await fetch(`${apiBase}/v1/upload/${type}/${activeTicker}`, {
        method: 'POST',
        headers,
        body: form,
      })
      const json = await res.json()
      if (res.ok) {
        setFeedback(prev => ({ ...prev, [key]: `✓ ${json.rows} linhas carregadas` }))
        await fetchStatus(activeTicker)
      } else {
        setFeedback(prev => ({ ...prev, [key]: `✗ ${json.detail || 'Erro no upload'}` }))
      }
    } catch (e: any) {
      setFeedback(prev => ({ ...prev, [key]: `✗ ${e.message}` }))
    }
    setUploading(prev => ({ ...prev, [key]: false }))
  }

  const handleDelete = async (type: 'options' | 'ohlcv') => {
    await fetch(`${apiBase}/v1/upload/${type}/${activeTicker}`, { method: 'DELETE', headers })
    await fetchStatus(activeTicker)
  }

  const s = status[activeTicker]
  const optKey  = `${activeTicker}_options`
  const ohlcvKey = `${activeTicker}_ohlcv`

  return (
    <div className="h-full flex flex-col gap-4 overflow-y-auto pr-1 text-xs">

      {/* Ticker selector */}
      <div>
        <p className="text-muted-foreground tracking-widest mb-2 font-bold">SELECIONAR ATIVO</p>
        <div className="flex flex-wrap gap-1">
          {TICKERS.map(t => {
            const st = status[t]
            const ready = st?.ready_for_analysis
            return (
              <button
                key={t}
                onClick={() => setActiveTicker(t)}
                className={`px-2 py-1 border font-bold tracking-widest transition-colors ${
                  activeTicker === t
                    ? 'bg-accent text-background border-accent'
                    : 'bg-panel border-border text-muted-foreground hover:border-accent hover:text-accent'
                }`}
              >
                {t.replace('.SA', '')}
                <span className={`ml-1 ${ ready ? 'text-bull' : 'text-bear' }`}>
                  {ready ? '●' : '○'}
                </span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Status atual */}
      <div className="bg-background border border-border p-3">
        <p className="text-muted-foreground tracking-widest font-bold mb-2">STATUS — {activeTicker}</p>
        <div className="grid grid-cols-2 gap-2">
          <StatusCard
            label="Grade de Opções"
            info={s?.options_chain ? `${s.options_chain.rows} contratos carregados` : null}
          />
          <StatusCard
            label="Histórico OHLCV"
            info={s?.ohlcv_history ? `${s.ohlcv_history.rows} pregões (${s.ohlcv_history.date_start?.slice(0,10)} → ${s.ohlcv_history.date_end?.slice(0,10)})` : null}
          />
        </div>
        {s?.ready_for_analysis && (
          <p className="mt-2 text-bull font-bold tracking-widest animate-pulse">✓ PRONTO PARA ANÁLISE</p>
        )}
      </div>

      {/* Upload opções */}
      <UploadCard
        title="GRADE DE OPÇÕES (xlsx / csv)"
        description="Template: PETR4_VALE3_opcoes_grade.xlsx · Colunas: ticker, type, strike, iv, delta, expiry_date"
        inputRef={optionsRef}
        uploading={!!uploading[optKey]}
        feedback={feedback[optKey]}
        hasFile={!!s?.options_chain}
        onFileChange={f => handleUpload('options', f)}
        onDelete={() => handleDelete('options')}
      />

      {/* Upload OHLCV */}
      <UploadCard
        title="HISTÓRICO OHLCV (xlsx / csv)"
        description="Colunas mínimas: Date, Close · Completo: Date, Open, High, Low, Close, Volume"
        inputRef={ohlcvRef}
        uploading={!!uploading[ohlcvKey]}
        feedback={feedback[ohlcvKey]}
        hasFile={!!s?.ohlcv_history}
        onFileChange={f => handleUpload('ohlcv', f)}
        onDelete={() => handleDelete('ohlcv')}
      />

      {/* API Keys */}
      <div className="bg-background border border-border p-3">
        <p className="text-muted-foreground tracking-widest font-bold mb-3">API KEYS — configurar quando disponível</p>
        <div className="flex flex-col gap-2">
          <ApiKeyRow
            label="Brapi Token"
            value={brapiKey}
            onChange={setBrapiKey}
            placeholder="Token brapi.dev (opcional)"
          />
          <ApiKeyRow
            label="HG Brasil Key"
            value={hgKey}
            onChange={setHgKey}
            placeholder="Chave HG Brasil (display/ticker tape)"
          />
        </div>
        <div className="flex items-center gap-3 mt-3">
          <button
            onClick={() => {
              // Salva no localStorage para persistir entre sessões
              localStorage.setItem('brapi_token', brapiKey)
              localStorage.setItem('hg_key', hgKey)
              setKeySaved(true)
              setTimeout(() => setKeySaved(false), 2500)
            }}
            className="px-3 py-1 bg-accent text-background font-bold tracking-widest hover:bg-accent/80 transition-colors"
          >
            SALVAR
          </button>
          {keySaved && <span className="text-bull font-bold tracking-widest animate-pulse">✓ SALVO</span>}
          <span className="text-muted-foreground">* As chaves são salvas localmente neste browser</span>
        </div>
      </div>

    </div>
  )
}

// ── Sub-componentes ────────────────────────────────────────────────────────

function StatusCard({ label, info }: { label: string; info: string | null }) {
  return (
    <div className={`border p-2 ${ info ? 'border-bull/40 bg-bull/5' : 'border-border' }`}>
      <p className="text-muted-foreground tracking-widest mb-1">{label}</p>
      {info
        ? <p className="text-bull font-bold">{info}</p>
        : <p className="text-bear">Nenhum arquivo carregado</p>
      }
    </div>
  )
}

function UploadCard({
  title, description, inputRef, uploading, feedback, hasFile, onFileChange, onDelete
}: {
  title: string
  description: string
  inputRef: React.RefObject<HTMLInputElement>
  uploading: boolean
  feedback?: string
  hasFile: boolean
  onFileChange: (f: File) => void
  onDelete: () => void
}) {
  return (
    <div className="bg-background border border-border p-3">
      <div className="flex items-center justify-between mb-1">
        <p className="text-muted-foreground tracking-widest font-bold">{title}</p>
        {hasFile && (
          <button
            onClick={onDelete}
            className="text-bear hover:text-bear/70 font-bold tracking-widest transition-colors"
          >
            ✕ REMOVER
          </button>
        )}
      </div>
      <p className="text-muted-foreground mb-2 leading-relaxed">{description}</p>
      <input
        ref={inputRef}
        type="file"
        accept=".xlsx,.xls,.csv"
        className="hidden"
        onChange={e => {
          const f = e.target.files?.[0]
          if (f) { onFileChange(f); e.target.value = '' }
        }}
      />
      <div className="flex items-center gap-3">
        <button
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
          className="px-4 py-1.5 bg-panel border border-accent text-accent font-bold tracking-widest hover:bg-accent hover:text-background transition-colors disabled:opacity-50"
        >
          {uploading ? 'ENVIANDO...' : hasFile ? '↺ SUBSTITUIR' : '↑ UPLOAD'}
        </button>
        {feedback && (
          <span className={feedback.startsWith('✓') ? 'text-bull font-bold' : 'text-bear font-bold'}>
            {feedback}
          </span>
        )}
      </div>
    </div>
  )
}

function ApiKeyRow({
  label, value, onChange, placeholder
}: {
  label: string
  value: string
  onChange: (v: string) => void
  placeholder: string
}) {
  const [show, setShow] = useState(false)
  return (
    <div className="flex items-center gap-2">
      <span className="text-muted-foreground w-28 shrink-0 tracking-widest">{label}</span>
      <input
        type={show ? 'text' : 'password'}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="flex-1 bg-panel border border-border px-2 py-1 text-foreground focus:outline-none focus:border-accent font-mono"
      />
      <button
        onClick={() => setShow(s => !s)}
        className="text-muted-foreground hover:text-accent px-1"
      >{show ? '🙈' : '👁'}</button>
    </div>
  )
}
