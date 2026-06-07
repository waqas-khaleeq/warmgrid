import { Pause, Play, Trash2, TestTube, ChevronRight } from 'lucide-react'
import HealthScoreBadge from './HealthScoreBadge'

export default function MailboxCard({ mailbox, onPause, onDelete, onTest, onView }) {
  const progress = mailbox.target_daily_volume > 0
    ? Math.round((mailbox.current_daily_volume / mailbox.target_daily_volume) * 100)
    : 0

  return (
    <div className="bg-surface border border-border rounded-lg p-4 flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div className="min-w-0">
          <p className="text-text-primary font-medium text-sm truncate">{mailbox.email}</p>
          <p className="text-text-muted text-xs font-mono">{mailbox.domain}</p>
        </div>
        <HealthScoreBadge score={mailbox.health_score} />
      </div>

      <div>
        <div className="flex justify-between text-xs text-text-muted mb-1">
          <span>Volume</span>
          <span className="font-mono">{mailbox.current_daily_volume}/{mailbox.target_daily_volume}/day</span>
        </div>
        <div className="h-1.5 bg-border rounded-full overflow-hidden">
          <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${progress}%` }} />
        </div>
      </div>

      <div className="flex items-center gap-3 text-xs">
        <span className={`px-2 py-0.5 rounded border text-xs font-medium ${
          mailbox.is_paused ? 'text-warning border-warning/30 bg-warning/10'
          : mailbox.is_active ? 'text-success border-success/30 bg-success/10'
          : 'text-text-muted border-border bg-white/5'
        }`}>
          {mailbox.is_paused ? 'Paused' : mailbox.is_active ? 'Active' : 'Inactive'}
        </span>
        <span className="text-text-muted">Week {mailbox.warmup_week}</span>
      </div>

      <div className="flex gap-1 pt-1 border-t border-border">
        <button onClick={() => onView(mailbox)} className="flex-1 flex items-center justify-center gap-1 text-xs text-text-muted hover:text-text-primary py-1.5 rounded hover:bg-white/5 transition-colors">
          <ChevronRight size={12} /> Details
        </button>
        <button onClick={() => onPause(mailbox)} className="flex items-center justify-center gap-1 text-xs text-text-muted hover:text-warning py-1.5 px-2 rounded hover:bg-white/5 transition-colors">
          {mailbox.is_paused ? <Play size={12} /> : <Pause size={12} />}
        </button>
        <button onClick={() => onTest(mailbox)} className="flex items-center justify-center gap-1 text-xs text-text-muted hover:text-primary py-1.5 px-2 rounded hover:bg-white/5 transition-colors">
          <TestTube size={12} />
        </button>
        <button onClick={() => onDelete(mailbox)} className="flex items-center justify-center gap-1 text-xs text-text-muted hover:text-danger py-1.5 px-2 rounded hover:bg-white/5 transition-colors">
          <Trash2 size={12} />
        </button>
      </div>
    </div>
  )
}
