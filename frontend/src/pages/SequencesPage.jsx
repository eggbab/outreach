import { useState, useEffect } from 'react'
import api from '../lib/api'
import { Plus, Play, Pause, Trash2, ChevronRight, X } from 'lucide-react'

export default function SequencesPage() {
  const [projects, setProjects] = useState([])
  const [selectedProject, setSelectedProject] = useState('')
  const [sequences, setSequences] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [selectedSeq, setSelectedSeq] = useState(null)
  const [steps, setSteps] = useState([])
  const [showStepForm, setShowStepForm] = useState(false)
  const [stepForm, setStepForm] = useState({ step_number: 1, delay_days: 1, subject: '', body: '', send_condition: 'always' })
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
    fetchSequences()
  }, [selectedProject])

  const fetchSequences = () => {
    api.get(`/projects/${selectedProject}/sequences`).then((r) => setSequences(r.data)).catch(() => {})
  }

  const createSequence = async () => {
    if (!newName.trim()) return
    try {
      await api.post(`/projects/${selectedProject}/sequences`, { name: newName.trim() })
      setNewName('')
      setShowCreate(false)
      fetchSequences()
      showToast('시퀀스가 생성되었습니다')
    } catch (err) { showToast(err.response?.data?.detail || '실패', 'error') }
  }

  const toggleStatus = async (seq) => {
    const newStatus = seq.status === 'active' ? 'paused' : 'active'
    await api.put(`/projects/${selectedProject}/sequences/${seq.id}/status?new_status=${newStatus}`)
    fetchSequences()
  }

  const deleteSequence = async (id) => {
    await api.delete(`/projects/${selectedProject}/sequences/${id}`)
    if (selectedSeq?.id === id) { setSelectedSeq(null); setSteps([]) }
    fetchSequences()
  }

  const selectSequence = async (seq) => {
    setSelectedSeq(seq)
    const r = await api.get(`/projects/${selectedProject}/sequences/${seq.id}/steps`)
    setSteps(r.data)
  }

  const addStep = async () => {
    try {
      await api.post(`/projects/${selectedProject}/sequences/${selectedSeq.id}/steps`, stepForm)
      setShowStepForm(false)
      setStepForm({ step_number: steps.length + 2, delay_days: 1, subject: '', body: '', send_condition: 'always' })
      const r = await api.get(`/projects/${selectedProject}/sequences/${selectedSeq.id}/steps`)
      setSteps(r.data)
      showToast('스텝이 추가되었습니다')
    } catch (err) { showToast(err.response?.data?.detail || '실패', 'error') }
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div></div>
  }

  return (
    <div>
      {toast && <div className={`fixed top-6 right-6 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium ${toast.type === 'error' ? 'bg-red-600 text-white' : 'bg-green-600 text-white'}`}>{toast.message}</div>}

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">이메일 시퀀스</h1>
          <p className="text-gray-500 mt-1 text-sm">자동 후속 이메일로 응답률을 높이세요</p>
        </div>
        <div className="flex gap-3">
          <select value={selectedProject} onChange={(e) => setSelectedProject(e.target.value)} className="px-3 py-2 border border-gray-300 rounded-lg text-sm">
            {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <button onClick={() => setShowCreate(true)} className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 cursor-pointer">
            <Plus className="w-4 h-4" /> 새 시퀀스
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sequence list */}
        <div className="space-y-3">
          {sequences.map((seq) => (
            <div
              key={seq.id}
              onClick={() => selectSequence(seq)}
              className={`bg-white rounded-xl border p-4 cursor-pointer transition-all ${selectedSeq?.id === seq.id ? 'border-blue-300 ring-1 ring-blue-100' : 'border-gray-200 hover:border-gray-300'}`}
            >
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-medium text-gray-900 text-sm">{seq.name}</h3>
                <div className="flex gap-1">
                  <button onClick={(e) => { e.stopPropagation(); toggleStatus(seq) }} className="p-1 text-gray-400 hover:text-blue-600 cursor-pointer">
                    {seq.status === 'active' ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
                  </button>
                  <button onClick={(e) => { e.stopPropagation(); deleteSequence(seq.id) }} className="p-1 text-gray-400 hover:text-red-600 cursor-pointer">
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
              <div className="flex gap-3 text-xs text-gray-500">
                <span className={`px-1.5 py-0.5 rounded ${seq.status === 'active' ? 'bg-green-50 text-green-700' : seq.status === 'paused' ? 'bg-yellow-50 text-yellow-700' : 'bg-gray-100 text-gray-600'}`}>
                  {seq.status === 'active' ? '실행중' : seq.status === 'paused' ? '일시중지' : '초안'}
                </span>
                <span>{seq.step_count || 0}단계</span>
                <span>{seq.enrollment_count || 0}명 등록</span>
              </div>
            </div>
          ))}
          {sequences.length === 0 && <p className="text-sm text-gray-400 text-center py-8">시퀀스가 없습니다</p>}
        </div>

        {/* Steps detail */}
        <div className="lg:col-span-2">
          {selectedSeq ? (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-base font-semibold text-gray-900">{selectedSeq.name} — 스텝</h2>
                <button onClick={() => { setStepForm({ ...stepForm, step_number: steps.length + 1 }); setShowStepForm(true) }} className="inline-flex items-center gap-1 px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-lg cursor-pointer">
                  <Plus className="w-3.5 h-3.5" /> 스텝 추가
                </button>
              </div>

              {steps.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-8">스텝을 추가하세요</p>
              ) : (
                <div className="space-y-3">
                  {steps.map((step, i) => (
                    <div key={step.id} className="border border-gray-200 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 text-xs font-bold flex items-center justify-center">{step.step_number}</span>
                        <span className="text-xs text-gray-500">{step.delay_days}일 후 발송</span>
                        <span className="text-xs text-gray-400 ml-auto">
                          {step.send_condition === 'always' ? '항상' : step.send_condition === 'not_opened' ? '미열람시' : '미클릭시'}
                        </span>
                      </div>
                      <p className="text-sm font-medium text-gray-900">{step.subject}</p>
                      <p className="text-xs text-gray-500 mt-1 line-clamp-2">{step.body}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-64 text-sm text-gray-400">시퀀스를 선택하세요</div>
          )}
        </div>
      </div>

      {/* Create modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">새 시퀀스</h3>
              <button onClick={() => setShowCreate(false)} className="text-gray-400 cursor-pointer"><X className="w-5 h-5" /></button>
            </div>
            <input type="text" value={newName} onChange={(e) => setNewName(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && createSequence()} placeholder="시퀀스 이름" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm mb-4" autoFocus />
            <div className="flex justify-end gap-3">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-gray-700 cursor-pointer">취소</button>
              <button onClick={createSequence} className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg cursor-pointer">생성</button>
            </div>
          </div>
        </div>
      )}

      {/* Step form modal */}
      {showStepForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">스텝 추가</h3>
              <button onClick={() => setShowStepForm(false)} className="text-gray-400 cursor-pointer"><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">스텝 번호</label>
                  <input type="number" value={stepForm.step_number} onChange={(e) => setStepForm({ ...stepForm, step_number: parseInt(e.target.value) })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">대기 일수</label>
                  <input type="number" value={stepForm.delay_days} onChange={(e) => setStepForm({ ...stepForm, delay_days: parseInt(e.target.value) })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">발송 조건</label>
                  <select value={stepForm.send_condition} onChange={(e) => setStepForm({ ...stepForm, send_condition: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
                    <option value="always">항상</option>
                    <option value="not_opened">미열람시</option>
                    <option value="not_clicked">미클릭시</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">제목</label>
                <input type="text" value={stepForm.subject} onChange={(e) => setStepForm({ ...stepForm, subject: e.target.value })} placeholder="이메일 제목" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">본문</label>
                <textarea value={stepForm.body} onChange={(e) => setStepForm({ ...stepForm, body: e.target.value })} rows={5} placeholder="이메일 본문" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm resize-y" />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-4">
              <button onClick={() => setShowStepForm(false)} className="px-4 py-2 text-sm text-gray-700 cursor-pointer">취소</button>
              <button onClick={addStep} className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg cursor-pointer">추가</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
