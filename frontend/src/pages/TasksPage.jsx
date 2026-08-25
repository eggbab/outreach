import { useState, useEffect } from 'react'
import api from '../lib/api'
import { Plus, Check, Trash2, Clock, AlertCircle } from 'lucide-react'

export default function TasksPage() {
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [title, setTitle] = useState('')
  const [dueAt, setDueAt] = useState('')
  const [showDone, setShowDone] = useState(false)

  const load = () => {
    setLoading(true)
    api.get('/tasks/').then(r => setTasks(r.data)).catch(() => {}).finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  const add = async () => {
    if (!title.trim()) return
    await api.post('/tasks/', { title: title.trim(), due_at: dueAt || null })
    setTitle(''); setDueAt(''); load()
  }
  const toggle = async (t) => { await api.patch(`/tasks/${t.id}`, { done: !t.done }); load() }
  const del = async (id) => { await api.delete(`/tasks/${id}`); load() }

  const pending = tasks.filter(t => !t.done)
  const done = tasks.filter(t => t.done)
  const now = Date.now()

  const dueLabel = (t) => {
    if (!t.due_at) return null
    const due = new Date(t.due_at).getTime()
    const overdue = due < now
    const soon = due - now < 24 * 3600 * 1000
    return (
      <span className={`inline-flex items-center gap-1 text-xs ${overdue ? 'text-red-600' : soon ? 'text-yellow-600' : 'text-gray-400'}`}>
        {overdue ? <AlertCircle className="w-3 h-3" /> : <Clock className="w-3 h-3" />}
        {new Date(t.due_at).toLocaleString('ko-KR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
        {overdue && ' · 지남'}
      </span>
    )
  }

  const Row = ({ t }) => (
    <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-50 last:border-0">
      <button onClick={() => toggle(t)} className={`w-5 h-5 rounded border flex items-center justify-center flex-shrink-0 cursor-pointer ${t.done ? 'bg-green-500 border-green-500' : 'border-gray-300 hover:border-green-400'}`}>
        {t.done && <Check className="w-3 h-3 text-white" />}
      </button>
      <div className="flex-1 min-w-0">
        <p className={`text-sm ${t.done ? 'line-through text-gray-400' : 'text-gray-900'}`}>{t.title}</p>
        <div className="flex items-center gap-3 mt-0.5">
          {dueLabel(t)}
          {t.prospect_name && <span className="text-xs text-blue-600">@ {t.prospect_name}</span>}
        </div>
      </div>
      <button onClick={() => del(t.id)} className="text-gray-300 hover:text-red-500 cursor-pointer"><Trash2 className="w-4 h-4" /></button>
    </div>
  )

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">할 일</h1>
        <p className="text-gray-500 mt-1 text-sm">후속 전화·미팅·제안 등 영업 할 일을 관리하세요. 마감 24시간 전 이메일 알림이 발송됩니다.</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
        <div className="flex flex-col sm:flex-row gap-2">
          <input value={title} onChange={e => setTitle(e.target.value)} onKeyDown={e => e.key === 'Enter' && add()}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="할 일 (예: A사 담당자에게 후속 전화)" />
          <input type="datetime-local" value={dueAt} onChange={e => setDueAt(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm" />
          <button onClick={add} className="inline-flex items-center justify-center gap-1.5 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 cursor-pointer">
            <Plus className="w-4 h-4" /> 추가
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center h-32 items-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" /></div>
      ) : (
        <>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden mb-4">
            {pending.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-10">할 일이 없습니다. 위에서 추가하세요.</p>
            ) : pending.map(t => <Row key={t.id} t={t} />)}
          </div>

          {done.length > 0 && (
            <div>
              <button onClick={() => setShowDone(!showDone)} className="text-sm text-gray-500 mb-2 cursor-pointer">
                완료됨 ({done.length}) {showDone ? '▲' : '▼'}
              </button>
              {showDone && (
                <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                  {done.map(t => <Row key={t.id} t={t} />)}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
