import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Zap, Loader, Eye, EyeOff } from 'lucide-react'

export default function Login() {
  const { login } = useAuth()
  const navigate   = useNavigate()

  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [showPass, setShowPass] = useState(false)
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!email || !password) {
      setError('Please enter your email and password.')
      return
    }
    setLoading(true)
    setError('')
    try {
      await login(email, password)
      navigate('/', { replace: true })
    } catch (err) {
      const msg = err.response?.data?.detail
      if (err.response?.status === 401) {
        setError('Invalid email or password.')
      } else if (err.response?.status >= 500) {
        setError('Server error. Please try again in a moment.')
      } else {
        setError(msg || 'Login failed. Check your connection.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center p-4">
      <div className="w-full max-w-sm">

        {/* Logo */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-2 mb-2">
            <Zap size={28} className="text-primary" />
            <span className="text-text-primary font-bold text-2xl tracking-tight">WarmGrid</span>
          </div>
          <p className="text-text-muted text-sm">Self-Hosted Email Warmup Engine</p>
        </div>

        {/* Card */}
        <div className="bg-surface border border-border rounded-xl p-6 shadow-xl">
          <h1 className="text-text-primary font-semibold text-lg mb-5">Sign In</h1>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-text-muted text-xs mb-1.5">Email address</label>
              <input
                type="email"
                value={email}
                onChange={(e) => { setEmail(e.target.value); setError('') }}
                autoComplete="email"
                autoFocus
                placeholder="you@example.com"
                className="w-full bg-bg border border-border rounded-md px-3 py-2.5 text-text-primary text-sm
                           placeholder:text-text-muted/50 focus:outline-none focus:border-primary transition-colors"
              />
            </div>

            <div>
              <label className="block text-text-muted text-xs mb-1.5">Password</label>
              <div className="relative">
                <input
                  type={showPass ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => { setPassword(e.target.value); setError('') }}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  className="w-full bg-bg border border-border rounded-md px-3 py-2.5 pr-10 text-text-primary text-sm
                             placeholder:text-text-muted/50 focus:outline-none focus:border-primary transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPass(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary transition-colors"
                >
                  {showPass ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="bg-danger/10 border border-danger/20 rounded-md px-3 py-2">
                <p className="text-danger text-sm">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-primary hover:bg-primary/80 disabled:opacity-50 disabled:cursor-not-allowed
                         text-white py-2.5 rounded-md text-sm font-medium transition-colors
                         flex items-center justify-center gap-2 mt-1"
            >
              {loading ? (
                <><Loader size={14} className="animate-spin" /> Signing in...</>
              ) : 'Sign In'}
            </button>
          </form>
        </div>

        {/* Setup link */}
        <p className="text-center text-text-muted text-xs mt-5">
          First time here?{' '}
          <Link to="/setup" className="text-primary hover:underline">
            Create admin account →
          </Link>
        </p>

      </div>
    </div>
  )
}
