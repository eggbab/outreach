import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../lib/api'
import ProspectTable from '../components/ProspectTable'
import {
  ArrowLeft,
  Search,
  Plus,
  X,
  Trash2,
  Play,
  Loader2,
  Mail,
  Send,
  CheckCircle,
  AlertCircle,
  Chrome,
  MessageCircle,
  RefreshCw,
} from 'lucide-react'

const SOURCES = [
  { value: 'naver', label: '네이버' },
  { value: 'google', label: '구글' },
  { value: 'instagram', label: '인스타그램' },
  { value: 'naver_shopping', label: '네이버쇼핑' },
  { value: 'naver_map', label: '네이버지도' },
]

const TABS = [
  { key: 'keywords', label: '키워드 관리', icon: Search },
  { key: 'prospects', label: '수집 결과', icon: CheckCircle },
  { key: 'email', label: '이메일 발송', icon: Mail },
  { key: 'dm', label: '인스타 DM', icon: MessageCircle },
]

export default function ProjectDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('keywords')
  const [project, setProject] = useState(null)
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState(null)

  const showToast = (message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  useEffect(() => {
    api.get(`/projects/${id}`)
      .then((res) => setProject(res.data))
      .catch(() => navigate('/'))
      .finally(() => setLoading(false))
  }, [id, navigate])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!project) return null

  return (
    <div>
      {toast && (
        <div
          className={`fixed top-6 right-6 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium ${
            toast.type === 'error' ? 'bg-red-600 text-white' : 'bg-green-600 text-white'
          }`}
        >
          {toast.message}
        </div>
      )}

      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate('/')}
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-3 cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" />
          대시보드로 돌아가기
        </button>
        <h1 className="text-2xl font-bold text-gray-900">{project.name}</h1>
        {project.description && <p className="text-gray-500 mt-1">{project.description}</p>}
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <div className="flex gap-0 -mb-px">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`inline-flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors cursor-pointer ${
                activeTab === tab.key
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'keywords' && <KeywordsTab projectId={id} showToast={showToast} />}
      {activeTab === 'prospects' && <ProspectsTab projectId={id} showToast={showToast} />}
      {activeTab === 'email' && <EmailTab projectId={id} showToast={showToast} />}
      {activeTab === 'dm' && <DmTab projectId={id} showToast={showToast} />}
    </div>
  )
}

function KeywordsTab({ projectId, showToast }) {
  const [keywords, setKeywords] = useState([])
  const [newKeyword, setNewKeyword] = useState('')
  const [selectedSources, setSelectedSources] = useState(['naver', 'google'])
  const [collecting, setCollecting] = useState(false)
  const [progress, setProgress] = useState(null)
  const [loading, setLoading] = useState(true)
  const progressInterval = useRef(null)

  useEffect(() => {
    api.get(`/projects/${projectId}/keywords`)
      .then((res) => setKeywords(res.data))
      .catch(() => {})
      .finally(() => setLoading(false))
    return () => {
      if (progressInterval.current) clearInterval(progressInterval.current)
    }
  }, [projectId])

  const addKeyword = async (e) => {
    e.preventDefault()
    if (!newKeyword.trim()) return
    try {
      const res = await api.post(`/projects/${projectId}/keywords`, { keyword: newKeyword.trim() })
      setKeywords((prev) => [...prev, res.data])
      setNewKeyword('')
    } catch (err) {
      showToast(err.response?.data?.detail || '키워드 추가 실패', 'error')
    }
  }

  const removeKeyword = async (keywordId) => {
    try {
      await api.delete(`/projects/${projectId}/keywords/${keywordId}`)
      setKeywords((prev) => prev.filter((k) => k.id !== keywordId))
    } catch {
      showToast('키워드 삭제 실패', 'error')
    }
  }

  const toggleSource = (source) => {
    setSelectedSources((prev) =>
      prev.includes(source) ? prev.filter((s) => s !== source) : [...prev, source]
    )
  }

  const startCollection = async () => {
    if (keywords.length === 0) {
      showToast('키워드를 먼저 추가해주세요.', 'error')
      return
    }
    if (selectedSources.length === 0) {
      showToast('수집 소스를 선택해주세요.', 'error')
      return
    }
    setCollecting(true)
    setProgress({ status: 'running', current: 0, total: 0, message: '수집 시작 중...' })
    try {
      await api.post(`/projects/${projectId}/collect`, { sources: selectedSources })
      progressInterval.current = setInterval(async () => {
        try {
          const res = await api.get(`/projects/${projectId}/collect/status`)
          setProgress(res.data)
          if (res.data.status === 'completed' || res.data.status === 'error') {
            clearInterval(progressInterval.current)
            progressInterval.current = null
            setCollecting(false)
            if (res.data.status === 'completed') {
              showToast(`수집 완료! ${res.data.total}건의 업체를 찾았습니다.`)
            } else {
              showToast('수집 중 오류가 발생했습니다.', 'error')
            }
          }
        } catch {
          clearInterval(progressInterval.current)
          progressInterval.current = null
          setCollecting(false)
        }
      }, 2000)
    } catch (err) {
      setCollecting(false)
      setProgress(null)
      showToast(err.response?.data?.detail || '수집 시작 실패', 'error')
    }
  }

  if (loading) {
    return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin text-gray-400" /></div>
  }

  return (
    <div className="space-y-6">
      {/* Add keyword */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">키워드 추가</h3>
        <form onSubmit={addKeyword} className="flex gap-3">
          <input
            type="text"
            value={newKeyword}
            onChange={(e) => setNewKeyword(e.target.value)}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            placeholder="예: 업소용 냉장고, 마트 진열대"
          />
          <button
            type="submit"
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            추가
          </button>
        </form>

        {keywords.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-4">
            {keywords.map((k) => (
              <span
                key={k.id}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 rounded-full text-sm text-gray-700"
              >
                {k.keyword}
                <button
                  onClick={() => removeKeyword(k.id)}
                  className="text-gray-400 hover:text-red-500 cursor-pointer"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Sources */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">수집 소스</h3>
        <div className="flex flex-wrap gap-3">
          {SOURCES.map((source) => (
            <button
              key={source.value}
              onClick={() => toggleSource(source.value)}
              className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors cursor-pointer ${
                selectedSources.includes(source.value)
                  ? 'border-blue-600 bg-blue-50 text-blue-700'
                  : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
              }`}
            >
              {source.label}
            </button>
          ))}
        </div>
      </div>

      {/* Collect button */}
      <div className="flex items-center gap-4">
        <button
          onClick={startCollection}
          disabled={collecting}
          className="inline-flex items-center gap-2 px-6 py-2.5 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
        >
          {collecting ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              수집 중...
            </>
          ) : (
            <>
              <Play className="w-4 h-4" />
              수집 시작
            </>
          )}
        </button>
      </div>

      {/* Progress */}
      {progress && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-3">
            {progress.status === 'running' ? (
              <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
            ) : progress.status === 'completed' ? (
              <CheckCircle className="w-5 h-5 text-green-600" />
            ) : (
              <AlertCircle className="w-5 h-5 text-red-600" />
            )}
            <span className="text-sm font-medium text-gray-900">
              {progress.status === 'running' ? '수집 진행 중' : progress.status === 'completed' ? '수집 완료' : '오류 발생'}
            </span>
          </div>
          {progress.total > 0 && (
            <div className="mb-2">
              <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span>{progress.current} / {progress.total}</span>
                <span>{Math.round((progress.current / progress.total) * 100)}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${(progress.current / progress.total) * 100}%` }}
                />
              </div>
            </div>
          )}
          {progress.message && (
            <p className="text-xs text-gray-500 mt-2">{progress.message}</p>
          )}
        </div>
      )}
    </div>
  )
}

function ProspectsTab({ projectId, showToast }) {
  const [prospects, setProspects] = useState([])
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [loading, setLoading] = useState(true)

  const fetchProspects = async (p = 1) => {
    setLoading(true)
    try {
      const res = await api.get(`/projects/${projectId}/prospects`, { params: { page: p, per_page: 20 } })
      setProspects(res.data.items)
      setTotalPages(res.data.total_pages)
      setPage(p)
    } catch {
      showToast('데이터 로드 실패', 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchProspects()
  }, [projectId])

  const handleApprove = async (prospectId) => {
    try {
      await api.patch(`/projects/${projectId}/prospects/${prospectId}`, { status: 'approved' })
      setProspects((prev) => prev.map((p) => (p.id === prospectId ? { ...p, status: 'approved' } : p)))
    } catch {
      showToast('상태 변경 실패', 'error')
    }
  }

  const handleReject = async (prospectId) => {
    try {
      await api.patch(`/projects/${projectId}/prospects/${prospectId}`, { status: 'rejected' })
      setProspects((prev) => prev.map((p) => (p.id === prospectId ? { ...p, status: 'rejected' } : p)))
    } catch {
      showToast('상태 변경 실패', 'error')
    }
  }

  const handleApproveAll = async () => {
    try {
      await api.post(`/projects/${projectId}/prospects/approve-all`)
      setProspects((prev) =>
        prev.map((p) => (p.status === 'collected' ? { ...p, status: 'approved' } : p))
      )
      showToast('전체 승인 완료')
    } catch {
      showToast('전체 승인 실패', 'error')
    }
  }

  if (loading) {
    return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin text-gray-400" /></div>
  }

  return (
    <ProspectTable
      prospects={prospects}
      page={page}
      totalPages={totalPages}
      onPageChange={fetchProspects}
      onApprove={handleApprove}
      onReject={handleReject}
      onApproveAll={handleApproveAll}
    />
  )
}

function EmailTab({ projectId, showToast }) {
  const [prospects, setProspects] = useState([])
  const [sending, setSending] = useState(false)
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [testSending, setTestSending] = useState(false)

  useEffect(() => {
    api.get(`/projects/${projectId}/prospects`, { params: { status: 'approved', has_email: true, per_page: 100 } })
      .then((res) => setProspects(res.data.items || res.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [projectId])

  const startSending = async () => {
    setSending(true)
    setLogs([])
    try {
      const res = await api.post(`/projects/${projectId}/send/email`)
      setLogs(res.data.logs || [{ message: `${res.data.sent_count}건 발송 완료`, type: 'success' }])
      showToast(`이메일 ${res.data.sent_count}건 발송 완료`)
    } catch (err) {
      showToast(err.response?.data?.detail || '발송 실패', 'error')
      setLogs((prev) => [...prev, { message: '발송 중 오류 발생', type: 'error' }])
    } finally {
      setSending(false)
    }
  }

  const sendTest = async () => {
    setTestSending(true)
    try {
      await api.post(`/projects/${projectId}/send/email/test`)
      showToast('테스트 이메일 발송 완료')
    } catch (err) {
      showToast(err.response?.data?.detail || '테스트 발송 실패', 'error')
    } finally {
      setTestSending(false)
    }
  }

  if (loading) {
    return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin text-gray-400" /></div>
  }

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-gray-900">이메일 발송 대상</h3>
            <p className="text-sm text-gray-500 mt-1">승인된 업체 중 이메일이 있는 업체: {prospects.length}건</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={sendTest}
              disabled={testSending}
              className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50 cursor-pointer"
            >
              {testSending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mail className="w-4 h-4" />}
              테스트 발송
            </button>
            <button
              onClick={startSending}
              disabled={sending || prospects.length === 0}
              className="inline-flex items-center gap-2 px-6 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {sending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  발송 중...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  발송 시작
                </>
              )}
            </button>
          </div>
        </div>

        {/* Prospect list preview */}
        {prospects.length > 0 && (
          <div className="border border-gray-200 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="text-left px-4 py-2.5 font-medium text-gray-600">업체명</th>
                  <th className="text-left px-4 py-2.5 font-medium text-gray-600">이메일</th>
                  <th className="text-left px-4 py-2.5 font-medium text-gray-600">상태</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {prospects.slice(0, 10).map((p) => (
                  <tr key={p.id}>
                    <td className="px-4 py-2.5 text-gray-900">{p.name}</td>
                    <td className="px-4 py-2.5 text-gray-600">{p.email}</td>
                    <td className="px-4 py-2.5">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                        p.status === 'sent' ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'
                      }`}>
                        {p.status === 'sent' ? '발송완료' : '승인'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {prospects.length > 10 && (
              <div className="px-4 py-2 bg-gray-50 text-xs text-gray-500 border-t border-gray-200">
                외 {prospects.length - 10}건 더
              </div>
            )}
          </div>
        )}
      </div>

      {/* Logs */}
      {logs.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">발송 로그</h3>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {logs.map((log, i) => (
              <div
                key={i}
                className={`text-sm px-3 py-2 rounded-lg ${
                  log.type === 'error' ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'
                }`}
              >
                {log.message}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function DmTab({ projectId, showToast }) {
  const [extensionConnected, setExtensionConnected] = useState(false)
  const [queue, setQueue] = useState([])
  const [sentLog, setSentLog] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.get(`/projects/${projectId}/dm/status`).catch(() => ({ data: { connected: false } })),
      api.get(`/projects/${projectId}/dm/queue`).catch(() => ({ data: [] })),
      api.get(`/projects/${projectId}/dm/log`).catch(() => ({ data: [] })),
    ]).then(([statusRes, queueRes, logRes]) => {
      setExtensionConnected(statusRes.data.connected)
      setQueue(queueRes.data)
      setSentLog(logRes.data)
    }).finally(() => setLoading(false))
  }, [projectId])

  const checkConnection = async () => {
    try {
      const res = await api.get(`/projects/${projectId}/dm/status`)
      setExtensionConnected(res.data.connected)
      if (res.data.connected) {
        showToast('Chrome 확장프로그램 연결됨')
      } else {
        showToast('확장프로그램이 감지되지 않습니다.', 'error')
      }
    } catch {
      showToast('연결 확인 실패', 'error')
    }
  }

  if (loading) {
    return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin text-gray-400" /></div>
  }

  return (
    <div className="space-y-6">
      {/* Extension status */}
      <div className={`rounded-xl border p-6 ${
        extensionConnected ? 'bg-green-50 border-green-200' : 'bg-amber-50 border-amber-200'
      }`}>
        <div className="flex items-start gap-4">
          <Chrome className={`w-8 h-8 mt-0.5 ${extensionConnected ? 'text-green-600' : 'text-amber-600'}`} />
          <div className="flex-1">
            <h3 className={`font-semibold ${extensionConnected ? 'text-green-800' : 'text-amber-800'}`}>
              {extensionConnected ? 'Chrome 확장프로그램 연결됨' : 'Chrome 확장프로그램 필요'}
            </h3>
            <p className={`text-sm mt-1 ${extensionConnected ? 'text-green-700' : 'text-amber-700'}`}>
              {extensionConnected
                ? '인스타그램 DM을 발송할 준비가 되었습니다.'
                : '인스타그램 DM 자동 발송을 위해 Chrome 확장프로그램을 설치해주세요. 확장프로그램은 로그인된 Instagram 세션을 활용하여 안전하게 DM을 발송합니다.'
              }
            </p>
            {!extensionConnected && (
              <div className="mt-3 flex gap-3">
                <button
                  onClick={checkConnection}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-amber-600 text-white text-sm font-medium rounded-lg hover:bg-amber-700 transition-colors cursor-pointer"
                >
                  <RefreshCw className="w-4 h-4" />
                  연결 확인
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* DM Queue */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">DM 발송 대기열</h3>
        {queue.length === 0 ? (
          <p className="text-sm text-gray-400 py-8 text-center">발송 대기 중인 DM이 없습니다.</p>
        ) : (
          <div className="border border-gray-200 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="text-left px-4 py-2.5 font-medium text-gray-600">업체명</th>
                  <th className="text-left px-4 py-2.5 font-medium text-gray-600">인스타그램</th>
                  <th className="text-left px-4 py-2.5 font-medium text-gray-600">상태</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {queue.map((item, i) => (
                  <tr key={i}>
                    <td className="px-4 py-2.5 text-gray-900">{item.name}</td>
                    <td className="px-4 py-2.5 text-blue-600">@{item.instagram}</td>
                    <td className="px-4 py-2.5">
                      <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700">
                        대기
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Sent log */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">발송 완료 로그</h3>
        {sentLog.length === 0 ? (
          <p className="text-sm text-gray-400 py-8 text-center">아직 발송된 DM이 없습니다.</p>
        ) : (
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {sentLog.map((log, i) => (
              <div key={i} className="flex items-center justify-between px-3 py-2 bg-gray-50 rounded-lg text-sm">
                <span className="text-gray-900">@{log.instagram} - {log.name}</span>
                <span className="text-xs text-gray-400">
                  {new Date(log.sent_at).toLocaleString('ko-KR')}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
