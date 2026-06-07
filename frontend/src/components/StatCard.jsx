export default function StatCard({ label, value, sub, color = 'text-text-primary', icon: Icon }) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-text-muted text-xs font-medium uppercase tracking-wide">{label}</span>
        {Icon && <Icon size={14} className="text-text-muted" />}
      </div>
      <div className={`text-2xl font-bold font-mono ${color}`}>{value ?? '—'}</div>
      {sub && <div className="text-text-muted text-xs mt-1">{sub}</div>}
    </div>
  )
}
