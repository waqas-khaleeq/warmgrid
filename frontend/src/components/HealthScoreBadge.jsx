export default function HealthScoreBadge({ score, size = 'md' }) {
  const color = score >= 80 ? 'text-success border-success/30 bg-success/10'
    : score >= 50 ? 'text-warning border-warning/30 bg-warning/10'
    : 'text-danger border-danger/30 bg-danger/10'

  const sizeClass = size === 'lg' ? 'text-2xl px-4 py-2' : size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-sm px-3 py-1'

  return (
    <span className={`font-mono font-bold border rounded-md ${color} ${sizeClass}`}>
      {score?.toFixed(0) ?? '—'}
    </span>
  )
}
