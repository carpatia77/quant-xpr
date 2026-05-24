import { useState, useRef, useEffect } from 'react'

interface UploadStatus {
  options_chain: { rows: number; iv_atm_sample?: number } | null
  ohlcv_history: { rows: number; date_start: string; date_end: string } | null
  ready_for_analysis: boolean
}

interface Props {
  apiBase: string
  apiKey: string
}

const TICKERS = ['PETR4', 'VALE3', 'ITUB4', 'BBDC4', 'BBAS3', 'B3SA3', 'ABEV3', 'WEGE3']

export default function DataSources({ apiBase, apiKey }: Props) {
  const [activeTicker, setActiveTicker] = useState('PETR4')
  const [status, setStatus] = useState<Record<string, UploadStatus>>({})
  const [uploading, setUploading] = useState<Record<string, boolean>>({})
  const [feedback, setFeedback] = useState<Record<string, string>>({})
  const [brapiKey, setBrapiKey] = useState(() => localStorage.getItem('brapi_token') || '')
  const [hgKey, setHgKey]       = useState(() => localStorage.getItem('hg_key') || '')
  const [keySaved, setKeySaved] = useState(false)

  const optionsRef = useRef<HTMLInputElement>(null)
  const ohlcvRef   = useRef<HTMLInputElement>(null)

  const headers = { 
    'X-API-Key': apiKey,
    ...(brapiKey && { 'X-Brapi-Token': brapiKey }),
    ...(hgKey && { 'X-HG-Token': hgKey })
  }

  // Usa ticker sem .SA nas rotas de upload para evitar problema de path param
  const cleanTicker = (t: string) => t.replace('.SA', '').replace('.sa', '')

  const fetchStatus = async (ticker: string) => {
    const t = cleanTicker(ticker)
    try {
      const res = await fetch(`${apiBase}/v1/upload/status/${t}`, { headers })
      if (res.ok) {
        const json = await res.json()
        setStatus(prev => ({ ...prev, [t]: json }))
      }
    } catch {}
  }

  useEffect(() => {
    TICKERS.forEach(t => fetchStatus(t))
  }, [])

  useEffect(() => {
    fetchStatus(activeTicker)
  }, [activeTicker])

  const handleUpload = async (type: 'options' | 'ohlcv', file: File) => {
    const t   = cleanTicker(activeTicker)
    const key = `${t}_${type}`
    setUploading(prev => ({ ...prev, [key]: true }))
    setFeedback(prev => ({ ...prev, [key]: '' }))

    const form = new FormData()
    form.append('file', file)

    try {
      const res = await fetch(`${apiBase}/v1/upload/${type}/${t}`, {
        method: 'POST',
        headers,   // sem Content-Type: browser define boundary automaticamente
        body: form,
      })
      const json = await res.json()
      if (res.ok) {
        const detail = type === 'options'
          ? `✓ ${json.rows} contratos | CALL ${json.contracts_call} PUT ${json.contracts_put} | IV med ${(json.iv_atm_sample * 100).toFixed(1)}%`
          : `✓ ${json.rows} pregões (${json.date_start} → ${json.date_end})`
        setFeedback(prev => ({ ...prev, [key]: detail }))
        await fetchStatus(t)
      } else {
        setFeedback(prev => ({ ...prev, [key]: `✗ ${json.detail || JSON.stringify(json)}` }))
      }
    } catch (e: any) {
      setFeedback(prev => ({ ...prev, [key]: `✗ ${e.message}` }))
    }
    setUploading(prev => ({ ...prev, [key]: false }))
  }

  const handleDelete = async (type: 'options' | 'ohlcv') => {
    const t = cleanTicker(activeTicker)
    await fetch(`${apiBase}/v1/upload/${type}/${t}`, { method: 'DELETE', headers })
    await fetchStatus(t)
    const key = `${t}_${type}`
    setFeedback(prev => ({ ...prev, [key]: '' }))
  }

  const t  = cleanTicker(activeTicker)
  const s  = status[t]
  const ok = `${t}_options`
  const ok2= `${t}_ohlcv`

  return (
    <div className="h-full flex flex-col gap-4 overflow-y-auto pr-1 text-xs">

      {/* Ticker selector */}
      <div>
        <p className="text-muted-foreground tracking-widest mb-2 font-bold">SELECIONAR ATIVO</p>
        <div className="flex flex-wrap gap-1">
          {TICKERS.map(tk => {
            const st = status[tk]
            const ready = st?.ready_for_analysis
            return (
              <button
                key={tk}
                onClick={() => setActiveTicker(tk)}
                className={`px-2 py-1 border font-bold tracking-widest transition-colors ${
                  activeTicker === tk
                    ? 'bg-accent text-background border-accent'
                    : 'bg-panel border-border text-muted-foreground hover:border-accent hover:text-accent'
                }`}
              >
                {tk}
                <span className={`ml-1 ${ready ? 'text-bull' : 'text-bear'}`}>
                  {ready ? '●' : '○'}
                </span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Status */}
      <div className="bg-background border border-border p-3">
        <p className="text-muted-foreground tracking-widest font-bold mb-2">STATUS — {t}</p>
        <div className="grid grid-cols-2 gap-2">
          <StatusCard
            label="Grade de Opções"
            info={s?.options_chain
              ? `${s.options_chain.rows} contratos${s.options_chain.iv_atm_sample ? ` | IV méd ${(s.options_chain.iv_atm_sample*100).toFixed(1)}%` : ''}`
              : null}
          />
          <StatusCard
            label="Histórico OHLCV"
            info={s?.ohlcv_history
              ? `${s.ohlcv_history.rows} pregões (${s.ohlcv_history.date_start?.slice(0,10)} → ${s.ohlcv_history.date_end?.slice(0,10)})`
              : null}
          />
        </div>
        {s?.ready_for_analysis && (
          <p className="mt-2 text-bull font-bold tracking-widest">✓ PRONTO PARA ANÁLISE</p>
        )}
      </div>

      {/* Upload Opcoes */}
      <UploadCard
        title="GRADE DE OPÇÕES (xlsx / csv)"
        description="Exportação direta do site B3 ou Inció. Formato automático detectado."
        inputRef={optionsRef}
        uploading={!!uploading[ok]}
        feedback={feedback[ok]}
        hasFile={!!s?.options_chain}
        onFileChange={f => handleUpload('options', f)}
        onDelete={() => handleDelete('options')}
      />

      {/* Upload OHLCV */}
      <UploadCard
        title="HISTÓRICO OHLCV (xlsx / csv)"
        description="Colunas mínimas: Date, Close. Completo: Date, Open, High, Low, Close, Volume."
        inputRef={ohlcvRef}
        uploading={!!uploading[ok2]}
        feedback={feedback[ok2]}
        hasFile={!!s?.ohlcv_history}
        onFileChange={f => handleUpload('ohlcv', f)}
        onDelete={() => handleDelete('ohlcv')}
      />

      {/* API Keys */}
      <div className="bg-background border border-border p-3">
        <p className="text-muted-foreground tracking-widest font-bold mb-3">API KEYS</p>
        <div className="flex flex-col gap-2">
          <ApiKeyRow label="Brapi Token" value={brapiKey} onChange={setBrapiKey} placeholder="Token brapi.dev (opcional)" />
          <ApiKeyRow label="HG Brasil"   value={hgKey}    onChange={setHgKey}    placeholder="Chave HG Brasil" />
        </div>
        <div className="flex items-center gap-3 mt-3">
          <button
            onClick={() => {
              localStorage.setItem('brapi_token', brapiKey)
              localStorage.setItem('hg_key', hgKey)
              setKeySaved(true)
              setTimeout(() => setKeySaved(false), 2500)
            }}
            className="px-3 py-1 bg-accent text-background font-bold tracking-widest hover:bg-accent/80"
          >
            SALVAR
          </button>
          {keySaved && <span className="text-bull font-bold animate-pulse">✓ SALVO</span>}
          <span className="text-muted-foreground">* salvas localmente neste browser</span>
        </div>
      </div>

    </div>
  )
}

function StatusCard({ label, info }: { label: string; info: string | null }) {
  return (
    <div className={`border p-2 ${info ? 'border-bull/40 bg-bull/5' : 'border-border'}`}>
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
          <button onClick={onDelete} className="text-bear hover:text-bear/70 font-bold tracking-widest">
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
      <div className="flex items-center gap-3 flex-wrap">
        <button
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
          className="px-4 py-1.5 bg-panel border border-accent text-accent font-bold tracking-widest hover:bg-accent hover:text-background transition-colors disabled:opacity-50"
        >
          {uploading ? 'ENVIANDO...' : hasFile ? '↺ SUBSTITUIR' : '↑ UPLOAD'}
        </button>
        {feedback && (
          <span className={`font-bold ${feedback.startsWith('✓') ? 'text-bull' : 'text-bear'}`}>
            {feedback}
          </span>
        )}
      </div>
    </div>
  )
}

function ApiKeyRow({ label, value, onChange, placeholder }: {
  label: string; value: string; onChange: (v: string) => void; placeholder: string
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
      <button onClick={() => setShow(s => !s)} className="text-muted-foreground hover:text-accent px-1">
        {show ? '🙈' : '👁'}
      </button>
    </div>
  )
}
