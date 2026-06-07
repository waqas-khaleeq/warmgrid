import { useState, useEffect } from 'react'
import { Plus, Upload } from 'lucide-react'
import api from '../api/client'
import SeedCard from '../components/SeedCard'
import Modal from '../components/Modal'
import SeedForm from '../components/SeedForm'
import CSVImporter from '../components/CSVImporter'

export default function SeedPool() {
  const [seeds, setSeeds] = useState([])
  const [showAdd, setShowAdd] = useState(false)
  const [showImport, setShowImport] = useState(false)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      const res = await api.get('/seeds')
      setSeeds(res.data)
    } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const handleDelete = async (seed) => {
    if (!confirm(`Remove ${seed.email} from seed pool?`)) return
    await api.delete(`/seeds/${seed.id}`)
    load()
  }

  const handleTest = async (seed) => {
    try {
      const res = await api.post(`/seeds/${seed.id}/test`)
      alert(`IMAP: ${res.data.imap.success ? 'OK' : res.data.imap.error}\nSMTP: ${res.data.smtp.success ? 'OK' : res.data.smtp.error}`)
    } catch { alert('Test failed') }
  }

  const totalReceived = seeds.reduce((a, s) => a + s.emails_received_total, 0)
  const totalReplied = seeds.reduce((a, s) => a + s.replies_sent_total, 0)
  const totalRescued = seeds.reduce((a, s) => a + s.spam_rescues_total, 0)

  if (loading) return <div className="text-text-muted text-sm">Loading...</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-text-primary font-bold text-xl">Seed Pool</h1>
        <div className="flex gap-2">
          <button onClick={() => setShowImport(true)}
            className="flex items-center gap-2 border border-border hover:border-primary text-text-primary px-4 py-2 rounded-md text-sm transition-colors">
            <Upload size={14} /> Import CSV
          </button>
          <button onClick={() => setShowAdd(true)}
            className="flex items-center gap-2 bg-primary hover:bg-primary/80 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors">
            <Plus size={14} /> Add Seed
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Total Seeds', value: seeds.length },
          { label: 'Active', value: seeds.filter(s => s.is_active).length },
          { label: 'Emails Received', value: totalReceived },
          { label: 'Spam Rescued', value: totalRescued },
        ].map((s) => (
          <div key={s.label} className="bg-surface border border-border rounded-lg p-3">
            <p className="text-text-muted text-xs mb-1">{s.label}</p>
            <p className="text-text-primary font-mono font-bold text-2xl">{s.value}</p>
          </div>
        ))}
      </div>

      {seeds.length === 0 ? (
        <div className="bg-surface border border-border rounded-lg p-12 text-center">
          <p className="text-text-muted text-sm mb-3">No seed mailboxes yet</p>
          <div className="flex items-center justify-center gap-3">
            <button onClick={() => setShowAdd(true)} className="text-primary text-sm hover:underline">Add single seed</button>
            <span className="text-text-muted text-xs">or</span>
            <button onClick={() => setShowImport(true)} className="text-primary text-sm hover:underline">Import CSV</button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {seeds.map((s) => (
            <SeedCard key={s.id} seed={s} onDelete={handleDelete} onTest={handleTest} />
          ))}
        </div>
      )}

      <Modal open={showAdd} onClose={() => setShowAdd(false)} title="Add Seed Mailbox">
        <SeedForm onSuccess={() => { setShowAdd(false); load() }} />
      </Modal>

      <Modal open={showImport} onClose={() => setShowImport(false)} title="Import Seeds from CSV" width="max-w-xl">
        <CSVImporter onComplete={() => { setShowImport(false); load() }} />
      </Modal>
    </div>
  )
}
