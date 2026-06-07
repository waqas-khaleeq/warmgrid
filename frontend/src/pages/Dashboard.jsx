import { useState, useEffect } from 'react'
import { Inbox, Send, Reply, ShieldCheck, Activity } from 'lucide-react'
import api from '../api/client'
import StatCard from '../components/StatCard'
import VolumeChart from '../components/VolumeChart'
import HealthChart from '../components/HealthChart'
import ActivityFeed from '../components/ActivityFeed'
import HealthScoreBadge from '../components/HealthScoreBadge'

export default function Dashboard() {
  const [overview, setOverview] = useState(null)
  const [mailboxes, setMailboxes] = useState([])
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      const [ov, mb, lg] = await Promise.all([
        api.get('/analytics/overview'),
        api.get('/mailboxes'),
        api.get('/logs?limit=20'),
      ])
      setOverview(ov.data)
      setMailboxes(mb.data)
      setLogs(lg.data)
    } catch {}
    setLoading(false)
  }

  useEffect(() => {
    load()
    const id = setInterval(load, 60000)
    return () => clearInterval(id)
  }, [])

  if (loading) return <div className="text-text-muted text-sm">Loading dashboard...</div>

  return (
    <div className="space-y-6">
      <h1 className="text-text-primary font-bold text-xl">Dashboard</h1>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <StatCard label="Total Mailboxes" value={overview?.total_sender_mailboxes}
          sub={`${overview?.active_mailboxes} active, ${overview?.paused_mailboxes} paused`} icon={Inbox} />
        <StatCard label="Sent Today" value={overview?.emails_sent_today} icon={Send} />
        <StatCard label="Replies Today" value={overview?.replies_received_today} icon={Reply} />
        <StatCard label="Spam Rescues Today" value={overview?.spam_rescues_today} icon={ShieldCheck} />
        <StatCard label="Avg Health Score" value={overview?.average_health_score?.toFixed(0)}
          color={overview?.average_health_score >= 80 ? 'text-success' : overview?.average_health_score >= 50 ? 'text-warning' : 'text-danger'}
          icon={Activity} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <VolumeChart data={overview?.warmup_emails_in_last_7_days || []} />
        <HealthChart data={mailboxes.slice(0, 1).flatMap(m => [])} />
      </div>

      <div className="bg-surface border border-border rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-border">
          <h2 className="text-text-primary text-sm font-medium">Mailbox Health Overview</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                {['Email', 'Domain', 'Health', 'Volume', 'Progress', 'Status'].map((h) => (
                  <th key={h} className="px-4 py-2 text-left text-text-muted text-xs font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {mailboxes.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-6 text-center text-text-muted text-sm">No mailboxes yet. Add your first sender mailbox.</td></tr>
              )}
              {mailboxes.map((mb) => {
                const progress = mb.target_daily_volume > 0 ? Math.round((mb.current_daily_volume / mb.target_daily_volume) * 100) : 0
                return (
                  <tr key={mb.id} className="border-b border-border last:border-0 hover:bg-white/5">
                    <td className="px-4 py-2.5 text-text-primary font-mono text-xs">{mb.email}</td>
                    <td className="px-4 py-2.5 text-text-muted text-xs">{mb.domain}</td>
                    <td className="px-4 py-2.5"><HealthScoreBadge score={mb.health_score} size="sm" /></td>
                    <td className="px-4 py-2.5 text-text-muted text-xs font-mono">{mb.current_daily_volume}/{mb.target_daily_volume}</td>
                    <td className="px-4 py-2.5 w-28">
                      <div className="h-1.5 bg-border rounded-full overflow-hidden">
                        <div className="h-full bg-primary rounded-full" style={{ width: `${progress}%` }} />
                      </div>
                    </td>
                    <td className="px-4 py-2.5">
                      <span className={`text-xs px-2 py-0.5 rounded border ${mb.is_paused ? 'text-warning border-warning/30' : 'text-success border-success/30'}`}>
                        {mb.is_paused ? 'Paused' : 'Active'}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      <ActivityFeed logs={logs} />
    </div>
  )
}
