import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../lib/api'
import {
  FolderOpen,
  Users,
  Mail,
  MessageCircle,
  Plus,
  X,
  ChevronRight,
  Calendar,
  Eye,
  MousePointer,
} from 'lucide-react'
import OnboardingGuide from '../components/OnboardingGuide'

export default function DashboardPage() {
  const navigate = useNavigate()
  const [stats, setStats] = useState({
    total_projects: 0,
    total_prospects: 0,
    emails_sent: 0,
    dms_sent: 0,
    emails_opened: 0,
    emails_clicked: 0,
  })
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const [newProjectDesc, setNewProjectDesc] = useState('')
  const [creating, setCreating] = useState(false)
  const [toast, setToast] = useState(null)

  const showToast = (message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  const fetchData = async () => {
    try {
      const [statsRes, projectsRes] = await Promise.all([
        api.get('/dashboard/stats'),
        api.get('/projects'),
      ])
      setStats(statsRes.data)
      setProjects(projectsRes.data)
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleCreateProject = async (e) => {
    e.preventDefault()
    if (!newProjectName.trim()) return
    setCreating(true)
    try {
      const res = await api.post('/projects', {
        name: newProjectName.trim(),
        description: newProjectDesc.trim(),
      })
      setProjects((prev) => [res.data, ...prev])
      setStats((prev) => ({ ...prev, total_projects: prev.total_projects + 1 }))
      setShowModal(false)
      setNewProjectName('')
      setNewProjectDesc('')
      showToast('프로젝트가 생성되었습니다.')
    } catch (err) {
      showToast(err.response?.data?.detail || '프로젝트 생성에 실패했습니다.', 'error')
    } finally {
      setCreating(false)
    }
  }

  const statCards = [
    { label: '전체 프로젝트', value: stats.total_projects, icon: FolderOpen, color: 'text-blue-600 bg-blue-50' },
    { label: '전체 잠재고객', value: stats.total_prospects, icon: Users, color: 'text-green-600 bg-green-50' },
    { label: '이메일 발송', value: stats.emails_sent, icon: Mail, color: 'text-purple-600 bg-purple-50' },
    { label: 'DM 발송', value: stats.dms_sent, icon: MessageCircle, color: 'text-orange-600 bg-orange-50' },
    { label: '이메일 열람', value: stats.emails_opened, icon: Eye, color: 'text-violet-600 bg-violet-50' },
    { label: '링크 클릭', value: stats.emails_clicked, icon: MousePointer, color: 'text-teal-600 bg-teal-50' },
  ]

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div>
      {/* Toast */}
      {toast && (
        <div
          className={`fixed top-6 right-6 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium ${
            toast.type === 'error' ? 'bg-red-600 text-white' : 'bg-green-600 text-white'
          }`}
        >
          {toast.message}
        </div>
      )}

      <OnboardingGuide />

      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">대시보드</h1>
        <p className="text-gray-500 mt-1">영업 자동화 현황을 한눈에 확인하세요.</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {statCards.map((card) => (
          <div key={card.label} className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center gap-3">
              <div className={`p-2.5 rounded-lg ${card.color}`}>
                <card.icon className="w-5 h-5" />
              </div>
              <div>
                <p className="text-sm text-gray-500">{card.label}</p>
                <p className="text-2xl font-bold text-gray-900">{card.value.toLocaleString()}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Projects */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">프로젝트</h2>
        <button
          onClick={() => setShowModal(true)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          새 프로젝트
        </button>
      </div>

      {projects.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <FolderOpen className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 mb-4">아직 프로젝트가 없습니다.</p>
          <button
            onClick={() => setShowModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            첫 프로젝트 만들기
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {projects.map((project) => (
            <div
              key={project.id}
              onClick={() => navigate(`/projects/${project.id}`)}
              className="bg-white rounded-xl border border-gray-200 p-5 hover:border-blue-300 hover:shadow-sm transition-all cursor-pointer group"
            >
              <div className="flex items-start justify-between mb-3">
                <h3 className="font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">
                  {project.name}
                </h3>
                <ChevronRight className="w-4 h-4 text-gray-400 group-hover:text-blue-600 transition-colors mt-0.5" />
              </div>
              {project.description && (
                <p className="text-sm text-gray-500 mb-3 line-clamp-2">{project.description}</p>
              )}
              <div className="flex items-center gap-4 text-xs text-gray-400">
                <span className="inline-flex items-center gap-1">
                  <Users className="w-3.5 h-3.5" />
                  {project.prospect_count ?? 0}건
                </span>
                <span className="inline-flex items-center gap-1">
                  <Calendar className="w-3.5 h-3.5" />
                  {new Date(project.created_at).toLocaleDateString('ko-KR')}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md">
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">새 프로젝트</h3>
              <button
                onClick={() => setShowModal(false)}
                className="p-1 text-gray-400 hover:text-gray-600 cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateProject} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">프로젝트 이름</label>
                <input
                  type="text"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                  placeholder="예: 업소용 냉장고 업체 영업"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">설명 (선택)</label>
                <textarea
                  value={newProjectDesc}
                  onChange={(e) => setNewProjectDesc(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm resize-none"
                  placeholder="프로젝트에 대한 간단한 설명"
                />
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors cursor-pointer"
                >
                  취소
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 cursor-pointer"
                >
                  {creating ? '생성 중...' : '생성'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
