import { useState, useEffect } from 'react'
import api from '../lib/api'
import { Plus, Send, Eye, Trash2, X, Edit2 } from 'lucide-react'

const statusLabels = { draft: '초안', sent: '발송', viewed: '열람', accepted: '수락' }
const statusColors = {
  draft: 'bg-gray-100 text-gray-700',
  sent: 'bg-blue-100 text-blue-700',
  viewed: 'bg-green-100 text-green-700',
  accepted: 'bg-purple-100 text-purple-700',
}

export default function ProposalsPage() {
  const [proposals, setProposals] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ prospect_id: '', title: '', content_html: '', total_amount: 0 })
  const [toast, setToast] = useState(null)

  const showToast = (msg) => { setToast(msg); setTimeout(() => setToast(null), 3000) }

  useEffect(() => { fetchProposals() }, [])

  const fetchProposals = () => {
    api.get('/proposals').then((r) => setProposals(r.data)).catch(() => {}).finally(() => setLoading(false))
  }

  const createProposal = async () => {
    if (!form.title.trim() || !form.prospect_id) return
    try {
      await api.post('/proposals', { ...form, prospect_id: parseInt(form.prospect_id), total_amount: parseInt(form.total_amount) || 0 })
      setShowForm(false)
      setForm({ prospect_id: '', title: '', content_html: '', total_amount: 0 })
      fetchProposals()
      showToast('제안서가 생성되었습니다')
    } catch {}
  }

  const sendProposal = async (id) => {
    await api.post(`/proposals/${id}/send`)
    fetchProposals()
    showToast('제안서가 발송되었습니다')
  }

  const deleteProposal = async (id) => {
    await api.delete(`/proposals/${id}`)
    fetchProposals()
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div></div>
  }

  return (
    <div>
      {toast && <div className="fixed top-6 right-6 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium bg-green-600 text-white">{toast}</div>}

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">제안서</h1>
          <p className="text-gray-500 mt-1 text-sm">제안서를 작성하고 발송 후 열람 여부를 추적하세요</p>
        </div>
        <button onClick={() => setShowForm(true)} className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg cursor-pointer">
          <Plus className="w-4 h-4" /> 새 제안서
        </button>
      </div>

      {proposals.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <p className="text-gray-400 mb-4">제안서가 없습니다</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {proposals.map((p) => (
            <div key={p.id} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-start justify-between mb-3">
                <h3 className="font-medium text-gray-900">{p.title}</h3>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusColors[p.status]}`}>
                  {statusLabels[p.status]}
                </span>
              </div>
              <p className="text-sm text-gray-500 mb-2">{p.total_amount.toLocaleString()}원</p>
              {p.viewed_at && <p className="text-xs text-green-600 mb-2">열람: {new Date(p.viewed_at).toLocaleString('ko-KR')}</p>}
              <div className="flex gap-2 mt-3">
                {p.status === 'draft' && (
                  <button onClick={() => sendProposal(p.id)} className="flex items-center gap-1 px-2 py-1 text-xs text-blue-600 hover:bg-blue-50 rounded cursor-pointer">
                    <Send className="w-3 h-3" /> 발송
                  </button>
                )}
                <button onClick={() => deleteProposal(p.id)} className="flex items-center gap-1 px-2 py-1 text-xs text-red-600 hover:bg-red-50 rounded cursor-pointer">
                  <Trash2 className="w-3 h-3" /> 삭제
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">새 제안서</h3>
              <button onClick={() => setShowForm(false)} className="text-gray-400 cursor-pointer"><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">잠재고객 ID</label>
                <input type="number" value={form.prospect_id} onChange={(e) => setForm({ ...form, prospect_id: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">제목</label>
                <input type="text" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">내용 (HTML)</label>
                <textarea value={form.content_html} onChange={(e) => setForm({ ...form, content_html: e.target.value })} rows={6} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono resize-y" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">총 금액 (원)</label>
                <input type="number" value={form.total_amount} onChange={(e) => setForm({ ...form, total_amount: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-4">
              <button onClick={() => setShowForm(false)} className="px-4 py-2 text-sm text-gray-700 cursor-pointer">취소</button>
              <button onClick={createProposal} className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg cursor-pointer">생성</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
