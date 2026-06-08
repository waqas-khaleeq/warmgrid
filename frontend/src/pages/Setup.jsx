import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Zap, Loader, Eye, EyeOff, CheckCircle, XCircle } from 'lucide-react'
import api from '../api/client'

export default function Setup() {
  const { setup }  = useAuth()
  const navigate   = useNavigate()

  const [email,     setEmail]     = useState('')
  const [password,  setPassword]  = useState('')
  const [confirm,   setConfirm]   = useState('')
  const [showPass,  setShowPass]  = useState(false)
  const [loading,   setLoading]   = useState(false)
  const [checking,  setChecking]  = useState(true)
  const [allowed,   setAllowed]   = useState(false)
  const [error,     setError]     = useState('')

  // Check if setup is allowed (no users exist yet)
  useEffect(() => {
    api.get('/auth/check-setup')
      .then(res => {
        if (res.data.needs_setup) {
          setAllowed(true)
        } else {
          // Already set up — redirect to login
          navigate('/login', { replace: true })
        }
      })
      .catch(() => {
        // Can't reach backend — show error
        setError('Cannot connect to the server. Make sure the backend is running.')
      })
      .finally(() => setChecking(false))
  }, [navigate])

  const passwordChecks = [
    { label: 'At least 8 characters', ok: password.length >= 8 },
    { label: 'Contains a number',      ok: /\d/.test(password) },
    { label: 'Passwords match',        ok: password.length > 0 && password === confirm },
  ]
  const passwordValid = passwordChecks.every(c => c.ok)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!email) { setError('Email is required.'); return }
    if (!passwordValid) { setError('Please fix the password issues above.'); return }

    setLoading(true)
    setError('')
    try {
      await setup(email, password)
      navigate('/', { replace: true })
    } catch (err) {
      const msg = err.response?.data?.detail
      if (err.response?.status === 400) {
        setError(msg || 'Admin account already exists. Go to Sign In.')
      } else {
        setError(msg || 'Setup failed. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  // Still checking whether setup is allowed
  if (checking) {
    return (
      <div className="flex items-center justify-center h-screen bg-bg">
        <div className="flex flex-col items-center gap-3">
          <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <span className="text-text-muted text-sm">Checking setup status...</span>
        </div>
      </div>
    )
  }

  // Backend unreachable
  if (error && !allowed) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center p-4">
        <div className="w-full max-w-sm bg-surface border border-border rounded-xl p-6 text-center">
          <XCircle size={32} className="text-danger mx-auto mb-3" />
          <h2 className="text-text-primary font-semibold mb-2">Cannot connect to backend</h2>
          <p className="text-text-muted text-sm mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="bg-primary hover:bg-primary/80 text-white px-4 py-2 rounded-md text-sm transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
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
          <p className="text-text-muted text-sm">First-time setup</p>
        </div>

        {/* Card */}
        <div className="bg-surface border border-border rounded-xl p-6 shadow-xl">
          <h1 className="text-text-primary font-semibold text-lg mb-1">Create Admin Account</h1>
          <p className="text-text-muted text-xs mb-5">
            This is your one-time setup. This account controls everything.
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-text-muted text-xs mb-1.5">Email address</label>
              <input
                type="email"
                value={email}
                onChange={(e) => { setEmail(e.target.value); setError('') }}
                autoComplete="email"
                autoFocus
                placeholder="admin@yourdomain.com"
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
                  autoComplete="new-password"
                  placeholder="Min 8 characters"
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

            <div>
              <label className="block text-text-muted text-xs mb-1.5">Confirm password</label>
              <input
                type={showPass ? 'text' : 'password'}
                value={confirm}
                onChange={(e) => { setConfirm(e.target.value); setError('') }}
                autoComplete="new-password"
                placeholder="Repeat password"
                className="w-full bg-bg border border-border rounded-md px-3 py-2.5 text-text-primary text-sm
                           placeholder:text-text-muted/50 focus:outline-none focus:border-primary transition-colors"
              />
            </div>

            {/* Password checklist — shows only when user has started typing */}
            {password.length > 0 && (
              <ul className="space-y-1">
                {passwordChecks.map((c) => (
                  <li key={c.label} className={`flex items-center gap-2 text-xs ${c.ok ? 'text-success' : 'text-text-muted'}`}>
                    {c.ok
                      ? <CheckCircle size={12} className="shrink-0" />
                      : <XCircle size={12} className="shrink-0 opacity-40" />}
                    {c.label}
                  </li>
                ))}
              </ul>
            )}

            {/* Error */}
            {error && (
              <div className="bg-danger/10 border border-danger/20 rounded-md px-3 py-2">
                <p className="text-danger text-sm">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !passwordValid || !email}
              className="w-full bg-primary hover:bg-primary/80 disabled:opacity-50 disabled:cursor-not-allowed
                         text-white py-2.5 rounded-md text-sm font-medium transition-colors
                         flex items-center justify-center gap-2 mt-1"
            >
              {loading ? (
                <><Loader size={14} className="animate-spin" /> Creating account...</>
              ) : 'Create Account & Sign In'}
            </button>
          </form>
        </div>

        <p className="text-center text-text-muted text-xs mt-5">
          Already have an account?{' '}
          <Link to="/login" className="text-primary hover:underline">Sign in →</Link>
        </p>

      </div>
    </div>
  )
}
