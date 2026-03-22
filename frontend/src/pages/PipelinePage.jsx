import { useState, useEffect, useRef } from 'react'
import api from '../lib/api'
import { Plus, X, GripVertical } from 'lucide-react'

export default function PipelinePage() {
  const [stages, setStages] = useState([])
  const [deals, setDeals] = useState([])
  const [loading, setLoading] = useState(true)
  const [showDealForm, setShowDealForm] = useState(null) // stage_id
  const [dealForm, setDealForm] = useState({ title: '', value: 0, prospect_id: '', project_id: '' })
  const [projects, setProjects] = useState([])
  const [stats, setStats] = useState(null)
  const [draggedDeal, setDraggedDeal] = useState(null)
  const [toast, setToast] = useState(null)

  const showToast = (msg) => { setToast(msg); setTimeout(() => setToast(null), 3000) }

  useEffect(() => {
    Promise.all([
      api.get('/pipeline/stages'),
      api.get('/pipeline/deals'),
      api.get('/projects'),
      api.get('/pipeline/stats'),
    ]).then(([stagesR, dealsR, projectsR, statsR]) => {
      setStages(stagesR.data)
      setDeals(dealsR.data)
      setProjects(projectsR.data)
      setStats(statsR.data)
    }).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const createDeal = async (stageId) => {
    if (!dealForm.title.trim() || !dealForm.project_id) return
    try {
      const res = await api.post('/pipeline/deals', {
        ...dealForm,
        stage_id: stageId,
        prospect_id: parseInt(dealForm.prospect_id) || 0,
        project_id: parseInt(dealForm.project_id),
        value: parseInt(dealForm.value) || 0,
      })
      setDeals([...deals, res.data])
      setShowDealForm(null)
      setDealForm({ title: '', value: 0, prospect_id: '', project_id: '' })
      showToast('딜이 생성되었습니다')
    } catch {}
  }

  const moveDeal = async (dealId, newStageId) => {
    try {
      const res = await api.put(`/pipeline/deals/${dealId}/move`, { stage_id: newStageId })
      setDeals(deals.map((d) => d.id === dealId ? res.data : d))
    } catch {}
  }

  const handleDragStart = (e, deal) => {
    setDraggedDeal(deal)
    e.dataTransfer.effectAllowed = 'move'
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }

  const handleDrop = (e, stageId) => {
    e.preventDefault()
    if (draggedDeal && draggedDeal.stage_id !== stageId) {
      moveDeal(draggedDeal.id, stageId)
    }
    setDraggedDeal(null)
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div></div>
  }

  return (
    <div>
      {toast && <div className="fixed top-6 right-6 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium bg-green-600 text-white">{toast}</div>}

      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">영업 파이프라인</h1>
        {stats && (
          <div className="flex gap-4 mt-2 text-sm text-gray-500">
            <span>전체 {stats.total_deals}건</span>
            <span>총 {stats.total_value.toLocaleString()}원</span>
            <span className="text-green-600">성사 {stats.won_deals}건 ({stats.won_value.toLocaleString()}원)</span>
          </div>
        )}
      </div>

      <div className="flex gap-4 overflow-x-auto pb-4" style={{ minHeight: '60vh' }}>
        {stages.map((stage) => {
          const stageDeals = deals.filter((d) => d.stage_id === stage.id)
          const stageTotal = stageDeals.reduce((s, d) => s + d.value, 0)
          return (
            <div
              key={stage.id}
              className="w-72 shrink-0 bg-gray-50 rounded-xl p-3"
              onDragOver={handleDragOver}
              onDrop={(e) => handleDrop(e, stage.id)}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: stage.color }} />
                  <span className="text-sm font-semibold text-gray-700">{stage.name}</span>
                  <span className="text-xs text-gray-400">{stageDeals.length}</span>
                </div>
                <span className="text-xs text-gray-500">{stageTotal.toLocaleString()}원</span>
              </div>

              <div className="space-y-2 min-h-[100px]">
                {stageDeals.map((deal) => (
                  <div
                    key={deal.id}
                    draggable
                    onDragStart={(e) => handleDragStart(e, deal)}
                    className="bg-white rounded-lg border border-gray-200 p-3 cursor-grab active:cursor-grabbing hover:shadow-sm transition-shadow"
                  >
                    <p className="text-sm font-medium text-gray-900 mb-1">{deal.title}</p>
                    <p className="text-xs text-gray-500">{deal.value.toLocaleString()}원</p>
                  </div>
                ))}
              </div>

              {showDealForm === stage.id ? (
                <div className="mt-2 bg-white rounded-lg border border-gray-200 p-3 space-y-2">
                  <input type="text" value={dealForm.title} onChange={(e) => setDealForm({ ...dealForm, title: e.target.value })} placeholder="딜 제목" className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm" autoFocus />
                  <input type="number" value={dealForm.value} onChange={(e) => setDealForm({ ...dealForm, value: e.target.value })} placeholder="금액 (원)" className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm" />
                  <select value={dealForm.project_id} onChange={(e) => setDealForm({ ...dealForm, project_id: e.target.value })} className="w-full px-2 py-1.5 border border-gray-300 rounded text-sm">
                    <option value="">프로젝트 선택</option>
                    {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                  <div className="flex justify-end gap-2">
                    <button onClick={() => setShowDealForm(null)} className="px-2 py-1 text-xs text-gray-500 cursor-pointer">취소</button>
                    <button onClick={() => createDeal(stage.id)} className="px-2 py-1 bg-blue-600 text-white text-xs rounded cursor-pointer">추가</button>
                  </div>
                </div>
              ) : (
                <button onClick={() => setShowDealForm(stage.id)} className="mt-2 w-full flex items-center justify-center gap-1 py-2 text-xs text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors cursor-pointer">
                  <Plus className="w-3.5 h-3.5" /> 딜 추가
                </button>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
