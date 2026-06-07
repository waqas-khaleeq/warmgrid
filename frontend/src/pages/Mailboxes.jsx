import { useState, useEffect } from 'react'
import { Plus } from 'lucide-react'
import api from '../api/client'
import MailboxCard from '../components/MailboxCard'
import Modal from '../components/Modal'
import MailboxForm from '../components/MailboxForm'
import VolumeChart from '../components/VolumeChart'
import HealthChart from '../components/HealthChart'
import ActivityFeed from '../components/ActivityFeed'
import HealthScoreBadge from '../components/HealthScoreBadge'

export default function Mailboxes() {
  const [mailboxes, setMailboxes] = useState([])
  const [showAdd, setShowAdd] = useState(false)
  const [detail, setDetail] = useState(null)
  const [detailStats, setDetailStats] = useState(null)
  const [detailLogs, setDetailLogs] = useState([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      const res = await api.get('/mailboxes')
      setMailboxes(res.data)
    } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const handlePause = async (mb) => {
    await api.post(`/mailboxes/${mb.id}/pause`)
    load()
  }

  const handleDelete = async (mb) => {
    if (!confirm(`Delete ${mb.email}? This cannot be undone.`)) return
    await api.delete(`/mailboxes/${mb.id}`)
    load()
  }

  const handleTest = async (mb) => {
    try {
      const res = await api.post(`/mailboxes/${mb.id}/test`)
      alert(`SMTP: ${res.data.smtp.success ? 'OK' : res.data.smtp.error}\nIMAP: ${res.data.imap.success ? 'OK' : res.data.imap.error}`)
    } catch { alert('Test failed') }
  }

  const handleView = async (mb) => {
    setDetail(mb)
    try {
      const [stats, logs] = await Promise.all([
        api.get(`/mailboxes/${mb.id}/stats`),
        api.get(`/logs?mailbox_id=${mb.id}&limit=20`),
      ])
      setDetailStats(stats.data)
      setDetailLogs(logs.data)
    } catch {}
  }

  if (loading) return <div className="text-text-muted text-sm">Loading...</div>

  if (detail) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <button onClick={() => { setDetail(null); setDetailStats(null) }}
            className="text-text-muted hover:text-text-primary text-sm transition-colors">← Back</button>
          <h1 className="text-text-primary font-bold text-xl">{detail.email}</h1>
          <HealthScoreBadge score={detail.health_score} size="lg" />
        </div>
        {detailStats && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: 'Total Sent', value: detailStats.emails_sent_total },
                { label: 'Reply Rate', value: `${detailStats.reply_rate}%` },
                { label: 'Spam Rate', value: `${detailStats.spam_rate}%` },
                { label: 'Warmup Week', value: detailStats.warmup_week },
              ].map((s) => (
                <div key={s.label} className="bg-surface border border-border rounded-lg p-3">
                  <p className="text-text-muted text-xs mb-1">{s.label}</p>
                  <p className="text-text-primary font-mono font-bold text-xl">{s.value}</p>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <VolumeChart data={detailStats.daily_sends_last_30_days} />
              <HealthChart data={detailStats.health_scores_last_30_days} />
            </div>
          </>
        )}
        <ActivityFeed logs={detailLogs} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-text-primary font-bold text-xl">Sender Mailboxes</h1>
        <button onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 bg-primary hover:bg-primary/80 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors">
          <Plus size={14} /> Add Mailbox
        </button>
      </div>

      {mailboxes.length === 0 ? (
        <div className="bg-surface border border-border rounded-lg p-12 text-center">
          <p className="text-text-muted text-sm mb-3">No sender mailboxes yet</p>
          <button onClick={() => setShowAdd(true)} className="text-primary text-sm hover:underline">Add your first mailbox</button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {mailboxes.map((mb) => (
            <MailboxCard key={mb.id} mailbox={mb} onPause={handlePause} onDelete={handleDelete} onTest={handleTest} onView={handleView} />
          ))}
        </div>
      )}

      <Modal open={showAdd} onClose={() => setShowAdd(false)} title="Add Sender Mailbox" width="max-w-xl">
        <MailboxForm onSuccess={() => { setShowAdd(false); load() }} onClose={() => setShowAdd(false)} />
      </Modal>
    </div>
  )
}
