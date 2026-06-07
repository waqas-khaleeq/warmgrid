import { formatDistanceToNow } from 'date-fns'

const levelColors = {
  info: 'text-primary bg-primary/10 border-primary/20',
  success: 'text-success bg-success/10 border-success/20',
  warning: 'text-warning bg-warning/10 border-warning/20',
  error: 'text-danger bg-danger/10 border-danger/20',
}

export default function ActivityFeed({ logs = [] }) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <h3 className="text-text-primary text-sm font-medium mb-4">Recent Activity</h3>
      <div className="space-y-2 max-h-72 overflow-y-auto">
        {logs.length === 0 && (
          <p className="text-text-muted text-sm text-center py-4">No activity yet</p>
        )}
        {logs.map((log) => (
          <div key={log.id} className="flex items-start gap-3 py-2 border-b border-border last:border-0">
            <span className={`text-xs font-mono font-medium border rounded px-1.5 py-0.5 uppercase shrink-0 ${levelColors[log.level] || levelColors.info}`}>
              {log.level}
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-text-primary text-xs truncate">{log.message}</p>
              {log.mailbox_email && (
                <p className="text-text-muted text-xs font-mono truncate">{log.mailbox_email}</p>
              )}
            </div>
            <span className="text-text-muted text-xs shrink-0 font-mono">
              {formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
