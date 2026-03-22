import { useState, useEffect } from 'react'
import { useAuth } from '../lib/auth'
import { Check, Minus, Coins, ArrowRight, Clock } from 'lucide-react'
import api from '../lib/api'

const plans = [
  {
    id: 'free',
    name: '무료',
    price: '0',
    description: '기능 체험용',
    features: [
      { text: '프로젝트 1개', included: true },
      { text: '이메일 3건/일', included: true },
      { text: 'DM 2건/일', included: true },
      { text: '수집 10건/일', included: true },
      { text: '한도 초과 불가', included: false },
      { text: '이메일 시퀀스', included: false },
      { text: '파이프라인 CRM', included: false },
    ],
  },
  {
    id: 'pro',
    name: '프로',
    price: '29,000',
    description: '본격 B2B 영업',
    popular: true,
    features: [
      { text: '프로젝트 10개', included: true },
      { text: '이메일 100건/일', included: true },
      { text: 'DM 30건/일', included: true },
      { text: '수집 500건/일', included: true },
      { text: '한도 초과 시 건당 과금', included: true },
      { text: '이메일 시퀀스 + A/B', included: true },
      { text: '파이프라인 CRM', included: true },
    ],
  },
  {
    id: 'agency',
    name: '에이전시',
    price: '79,000',
    description: '대규모 아웃리치',
    features: [
      { text: '프로젝트 무제한', included: true },
      { text: '이메일 500건/일', included: true },
      { text: 'DM 100건/일', included: true },
      { text: '수집 2,000건/일', included: true },
      { text: '한도 초과 시 건당 과금', included: true },
      { text: '팀 협업 + API', included: true },
      { text: '우선 지원', included: true },
    ],
  },
]

const comparisons = [
  ['프로젝트', '1개', '10개', '무제한'],
  ['일일 이메일', '3건', '100건', '500건'],
  ['일일 DM', '2건', '30건', '100건'],
  ['일일 수집', '10건', '500건', '2,000건'],
  ['한도 초과 과금', false, true, true],
  ['이메일 시퀀스', false, true, true],
  ['파이프라인', false, true, true],
  ['팀 협업', false, false, true],
]

const faqs = [
  ['무료 플랜으로도 쓸 수 있나요?', '네. 기능은 동일하지만 일일 한도가 매우 작습니다 (이메일 3건, DM 2건, 수집 10건). 서비스를 체험해보는 용도입니다.'],
  ['건당 과금이 뭔가요?', '유료 플랜의 일일 한도를 초과하면, 크레딧을 사용해서 추가로 발송/수집할 수 있습니다. 이메일 1건당 5크레딧, DM 1건당 10크레딧, 수집 1건당 2크레딧입니다.'],
  ['크레딧은 어떻게 충전하나요?', '요금제 페이지 하단에서 크레딧 패키지를 구매할 수 있습니다. 5,000 크레딧 패키지는 20% 보너스가 포함됩니다.'],
  ['크레딧 유효기간이 있나요?', '아니요. 충전한 크레딧은 만료되지 않습니다.'],
  ['플랜 변경이 가능한가요?', '네. 업그레이드는 즉시, 다운그레이드는 다음 결제일부터 적용됩니다.'],
]

export default function PricingPage() {
  const { user } = useAuth()
  const [toast, setToast] = useState(null)
  const [changing, setChanging] = useState(false)
  const [credits, setCredits] = useState(0)
  const [packages, setPackages] = useState([])
  const [history, setHistory] = useState([])
  const [showHistory, setShowHistory] = useState(false)
  const currentPlan = user?.plan || 'free'
  const isFree = currentPlan === 'free' || currentPlan === 'personal'

  const showToast = (message) => {
    setToast(message)
    setTimeout(() => setToast(null), 3000)
  }

  useEffect(() => {
    api.get('/subscription').then((r) => setCredits(r.data.credits)).catch(() => {})
    api.get('/subscription/credit-packages').then((r) => setPackages(r.data)).catch(() => {})

    // Handle Toss payment callback (redirect back with query params)
    const params = new URLSearchParams(window.location.search)
    if (params.get('payment') === 'success') {
      const paymentKey = params.get('paymentKey')
      const orderId = params.get('orderId')
      const amount = Number(params.get('amount'))
      if (paymentKey && orderId && amount) {
        api.post('/payments/confirm', { paymentKey, orderId, amount })
          .then((res) => {
            setCredits(res.data.credits)
            showToast(`크레딧 ${res.data.added}개가 충전되었습니다!`)
          })
          .catch((err) => {
            showToast(err.response?.data?.detail || '결제 확인 실패')
          })
      }
      // Clean URL
      window.history.replaceState({}, '', '/pricing')
    } else if (params.get('payment') === 'fail') {
      showToast(params.get('message') || '결제가 취소되었습니다.')
      window.history.replaceState({}, '', '/pricing')
    }
  }, [])

  const planOrder = { free: 0, personal: 0, pro: 1, agency: 2 }

  const getButtonLabel = (planId) => {
    if (planId === currentPlan) return '현재 플랜'
    if ((planOrder[planId] ?? 0) < (planOrder[currentPlan] ?? 0)) return '다운그레이드'
    return '업그레이드'
  }

  const handlePlanChange = async (planId) => {
    if (planId === currentPlan || changing) return
    setChanging(true)
    try {
      const isUpgrade = (planOrder[planId] ?? 0) > (planOrder[currentPlan] ?? 0)
      const endpoint = isUpgrade ? '/subscription/upgrade' : '/subscription/downgrade'
      const res = await api.post(endpoint, { plan: planId })
      setCredits(res.data.credits)
      showToast(`${isUpgrade ? '업그레이드' : '다운그레이드'} 완료! 새로고침하면 반영됩니다.`)
    } catch (err) {
      showToast(err.response?.data?.detail || '플랜 변경 실패')
    } finally {
      setChanging(false)
    }
  }

  const handlePurchaseCredits = async (packageId) => {
    try {
      // Step 1: Prepare payment (get orderId + clientKey)
      const prepRes = await api.post('/payments/prepare', { package_id: packageId })
      const { orderId, clientKey, amount, packageId: pkgId } = prepRes.data

      // Step 2: Load Toss Payments widget
      const tossPayments = window.TossPayments(clientKey)

      // Step 3: Request payment
      await tossPayments.requestPayment('카드', {
        amount,
        orderId,
        orderName: '크레딧 충전',
        successUrl: `${window.location.origin}/pricing?payment=success`,
        failUrl: `${window.location.origin}/pricing?payment=fail`,
      })
    } catch (err) {
      // User cancelled or error
      if (err.code === 'USER_CANCEL') return
      showToast(err.response?.data?.detail || err.message || '결제 실패')
    }
  }

  const loadHistory = async () => {
    setShowHistory(!showHistory)
    if (!showHistory) {
      const res = await api.get('/subscription/credit-history')
      setHistory(res.data)
    }
  }

  return (
    <div>
      {toast && (
        <div className="fixed top-6 right-6 z-50 px-3 py-2 rounded-lg shadow-lg text-xs font-medium bg-gray-900 text-white">
          {toast}
        </div>
      )}

      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">요금제</h1>
        <p className="text-gray-500 mt-1 text-sm">비즈니스에 맞는 플랜을 선택하세요</p>
      </div>

      {/* Plan cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {plans.map((plan) => {
          const isCurrent = plan.id === currentPlan
          return (
            <div
              key={plan.id}
              className={`rounded-xl p-5 flex flex-col ${
                plan.popular
                  ? 'bg-gray-900 text-white ring-1 ring-gray-900'
                  : 'bg-white ring-1 ring-gray-200'
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <span className={`text-sm font-semibold ${plan.popular ? 'text-gray-300' : 'text-gray-900'}`}>
                  {plan.name}
                </span>
                {isCurrent && (
                  <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
                    plan.popular ? 'bg-white/20 text-white' : 'bg-green-50 text-green-700'
                  }`}>현재</span>
                )}
                {plan.popular && !isCurrent && (
                  <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-blue-500 text-white">추천</span>
                )}
              </div>

              <div className="mb-1">
                <span className={`text-2xl font-bold ${plan.popular ? 'text-white' : 'text-gray-900'}`}>
                  {plan.price === '0' ? '무료' : `${plan.price}원`}
                </span>
                {plan.price !== '0' && (
                  <span className={`text-xs ml-1 ${plan.popular ? 'text-gray-400' : 'text-gray-500'}`}>/월</span>
                )}
              </div>
              <p className={`text-xs mb-5 ${plan.popular ? 'text-gray-400' : 'text-gray-500'}`}>
                {plan.description}
              </p>

              <div className={`border-t pt-4 mb-5 flex-1 ${plan.popular ? 'border-gray-700' : 'border-gray-100'}`}>
                <ul className="space-y-2.5">
                  {plan.features.map((feature, idx) => (
                    <li key={idx} className="flex items-center gap-2">
                      {feature.included ? (
                        <Check className={`w-3.5 h-3.5 shrink-0 ${plan.popular ? 'text-blue-400' : 'text-blue-600'}`} />
                      ) : (
                        <Minus className={`w-3.5 h-3.5 shrink-0 ${plan.popular ? 'text-gray-600' : 'text-gray-300'}`} />
                      )}
                      <span className={`text-xs ${
                        feature.included
                          ? plan.popular ? 'text-gray-300' : 'text-gray-700'
                          : plan.popular ? 'text-gray-600' : 'text-gray-400'
                      }`}>
                        {feature.text}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>

              {isCurrent && user?.trial_ends_at && (
                <div className={`text-[10px] text-center mb-2 ${plan.popular ? 'text-gray-400' : 'text-blue-600'}`}>
                  체험 중 ({new Date(user.trial_ends_at).toLocaleDateString('ko-KR')}까지)
                </div>
              )}

              <button
                onClick={() => handlePlanChange(plan.id)}
                disabled={isCurrent || changing}
                className={`w-full py-2 rounded-lg text-sm font-medium transition-colors ${
                  isCurrent
                    ? plan.popular ? 'bg-white/10 text-gray-500 cursor-default' : 'bg-gray-100 text-gray-400 cursor-default'
                    : plan.popular ? 'bg-white text-gray-900 hover:bg-gray-100 cursor-pointer' : 'bg-gray-900 text-white hover:bg-gray-800 cursor-pointer'
                }`}
              >
                {getButtonLabel(plan.id)}
              </button>
            </div>
          )
        })}
      </div>

      {/* Overage rates */}
      <div className="bg-blue-50 rounded-xl ring-1 ring-blue-200 p-5 mb-6">
        <div className="flex items-center gap-2 mb-3">
          <Coins className="w-4 h-4 text-blue-600" />
          <h2 className="text-sm font-semibold text-blue-900">건당 과금 (유료 플랜 전용)</h2>
        </div>
        <p className="text-xs text-blue-700 mb-3">일일 한도를 초과하면, 크레딧을 사용해서 추가로 이용할 수 있습니다.</p>
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: '이메일 1건', cost: '5 크레딧' },
            { label: 'DM 1건', cost: '10 크레딧' },
            { label: '수집 1건', cost: '2 크레딧' },
          ].map((r) => (
            <div key={r.label} className="bg-white rounded-lg p-3 ring-1 ring-blue-100">
              <p className="text-xs text-gray-500">{r.label}</p>
              <p className="text-sm font-semibold text-gray-900">{r.cost}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Credit purchase */}
      {!isFree && (
        <div className="bg-white rounded-xl ring-1 ring-gray-200 p-5 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-semibold text-gray-900">크레딧 충전</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                현재 잔액: <span className="font-semibold text-gray-900">{credits.toLocaleString()} 크레딧</span>
              </p>
            </div>
            <button
              onClick={loadHistory}
              className="text-xs text-blue-600 hover:underline cursor-pointer flex items-center gap-1"
            >
              <Clock className="w-3 h-3" />
              {showHistory ? '닫기' : '사용 내역'}
            </button>
          </div>

          <div className="grid grid-cols-3 gap-3 mb-4">
            {packages.map((pkg) => (
              <button
                key={pkg.id}
                onClick={() => handlePurchaseCredits(pkg.id)}
                className={`rounded-lg p-4 text-left transition-all cursor-pointer ${
                  pkg.popular
                    ? 'bg-gray-900 text-white ring-1 ring-gray-900'
                    : 'bg-gray-50 ring-1 ring-gray-200 hover:ring-gray-300'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className={`text-sm font-semibold ${pkg.popular ? 'text-white' : 'text-gray-900'}`}>
                    {pkg.label}
                  </span>
                  {pkg.popular && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-500 text-white font-medium">인기</span>
                  )}
                  {pkg.bonus && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-green-500 text-white font-medium">{pkg.bonus}</span>
                  )}
                </div>
                <p className={`text-lg font-bold ${pkg.popular ? 'text-white' : 'text-gray-900'}`}>
                  {pkg.price_label}
                </p>
                <p className={`text-[10px] mt-1 ${pkg.popular ? 'text-gray-400' : 'text-gray-500'}`}>
                  {pkg.bonus ? `실제 ${(pkg.credits * 1.2).toLocaleString()} 크레딧` : `크레딧당 ${pkg.price / pkg.credits}원`}
                </p>
              </button>
            ))}
          </div>

          {/* Credit history */}
          {showHistory && (
            <div className="border-t border-gray-200 pt-4">
              {history.length === 0 ? (
                <p className="text-xs text-gray-400 text-center py-4">사용 내역이 없습니다</p>
              ) : (
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {history.map((tx) => (
                    <div key={tx.id} className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <span className={`font-semibold ${tx.amount > 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {tx.amount > 0 ? '+' : ''}{tx.amount}
                        </span>
                        <span className="text-gray-600">{tx.description}</span>
                      </div>
                      <div className="flex items-center gap-3 text-gray-400">
                        <span>잔액 {tx.balance_after}</span>
                        <span>{new Date(tx.created_at).toLocaleDateString('ko-KR')}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Comparison table */}
      <div className="bg-white rounded-xl ring-1 ring-gray-200 overflow-hidden mb-6">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-100">
              <th className="text-left px-5 py-3 font-medium text-gray-500">기능 비교</th>
              {plans.map((p) => (
                <th key={p.id} className={`text-center px-4 py-3 font-medium ${p.id === currentPlan ? 'text-blue-600' : 'text-gray-500'}`}>
                  {p.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {comparisons.map(([feature, ...vals], i) => (
              <tr key={i}>
                <td className="px-5 py-2.5 text-gray-700">{feature}</td>
                {vals.map((v, j) => (
                  <td key={j} className="text-center px-4 py-2.5 text-gray-500">
                    {typeof v === 'boolean' ? (
                      v ? <Check className="w-4 h-4 text-blue-600 mx-auto" /> : <span className="text-gray-300">-</span>
                    ) : v}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* FAQ */}
      <div className="bg-white rounded-xl ring-1 ring-gray-200 p-5">
        <h2 className="text-sm font-semibold text-gray-900 mb-4">자주 묻는 질문</h2>
        <div className="space-y-4">
          {faqs.map(([q, a]) => (
            <div key={q}>
              <p className="text-sm font-medium text-gray-700">{q}</p>
              <p className="text-sm text-gray-500 mt-0.5">{a}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
