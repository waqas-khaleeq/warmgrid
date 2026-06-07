import { useState } from 'react'
import { CheckCircle, XCircle, Loader, Info } from 'lucide-react'
import api from '../api/client'

function detectProvider(email) {
  const domain = email.split('@')[1]?.toLowerCase() || ''
  if (domain.includes('gmail')) return 'gmail'
  if (domain.includes('outlook') || domain.includes('hotmail') || domain.includes('live') || domain.includes('office365')) return 'outlook'
  if (domain.includes('yahoo')) return 'yahoo'
  return 'other'
}

export default function SeedForm({ onSuccess }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [testResult, setTestResult] = useState(null)
  const [testing, setTesting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const provider = email.includes('@') ? detectProvider(email) : ''

  const test = async () => {
    setTesting(true)
    setTestResult(null)
    setError('')
    try {
      const res = await api.post('/seeds/test-connection', { email, app_password: password })
      setTestResult(res.data)
    } catch (e) {
      setTestResult({ success: false, error: e.response?.data?.detail || 'Test failed' })
    }
    setTesting(false)
  }

  const save = async () => {
    setSaving(true)
    setError('')
    try {
      await api.post('/seeds', { email, app_password: password })
      onSuccess()
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to save seed')
    }
    setSaving(false)
  }

  const inputClass = 'w-full bg-bg border border-border rounded-md px-3 py-2 text-text-primary text-sm focus:outline-none focus:border-primary'

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-text-muted text-xs mb-1">Email Address *</label>
        <input className={inputClass} type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="seed@gmail.com" />
        {provider && (
          <p className="text-text-muted text-xs mt-1">Provider detected: <span className="text-primary capitalize">{provider}</span></p>
        )}
      </div>

      <div>
        <label className="block text-text-muted text-xs mb-1 flex items-center gap-1">
          App Password *
          <span className="group relative">
            <Info size={12} className="text-text-muted cursor-help" />
            <span className="absolute left-4 top-0 w-48 text-xs bg-surface border border-border rounded p-2 hidden group-hover:block z-10 text-text-muted">
              Use an App Password, not your regular password. For Gmail: Google Account → Security → App Passwords.
            </span>
          </span>
        </label>
        <input className={inputClass} type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="App-specific password" />
      </div>

      <div className="flex items-center gap-3">
        <button onClick={test} disabled={testing || !email || !password}
          className="bg-surface border border-border hover:border-primary text-text-primary text-sm px-4 py-2 rounded-md disabled:opacity-40 transition-colors flex items-center gap-2">
          {testing ? <><Loader size={14} className="animate-spin" /> Testing...</> : 'Test Connection'}
        </button>
        {testResult && (
          testResult.success
            ? <span className="flex items-center gap-1 text-success text-sm"><CheckCircle size={14} /> Connected</span>
            : <span className="flex items-center gap-1 text-danger text-sm"><XCircle size={14} /> {testResult.error}</span>
        )}
      </div>

      {error && <p className="text-danger text-sm">{error}</p>}

      <button onClick={save} disabled={!testResult?.success || saving}
        className="w-full bg-primary hover:bg-primary/80 disabled:opacity-40 text-white py-2 rounded-md text-sm font-medium transition-colors flex items-center justify-center gap-2">
        {saving ? <><Loader size={14} className="animate-spin" /> Saving...</> : 'Add Seed Mailbox'}
      </button>
    </div>
  )
}
