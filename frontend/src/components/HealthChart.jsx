import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export default function HealthChart({ data = [] }) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <h3 className="text-text-primary text-sm font-medium mb-4">Health Score History</h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2e" />
          <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} tickFormatter={(v) => v?.slice(5)} />
          <YAxis domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 10 }} />
          <Tooltip
            contentStyle={{ background: '#111118', border: '1px solid #1e1e2e', borderRadius: 6 }}
            labelStyle={{ color: '#f1f5f9' }}
            itemStyle={{ color: '#22c55e' }}
          />
          <Bar dataKey="score" fill="#22c55e" radius={[2, 2, 0, 0]} name="Health Score" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
