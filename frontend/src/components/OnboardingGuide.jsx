import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import api from '../lib/api'
import { ArrowRight, X, Sparkles } from 'lucide-react'

const STEPS = [
  {
    id: 'welcome',
    type: 'modal',
    title: '환영합니다!',
    desc: 'Outreach를 시작해볼까요?\n3분이면 첫 영업 캠페인을 만들 수 있습니다.',
    btn: '시작하기',
  },
  {
    id: 'create_project',
    type: 'spotlight',
    page: '/dashboard',
    target: '[data-onboarding="new-project"]',
    title: '프로젝트 만들기',
    desc: '이 버튼을 눌러 영업 캠페인 프로젝트를 만드세요.',
    btn: '다음',
  },
  {
    id: 'setup_email',
    type: 'spotlight',
    page: '/settings',
    target: '[data-onboarding="gmail-section"]',
    title: 'Gmail 연동',
    desc: 'Gmail 앱 비밀번호를 등록하면 이메일을 보낼 수 있습니다.',
    btn: '다음',
  },
  {
    id: 'setup_instagram',
    type: 'spotlight',
    page: '/settings',
    target: '[data-onboarding="instagram-section"]',
    title: '인스타 DM 자동화',
    desc: '크롬 확장을 설치하면 본인 브라우저에서 자동 DM 발송이 가능합니다. 안전성 1등 방식.',
    btn: '다음',
  },
  {
    id: 'go_pipeline',
    type: 'spotlight',
    page: '/pipeline',
    target: '[data-onboarding="pipeline-board"]',
    title: '영업 파이프라인',
    desc: '영업 딜을 칸반 보드로 단계별 관리할 수 있습니다.',
    btn: '다음',
  },
  {
    id: 'complete',
    type: 'modal',
    title: '준비 완료!',
    desc: '이제 프로젝트에서 키워드를 추가하고\n잠재고객을 수집해보세요.',
    btn: '시작하기',
    emoji: '🎉',
  },
]

export default function OnboardingGuide() {
  const [show, setShow] = useState(false)
  const [step, setStep] = useState(0)
  const [rect, setRect] = useState(null)
  const [ready, setReady] = useState(false) // target element found
  const navigate = useNavigate()
  const location = useLocation()
  const retriesRef = useRef(null)

  useEffect(() => {
    api.get('/onboarding')
      .then((r) => {
        if (!r.data.dismissed && !r.data.is_completed) setShow(true)
      })
      .catch(() => {})
  }, [])

  // Navigate to the step's page if needed
  useEffect(() => {
    if (!show) return
    const s = STEPS[step]
    if (s.page && location.pathname !== s.page) {
      navigate(s.page)
    }
  }, [show, step])

  // Find target element (with retries for lazy-loaded pages)
  const track = useCallback(() => {
    const s = STEPS[step]
    if (s.type !== 'spotlight' || !s.target) {
      setRect(null)
      setReady(true)
      return
    }
    const el = document.querySelector(s.target)
    if (!el) {
      setRect(null)
      setReady(false)
      return
    }
    const r = el.getBoundingClientRect()
    setRect({ top: r.top, left: r.left, width: r.width, height: r.height })
    setReady(true)
  }, [step])

  useEffect(() => {
    if (!show) return
    setReady(false)
    setRect(null)

    // Retry until element is found (page might still be loading)
    let attempts = 0
    const tryFind = () => {
      track()
      attempts++
      if (attempts < 15) {
        retriesRef.current = setTimeout(tryFind, 200)
      }
    }
    tryFind()

    window.addEventListener('resize', track)
    window.addEventListener('scroll', track, true)
    return () => {
      clearTimeout(retriesRef.current)
      window.removeEventListener('resize', track)
      window.removeEventListener('scroll', track, true)
    }
  }, [show, step, location.pathname, track])

  const completeStep = (id) => {
    if (id === 'welcome' || id === 'complete') return
    api.post('/onboarding/complete-step', { step_id: id }).catch(() => {})
  }

  const next = () => {
    completeStep(STEPS[step].id)
    if (step + 1 >= STEPS.length) {
      dismiss()
      navigate('/dashboard')
      return
    }
    setStep(step + 1)
  }

  const dismiss = () => {
    setShow(false)
    api.post('/onboarding/dismiss').catch(() => {})
  }

  if (!show) return null

  const s = STEPS[step]
  const isSpotlight = s.type === 'spotlight'
  const progress = ((step + 1) / STEPS.length) * 100
  const pad = 12

  // Don't render spotlight until target is found
  if (isSpotlight && !ready) {
    return (
      <div className="fixed inset-0 bg-black/55 flex items-center justify-center" style={{ zIndex: 10000 }}>
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white" />
      </div>
    )
  }

  // Tooltip position
  const getTooltipPos = () => {
    if (!rect) return {}
    const tw = 280, gap = 16
    let top = rect.top + rect.height + pad + gap
    let left = rect.left + rect.width / 2 - tw / 2
    if (top + 200 > window.innerHeight) top = rect.top - pad - gap - 180
    left = Math.max(12, Math.min(left, window.innerWidth - tw - 12))
    top = Math.max(12, top)
    return { position: 'fixed', top, left, width: tw, zIndex: 10003 }
  }

  // Shared card
  const Card = ({ large }) => (
    <div className={`bg-white shadow-xl ${large ? 'rounded-2xl p-7 w-full max-w-xs' : 'rounded-xl p-4 w-[280px]'}`}>
      <div className={`flex justify-end ${large ? '-mt-1 -mr-1 mb-1' : '-mt-0.5 -mr-0.5 mb-0.5'}`}>
        <button onClick={dismiss} className="p-1 text-gray-400 hover:text-gray-600 cursor-pointer">
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
      {large && s.id === 'welcome' && (
        <div className="w-11 h-11 bg-blue-50 rounded-full flex items-center justify-center mx-auto mb-3">
          <Sparkles className="w-5 h-5 text-blue-600" />
        </div>
      )}
      {large && s.emoji && <p className="text-3xl text-center mb-3">{s.emoji}</p>}
      <div className={large ? 'text-center' : ''}>
        <h3 className={`font-semibold text-gray-900 mb-1 ${large ? 'text-base' : 'text-sm'}`}>{s.title}</h3>
        <p className={`text-gray-500 whitespace-pre-line leading-relaxed ${large ? 'text-sm mb-5' : 'text-xs mb-3'}`}>{s.desc}</p>
      </div>
      <div className="h-1 bg-gray-100 rounded-full mb-3 overflow-hidden">
        <div className="h-full bg-blue-600 rounded-full" style={{ width: `${progress}%` }} />
      </div>
      <div className="flex gap-2">
        <button onClick={dismiss} className={`flex-1 text-gray-400 hover:text-gray-600 cursor-pointer ${large ? 'py-2 text-sm' : 'py-1.5 text-xs'}`}>
          건너뛰기
        </button>
        <button onClick={next} className={`flex-1 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 cursor-pointer flex items-center justify-center gap-1 ${large ? 'py-2 text-sm' : 'py-1.5 text-xs'}`}>
          {s.btn} <ArrowRight className={large ? 'w-3.5 h-3.5' : 'w-3 h-3'} />
        </button>
      </div>
    </div>
  )

  return (
    <>
      {/* Overlay — 스포트라이트 모드에선 클릭을 가로채지 않음 (실제 버튼이 눌려야 함) */}
      <div className="fixed inset-0" style={{ zIndex: 10000, pointerEvents: isSpotlight ? 'none' : 'auto' }}>
        {isSpotlight && rect ? (
          <div style={{
            position: 'fixed',
            top: rect.top - pad,
            left: rect.left - pad,
            width: rect.width + pad * 2,
            height: rect.height + pad * 2,
            borderRadius: 12,
            boxShadow: '0 0 0 9999px rgba(0,0,0,0.55)',
            border: '2px solid rgba(96,165,250,0.6)',
            zIndex: 10001,
            pointerEvents: 'none',
          }} />
        ) : (
          <div className="absolute inset-0 bg-black/55" />
        )}
      </div>

      {/* Click zone on spotlight target — 실제 요소를 클릭시키고 투어 종료 (사용자가 실작업 시작) */}
      {isSpotlight && rect && (
        <div
          style={{
            position: 'fixed',
            top: rect.top,
            left: rect.left,
            width: rect.width,
            height: rect.height,
            zIndex: 10002,
            cursor: 'pointer',
          }}
          onClick={() => {
            completeStep(s.id)
            setShow(false)
            api.post('/onboarding/dismiss').catch(() => {})
            const el = document.querySelector(s.target)
            if (el) {
              const clickable = el.matches('button, a, [role="button"]')
                ? el
                : el.querySelector('button, a, [role="button"]') || el
              // 오버레이 언마운트 후 실제 클릭 전달
              setTimeout(() => clickable.click?.(), 0)
            }
          }}
        />
      )}

      {/* Card */}
      {isSpotlight && rect ? (
        <div style={getTooltipPos()}>
          <Card large={false} />
        </div>
      ) : !isSpotlight ? (
        <div className="fixed inset-0 flex items-center justify-center p-4" style={{ zIndex: 10003 }}>
          <Card large={true} />
        </div>
      ) : null}
    </>
  )
}
