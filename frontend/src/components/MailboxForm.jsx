import { useState } from 'react'
import { CheckCircle, XCircle, Loader } from 'lucide-react'
import api from '../api/client'

const PROVIDERS = {
  microsoft365: {
    label: 'Microsoft 365',
    smtp_host: 'smtp.office365.com', smtp_port: 587,
    imap_host: 'outlook.office365.com', imap_port: 993,
  },
  gmail: {
    label: 'Gmail',
    smtp_host: 'smtp.gmail.com', smtp_port: 587,
    imap_host: 'imap.gmail.com', imap_port: 993,
  },
  custom: { label: 'Custom', smtp_host: '', smtp_port: 587, imap_host: '', imap_port: 993 },
}

export default function MailboxForm({ onSuccess, onClose }) {
  const [step, setStep] = useState(1)
  const [provider, setProvider] = useState('microsoft365')
  const [form, setForm] = useState({
    email: '', display_name: '',
    smtp_host: 'smtp.office365.com', smtp_port: 587,
    smtp_username: '', smtp_password: '',
    imap_host: 'outlook.office365.com', imap_port: 993,
    imap_username: '', imap_password: '',
    target_daily_volume: 50,
  })
  const [smtpTest, setSmtpTest] = useState(null)
  const [imapTest, setImapTest] = useState(null)
  const [testing, setTesting] = useState({ smtp: false, imap: false })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }))

  const selectProvider = (key) => {
    setProvider(key)
    const p = PROVIDERS[key]
    setForm((f) => ({
      ...f,
      smtp_host: p.smtp_host, smtp_port: p.smtp_port,
      imap_host: p.imap_host, imap_port: p.imap_port,
    }))
    setSmtpTest(null)
    setImapTest(null)
  }

  const testSmtp = async () => {
    setTesting((t) => ({ ...t, smtp: true }))
    setSmtpTest(null)
    try {
      const res = await api.post('/mailboxes/test-smtp', {
        host: form.smtp_host, port: form.smtp_port,
        username: form.smtp_username || form.email,
        password: form.smtp_password,
      })
      setSmtpTest(res.data)
    } catch (e) {
      setSmtpTest({ success: false, error: e.response?.data?.detail || 'Test failed' })
    }
    setTesting((t) => ({ ...t, smtp: false }))
  }

  const testImap = async () => {
    setTesting((t) => ({ ...t, imap: true }))
    setImapTest(null)
    try {
      const res = await api.post('/mailboxes/test-imap', {
        host: form.imap_host, port: form.imap_port,
        username: form.imap_username || form.email,
        password: form.imap_password || form.smtp_password,
      })
      setImapTest(res.data)
    } catch (e) {
      setImapTest({ success: false, error: e.response?.data?.detail || 'Test failed' })
    }
    setTesting((t) => ({ ...t, imap: false }))
  }

  const save = async () => {
    setSaving(true)
    setError('')
    try {
      await api.post('/mailboxes', {
        ...form,
        smtp_username: form.smtp_username || form.email,
        imap_username: form.imap_username || form.email,
        imap_password: form.imap_password || form.smtp_password,
      })
      onSuccess()
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to save mailbox')
    }
    setSaving(false)
  }

  const canSave = smtpTest?.success && imapTest?.success

  const inputClass = 'w-full bg-bg border border-border rounded-md px-3 py-2 text-text-primary text-sm focus:outline-none focus:border-primary'
  const labelClass = 'block text-text-muted text-xs mb-1'

  return (
    <div>
      <div className="flex gap-1 mb-6">
        {[1,2,3,4].map((s) => (
          <div key={s} className={`flex-1 h-1 rounded-full ${step >= s ? 'bg-primary' : 'bg-border'}`} />
        ))}
      </div>

      {step === 1 && (
        <div className="space-y-4">
          <h3 className="text-text-primary font-medium">Basic Info</h3>
          <div>
            <label className={labelClass}>Display Name</label>
            <input className={inputClass} value={form.display_name} onChange={(e) => set('display_name', e.target.value)} placeholder="John Smith" />
          </div>
          <div>
            <label className={labelClass}>Email Address *</label>
            <input className={inputClass} type="email" value={form.email} onChange={(e) => set('email', e.target.value)} placeholder="john@company.com" />
          </div>
          <div>
            <label className={labelClass}>Provider</label>
            <div className="flex gap-2">
              {Object.entries(PROVIDERS).map(([key, p]) => (
                <button key={key} onClick={() => selectProvider(key)}
                  className={`flex-1 py-2 text-xs rounded-md border transition-colors ${provider === key ? 'border-primary bg-primary/10 text-primary' : 'border-border text-text-muted hover:border-primary/50'}`}>
                  {p.label}
                </button>
              ))}
            </div>
          </div>
          <button onClick={() => setStep(2)} disabled={!form.email}
            className="w-full bg-primary hover:bg-primary/80 disabled:opacity-40 text-white py-2 rounded-md text-sm font-medium transition-colors">
            Next: SMTP Settings
          </button>
        </div>
      )}

      {step === 2 && (
        <div className="space-y-4">
          <h3 className="text-text-primary font-medium">SMTP Settings</h3>
          <div className="grid grid-cols-3 gap-2">
            <div className="col-span-2">
              <label className={labelClass}>SMTP Host</label>
              <input className={inputClass} value={form.smtp_host} onChange={(e) => set('smtp_host', e.target.value)} />
            </div>
            <div>
              <label className={labelClass}>Port</label>
              <input className={inputClass} type="number" value={form.smtp_port} onChange={(e) => set('smtp_port', parseInt(e.target.value))} />
            </div>
          </div>
          <div>
            <label className={labelClass}>SMTP Username</label>
            <input className={inputClass} value={form.smtp_username} onChange={(e) => set('smtp_username', e.target.value)} placeholder={form.email} />
          </div>
          <div>
            <label className={labelClass}>SMTP Password *</label>
            <input className={inputClass} type="password" value={form.smtp_password} onChange={(e) => set('smtp_password', e.target.value)} />
          </div>
          <div className="flex items-center gap-3">
            <button onClick={testSmtp} disabled={testing.smtp || !form.smtp_password}
              className="bg-surface border border-border hover:border-primary text-text-primary text-sm px-4 py-2 rounded-md disabled:opacity-40 transition-colors flex items-center gap-2">
              {testing.smtp ? <Loader size={14} className="animate-spin" /> : 'Test SMTP'}
            </button>
            {smtpTest && (
              smtpTest.success
                ? <span className="flex items-center gap-1 text-success text-sm"><CheckCircle size={14} /> Connected ({smtpTest.latency_ms}ms)</span>
                : <span className="flex items-center gap-1 text-danger text-sm"><XCircle size={14} /> {smtpTest.error}</span>
            )}
          </div>
          <div className="flex gap-2">
            <button onClick={() => setStep(1)} className="flex-1 border border-border text-text-muted text-sm py-2 rounded-md hover:border-primary/50 transition-colors">Back</button>
            <button onClick={() => setStep(3)} className="flex-1 bg-primary hover:bg-primary/80 text-white py-2 rounded-md text-sm font-medium transition-colors">Next: IMAP</button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="space-y-4">
          <h3 className="text-text-primary font-medium">IMAP Settings</h3>
          <div className="grid grid-cols-3 gap-2">
            <div className="col-span-2">
              <label className={labelClass}>IMAP Host</label>
              <input className={inputClass} value={form.imap_host} onChange={(e) => set('imap_host', e.target.value)} />
            </div>
            <div>
              <label className={labelClass}>Port</label>
              <input className={inputClass} type="number" value={form.imap_port} onChange={(e) => set('imap_port', parseInt(e.target.value))} />
            </div>
          </div>
          <div>
            <label className={labelClass}>IMAP Username</label>
            <input className={inputClass} value={form.imap_username} onChange={(e) => set('imap_username', e.target.value)} placeholder={form.email} />
          </div>
          <div>
            <label className={labelClass}>IMAP Password (leave blank to use SMTP password)</label>
            <input className={inputClass} type="password" value={form.imap_password} onChange={(e) => set('imap_password', e.target.value)} placeholder="Same as SMTP password" />
          </div>
          <div className="flex items-center gap-3">
            <button onClick={testImap} disabled={testing.imap}
              className="bg-surface border border-border hover:border-primary text-text-primary text-sm px-4 py-2 rounded-md disabled:opacity-40 transition-colors flex items-center gap-2">
              {testing.imap ? <Loader size={14} className="animate-spin" /> : 'Test IMAP'}
            </button>
            {imapTest && (
              imapTest.success
                ? <span className="flex items-center gap-1 text-success text-sm"><CheckCircle size={14} /> Connected</span>
                : <span className="flex items-center gap-1 text-danger text-sm"><XCircle size={14} /> {imapTest.error}</span>
            )}
          </div>
          <div className="flex gap-2">
            <button onClick={() => setStep(2)} className="flex-1 border border-border text-text-muted text-sm py-2 rounded-md hover:border-primary/50 transition-colors">Back</button>
            <button onClick={() => setStep(4)} className="flex-1 bg-primary hover:bg-primary/80 text-white py-2 rounded-md text-sm font-medium transition-colors">Next: Warmup</button>
          </div>
        </div>
      )}

      {step === 4 && (
        <div className="space-y-4">
          <h3 className="text-text-primary font-medium">Warmup Settings</h3>
          <div>
            <label className={labelClass}>Target Daily Volume: {form.target_daily_volume} emails/day</label>
            <input type="range" min={10} max={100} value={form.target_daily_volume}
              onChange={(e) => set('target_daily_volume', parseInt(e.target.value))}
              className="w-full accent-primary" />
            <div className="flex justify-between text-xs text-text-muted mt-1"><span>10</span><span>100</span></div>
          </div>
          {error && <p className="text-danger text-sm">{error}</p>}
          {!canSave && (
            <p className="text-warning text-xs">Both SMTP and IMAP tests must pass before saving.</p>
          )}
          <div className="flex gap-2">
            <button onClick={() => setStep(3)} className="flex-1 border border-border text-text-muted text-sm py-2 rounded-md hover:border-primary/50 transition-colors">Back</button>
            <button onClick={save} disabled={!canSave || saving}
              className="flex-1 bg-primary hover:bg-primary/80 disabled:opacity-40 text-white py-2 rounded-md text-sm font-medium transition-colors flex items-center justify-center gap-2">
              {saving ? <><Loader size={14} className="animate-spin" /> Saving...</> : 'Save Mailbox'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
