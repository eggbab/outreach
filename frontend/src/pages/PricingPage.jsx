import { useState, useEffect } from 'react'
import { useAuth } from '../lib/auth'
import { Coins, Clock, Check, Search, Mail, MessageCircle, ChevronDown, Zap, CreditCard, Copy, X, Hourglass } from 'lucide-react'
import api from '../lib/api'

const faqs = [
  ['가격 정책은 어떻게 되나요?', 'Outreach는 월 구독료가 없습니다. 대신 크레딧을 충전해서 쓴 만큼만 지불하는 종량제 방식입니다. 업체를 수집하면 건당 1크레딧, 이메일을 발송하면 건당 2크레딧, 인스타그램 DM을 보내면 건당 3크레딧이 사용됩니다. 이메일 발송에는 열람 및 클릭 추적이 기본 포함되어 있고, 업체 수집의 경우 이메일이 실제로 확인된 업체만 크레딧이 차감되므로 헛돈이 나갈 걱정이 없습니다.\n\n크레딧은 4가지 패키지로 충전할 수 있습니다. 스탠다드 10,000 크레딧은 590,000원(건당 59원), 프로 30,000 크레딧은 1,590,000원(건당 53원), 비즈니스 70,000 크레딧은 3,490,000원(건당 49.8원), 엔터프라이즈 100,000 크레딧은 4,690,000원(건당 46.9원)입니다. 많이 충전할수록 건당 단가가 낮아집니다.\n\n회원가입만 하면 30 크레딧이 무료로 지급되어, 결제 없이도 수집 10건, 본인에게 테스트 이메일 발송, 본인에게 테스트 DM 발송 등 한 사이클을 체험해보실 수 있습니다. 그 외에 CRM 파이프라인, 분석 리포트, 블랙리스트 관리, CSV 내보내기 같은 기능은 크레딧 소모 없이 자유롭게 이용 가능합니다.'],
  ['크레딧이 뭔가요?', 'Outreach의 모든 기능은 크레딧으로 이용합니다. 업체 수집 1건 = 1크레딧, 이메일 발송 1건 = 2크레딧, 인스타 DM 1건 = 3크레딧입니다. 월정액 구독이 아니라 쓴 만큼만 과금되는 종량제 방식입니다.'],
  ['가입하면 무료 크레딧을 받나요?', '네. 회원가입 시 30 크레딧이 무료로 지급됩니다. 수집 10건 + 본인 이메일 테스트 + 본인 DM 테스트 등 서비스가 어떻게 동작하는지 한 사이클 체험해볼 수 있습니다. 본격 사용은 충전 후에 가능합니다.'],
  ['크레딧 유효기간이 있나요?', '아니요. 한번 충전한 크레딧은 만료되지 않습니다. 필요할 때 충전하고, 필요할 때 사용하세요.'],
  ['크레딧 패키지별 가격이 다른 이유는?', '대량 충전할수록 크레딧당 단가가 낮아집니다. 10,000 크레딧은 건당 59원, 100,000 크레딧은 건당 46.9원으로 최대 21% 할인됩니다.'],
  ['패키지로 얼마나 쓸 수 있나요?', '실 영업 흐름(수집→이메일→DM)으로 균형 있게 쓰신다면:\n\n· 스탠다드 10,000 크레딧 — 업체 4,000곳 발굴 + 이메일 2,000통 + DM 666통\n· 프로 30,000 크레딧 — 업체 12,000곳 + 이메일 6,000통 + DM 2,000통\n· 비즈니스 70,000 크레딧 — 업체 28,000곳 + 이메일 14,000통 + DM 4,666통\n· 엔터프라이즈 100,000 크레딧 — 업체 40,000곳 + 이메일 20,000통 + DM 6,666통\n\n한 가지에만 집중한다면 더 많이 쓸 수 있습니다. 예: 스탠다드 패키지로 수집만 한다면 10,000건, 이메일만 보낸다면 5,000통, DM만 보낸다면 3,333통이 가능합니다.'],
  ['업체 수집 시 이메일이 없으면 크레딧이 차감되나요?', '아니요. 이메일이 확인된 업체만 수집 결과에 포함되며, 이메일을 찾지 못한 업체는 크레딧이 차감되지 않습니다.'],
  ['이메일이나 DM을 보내다 계정이 제한되면 어떻게 되나요?', '발송에 사용된 크레딧은 이미 소진된 것으로 처리됩니다. 설정 페이지의 "발송 안전 가이드"를 참고하시면 계정 제한을 최소화할 수 있습니다. 제한이 풀리면 다시 발송할 수 있습니다.'],
  ['하루에 보낼 수 있는 양에 제한이 있나요?', '크레딧 자체에는 일일 한도가 없습니다. 다만 Gmail과 인스타그램의 계정 보호를 위해 권장 발송량이 있으며, 설정에서 직접 조정할 수 있습니다. 권장량을 초과하면 위험도가 표시됩니다.'],
  ['CRM, 파이프라인, 분석 등 다른 기능도 크레딧이 드나요?', '아니요. 크레딧은 업체 수집, 이메일 발송, DM 발송에만 사용됩니다. CRM 파이프라인, 분석 리포트, 블랙리스트, CSV 내보내기 등은 모든 계정에서 무료로 이용 가능합니다.'],
  ['환불이 가능한가요?', '충전 후 미사용 크레딧은 7일 이내 환불 가능합니다. 고객센터로 문의해주세요.'],
  ['팀원과 크레딧을 공유할 수 있나요?', '현재는 계정별로 크레딧이 관리됩니다. 팀 기능에서 같은 프로젝트를 공유할 수 있지만, 크레딧은 각자 충전해야 합니다.'],
]

export default function PricingPage() {
  const { user } = useAuth()
  const [toast, setToast] = useState(null)
  const [credits, setCredits] = useState(0)
  const [packages, setPackages] = useState([])
  const [history, setHistory] = useState([])
  const [showHistory, setShowHistory] = useState(false)
  const [selected, setSelected] = useState(null)
  const [purchasing, setPurchasing] = useState(false)
  const [openFaq, setOpenFaq] = useState(null)
  const [bankInfo, setBankInfo] = useState(null)
  const [showModal, setShowModal] = useState(false)
  const [depositorName, setDepositorName] = useState('')
  const [memo, setMemo] = useState('')
  const [myRequests, setMyRequests] = useState([])

  const showToast = (message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 4000)
  }

  useEffect(() => {
    api.get('/subscription').then((r) => setCredits(r.data.credits)).catch(() => {})
    api.get('/subscription/credit-packages').then((r) => {
      setPackages(r.data)
      const pop = r.data.find(p => p.popular)
      if (pop) setSelected(pop.id)
    }).catch(() => {})
    api.get('/payments/bank-info').then((r) => setBankInfo(r.data)).catch(() => {})
    api.get('/payments/my-requests').then((r) => setMyRequests(r.data)).catch(() => {})
    if (user?.name && !depositorName) setDepositorName(user.name)
  }, [user])

  const refreshMyRequests = () => {
    api.get('/payments/my-requests').then((r) => setMyRequests(r.data)).catch(() => {})
    api.get('/subscription').then((r) => setCredits(r.data.credits)).catch(() => {})
  }

  const handlePurchase = () => {
    if (!selected) return
    if (!bankInfo?.configured) {
      showToast('관리자가 입금 계좌를 아직 설정하지 않았습니다.', 'error')
      return
    }
    setShowModal(true)
  }

  const submitRequest = async () => {
    if (!depositorName.trim()) { showToast('입금자명을 입력해주세요', 'error'); return }
    setPurchasing(true)
    try {
      await api.post('/payments/request', {
        package_id: selected,
        depositor_name: depositorName.trim(),
        memo: memo.trim() || null,
      })
      showToast('입금 알림이 등록되었습니다. 관리자 확인 후 크레딧이 충전됩니다.')
      setShowModal(false)
      setMemo('')
      refreshMyRequests()
    } catch (err) {
      showToast(err.response?.data?.detail || '요청 실패', 'error')
    } finally {
      setPurchasing(false)
    }
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
    showToast('복사되었습니다')
  }

  const selectedPkg = packages.find(p => p.id === selected)

  return (
    <div className="max-w-3xl mx-auto">
      {toast && (
        <div className={`fixed top-6 right-6 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium ${
          toast.type === 'error' ? 'bg-red-600 text-white' : 'bg-green-600 text-white'
        }`}>
          {toast.message}
        </div>
      )}

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">크레딧 충전</h1>
        <p className="text-gray-500 mt-1">쓴 만큼만 내세요. 월 구독료가 없습니다.</p>
      </div>

      {/* Balance card */}
      <div className="bg-gradient-to-br from-gray-900 to-gray-800 text-white rounded-2xl p-6 mb-8">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-yellow-400/20 rounded-xl flex items-center justify-center">
              <Coins className="w-5 h-5 text-yellow-400" />
            </div>
            <div>
              <p className="text-xs text-gray-400">보유 크레딧</p>
              <p className="text-2xl font-bold">{credits.toLocaleString()}</p>
            </div>
          </div>
          <button
            onClick={async () => {
              setShowHistory(!showHistory)
              if (!showHistory) {
                try { const res = await api.get('/subscription/credit-history'); setHistory(res.data) } catch {}
              }
            }}
            className="text-xs text-gray-400 hover:text-white cursor-pointer flex items-center gap-1"
          >
            <Clock className="w-3 h-3" /> 내역
          </button>
        </div>
        <div className="grid grid-cols-3 gap-3">
          {[
            { icon: Search, label: '수집', cost: '1크레딧/건' },
            { icon: Mail, label: '이메일', cost: '2크레딧/건' },
            { icon: MessageCircle, label: 'DM', cost: '3크레딧/건' },
          ].map((item) => (
            <div key={item.label} className="bg-white/5 rounded-lg p-3 text-center">
              <item.icon className="w-4 h-4 text-gray-400 mx-auto mb-1" />
              <p className="text-[10px] text-gray-400">{item.label}</p>
              <p className="text-xs font-semibold">{item.cost}</p>
            </div>
          ))}
        </div>

        {/* History inline */}
        {showHistory && (
          <div className="mt-4 pt-4 border-t border-white/10">
            {history.length === 0 ? (
              <p className="text-xs text-gray-500 text-center py-2">내역이 없습니다</p>
            ) : (
              <div className="space-y-1.5 max-h-40 overflow-y-auto">
                {history.map((tx) => (
                  <div key={tx.id} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className={tx.amount > 0 ? 'text-green-400' : 'text-gray-400'}>
                        {tx.amount > 0 ? '+' : ''}{tx.amount}
                      </span>
                      <span className="text-gray-400 truncate max-w-[200px]">{tx.description}</span>
                    </div>
                    <span className="text-gray-500 shrink-0">{new Date(tx.created_at).toLocaleDateString('ko-KR')}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Package selection */}
      <div className="mb-4">
        <h2 className="text-sm font-semibold text-gray-900 mb-3">충전 패키지 선택</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {packages.map((pkg) => {
            const isSelected = selected === pkg.id
            return (
              <button
                key={pkg.id}
                onClick={() => setSelected(pkg.id)}
                className={`relative rounded-xl p-4 text-left cursor-pointer border-2 transition-all ${
                  isSelected
                    ? 'border-blue-600 bg-blue-50 shadow-sm'
                    : 'border-gray-200 bg-white hover:border-gray-300'
                }`}
              >
                {pkg.popular && (
                  <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 text-[10px] font-semibold bg-blue-600 text-white px-2.5 py-0.5 rounded-full">인기</span>
                )}
                {pkg.bonus && !pkg.popular && (
                  <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 text-[10px] font-semibold bg-gray-900 text-white px-2.5 py-0.5 rounded-full">{pkg.bonus}</span>
                )}
                <p className={`text-sm font-bold mb-1 ${isSelected ? 'text-blue-700' : 'text-gray-900'}`}>
                  {pkg.label}
                </p>
                <p className={`text-xl font-bold ${isSelected ? 'text-blue-700' : 'text-gray-900'}`}>
                  {pkg.price_label}
                </p>
                <p className="text-xs text-gray-500 mt-1">{pkg.per_credit}/크레딧</p>
                {isSelected && (
                  <div className="absolute top-3 right-3 w-5 h-5 bg-blue-600 rounded-full flex items-center justify-center">
                    <Check className="w-3 h-3 text-white" />
                  </div>
                )}
              </button>
            )
          })}
        </div>
      </div>

      {/* 선택한 패키지 — 활용 예시 */}
      {selectedPkg && selectedPkg.examples && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 mb-4">
          <h3 className="text-sm font-semibold text-blue-900 mb-3 flex items-center gap-2">
            <Zap className="w-4 h-4" /> 이 패키지로 할 수 있는 것
          </h3>
          <div className="space-y-3">
            <div>
              <div className="text-xs font-semibold text-blue-700 mb-1.5">⭐ 균형 사용 (실 영업 흐름)</div>
              <div className="bg-white rounded-lg p-3 text-sm text-gray-800 leading-relaxed">
                {selectedPkg.examples.balanced}
              </div>
            </div>
            <div>
              <div className="text-xs font-semibold text-blue-700 mb-1.5">또는 한 가지에만 집중하면</div>
              <div className="grid grid-cols-3 gap-2">
                <div className="bg-white rounded-lg p-3 text-center">
                  <div className="flex justify-center mb-1"><Search className="w-4 h-4 text-gray-500" /></div>
                  <div className="text-xs text-gray-500">업체 수집</div>
                  <div className="text-sm font-bold text-gray-900 mt-0.5">{selectedPkg.examples.single.scrape}</div>
                </div>
                <div className="bg-white rounded-lg p-3 text-center">
                  <div className="flex justify-center mb-1"><Mail className="w-4 h-4 text-gray-500" /></div>
                  <div className="text-xs text-gray-500">이메일</div>
                  <div className="text-sm font-bold text-gray-900 mt-0.5">{selectedPkg.examples.single.email}</div>
                </div>
                <div className="bg-white rounded-lg p-3 text-center">
                  <div className="flex justify-center mb-1"><MessageCircle className="w-4 h-4 text-gray-500" /></div>
                  <div className="text-xs text-gray-500">DM</div>
                  <div className="text-sm font-bold text-gray-900 mt-0.5">{selectedPkg.examples.single.dm}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Purchase button */}
      <button
        onClick={handlePurchase}
        disabled={!selected}
        className="w-full py-3.5 bg-blue-600 text-white font-semibold rounded-xl hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer flex items-center justify-center gap-2 mb-8"
      >
        {selectedPkg ? (
          <>
            <CreditCard className="w-4 h-4" />
            계좌이체로 {selectedPkg.price_label} 결제
          </>
        ) : (
          '패키지를 선택해주세요'
        )}
      </button>

      {/* 내 결제 요청 내역 */}
      {myRequests.length > 0 && (
        <div className="bg-white rounded-xl ring-1 ring-gray-200 p-5 mb-6">
          <h2 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <Hourglass className="w-4 h-4 text-gray-500" />
            내 결제 요청
          </h2>
          <div className="space-y-2">
            {myRequests.slice(0, 5).map((r) => (
              <div key={r.id} className="flex items-center justify-between text-sm border border-gray-100 rounded-lg p-3">
                <div>
                  <div className="font-medium text-gray-900">{r.package_label} ({r.amount.toLocaleString()}원)</div>
                  <div className="text-xs text-gray-500">입금자: {r.depositor_name} · {new Date(r.created_at).toLocaleString('ko-KR')}</div>
                  {r.rejection_reason && <div className="text-xs text-red-600 mt-1">거절 사유: {r.rejection_reason}</div>}
                </div>
                <span className={`text-xs font-semibold px-2 py-1 rounded-full ${
                  r.status === 'approved' ? 'bg-green-100 text-green-700' :
                  r.status === 'rejected' ? 'bg-red-100 text-red-700' :
                  'bg-yellow-100 text-yellow-700'
                }`}>
                  {r.status === 'approved' ? '승인 완료' : r.status === 'rejected' ? '거절됨' : '확인 대기 중'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 계좌이체 모달 */}
      {showModal && selectedPkg && bankInfo && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-md p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-lg font-bold text-gray-900">계좌이체로 결제</h3>
                <p className="text-sm text-gray-500">{selectedPkg.label} · {selectedPkg.price_label}</p>
              </div>
              <button onClick={() => setShowModal(false)} className="p-1 text-gray-400 hover:text-gray-600 cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* 1. 계좌 정보 */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <div className="text-xs font-semibold text-blue-900 mb-2">📥 아래 계좌로 입금해주세요</div>
              <div className="space-y-2 text-sm">
                <Row label="은행" value={bankInfo.bank_name} onCopy={() => copyToClipboard(bankInfo.bank_name)} />
                <Row label="계좌번호" value={bankInfo.bank_account} onCopy={() => copyToClipboard(bankInfo.bank_account)} bold />
                <Row label="예금주" value={bankInfo.bank_holder} onCopy={() => copyToClipboard(bankInfo.bank_holder)} />
                <Row label="입금액" value={`${selectedPkg.price.toLocaleString()}원`} onCopy={() => copyToClipboard(String(selectedPkg.price))} bold />
              </div>
            </div>

            {/* 2. 입금자 정보 */}
            <div className="space-y-3 mb-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  입금자명 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={depositorName}
                  onChange={(e) => setDepositorName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  placeholder="통장에 찍힐 이름"
                />
                <p className="text-xs text-gray-500 mt-1">관리자가 통장에서 이 이름으로 입금을 확인합니다.</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">메모 (선택)</label>
                <input
                  type="text"
                  value={memo}
                  onChange={(e) => setMemo(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                  placeholder="회사명 / 추가 안내 등"
                />
              </div>
            </div>

            {/* 3. 안내 */}
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-4 text-xs text-gray-600 leading-relaxed">
              <strong>이렇게 진행됩니다:</strong><br/>
              1. 위 계좌로 정확한 금액 입금<br/>
              2. 아래 "입금 완료 알림" 버튼 클릭<br/>
              3. 관리자가 통장 확인 후 승인 (영업시간 기준 보통 1시간 이내)<br/>
              4. 크레딧 자동 충전 — 알림 도착
            </div>

            <div className="flex gap-2">
              <button onClick={() => setShowModal(false)} className="flex-1 py-2.5 border border-gray-300 rounded-lg text-sm cursor-pointer">
                취소
              </button>
              <button
                onClick={submitRequest}
                disabled={purchasing || !depositorName.trim()}
                className="flex-1 py-2.5 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-50 cursor-pointer"
              >
                {purchasing ? '전송 중...' : '입금 완료 알림'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* What credits get you */}
      <div className="bg-white rounded-xl ring-1 ring-gray-200 p-6 mb-6">
        <h2 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
          <Zap className="w-4 h-4 text-yellow-500" />
          크레딧으로 할 수 있는 것
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { icon: Search, action: '업체 수집', cost: 1, desc: '네이버·구글·지도 통합 검색', sub: '이메일 확인된 업체만 과금' },
            { icon: Mail, action: '이메일 발송', cost: 2, desc: '개인화 발송 + 추적 포함', sub: '열람/클릭 추적 무료' },
            { icon: MessageCircle, action: '인스타 DM', cost: 3, desc: '크롬 확장 자동 발송', sub: '안전 가이드 제공' },
          ].map((item) => (
            <div key={item.action} className="flex gap-3">
              <div className="w-9 h-9 bg-gray-100 rounded-lg flex items-center justify-center shrink-0">
                <item.icon className="w-4 h-4 text-gray-500" />
              </div>
              <div>
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-sm font-medium text-gray-900">{item.action}</span>
                  <span className="text-xs font-semibold text-blue-600">{item.cost}크레딧</span>
                </div>
                <p className="text-xs text-gray-500">{item.desc}</p>
                <p className="text-[10px] text-gray-400">{item.sub}</p>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-5 pt-4 border-t border-gray-100">
          <p className="text-xs font-medium text-gray-600 mb-2">무료 기능</p>
          <div className="flex flex-wrap gap-x-4 gap-y-1.5">
            {['CRM 파이프라인', '분석 리포트', '블랙리스트', 'CSV 내보내기', '발송 안전 가이드', '이메일 시퀀스'].map((f) => (
              <span key={f} className="text-xs text-gray-500 flex items-center gap-1">
                <Check className="w-3 h-3 text-green-500" />{f}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* FAQ */}
      <div className="bg-white rounded-xl ring-1 ring-gray-200 overflow-hidden mb-8">
        <h2 className="text-sm font-semibold text-gray-900 px-6 pt-5 pb-3">자주 묻는 질문</h2>
        {faqs.map(([q, a], i) => (
          <div key={i} className="border-t border-gray-100">
            <button
              onClick={() => setOpenFaq(openFaq === i ? null : i)}
              className="w-full flex items-center justify-between px-6 py-3.5 text-left cursor-pointer hover:bg-gray-50"
            >
              <span className="text-sm font-medium text-gray-700">{q}</span>
              <ChevronDown className={`w-4 h-4 text-gray-400 shrink-0 transition-transform ${openFaq === i ? 'rotate-180' : ''}`} />
            </button>
            {openFaq === i && (
              <div className="px-6 pb-4">
                <p className="text-sm text-gray-500 leading-relaxed whitespace-pre-line">{a}</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function Row({ label, value, onCopy, bold }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-blue-700/70">{label}</span>
      <div className="flex items-center gap-1.5">
        <span className={`text-blue-900 ${bold ? 'font-bold' : 'font-medium'}`}>{value || '-'}</span>
        {value && (
          <button onClick={onCopy} className="p-1 text-blue-500 hover:text-blue-700 cursor-pointer" title="복사">
            <Copy className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  )
}
