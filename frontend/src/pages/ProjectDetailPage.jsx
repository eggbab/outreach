import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
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
  MessageCircle,
  Download,
  Clock,
  ShieldX,
} from 'lucide-react'

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
      .catch(() => navigate('/dashboard'))
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
          onClick={() => navigate('/dashboard')}
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-3 cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" />
          대시보드로 돌아가기
        </button>
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">{project.name}</h1>
          <button
            onClick={async () => {
              if (!window.confirm('정말로 이 프로젝트를 삭제하시겠습니까?')) return
              try {
                await api.delete(`/projects/${id}`)
                navigate('/dashboard')
              } catch (err) {
                showToast(err.response?.data?.detail || '프로젝트 삭제 실패', 'error')
              }
            }}
            className="inline-flex items-center gap-1 text-sm text-red-500 hover:text-red-700 cursor-pointer"
          >
            <Trash2 className="w-4 h-4" />
            삭제
          </button>
        </div>
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
  const [maxResults, setMaxResults] = useState(20)
  const [matchLevel, setMatchLevel] = useState('medium')
  const [collecting, setCollecting] = useState(false)
  const [progress, setProgress] = useState(null)
  const [usage, setUsage] = useState(null)
  const [loading, setLoading] = useState(true)
  const progressInterval = useRef(null)

  useEffect(() => {
    Promise.all([
      api.get(`/projects/${projectId}/keywords`),
      api.get('/subscription/usage'),
    ]).then(([kwRes, usageRes]) => {
      setKeywords(kwRes.data)
      setUsage(usageRes.data)
    }).catch(() => {}).finally(() => setLoading(false))
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

  const startCollection = async () => {
    if (keywords.length === 0) {
      showToast('키워드를 먼저 추가해주세요.', 'error')
      return
    }
    setCollecting(true)
    setProgress({ status: 'running', current: 0, total: 0, message: '수집 시작 중...' })
    try {
      await api.post(`/projects/${projectId}/collect`, { max_results: maxResults, match_level: matchLevel })
      progressInterval.current = setInterval(async () => {
        try {
          const res = await api.get(`/projects/${projectId}/collect/status`)
          setProgress(res.data)
          if (res.data.status === 'completed' || res.data.status === 'error') {
            clearInterval(progressInterval.current)
            progressInterval.current = null
            setCollecting(false)
            if (res.data.status === 'completed') {
              showToast(`수집 완료! ${res.data.prospects_found}건의 업체를 찾았습니다.`)
            } else {
              showToast(`수집 중 오류가 발생했습니다.${res.data.error ? ' ' + res.data.error : ''}`, 'error')
            }
          }
        } catch {
          clearInterval(progressInterval.current)
          progressInterval.current = null
          setCollecting(false)
        }
      }, 1500)
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

      {/* Credits + Usage */}
      {usage && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <h3 className="text-sm font-semibold text-gray-900">오늘 사용량</h3>
              <span className="text-xs font-medium px-2.5 py-0.5 rounded-full bg-yellow-50 text-yellow-700">
                {usage.credits} 크레딧
              </span>
            </div>
            <Link to="/pricing" className="text-xs text-blue-600 hover:underline">충전하기</Link>
          </div>
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: '수집', used: usage.prospects_collected, cost: usage.overage_rates?.prospect || 1 },
              { label: '이메일', used: usage.emails_sent, cost: usage.overage_rates?.email || 2 },
              { label: 'DM', used: usage.dms_sent, cost: usage.overage_rates?.dm || 3 },
            ].map((item) => (
              <div key={item.label} className="text-center">
                <p className="text-xs text-gray-500">{item.label}</p>
                <p className="text-lg font-bold text-gray-900">{item.used}</p>
                <p className="text-[10px] text-gray-400">{item.cost}cr/건</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 수집 로직 안내 */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-blue-900 mb-2">📥 어떻게 동작하나요?</h3>
        <ol className="space-y-1.5 text-sm text-blue-800 list-decimal list-inside">
          <li>위에서 입력한 <strong>키워드</strong>로 네이버 웹 + 쇼핑 + 지도 + 구글에 자동 검색</li>
          <li>검색 결과 사이트들을 한 곳씩 방문 (헤드리스 브라우저)</li>
          <li>각 사이트에서 <strong>이메일·전화번호·인스타 핸들·회사명</strong> 자동 추출 (5단계 탐색: 메인→링크→하위경로→푸터→mailto)</li>
          <li>아래 <strong>정밀도 설정</strong>에 따라 키워드와 잘 맞는 페이지만 저장</li>
          <li>중복·블랙리스트 자동 제외 → 잠재고객 목록에 등록 (수집 1건 = 1 크레딧)</li>
        </ol>
      </div>

      {/* Collect */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-900">업체 수집</h3>
          <button
            onClick={startCollection}
            disabled={collecting}
            className="inline-flex items-center gap-2 px-5 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {collecting ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> 수집 중...</>
            ) : (
              <><Play className="w-4 h-4" /> 수집 시작</>
            )}
          </button>
        </div>

        {/* 키워드당 수집 수 */}
        <div className="mb-5">
          <div className="text-xs font-medium text-gray-700 mb-2">키워드당 수집 개수</div>
          <div className="flex items-center gap-3">
            <div className="flex gap-1.5">
              {[10, 20, 50, 100].map((n) => (
                <button
                  key={n}
                  onClick={() => setMaxResults(n)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium cursor-pointer ${
                    maxResults === n ? 'bg-green-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                >{n}개</button>
              ))}
            </div>
          </div>
        </div>

        {/* 정밀도 */}
        <div className="mb-2">
          <div className="text-xs font-medium text-gray-700 mb-2">키워드 매칭 정밀도</div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {[
              { value: 'loose', title: '느슨', desc: '검색 결과 모두 가져옴', sub: '양 ↑ 정확도 ↓ · 가장 많이 모임' },
              { value: 'medium', title: '보통 (권장)', desc: '제목 또는 본문에 키워드 포함', sub: '양과 정확도 균형' },
              { value: 'strict', title: '엄격', desc: '제목·본문 모두에 키워드 포함', sub: '양 ↓ 정확도 ↑ · 진짜 타겟만' },
            ].map(opt => (
              <button
                key={opt.value}
                onClick={() => setMatchLevel(opt.value)}
                className={`text-left p-3 rounded-lg border-2 cursor-pointer transition-all ${
                  matchLevel === opt.value
                    ? 'border-green-600 bg-green-50'
                    : 'border-gray-200 bg-white hover:border-gray-300'
                }`}
              >
                <div className={`text-sm font-semibold ${matchLevel === opt.value ? 'text-green-700' : 'text-gray-900'}`}>
                  {opt.title}
                </div>
                <div className="text-xs text-gray-600 mt-0.5">{opt.desc}</div>
                <div className="text-[10px] text-gray-400 mt-1">{opt.sub}</div>
              </button>
            ))}
          </div>
        </div>

        {keywords.length > 0 && (
          <p className="text-xs text-gray-500 mt-4 pt-3 border-t border-gray-100">
            키워드 {keywords.length}개 × {maxResults}개 = 최대 <span className="font-medium text-gray-700">{keywords.length * maxResults}개</span> 수집 예정
            {usage && <span className="ml-2">· 예상 최대 {keywords.length * maxResults * (usage.overage_rates?.prospect || 1)} 크레딧</span>}
            <br/>
            <span className="text-gray-400">(정밀도 "엄격"이면 키워드와 안 맞는 페이지는 자동 제외돼서 실제 수집은 더 적을 수 있어요)</span>
          </p>
        )}
      </div>

      {/* Progress */}
      {progress && (
        <div className={`rounded-xl border p-6 ${
          progress.status === 'running' ? 'bg-blue-50 border-blue-200' :
          progress.status === 'completed' ? 'bg-green-50 border-green-200' :
          'bg-red-50 border-red-200'
        }`}>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
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
            {progress.prospects_found > 0 && (
              <span className="text-sm font-semibold text-blue-700 bg-blue-100 px-3 py-1 rounded-full">
                {progress.prospects_found}건 발견
              </span>
            )}
          </div>
          {progress.total > 0 && (
            <div className="mb-2">
              <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span>키워드 {progress.current} / {progress.total}</span>
                <span>{Math.round((progress.current / progress.total) * 100)}%</span>
              </div>
              <div className="w-full bg-white/60 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${(progress.current / progress.total) * 100}%` }}
                />
              </div>
            </div>
          )}
          {progress.message && (
            <p className="text-xs text-gray-600 mt-2">
              현재 수집 중: <span className="font-medium">{progress.message}</span>
            </p>
          )}
          {progress.error && (
            <p className="text-xs text-red-600 mt-2">{progress.error}</p>
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

  const downloadExcel = async () => {
    try {
      const res = await api.get(`/projects/${projectId}/export/prospects`, { responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', 'prospects.csv')
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch { showToast('다운로드 실패', 'error') }
  }

  const addToBlacklist = async (prospect) => {
    try {
      await api.post('/blacklist', {
        company_name: prospect.name || '',
        email: prospect.email || '',
        phone: prospect.phone || '',
        instagram: prospect.instagram || '',
        reason: '거절된 잠재고객',
      })
      showToast('블랙리스트에 추가되었습니다')
    } catch (err) {
      showToast(err.response?.data?.detail || '블랙리스트 추가 실패', 'error')
    }
  }

  if (loading) {
    return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin text-gray-400" /></div>
  }

  return (
    <div>
      <div className="mb-4 flex items-center gap-3">
        <button onClick={downloadExcel} className="inline-flex items-center gap-2 px-4 py-2 border border-gray-300 text-sm font-medium rounded-lg hover:bg-gray-50 cursor-pointer">
          <Download className="w-4 h-4" />
          엑셀 다운로드
        </button>
      </div>
      <ProspectTable
        prospects={prospects}
        page={page}
        totalPages={totalPages}
        onPageChange={fetchProspects}
        onApprove={handleApprove}
        onReject={handleReject}
        onApproveAll={handleApproveAll}
        projectId={projectId}
        onBlacklist={addToBlacklist}
      />
    </div>
  )
}

function EmailTab({ projectId, showToast }) {
  const [prospects, setProspects] = useState([])
  const [sending, setSending] = useState(false)
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [testSending, setTestSending] = useState(false)
  const [previewData, setPreviewData] = useState(null)
  const [scheduleAt, setScheduleAt] = useState('')

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
      const res = await api.post(`/projects/${projectId}/send-email`)
      const targetCount = res.data.target_count || 0
      setLogs([{ message: `이메일 발송이 시작되었습니다. ${targetCount}건 대상`, type: 'success' }])
      showToast(`이메일 발송이 시작되었습니다. ${targetCount}건 대상`)
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
      await api.post(`/projects/${projectId}/send-test-email`)
      showToast('테스트 이메일 발송 완료')
    } catch (err) {
      showToast(err.response?.data?.detail || '테스트 발송 실패', 'error')
    } finally {
      setTestSending(false)
    }
  }

  const previewEmail = async (prospectId) => {
    try {
      const res = await api.post(`/projects/${projectId}/send-email/preview`, { prospect_id: prospectId })
      setPreviewData(res.data)
    } catch { showToast('미리보기 실패', 'error') }
  }

  if (loading) {
    return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin text-gray-400" /></div>
  }

  return (
    <div className="space-y-6">
      {previewData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="bg-white rounded-xl shadow-xl max-w-lg w-full mx-4 max-h-[80vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">이메일 미리보기</h3>
                <button onClick={() => setPreviewData(null)} className="text-gray-400 hover:text-gray-600 cursor-pointer">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="space-y-3">
                <div><span className="text-sm text-gray-500">받는 사람:</span> <span className="text-sm">{previewData.to_email}</span></div>
                <div><span className="text-sm text-gray-500">제목:</span> <span className="text-sm font-medium">{previewData.subject}</span></div>
                <div className="border rounded-lg p-4">
                  <div dangerouslySetInnerHTML={{ __html: previewData.html_body }} />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Summary */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-gray-900">이메일 발송 대상</h3>
            <p className="text-sm text-gray-500 mt-1">승인된 업체 중 이메일이 있는 업체: {prospects.length}건</p>
          </div>
          <div className="flex flex-wrap gap-3">
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
            <input
              type="datetime-local"
              value={scheduleAt}
              onChange={e => setScheduleAt(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
            <button
              onClick={async () => {
                if (!scheduleAt) { showToast('예약 시간을 선택해주세요', 'error'); return }
                try {
                  await api.post(`/projects/${projectId}/send-email`, { scheduled_at: new Date(scheduleAt).toISOString() })
                  showToast(`${scheduleAt}에 발송이 예약되었습니다`)
                  setScheduleAt('')
                } catch (err) { showToast(err.response?.data?.detail || '예약 실패', 'error') }
              }}
              disabled={!scheduleAt || prospects.length === 0}
              className="inline-flex items-center gap-2 px-4 py-2 border border-blue-300 text-blue-600 text-sm font-medium rounded-lg hover:bg-blue-50 disabled:opacity-50 cursor-pointer"
            >
              <Clock className="w-4 h-4" />
              예약 발송
            </button>
            <button
              onClick={async () => {
                try {
                  const res = await api.post(`/projects/${projectId}/send-email`, { smart_send: true })
                  showToast(res.data.message)
                } catch (err) { showToast(err.response?.data?.detail || '예약 실패', 'error') }
              }}
              disabled={prospects.length === 0}
              className="inline-flex items-center gap-2 px-4 py-2 border border-purple-300 text-purple-600 text-sm font-medium rounded-lg hover:bg-purple-50 disabled:opacity-50 cursor-pointer"
              title="업종 데이터 기반 최적 발송 시각에 자동 예약 (주말·야간 회피)"
            >
              <Clock className="w-4 h-4" />
              최적 시간 자동 발송
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
                  <th className="text-left px-4 py-2.5 font-medium text-gray-600">미리보기</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {prospects.slice(0, 10).map((p) => (
                  <tr key={p.id}>
                    <td className="px-4 py-2.5 text-gray-900">{p.name}</td>
                    <td className="px-4 py-2.5 text-gray-600">{p.email}</td>
                    <td className="px-4 py-2.5">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                        p.status === 'sent' ? 'bg-blue-100 text-blue-700' : p.status === 'replied' ? 'bg-purple-100 text-purple-700' : 'bg-green-100 text-green-700'
                      }`}>
                        {p.status === 'sent' ? '발송완료' : p.status === 'replied' ? '답장받음' : '승인'}
                      </span>
                    </td>
                    <td className="px-4 py-2.5">
                      <button onClick={() => previewEmail(p.id)} className="text-xs text-blue-600 hover:underline cursor-pointer">미리보기</button>
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
  const [queue, setQueue] = useState([])
  const [sentLog, setSentLog] = useState([])
  const [loading, setLoading] = useState(true)
  const [extConnected, setExtConnected] = useState(false)
  const [igSettings, setIgSettings] = useState({ dm_template: null })
  const navigate = useNavigate()

  useEffect(() => {
    Promise.all([
      api.get(`/projects/${projectId}/dm/queue`).catch(() => ({ data: [] })),
      api.get(`/projects/${projectId}/dm/log`).catch(() => ({ data: [] })),
      api.get(`/projects/${projectId}/dm/status`).catch(() => ({ data: { connected: false } })),
      api.get(`/settings`).catch(() => ({ data: {} })),
    ]).then(([queueRes, logRes, statusRes, settingsRes]) => {
      setQueue(queueRes.data)
      setSentLog(logRes.data)
      setExtConnected(statusRes.data.connected)
      setIgSettings(settingsRes.data || {})
    }).finally(() => setLoading(false))
  }, [projectId])

  const refreshStatus = async () => {
    try {
      const res = await api.get(`/projects/${projectId}/dm/status`)
      setExtConnected(res.data.connected)
      showToast(res.data.connected ? '확장이 연결되어 있습니다' : '확장이 감지되지 않습니다. 크롬에서 인스타 탭을 열고 확장 팝업을 확인해주세요.', res.data.connected ? 'success' : 'error')
    } catch { showToast('상태 확인 실패', 'error') }
  }

  if (loading) {
    return <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin text-gray-400" /></div>
  }

  const hasDmTemplate = !!igSettings.dm_template
  const hasTargets = queue.length > 0

  const StepRow = ({ done, num, title, desc, action }) => (
    <div className={`flex items-start gap-4 p-4 rounded-lg border ${done ? 'border-green-200 bg-green-50' : 'border-gray-200 bg-white'}`}>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-sm font-bold ${
        done ? 'bg-green-500 text-white' : 'bg-gray-200 text-gray-600'
      }`}>
        {done ? '✓' : num}
      </div>
      <div className="flex-1">
        <div className="font-semibold text-gray-900">{title}</div>
        <div className="text-sm text-gray-600 mt-0.5">{desc}</div>
      </div>
      {action && !done && (
        <button
          onClick={action.onClick}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 cursor-pointer flex-shrink-0"
        >
          {action.label}
        </button>
      )}
    </div>
  )

  return (
    <div className="space-y-6">
      {/* 한 눈에 보는 4단계 */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-900">인스타그램 DM 발송 — 4단계</h3>
          <span className="text-xs text-gray-500">크롬 확장 + 본인 인스타 세션 = 가장 안전</span>
        </div>
        <div className="space-y-3">
          <StepRow
            num={1} done={extConnected}
            title="크롬 확장 설치 + 인스타 로그인"
            desc={extConnected ? '확장이 연결되어 있습니다' : '확장 다운로드 → chrome://extensions에 로드 → 인스타에 본인 계정으로 로그인'}
            action={{ label: '설치 가이드 보기', onClick: () => navigate('/extension') }}
          />
          <StepRow
            num={2} done={hasDmTemplate}
            title="DM 메시지 작성"
            desc={hasDmTemplate ? '메시지 등록 완료' : '설정 페이지에서 DM 메시지를 작성하세요. {name}, {company_name} 변수 사용 가능.'}
            action={{ label: '메시지 작성', onClick: () => navigate('/settings') }}
          />
          <StepRow
            num={3} done={hasTargets}
            title="DM 보낼 잠재고객 준비"
            desc={hasTargets ? `${queue.length}명 대기 중` : '키워드 추가 → 수집 → 잠재고객 탭에서 인스타 핸들 있는 사람 "승인"'}
          />
          <StepRow
            num={4} done={sentLog.length > 0}
            title='크롬 확장 팝업에서 "발송 시작" 클릭'
            desc={sentLog.length > 0
              ? `지금까지 ${sentLog.length}건 발송됨`
              : '확장이 본인 브라우저로 한 명씩 90~180초 간격 발송. 발송 중에는 인스타그램 탭을 열어두세요.'}
          />
        </div>
        <div className="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between">
          <span className={`text-sm ${extConnected ? 'text-green-700' : 'text-gray-500'}`}>
            ● 확장 연결 상태: <strong>{extConnected ? '연결됨' : '미연결'}</strong>
          </span>
          <button onClick={refreshStatus} className="text-sm text-blue-600 hover:underline cursor-pointer">
            연결 다시 확인
          </button>
        </div>
      </div>

      {/* DM Queue */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-4">DM 발송 대기열 ({queue.length}건)</h3>
        {queue.length === 0 ? (
          <p className="text-sm text-gray-400 py-8 text-center">발송 대기 중인 DM이 없습니다.</p>
        ) : (
          <div className="border border-gray-200 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="text-left px-4 py-2.5 font-medium text-gray-600">업체명</th>
                  <th className="text-left px-4 py-2.5 font-medium text-gray-600">인스타그램</th>
                  <th className="text-left px-4 py-2.5 font-medium text-gray-600">카테고리</th>
                  <th className="text-left px-4 py-2.5 font-medium text-gray-600">상태</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {queue.map((item) => (
                  <tr key={item.prospect_id}>
                    <td className="px-4 py-2.5 text-gray-900">{item.name}</td>
                    <td className="px-4 py-2.5 text-blue-600">@{item.instagram}</td>
                    <td className="px-4 py-2.5 text-gray-600">{item.category || '-'}</td>
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
            {sentLog.map((log, i) => {
              const ok = log.status === 'success'
              return (
                <div key={i} className="flex items-center justify-between px-3 py-2 bg-gray-50 rounded-lg text-sm">
                  <span className="text-gray-900">@{log.instagram} - {log.name}</span>
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${ok ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                      {ok ? '성공' : '실패'}
                    </span>
                    {!ok && log.error_message && (
                      <span className="text-xs text-red-400" title={log.error_message}>
                        {log.error_message.slice(0, 20)}
                      </span>
                    )}
                    <span className="text-xs text-gray-400">
                      {new Date(log.sent_at).toLocaleString('ko-KR')}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
