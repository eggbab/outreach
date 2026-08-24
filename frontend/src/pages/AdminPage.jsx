import { useState, useEffect } from 'react'
import api from '../lib/api'
import { useAuth } from '../lib/auth'
import { Navigate } from 'react-router-dom'
import {
  Key, Plus, Trash2, Copy, CheckCircle, Users, TrendingUp,
  Search, Coins, ShieldOff, ShieldCheck, Crown, CreditCard, X,
} from 'lucide-react'

export default function AdminPage() {
  const { user } = useAuth()
  const [tab, setTab] = useState('stats')

  // 비관리자 처리: 자동 승격 옵션 제공
  if (!user) return <Navigate to="/login" replace />
  if (!user.is_admin) return <NonAdminGate />

  const tabs = [
    { id: 'stats', label: '매출·통계', icon: TrendingUp },
    { id: 'payments', label: '결제 요청', icon: CreditCard },
    { id: 'users', label: '사용자 관리', icon: Users },
    { id: 'keys', label: '서비스 키', icon: Key },
  ]

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">관리자 대시보드</h1>
        <p className="text-gray-500 text-sm mt-1">사용자 관리, 매출 통계, 서비스 키 발급</p>
      </div>

      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-1">
          {tabs.map((t) => {
            const Icon = t.icon
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 cursor-pointer transition-colors ${
                  tab === t.id
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <Icon className="w-4 h-4" />
                {t.label}
              </button>
            )
          })}
        </nav>
      </div>

      {tab === 'stats' && <StatsTab />}
      {tab === 'payments' && <PaymentRequestsTab />}
      {tab === 'users' && <UsersTab />}
      {tab === 'keys' && <KeysTab />}
    </div>
  )
}

// ─────────────────────────────────
// 비관리자 진입 가드 — bootstrap 옵션 제공
// ─────────────────────────────────
function NonAdminGate() {
  const [bootstrapping, setBootstrapping] = useState(false)
  const [error, setError] = useState('')

  const tryBootstrap = async () => {
    setBootstrapping(true)
    setError('')
    try {
      await api.post('/admin/bootstrap-first-admin')
      window.location.reload()
    } catch (e) {
      setError(e.response?.data?.detail || '실패했습니다.')
    } finally {
      setBootstrapping(false)
    }
  }

  return (
    <div className="max-w-md mx-auto mt-20 bg-white rounded-2xl border border-gray-200 p-8 text-center">
      <Crown className="w-12 h-12 text-yellow-500 mx-auto mb-4" />
      <h2 className="text-xl font-bold text-gray-900 mb-2">관리자 전용 페이지</h2>
      <p className="text-sm text-gray-600 mb-4">
        이 페이지는 관리자만 접근할 수 있습니다.
      </p>
      <p className="text-xs text-gray-500 mb-4">
        만약 본인이 사장님(최초 가입자)이고 아직 관리자가 한 명도 지정되지 않았다면,
        아래 버튼으로 본인을 관리자로 승격할 수 있습니다.
      </p>
      <button
        onClick={tryBootstrap}
        disabled={bootstrapping}
        className="px-4 py-2 bg-yellow-500 text-white text-sm font-medium rounded-lg hover:bg-yellow-600 disabled:opacity-50 cursor-pointer"
      >
        {bootstrapping ? '처리 중...' : '나를 관리자로 만들기 (최초 1회)'}
      </button>
      {error && <p className="text-sm text-red-600 mt-3">{error}</p>}
    </div>
  )
}

// ─────────────────────────────────
// 매출·통계 탭
// ─────────────────────────────────
function StatsTab() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/admin/stats')
      .then(r => setStats(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-sm text-gray-500">불러오는 중...</div>
  if (!stats) return <div className="text-sm text-red-600">통계를 불러오지 못했습니다.</div>

  const fmt = (n) => (n || 0).toLocaleString('ko-KR')

  const cards = [
    { label: '누적 매출', value: `${fmt(stats.total_revenue)}원`, accent: 'text-blue-600' },
    { label: '이번 달 매출', value: `${fmt(stats.revenue_this_month)}원`, accent: 'text-green-600' },
    { label: '지난 달 매출', value: `${fmt(stats.revenue_last_month)}원`, accent: 'text-gray-700' },
    { label: '결제 사용자 수', value: `${fmt(stats.paid_users_count)}명`, accent: 'text-purple-600' },
    { label: '전체 사용자', value: `${fmt(stats.total_users)}명`, accent: 'text-gray-700' },
    { label: '이번 달 신규 가입', value: `${fmt(stats.new_users_this_month)}명`, accent: 'text-blue-600' },
    { label: '활성 사용자 (30일)', value: `${fmt(stats.active_users_30d)}명`, accent: 'text-green-600' },
    { label: '결제자당 평균 매출', value: `${fmt(stats.avg_revenue_per_paid_user)}원`, accent: 'text-purple-600' },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {cards.map((c) => (
        <div key={c.label} className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="text-xs text-gray-500 mb-1">{c.label}</div>
          <div className={`text-xl font-bold ${c.accent}`}>{c.value}</div>
        </div>
      ))}
    </div>
  )
}

// ─────────────────────────────────
// 결제 요청 탭 — 계좌이체 승인/거절
// ─────────────────────────────────
function PaymentRequestsTab() {
  const [items, setItems] = useState([])
  const [filter, setFilter] = useState('pending')
  const [loading, setLoading] = useState(true)
  const [rejectTarget, setRejectTarget] = useState(null)

  const fetchList = () => {
    setLoading(true)
    api.get('/admin/payment-requests/', { params: filter ? { status: filter } : {} })
      .then(r => setItems(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchList() }, [filter])

  const approve = async (id) => {
    if (!confirm('이 결제 요청을 승인하시겠습니까? (크레딧이 자동 충전됩니다)')) return
    try {
      const r = await api.post(`/admin/payment-requests/${id}/approve`)
      alert(`승인 완료 — ${r.data.credits_added} 크레딧 충전`)
      fetchList()
    } catch (e) { alert(e.response?.data?.detail || '실패') }
  }

  return (
    <div>
      <div className="mb-4 flex gap-2 items-center">
        <span className="text-sm text-gray-600">상태:</span>
        {[
          { v: 'pending', label: '대기 중' },
          { v: 'approved', label: '승인됨' },
          { v: 'rejected', label: '거절됨' },
          { v: '', label: '전체' },
        ].map(f => (
          <button
            key={f.v || 'all'}
            onClick={() => setFilter(f.v)}
            className={`text-sm px-3 py-1 rounded-full cursor-pointer ${
              filter === f.v ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >{f.label}</button>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-sm text-gray-500">불러오는 중...</div>
        ) : items.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-500">결제 요청이 없습니다.</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">신청자</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">패키지</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">금액</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">입금자명</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">메모</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">상태</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">신청일</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">관리</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map(it => (
                <tr key={it.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{it.user_name}</div>
                    <div className="text-xs text-gray-500">{it.user_email}</div>
                  </td>
                  <td className="px-4 py-3 text-gray-700">{it.package_label}<br/><span className="text-xs text-gray-500">{it.credits.toLocaleString()}cr</span></td>
                  <td className="px-4 py-3 font-bold text-gray-900">{it.amount.toLocaleString()}원</td>
                  <td className="px-4 py-3 text-gray-900">{it.depositor_name}</td>
                  <td className="px-4 py-3 text-xs text-gray-500 max-w-[200px] truncate">{it.memo || '-'}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                      it.status === 'approved' ? 'bg-green-100 text-green-700' :
                      it.status === 'rejected' ? 'bg-red-100 text-red-700' :
                      'bg-yellow-100 text-yellow-700'
                    }`}>
                      {it.status === 'approved' ? '승인' : it.status === 'rejected' ? '거절' : '대기'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {new Date(it.created_at).toLocaleString('ko-KR', { hour12: false })}
                  </td>
                  <td className="px-4 py-3">
                    {it.status === 'pending' && (
                      <div className="flex items-center gap-1">
                        <button onClick={() => approve(it.id)}
                          className="text-xs px-2 py-1 bg-green-600 text-white rounded hover:bg-green-700 cursor-pointer">
                          승인
                        </button>
                        <button onClick={() => setRejectTarget(it)}
                          className="text-xs px-2 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 cursor-pointer">
                          거절
                        </button>
                      </div>
                    )}
                    {it.status === 'rejected' && it.rejection_reason && (
                      <span className="text-xs text-red-600" title={it.rejection_reason}>{it.rejection_reason.slice(0, 20)}{it.rejection_reason.length > 20 ? '...' : ''}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {rejectTarget && (
        <RejectModal target={rejectTarget} onClose={() => setRejectTarget(null)} onSuccess={() => { setRejectTarget(null); fetchList() }} />
      )}
    </div>
  )
}

function RejectModal({ target, onClose, onSuccess }) {
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    if (!reason.trim()) return
    setLoading(true)
    try {
      await api.post(`/admin/payment-requests/${target.id}/reject`, { reason: reason.trim() })
      onSuccess()
    } catch (e) { alert(e.response?.data?.detail || '실패') }
    finally { setLoading(false) }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-md p-6">
        <div className="flex items-start justify-between mb-3">
          <h3 className="text-lg font-semibold text-gray-900">결제 요청 거절</h3>
          <button onClick={onClose} className="p-1 text-gray-400 hover:text-gray-600 cursor-pointer">
            <X className="w-5 h-5" />
          </button>
        </div>
        <p className="text-sm text-gray-500 mb-4">
          {target.user_email} · {target.package_label} ({target.amount.toLocaleString()}원)
        </p>
        <form onSubmit={submit} className="space-y-3">
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            placeholder="거절 사유 (사용자에게 보여집니다) — 예: 입금 확인 불가, 금액 불일치"
            required
          />
          <div className="flex gap-2">
            <button type="button" onClick={onClose} className="flex-1 py-2 border border-gray-300 rounded-lg text-sm cursor-pointer">취소</button>
            <button type="submit" disabled={loading || !reason.trim()} className="flex-1 py-2 bg-red-600 text-white text-sm rounded-lg hover:bg-red-700 disabled:opacity-50 cursor-pointer">
              {loading ? '처리 중...' : '거절'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─────────────────────────────────
// 사용자 관리 탭
// ─────────────────────────────────
function UsersTab() {
  const [list, setList] = useState({ items: [], total: 0, page: 1, total_pages: 1 })
  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [grantTarget, setGrantTarget] = useState(null)

  const fetchList = () => {
    setLoading(true)
    api.get('/admin/users', { params: { q: q || undefined, page, page_size: 20 } })
      .then(r => setList(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchList() }, [page])

  const search = (e) => { e.preventDefault(); setPage(1); fetchList() }

  const toggleActive = async (u) => {
    try {
      await api.patch(`/admin/users/${u.id}`, { is_active: !u.is_active })
      fetchList()
    } catch (e) { alert(e.response?.data?.detail || '실패') }
  }

  const toggleAdmin = async (u) => {
    if (!confirm(`${u.email}을(를) ${u.is_admin ? '관리자에서 해제' : '관리자로 승격'}하시겠습니까?`)) return
    try {
      await api.patch(`/admin/users/${u.id}`, { is_admin: !u.is_admin })
      fetchList()
    } catch (e) { alert(e.response?.data?.detail || '실패') }
  }

  const remove = async (u) => {
    if (!confirm(`${u.email} 계정을 정말 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.`)) return
    try {
      await api.delete(`/admin/users/${u.id}`)
      fetchList()
    } catch (e) { alert(e.response?.data?.detail || '실패') }
  }

  return (
    <div>
      <form onSubmit={search} className="mb-4 flex gap-2">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={q}
            onChange={e => setQ(e.target.value)}
            placeholder="이메일 또는 이름으로 검색"
            className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        <button type="submit" className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 cursor-pointer">
          검색
        </button>
      </form>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-sm text-gray-500">불러오는 중...</div>
        ) : list.items.length === 0 ? (
          <div className="p-8 text-center text-sm text-gray-500">사용자가 없습니다.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">사용자</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">플랜</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">크레딧</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">프로젝트</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">발송</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">상태</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">가입일</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">관리</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {list.items.map(u => (
                  <tr key={u.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900 flex items-center gap-1.5">
                        {u.name}
                        {u.is_admin && <Crown className="w-3.5 h-3.5 text-yellow-500" />}
                      </div>
                      <div className="text-xs text-gray-500">{u.email}</div>
                    </td>
                    <td className="px-4 py-3 text-gray-700">{u.plan}</td>
                    <td className="px-4 py-3 font-medium text-gray-900">{u.credits.toLocaleString('ko-KR')}</td>
                    <td className="px-4 py-3 text-gray-600">{u.project_count}</td>
                    <td className="px-4 py-3 text-gray-600">{u.total_emails_sent.toLocaleString('ko-KR')}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                        u.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                      }`}>
                        {u.is_active ? '활성' : '정지'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {new Date(u.created_at).toLocaleDateString('ko-KR')}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => setGrantTarget(u)}
                          title="크레딧 부여/차감"
                          className="p-1.5 text-yellow-600 hover:bg-yellow-50 rounded cursor-pointer"
                        >
                          <Coins className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => toggleActive(u)}
                          title={u.is_active ? '계정 정지' : '계정 활성화'}
                          className={`p-1.5 rounded cursor-pointer ${
                            u.is_active ? 'text-red-600 hover:bg-red-50' : 'text-green-600 hover:bg-green-50'
                          }`}
                        >
                          {u.is_active ? <ShieldOff className="w-4 h-4" /> : <ShieldCheck className="w-4 h-4" />}
                        </button>
                        <button
                          onClick={() => toggleAdmin(u)}
                          title={u.is_admin ? '관리자 해제' : '관리자 승격'}
                          className="p-1.5 text-purple-600 hover:bg-purple-50 rounded cursor-pointer"
                        >
                          <Crown className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => remove(u)}
                          title="삭제"
                          className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded cursor-pointer"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {list.total_pages > 1 && (
        <div className="mt-4 flex items-center justify-between text-sm">
          <span className="text-gray-500">총 {list.total.toLocaleString('ko-KR')}명</span>
          <div className="flex gap-1">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1 border border-gray-300 rounded disabled:opacity-50 cursor-pointer"
            >이전</button>
            <span className="px-3 py-1">{page} / {list.total_pages}</span>
            <button
              onClick={() => setPage(p => Math.min(list.total_pages, p + 1))}
              disabled={page === list.total_pages}
              className="px-3 py-1 border border-gray-300 rounded disabled:opacity-50 cursor-pointer"
            >다음</button>
          </div>
        </div>
      )}

      {grantTarget && (
        <GrantCreditsModal
          user={grantTarget}
          onClose={() => setGrantTarget(null)}
          onSuccess={() => { setGrantTarget(null); fetchList() }}
        />
      )}
    </div>
  )
}

function GrantCreditsModal({ user, onClose, onSuccess }) {
  const [amount, setAmount] = useState(100)
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    if (!reason.trim()) { setError('사유를 입력하세요.'); return }
    setLoading(true)
    try {
      await api.post(`/admin/users/${user.id}/grant-credits`, { amount: Number(amount), reason })
      onSuccess()
    } catch (e) {
      setError(e.response?.data?.detail || '실패')
    } finally { setLoading(false) }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-1">크레딧 부여 / 차감</h3>
        <p className="text-sm text-gray-500 mb-4">{user.email} (현재 {user.credits.toLocaleString('ko-KR')}크레딧)</p>

        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">변경량 (양수=부여, 음수=차감)</label>
            <input
              type="number"
              value={amount}
              onChange={e => setAmount(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              placeholder="100"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">사유 (필수, 거래 내역에 기록됨)</label>
            <input
              type="text"
              value={reason}
              onChange={e => setReason(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
              placeholder="예: 환불, 이벤트 보상, 베타 보너스"
              required
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex gap-2">
            <button type="button" onClick={onClose} className="flex-1 py-2 border border-gray-300 rounded-lg text-sm cursor-pointer">취소</button>
            <button type="submit" disabled={loading} className="flex-1 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50 cursor-pointer">
              {loading ? '처리 중...' : '적용'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─────────────────────────────────
// 서비스 키 탭 (기존)
// ─────────────────────────────────
function KeysTab() {
  const [keys, setKeys] = useState([])
  const [loading, setLoading] = useState(true)
  const [memo, setMemo] = useState('')
  const [creating, setCreating] = useState(false)
  const [copied, setCopied] = useState(null)

  const fetchKeys = () => {
    setLoading(true)
    api.get('/admin/service-keys')
      .then(r => setKeys(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { fetchKeys() }, [])

  const createKey = async (e) => {
    e.preventDefault()
    setCreating(true)
    try {
      await api.post('/admin/service-keys', { memo: memo || null })
      setMemo('')
      fetchKeys()
    } catch (err) { alert(err.response?.data?.detail || '생성 실패') }
    finally { setCreating(false) }
  }

  const toggleKey = async (id) => {
    try { await api.patch(`/admin/service-keys/${id}`); fetchKeys() }
    catch { alert('변경 실패') }
  }

  const deleteKey = async (id) => {
    if (!confirm('정말 삭제하시겠습니까?')) return
    try { await api.delete(`/admin/service-keys/${id}`); fetchKeys() }
    catch { alert('삭제 실패') }
  }

  const copyKey = (key) => {
    navigator.clipboard.writeText(key)
    setCopied(key)
    setTimeout(() => setCopied(null), 2000)
  }

  return (
    <>
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">새 서비스 키 생성</h3>
        <form onSubmit={createKey} className="flex gap-3">
          <input
            type="text"
            value={memo}
            onChange={e => setMemo(e.target.value)}
            placeholder="메모 (고객명 등)"
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm"
          />
          <button
            type="submit"
            disabled={creating}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            {creating ? '생성 중...' : '키 생성'}
          </button>
        </form>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-sm text-gray-500">불러오는 중...</div>
        ) : keys.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-gray-400">
            <Key className="w-10 h-10 mb-2" />
            <p className="text-sm">생성된 서비스 키가 없습니다</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">키</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">메모</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">상태</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">사용자</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">생성일</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">관리</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {keys.map(k => (
                  <tr key={k.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <code className="text-xs bg-gray-100 px-2 py-1 rounded font-mono">{k.key.slice(0, 12)}...</code>
                        <button onClick={() => copyKey(k.key)} className="text-gray-400 hover:text-blue-600 cursor-pointer">
                          {copied === k.key ? <CheckCircle className="w-3.5 h-3.5 text-green-500" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{k.memo || '-'}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                        k.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                      }`}>
                        {k.is_active ? '활성' : '비활성'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-xs">{k.activated_by_email || '미사용'}</td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{new Date(k.created_at).toLocaleDateString('ko-KR')}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => toggleKey(k.id)}
                          className={`text-xs px-2 py-1 rounded cursor-pointer ${
                            k.is_active ? 'text-red-600 hover:bg-red-50' : 'text-green-600 hover:bg-green-50'
                          }`}
                        >
                          {k.is_active ? '비활성화' : '활성화'}
                        </button>
                        <button onClick={() => deleteKey(k.id)} className="text-gray-400 hover:text-red-500 cursor-pointer">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  )
}
