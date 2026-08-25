import { useState, useEffect } from 'react'
import api from '../lib/api'
import { Plus, Edit2, Trash2, X, FlaskConical, BarChart2 } from 'lucide-react'

function VariantPanel({ template, showToast }) {
  const [open, setOpen] = useState(false)
  const [variants, setVariants] = useState([])
  const [stats, setStats] = useState([])
  const [adding, setAdding] = useState(false)
  const [v, setV] = useState({ variant_name: 'B', subject: '', body: '', weight: 50 })

  const load = () => {
    api.get(`/templates/${template.id}/variants`).then(r => setVariants(r.data)).catch(() => {})
    api.get(`/templates/${template.id}/variants/stats`).then(r => setStats(r.data)).catch(() => {})
  }
  useEffect(() => { if (open) load() }, [open])

  const addVariant = async () => {
    if (!v.subject.trim()) return
    try {
      await api.post(`/templates/${template.id}/variants`, v)
      setAdding(false)
      setV({ variant_name: 'B', subject: '', body: '', weight: 50 })
      load()
      showToast('변형이 추가되었습니다')
    } catch (e) { showToast(e.response?.data?.detail || '실패', 'error') }
  }
  const del = async (id) => { await api.delete(`/templates/${template.id}/variants/${id}`); load() }

  const statOf = (id) => stats.find(s => s.variant_id === id) || {}
  const best = stats.length > 1
    ? stats.reduce((a, b) => (b.open_rate > (a?.open_rate ?? -1) ? b : a), null)
    : null

  return (
    <div className="mt-3 pt-3 border-t border-gray-100">
      <button onClick={() => setOpen(!open)} className="flex items-center gap-1.5 text-xs font-medium text-blue-600 cursor-pointer">
        <FlaskConical className="w-3.5 h-3.5" /> A/B 변형 {variants.length > 0 && `(${variants.length})`} {open ? '▲' : '▼'}
      </button>
      {open && (
        <div className="mt-2 space-y-2">
          {variants.length === 0 && (
            <p className="text-xs text-gray-400">변형을 추가하면 발송 시 수신자에게 무작위 분배되어 성과를 비교합니다.</p>
          )}
          {variants.map((vr) => {
            const s = statOf(vr.id)
            const isBest = best && best.variant_id === vr.id && (s.sent || 0) > 0
            return (
              <div key={vr.id} className={`rounded-lg border p-2.5 ${isBest ? 'border-green-300 bg-green-50/50' : 'border-gray-100'}`}>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-gray-800">
                    변형 {vr.variant_name} · weight {vr.weight}
                    {isBest && <span className="ml-1.5 text-green-600">← 우세</span>}
                  </span>
                  <button onClick={() => del(vr.id)} className="text-gray-300 hover:text-red-500 cursor-pointer"><Trash2 className="w-3 h-3" /></button>
                </div>
                <p className="text-xs text-gray-600 mt-0.5 truncate">{vr.subject}</p>
                {(s.sent || 0) > 0 && (
                  <div className="flex items-center gap-3 mt-1.5 text-[11px] text-gray-500">
                    <span className="flex items-center gap-1"><BarChart2 className="w-3 h-3" />발송 {s.sent}</span>
                    <span>열람 {s.open_rate}%</span>
                    <span>클릭 {s.click_rate}%</span>
                  </div>
                )}
              </div>
            )
          })}
          {adding ? (
            <div className="rounded-lg border border-blue-200 p-2.5 space-y-2">
              <div className="flex gap-2">
                <input value={v.variant_name} onChange={e => setV({ ...v, variant_name: e.target.value.slice(0, 10) })} className="w-16 px-2 py-1 border border-gray-200 rounded text-xs" placeholder="B" />
                <input type="number" value={v.weight} onChange={e => setV({ ...v, weight: parseInt(e.target.value) || 0 })} className="w-20 px-2 py-1 border border-gray-200 rounded text-xs" placeholder="weight" />
              </div>
              <input value={v.subject} onChange={e => setV({ ...v, subject: e.target.value })} className="w-full px-2 py-1 border border-gray-200 rounded text-xs" placeholder="변형 제목" />
              <textarea value={v.body} onChange={e => setV({ ...v, body: e.target.value })} rows={3} className="w-full px-2 py-1 border border-gray-200 rounded text-xs font-mono resize-y" placeholder="변형 본문 ({company_name} 사용 가능)" />
              <div className="flex justify-end gap-2">
                <button onClick={() => setAdding(false)} className="text-xs text-gray-500 cursor-pointer">취소</button>
                <button onClick={addVariant} className="text-xs px-2.5 py-1 bg-blue-600 text-white rounded cursor-pointer">추가</button>
              </div>
            </div>
          ) : (
            <button onClick={() => setAdding(true)} className="text-xs text-gray-500 hover:text-blue-600 cursor-pointer flex items-center gap-1">
              <Plus className="w-3 h-3" /> 변형 추가
            </button>
          )}
        </div>
      )}
    </div>
  )
}

export default function TemplatesPage() {
  const [templates, setTemplates] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState(null)
  const [form, setForm] = useState({ name: '', subject: '', body: '' })
  const [toast, setToast] = useState(null)

  const showToast = (msg, type = 'success') => { setToast({ message: msg, type }); setTimeout(() => setToast(null), 3000) }

  useEffect(() => {
    fetchTemplates()
  }, [])

  const fetchTemplates = () => {
    api.get('/templates').then((r) => setTemplates(r.data)).catch(() => {}).finally(() => setLoading(false))
  }

  const saveTemplate = async () => {
    if (!form.name.trim() || !form.subject.trim()) return
    try {
      if (editing) {
        await api.put(`/templates/${editing}`, form)
        showToast('템플릿이 수정되었습니다')
      } else {
        await api.post('/templates', form)
        showToast('템플릿이 생성되었습니다')
      }
      setShowForm(false)
      setEditing(null)
      setForm({ name: '', subject: '', body: '' })
      fetchTemplates()
    } catch (err) { showToast(err.response?.data?.detail || '실패', 'error') }
  }

  const editTemplate = (t) => {
    setForm({ name: t.name, subject: t.subject, body: t.body })
    setEditing(t.id)
    setShowForm(true)
  }

  const deleteTemplate = async (id) => {
    await api.delete(`/templates/${id}`)
    fetchTemplates()
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div></div>
  }

  return (
    <div>
      {toast && <div className={`fixed top-6 right-6 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium ${toast.type === 'error' ? 'bg-red-600 text-white' : 'bg-green-600 text-white'}`}>{toast.message}</div>}

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">이메일 템플릿</h1>
          <p className="text-gray-500 mt-1 text-sm">재사용 가능한 이메일 템플릿을 관리하세요</p>
        </div>
        <button onClick={() => { setForm({ name: '', subject: '', body: '' }); setEditing(null); setShowForm(true) }} className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 cursor-pointer">
          <Plus className="w-4 h-4" /> 새 템플릿
        </button>
      </div>

      {templates.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <p className="text-gray-400 mb-4">템플릿이 없습니다</p>
          <button onClick={() => setShowForm(true)} className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg cursor-pointer">첫 템플릿 만들기</button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {templates.map((t) => (
            <div key={t.id} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-start justify-between mb-3">
                <h3 className="font-medium text-gray-900">{t.name}</h3>
                <div className="flex gap-1">
                  <button onClick={() => editTemplate(t)} className="p-1 text-gray-400 hover:text-blue-600 cursor-pointer"><Edit2 className="w-3.5 h-3.5" /></button>
                  <button onClick={() => deleteTemplate(t.id)} className="p-1 text-gray-400 hover:text-red-600 cursor-pointer"><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
              </div>
              <p className="text-sm text-gray-600 font-medium mb-1">{t.subject}</p>
              <p className="text-xs text-gray-400 line-clamp-3">{t.body}</p>
              <VariantPanel template={t} showToast={showToast} />
            </div>
          ))}
        </div>
      )}

      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">{editing ? '템플릿 수정' : '새 템플릿'}</h3>
              <button onClick={() => setShowForm(false)} className="text-gray-400 cursor-pointer"><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">템플릿 이름</label>
                <input type="text" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="예: 초기 컨택 이메일" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">제목</label>
                <input type="text" value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="이메일 제목" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">본문</label>
                <textarea value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} rows={8} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono resize-y" placeholder="이메일 본문" />
                <p className="text-xs text-gray-400 mt-1">변수: {'{company_name}'}, {'{email}'}, {'{phone}'}</p>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-4">
              <button onClick={() => setShowForm(false)} className="px-4 py-2 text-sm text-gray-700 cursor-pointer">취소</button>
              <button onClick={saveTemplate} className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg cursor-pointer">{editing ? '수정' : '생성'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
