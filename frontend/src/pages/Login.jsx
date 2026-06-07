import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { Zap, Loader } from 'lucide-react'

export default function Login() {
  const { login, setup, needsSetup } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      if (needsSetup) {
        await setup(email, password)
      } else {
        await login(email, password)
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Authentication failed')
    }
    setLoading(false)
  }

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-2 mb-2">
            <Zap size={28} className="text-primary" />
            <span className="text-text-primary font-bold text-2xl tracking-tight">WarmGrid</span>
          </div>
          <p className="text-text-muted text-sm">Self-Hosted Email Warmup Engine</p>
        </div>

        <div className="bg-surface border border-border rounded-xl p-6">
          <h1 className="text-text-primary font-semibold text-lg mb-1">
            {needsSetup ? 'Create Admin Account' : 'Sign In'}
          </h1>
          {needsSetup && (
            <p className="text-text-muted text-xs mb-4">First-time setup — create your admin account to get started.</p>
          )}

          <form onSubmit={handleSubmit} className="space-y-4 mt-4">
            <div>
              <label className="block text-text-muted text-xs mb-1">Email</label>
              <input
                type="email" value={email} onChange={(e) => setEmail(e.target.value)} required
                className="w-full bg-bg border border-border rounded-md px-3 py-2 text-text-primary text-sm focus:outline-none focus:border-primary"
                placeholder="admin@example.com"
              />
            </div>
            <div>
              <label className="block text-text-muted text-xs mb-1">Password</label>
              <input
                type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
                className="w-full bg-bg border border-border rounded-md px-3 py-2 text-text-primary text-sm focus:outline-none focus:border-primary"
                placeholder="••••••••"
              />
            </div>
            {error && <p className="text-danger text-sm">{error}</p>}
            <button type="submit" disabled={loading}
              className="w-full bg-primary hover:bg-primary/80 disabled:opacity-50 text-white py-2.5 rounded-md text-sm font-medium transition-colors flex items-center justify-center gap-2">
              {loading ? <><Loader size={14} className="animate-spin" /> {needsSetup ? 'Creating...' : 'Signing in...'}</> : (needsSetup ? 'Create Account' : 'Sign In')}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
