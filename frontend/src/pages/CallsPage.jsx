import { useState, useEffect } from 'react'
import api from '../lib/api'
import { Phone, Plus, X, Clock, PhoneOutgoing, PhoneIncoming, PhoneMissed } from 'lucide-react'

export default function CallsPage() {
  const [projects, setProjects] = useState([])
  const [selectedProject, setSelectedProject] = useState('')
  const [calls, setCalls] = useState([])
  const [callbacks, setCallbacks] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    prospect_id: '', call_type: 'outbound', duration_seconds: 0,
    notes: '', outcome: '', callback_at: '',
  })
  const [toast, setToast] = useState(null)

  const showToast = (msg, type = 'success') => { setToast({ message: msg, type }); setTimeout(() => setToast(null), 3000) }

  useEffect(() => {
    api.get('/projects').then((r) => {
      setProjects(r.data)
      if (r.data.length > 0) setSelectedProject(String(r.data[0].id))
    }).catch(() => {}).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!selectedProject) return
    fetchCalls()
  }, [selectedProject])

  const fetchCalls = () => {
    Promise.all([
      api.get(`/projects/${selectedProject}/calls`),
      api.get(`/projects/${selectedProject}/calls/callbacks`),
    ]).then(([callsR, callbacksR]) => {
      setCalls(callsR.data)
      setCallbacks(callbacksR.data)
    }).catch(() => {})
  }

  const createCall = async () => {
    if (!form.prospect_id) return
    try {
      await api.post(`/projects/${selectedProject}/calls`, {
        ...form,
        prospect_id: parseInt(form.prospect_id),
        duration_seconds: parseInt(form.duration_seconds) || 0,
        callback_at: form.callback_at || null,
      })
      setShowForm(false)
      setForm({ prospect_id: '', call_type: 'outbound', duration_seconds: 0, notes: '', outcome: '', callback_at: '' })
      fetchCalls()
      showToast('통화 기록이 추가되었습니다')
    } catch (err) { showToast(err.response?.data?.detail || '실패', 'error') }
  }

  const callTypeIcon = (type) => {
    if (type === 'outbound') return <PhoneOutgoing className="w-4 h-4 text-blue-500" />
    if (type === 'inbound') return <PhoneIncoming className="w-4 h-4 text-green-500" />
    return <PhoneMissed className="w-4 h-4 text-red-500" />
  }

  const callTypeLabel = (type) => {
    return { outbound: '발신', inbound: '수신', missed: '부재중' }[type] || type
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div></div>
  }

  return (
    <div>
      {toast && <div className={`fixed top-6 right-6 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium ${toast.type === 'error' ? 'bg-red-600 text-white' : 'bg-green-600 text-white'}`}>{toast.message}</div>}

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">통화 기록</h1>
          <p className="text-gray-500 mt-1 text-sm">통화 기록과 콜백 스케줄을 관리하세요</p>
        </div>
        <div className="flex gap-3">
          <select value={selectedProject} onChange={(e) => setSelectedProject(e.target.value)} className="px-3 py-2 border border-gray-300 rounded-lg text-sm">
            {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <button onClick={() => setShowForm(true)} className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg cursor-pointer">
            <Plus className="w-4 h-4" /> 통화 기록
          </button>
        </div>
      </div>

      {/* Callbacks */}
      {callbacks.length > 0 && (
        <div className="mb-6 bg-yellow-50 border border-yellow-200 rounded-xl p-4">
          <h2 className="text-sm font-semibold text-yellow-800 mb-2 flex items-center gap-2"><Clock className="w-4 h-4" /> 콜백 스케줄</h2>
          <div className="space-y-2">
            {callbacks.map((c) => (
              <div key={c.id} className="flex items-center justify-between text-sm">
                <span className="text-yellow-900">잠재고객 #{c.prospect_id} — {c.outcome || '메모 없음'}</span>
                <span className="text-yellow-700">{new Date(c.callback_at).toLocaleString('ko-KR')}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Call list */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-4 py-3 font-medium text-gray-600">유형</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">잠재고객</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">통화시간</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">결과</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">메모</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">일시</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {calls.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-12 text-center text-gray-400">통화 기록이 없습니다</td></tr>
            ) : calls.map((c) => (
              <tr key={c.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">{callTypeIcon(c.call_type)} <span className="ml-1 text-gray-600">{callTypeLabel(c.call_type)}</span></td>
                <td className="px-4 py-3 text-gray-600">#{c.prospect_id}</td>
                <td className="px-4 py-3 text-gray-600">{Math.floor(c.duration_seconds / 60)}분 {c.duration_seconds % 60}초</td>
                <td className="px-4 py-3 text-gray-600">{c.outcome || '-'}</td>
                <td className="px-4 py-3 text-gray-500 max-w-xs truncate">{c.notes || '-'}</td>
                <td className="px-4 py-3 text-gray-400">{new Date(c.called_at).toLocaleString('ko-KR')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">통화 기록 추가</h3>
              <button onClick={() => setShowForm(false)} className="text-gray-400 cursor-pointer"><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">잠재고객 ID</label>
                <input type="number" value={form.prospect_id} onChange={(e) => setForm({ ...form, prospect_id: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">통화 유형</label>
                  <select value={form.call_type} onChange={(e) => setForm({ ...form, call_type: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
                    <option value="outbound">발신</option>
                    <option value="inbound">수신</option>
                    <option value="missed">부재중</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">통화시간 (초)</label>
                  <input type="number" value={form.duration_seconds} onChange={(e) => setForm({ ...form, duration_seconds: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">결과</label>
                <input type="text" value={form.outcome} onChange={(e) => setForm({ ...form, outcome: e.target.value })} placeholder="예: 미팅 확정, 거절" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">메모</label>
                <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} rows={3} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm resize-y" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">콜백 일시 (선택)</label>
                <input type="datetime-local" value={form.callback_at} onChange={(e) => setForm({ ...form, callback_at: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-4">
              <button onClick={() => setShowForm(false)} className="px-4 py-2 text-sm text-gray-700 cursor-pointer">취소</button>
              <button onClick={createCall} className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg cursor-pointer">저장</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
