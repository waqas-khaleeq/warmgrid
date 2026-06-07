import { Trash2, TestTube, Mail } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

const providerColors = {
  gmail: 'text-danger border-danger/30 bg-danger/10',
  outlook: 'text-primary border-primary/30 bg-primary/10',
  yahoo: 'text-warning border-warning/30 bg-warning/10',
  other: 'text-text-muted border-border bg-white/5',
}

export default function SeedCard({ seed, onDelete, onTest }) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4 flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div className="min-w-0 flex-1">
          <p className="text-text-primary font-medium text-sm truncate">{seed.email}</p>
          <p className="text-text-muted text-xs font-mono">
            {seed.last_used
              ? `Used ${formatDistanceToNow(new Date(seed.last_used), { addSuffix: true })}`
              : 'Never used'}
          </p>
        </div>
        <span className={`text-xs font-medium border rounded px-1.5 py-0.5 uppercase ml-2 shrink-0 ${providerColors[seed.provider] || providerColors.other}`}>
          {seed.provider}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 text-center">
        <div>
          <p className="text-text-primary font-mono text-sm font-bold">{seed.emails_received_total}</p>
          <p className="text-text-muted text-xs">Received</p>
        </div>
        <div>
          <p className="text-text-primary font-mono text-sm font-bold">{seed.replies_sent_total}</p>
          <p className="text-text-muted text-xs">Replied</p>
        </div>
        <div>
          <p className="text-text-primary font-mono text-sm font-bold">{seed.spam_rescues_total}</p>
          <p className="text-text-muted text-xs">Rescued</p>
        </div>
      </div>

      <div className="flex gap-1 pt-1 border-t border-border">
        <button onClick={() => onTest(seed)} className="flex-1 flex items-center justify-center gap-1 text-xs text-text-muted hover:text-primary py-1.5 rounded hover:bg-white/5 transition-colors">
          <TestTube size={12} /> Test
        </button>
        <button onClick={() => onDelete(seed)} className="flex items-center justify-center gap-1 text-xs text-text-muted hover:text-danger py-1.5 px-3 rounded hover:bg-white/5 transition-colors">
          <Trash2 size={12} />
        </button>
      </div>
    </div>
  )
}
