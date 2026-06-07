import { useState, useEffect } from 'react'
import { Download, ChevronDown, ChevronRight } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import api from '../api/client'

const LEVEL_COLORS = {
  info: 'text-primary bg-primary/10 border-primary/20',
  success: 'text-success bg-success/10 border-success/20',
  warning: 'text-warning bg-warning/10 border-warning/20',
  error: 'text-danger bg-danger/10 border-danger/20',
}

export default function Logs() {
  const [logs, setLogs] = useState([])
  const [mailboxes, setMailboxes] = useState([])
  const [filters, setFilters] = useState({ mailbox_id: '', level: '', search: '' })
  const [page, setPage] = useState(0)
  const [expanded, setExpanded] = useState({})
  const [loading, setLoading] = useState(true)
  const PER_PAGE = 50

  const load = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ limit: PER_PAGE, offset: page * PER_PAGE })
      if (filters.mailbox_id) params.set('mailbox_id', filters.mailbox_id)
      if (filters.level) params.set('level', filters.level)
      if (filters.search) params.set('search', filters.search)
      const res = await api.get(`/logs?${params}`)
      setLogs(res.data)
    } catch {}
    setLoading(false)
  }

  useEffect(() => {
    api.get('/mailboxes').then(r => setMailboxes(r.data)).catch(() => {})
  }, [])

  useEffect(() => { load() }, [filters, page])

  const exportCsv = () => {
    const params = new URLSearchParams()
    if (filters.mailbox_id) params.set('mailbox_id', filters.mailbox_id)
    if (filters.level) params.set('level', filters.level)
    const token = localStorage.getItem('token')
    window.open(`/api/logs/export?${params}&token=${token}`)
  }

  const setFilter = (k, v) => { setFilters(f => ({ ...f, [k]: v })); setPage(0) }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-text-primary font-bold text-xl">Activity Logs</h1>
        <button onClick={exportCsv} className="flex items-center gap-2 border border-border hover:border-primary text-text-primary px-3 py-1.5 rounded-md text-sm transition-colors">
          <Download size={14} /> Export CSV
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        <select value={filters.mailbox_id} onChange={(e) => setFilter('mailbox_id', e.target.value)}
          className="bg-surface border border-border rounded-md px-3 py-1.5 text-text-primary text-sm focus:outline-none focus:border-primary">
          <option value="">All Mailboxes</option>
          {mailboxes.map((m) => <option key={m.id} value={m.id}>{m.email}</option>)}
        </select>
        <select value={filters.level} onChange={(e) => setFilter('level', e.target.value)}
          className="bg-surface border border-border rounded-md px-3 py-1.5 text-text-primary text-sm focus:outline-none focus:border-primary">
          <option value="">All Levels</option>
          {['info', 'success', 'warning', 'error'].map((l) => <option key={l} value={l}>{l}</option>)}
        </select>
        <input value={filters.search} onChange={(e) => setFilter('search', e.target.value)}
          placeholder="Search messages..."
          className="bg-surface border border-border rounded-md px-3 py-1.5 text-text-primary text-sm focus:outline-none focus:border-primary flex-1 min-w-40" />
      </div>

      <div className="bg-surface border border-border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              {['', 'Timestamp', 'Level', 'Mailbox', 'Action', 'Message'].map((h) => (
                <th key={h} className="px-4 py-2 text-left text-text-muted text-xs font-medium">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={6} className="px-4 py-6 text-center text-text-muted text-sm">Loading...</td></tr>
            )}
            {!loading && logs.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-6 text-center text-text-muted text-sm">No logs found</td></tr>
            )}
            {logs.map((log) => (
              <>
                <tr key={log.id} className="border-b border-border last:border-0 hover:bg-white/5 cursor-pointer" onClick={() => setExpanded(e => ({ ...e, [log.id]: !e[log.id] }))}>
                  <td className="px-3 py-2.5 text-text-muted">
                    {log.details ? (expanded[log.id] ? <ChevronDown size={12} /> : <ChevronRight size={12} />) : null}
                  </td>
                  <td className="px-4 py-2.5 text-text-muted font-mono text-xs whitespace-nowrap">
                    {formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}
                  </td>
                  <td className="px-4 py-2.5">
                    <span className={`text-xs font-mono border rounded px-1.5 py-0.5 uppercase ${LEVEL_COLORS[log.level] || LEVEL_COLORS.info}`}>
                      {log.level}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-text-muted font-mono text-xs max-w-32 truncate">{log.mailbox_email || '—'}</td>
                  <td className="px-4 py-2.5 text-text-muted text-xs">{log.action}</td>
                  <td className="px-4 py-2.5 text-text-primary text-xs max-w-sm truncate">{log.message}</td>
                </tr>
                {expanded[log.id] && log.details && (
                  <tr key={`${log.id}-details`} className="border-b border-border bg-bg">
                    <td colSpan={6} className="px-8 py-3">
                      <pre className="text-text-muted text-xs overflow-x-auto whitespace-pre-wrap">{JSON.stringify(JSON.parse(log.details), null, 2)}</pre>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-sm">
        <button onClick={() => setPage(Math.max(0, page - 1))} disabled={page === 0}
          className="text-text-muted hover:text-text-primary disabled:opacity-40 transition-colors">← Previous</button>
        <span className="text-text-muted text-xs">Page {page + 1}</span>
        <button onClick={() => setPage(page + 1)} disabled={logs.length < PER_PAGE}
          className="text-text-muted hover:text-text-primary disabled:opacity-40 transition-colors">Next →</button>
      </div>
    </div>
  )
}
