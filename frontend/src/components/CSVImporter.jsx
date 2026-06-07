import { useState, useRef } from 'react'
import { Upload, Download, CheckCircle, XCircle, Loader } from 'lucide-react'

export default function CSVImporter({ onComplete }) {
  const [file, setFile] = useState(null)
  const [rows, setRows] = useState([])
  const [importing, setImporting] = useState(false)
  const [progress, setProgress] = useState([])
  const [done, setDone] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const fileRef = useRef()

  const downloadTemplate = () => {
    const csv = 'email,app_password\nseed1@gmail.com,xxxx-xxxx-xxxx-xxxx\nseed2@gmail.com,xxxx-xxxx-xxxx-xxxx\n'
    const blob = new Blob([csv], { type: 'text/csv' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'seeds_template.csv'
    a.click()
  }

  const parsePreview = (text) => {
    const lines = text.trim().split('\n').slice(1)
    return lines.map((l) => {
      const [email, pwd] = l.split(',').map((s) => s.trim())
      return { email, pwd }
    }).filter((r) => r.email)
  }

  const handleFile = (f) => {
    setFile(f)
    setDone(null)
    setProgress([])
    const reader = new FileReader()
    reader.onload = (e) => setRows(parsePreview(e.target.result))
    reader.readAsText(f)
  }

  const startImport = async () => {
    if (!file) return
    setImporting(true)
    setProgress([])
    setDone(null)
    const token = localStorage.getItem('token')
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('/api/seeds/import-csv-sse', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done: streamDone, value } = await reader.read()
        if (streamDone) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()
        for (const line of lines) {
          if (line.startsWith('data:')) {
            try {
              const msg = JSON.parse(line.slice(5).trim())
              if (msg.type === 'row_success') {
                setProgress((p) => [...p, { email: msg.email, status: 'success' }])
              } else if (msg.type === 'row_failed') {
                setProgress((p) => [...p, { email: msg.email, status: 'failed', error: msg.error }])
              } else if (msg.type === 'complete') {
                setDone(msg)
                if (onComplete) onComplete()
              }
            } catch {}
          }
        }
      }
    } catch (e) {
      setDone({ error: String(e) })
    }
    setImporting(false)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-text-primary font-medium text-sm">Import from CSV</h3>
        <button onClick={downloadTemplate} className="flex items-center gap-1 text-xs text-primary hover:text-primary/80 transition-colors">
          <Download size={12} /> Download Template
        </button>
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer.files[0]; if (f) handleFile(f) }}
        onClick={() => fileRef.current.click()}
        className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${dragOver ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'}`}
      >
        <Upload size={20} className="mx-auto text-text-muted mb-2" />
        <p className="text-text-muted text-sm">{file ? file.name : 'Drop CSV file here or click to browse'}</p>
        <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={(e) => { if (e.target.files[0]) handleFile(e.target.files[0]) }} />
      </div>

      {rows.length > 0 && !importing && !done && (
        <div>
          <p className="text-text-muted text-xs mb-2">{rows.length} accounts found</p>
          <div className="bg-bg border border-border rounded-md max-h-32 overflow-y-auto">
            {rows.map((r, i) => (
              <div key={i} className="flex items-center justify-between px-3 py-1.5 border-b border-border last:border-0">
                <span className="text-text-primary text-xs font-mono">{r.email}</span>
                <span className="text-text-muted text-xs">••••••</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {importing && (
        <div>
          <div className="flex items-center justify-between text-xs text-text-muted mb-2">
            <span>Testing accounts...</span>
            <span className="font-mono">{progress.length}/{rows.length}</span>
          </div>
          <div className="h-2 bg-border rounded-full overflow-hidden mb-3">
            <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${rows.length > 0 ? (progress.length / rows.length) * 100 : 0}%` }} />
          </div>
          <div className="bg-bg border border-border rounded-md max-h-40 overflow-y-auto">
            {progress.map((p, i) => (
              <div key={i} className="flex items-center gap-2 px-3 py-1.5 border-b border-border last:border-0">
                {p.status === 'success'
                  ? <CheckCircle size={12} className="text-success shrink-0" />
                  : <XCircle size={12} className="text-danger shrink-0" />}
                <span className="text-text-primary text-xs font-mono flex-1 truncate">{p.email}</span>
                {p.error && <span className="text-danger text-xs truncate max-w-32">{p.error}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {done && (
        <div className="bg-success/10 border border-success/20 rounded-md p-3">
          <p className="text-success text-sm font-medium">Import complete</p>
          <p className="text-text-muted text-xs mt-1">
            {done.imported} imported, {done.failed} failed out of {done.total_rows} rows
          </p>
        </div>
      )}

      {!done && (
        <button onClick={startImport} disabled={!file || importing || rows.length === 0}
          className="w-full bg-primary hover:bg-primary/80 disabled:opacity-40 text-white py-2 rounded-md text-sm font-medium transition-colors flex items-center justify-center gap-2">
          {importing ? <><Loader size={14} className="animate-spin" /> Importing {progress.length}/{rows.length}...</> : `Import ${rows.length} Accounts`}
        </button>
      )}
    </div>
  )
}
