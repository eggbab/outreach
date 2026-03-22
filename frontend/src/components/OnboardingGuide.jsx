import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import api from '../lib/api'
import { ArrowRight, X, CheckCircle, Sparkles } from 'lucide-react'

/*
  Spotlight onboarding — dims entire screen, highlights only
  the element the user needs to interact with.
*/

const TOUR_STEPS = [
  {
    id: 'welcome',
    target: null, // center modal, no spotlight
    title: '환영합니다!',
    description: 'Outreach를 시작해볼까요?\n3분이면 첫 영업 캠페인을 만들 수 있습니다.',
    buttonText: '시작하기',
    position: 'center',
  },
  {
    id: 'create_project',
    target: '[data-onboarding="new-project"]',
    title: '1단계: 프로젝트 만들기',
    description: '영업 캠페인을 프로젝트 단위로 관리합니다.\n"새 프로젝트" 버튼을 클릭하세요.',
    buttonText: null, // user must click the target
    position: 'bottom',
    page: '/dashboard',
  },
  {
    id: 'go_settings',
    target: '[data-onboarding="nav-settings"]',
    title: '2단계: Gmail 연동하기',
    description: '이메일을 보내려면 Gmail 설정이 필요합니다.\n설정 메뉴를 클릭하세요.',
    buttonText: null,
    position: 'right',
    page: '/dashboard',
  },
  {
    id: 'setup_email',
    target: '[data-onboarding="gmail-section"]',
    title: 'Gmail 앱 비밀번호 입력',
    description: 'Gmail 주소와 앱 비밀번호를 입력하고 저장하세요.\nGoogle 계정 → 보안 → 앱 비밀번호에서 생성할 수 있습니다.',
    buttonText: '다음으로',
    position: 'bottom',
    page: '/settings',
  },
  {
    id: 'go_pipeline',
    target: '[data-onboarding="nav-pipeline"]',
    title: '3단계: 파이프라인 확인',
    description: '영업 딜을 관리하는 칸반 보드입니다.\n파이프라인을 클릭해서 확인해보세요.',
    buttonText: null,
    position: 'right',
    page: '/settings',
  },
  {
    id: 'complete',
    target: null,
    title: '설정 완료!',
    description: '이제 프로젝트에서 키워드를 추가하고\n잠재고객을 수집해보세요.',
    buttonText: '시작하기',
    position: 'center',
  },
]

export default function OnboardingGuide() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [currentStep, setCurrentStep] = useState(-1) // -1 = not started
  const [spotlight, setSpotlight] = useState(null) // {top, left, width, height}
  const navigate = useNavigate()
  const location = useLocation()
  const observerRef = useRef(null)

  useEffect(() => {
    api.get('/onboarding')
      .then((r) => {
        setData(r.data)
        if (!r.data.dismissed && !r.data.is_completed) {
          // Find first incomplete step
          const firstIncomplete = TOUR_STEPS.findIndex(
            (s) => s.id !== 'welcome' && s.id !== 'complete' && !r.data.steps_completed.includes(s.id)
          )
          setCurrentStep(firstIncomplete === -1 ? 0 : 0) // always start from welcome
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const updateSpotlight = useCallback(() => {
    if (currentStep < 0 || currentStep >= TOUR_STEPS.length) return
    const step = TOUR_STEPS[currentStep]
    if (!step.target) {
      setSpotlight(null)
      return
    }
    const el = document.querySelector(step.target)
    if (el) {
      const rect = el.getBoundingClientRect()
      setSpotlight({
        top: rect.top - 6,
        left: rect.left - 6,
        width: rect.width + 12,
        height: rect.height + 12,
      })
      // Scroll into view if needed
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    } else {
      setSpotlight(null)
    }
  }, [currentStep])

  // Update spotlight when step changes or page navigates
  useEffect(() => {
    updateSpotlight()
    const timer = setTimeout(updateSpotlight, 300) // retry after animations
    window.addEventListener('resize', updateSpotlight)
    return () => {
      clearTimeout(timer)
      window.removeEventListener('resize', updateSpotlight)
    }
  }, [currentStep, location.pathname, updateSpotlight])

  // Listen for target element clicks
  useEffect(() => {
    if (currentStep < 0 || currentStep >= TOUR_STEPS.length) return
    const step = TOUR_STEPS[currentStep]
    if (!step.target || step.buttonText) return // skip if has explicit button

    const handler = () => {
      completeStep(step.id)
      goNext()
    }

    // Wait for element to exist
    const interval = setInterval(() => {
      const el = document.querySelector(step.target)
      if (el) {
        el.addEventListener('click', handler, { once: true })
        clearInterval(interval)
      }
    }, 200)

    return () => {
      clearInterval(interval)
      const el = document.querySelector(step.target)
      if (el) el.removeEventListener('click', handler)
    }
  }, [currentStep])

  const completeStep = async (stepId) => {
    if (stepId === 'welcome' || stepId === 'complete') return
    try {
      await api.post('/onboarding/complete-step', { step_id: stepId })
    } catch {}
  }

  const goNext = () => {
    const nextStep = currentStep + 1
    if (nextStep >= TOUR_STEPS.length) {
      dismiss()
      return
    }
    const next = TOUR_STEPS[nextStep]
    if (next.page && location.pathname !== next.page) {
      navigate(next.page)
    }
    setCurrentStep(nextStep)
  }

  const dismiss = async () => {
    setCurrentStep(-1)
    try {
      await api.post('/onboarding/dismiss')
      setData({ ...data, dismissed: true })
    } catch {}
  }

  if (loading || !data || data.dismissed || data.is_completed || currentStep < 0) return null

  const step = TOUR_STEPS[currentStep]
  const isCenter = step.position === 'center'
  const progress = ((currentStep + 1) / TOUR_STEPS.length) * 100

  // Calculate tooltip position
  const getTooltipStyle = () => {
    if (isCenter || !spotlight) return {}
    const pad = 16
    switch (step.position) {
      case 'bottom':
        return {
          position: 'fixed',
          top: spotlight.top + spotlight.height + pad,
          left: Math.max(16, spotlight.left + spotlight.width / 2 - 160),
          zIndex: 10002,
        }
      case 'right':
        return {
          position: 'fixed',
          top: spotlight.top,
          left: spotlight.left + spotlight.width + pad,
          zIndex: 10002,
        }
      case 'left':
        return {
          position: 'fixed',
          top: spotlight.top,
          right: window.innerWidth - spotlight.left + pad,
          zIndex: 10002,
        }
      case 'top':
        return {
          position: 'fixed',
          bottom: window.innerHeight - spotlight.top + pad,
          left: Math.max(16, spotlight.left + spotlight.width / 2 - 160),
          zIndex: 10002,
        }
      default:
        return {}
    }
  }

  return (
    <>
      {/* Dark overlay with spotlight cutout */}
      <div
        className="fixed inset-0"
        style={{ zIndex: 10000 }}
        onClick={(e) => {
          // Only dismiss if clicking overlay (not spotlight area)
          if (!spotlight) return
          const { top, left, width, height } = spotlight
          const x = e.clientX, y = e.clientY
          if (x < left || x > left + width || y < top || y > top + height) {
            // clicked outside spotlight — do nothing (trap clicks)
          }
        }}
      >
        <svg width="100%" height="100%" className="absolute inset-0">
          <defs>
            <mask id="spotlight-mask">
              <rect width="100%" height="100%" fill="white" />
              {spotlight && (
                <rect
                  x={spotlight.left}
                  y={spotlight.top}
                  width={spotlight.width}
                  height={spotlight.height}
                  rx="12"
                  fill="black"
                />
              )}
            </mask>
          </defs>
          <rect
            width="100%"
            height="100%"
            fill="rgba(0,0,0,0.6)"
            mask="url(#spotlight-mask)"
          />
        </svg>

        {/* Spotlight border glow */}
        {spotlight && (
          <div
            className="absolute rounded-xl pointer-events-none"
            style={{
              top: spotlight.top - 2,
              left: spotlight.left - 2,
              width: spotlight.width + 4,
              height: spotlight.height + 4,
              border: '2px solid rgba(59,130,246,0.6)',
              boxShadow: '0 0 20px rgba(59,130,246,0.3)',
              zIndex: 10001,
              animation: 'spotlightPulse 2s ease-in-out infinite',
            }}
          />
        )}
      </div>

      {/* Tooltip / Modal */}
      {isCenter ? (
        // Center modal
        <div className="fixed inset-0 flex items-center justify-center" style={{ zIndex: 10002 }}>
          <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-sm w-full mx-4" style={{ animation: 'tooltipIn 0.3s ease' }}>
            <div className="flex justify-end mb-2">
              <button onClick={dismiss} className="p-1 text-gray-400 hover:text-gray-600 cursor-pointer">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="text-center">
              <div className="w-14 h-14 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Sparkles className="w-7 h-7 text-blue-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">{step.title}</h3>
              <p className="text-sm text-gray-500 whitespace-pre-line mb-6">{step.description}</p>
              {/* Progress */}
              <div className="h-1 bg-gray-100 rounded-full mb-4 overflow-hidden">
                <div className="h-full bg-blue-600 rounded-full transition-all duration-500" style={{ width: `${progress}%` }} />
              </div>
              <div className="flex gap-3">
                <button
                  onClick={dismiss}
                  className="flex-1 py-2.5 text-sm text-gray-500 hover:text-gray-700 cursor-pointer"
                >
                  건너뛰기
                </button>
                <button
                  onClick={goNext}
                  className="flex-1 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 cursor-pointer flex items-center justify-center gap-2"
                >
                  {step.buttonText} <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : (
        // Positioned tooltip near spotlight
        <div style={getTooltipStyle()}>
          <div
            className="bg-white rounded-xl shadow-2xl p-5 w-80"
            style={{ animation: 'tooltipIn 0.3s ease' }}
          >
            <div className="flex items-start justify-between mb-2">
              <h3 className="text-sm font-semibold text-gray-900">{step.title}</h3>
              <button onClick={dismiss} className="p-0.5 text-gray-400 hover:text-gray-600 cursor-pointer shrink-0">
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
            <p className="text-xs text-gray-500 whitespace-pre-line mb-4">{step.description}</p>
            {/* Progress */}
            <div className="h-1 bg-gray-100 rounded-full mb-3 overflow-hidden">
              <div className="h-full bg-blue-600 rounded-full transition-all duration-500" style={{ width: `${progress}%` }} />
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-gray-400">{currentStep + 1}/{TOUR_STEPS.length}</span>
              <div className="flex gap-2">
                <button onClick={dismiss} className="text-xs text-gray-400 hover:text-gray-600 cursor-pointer">
                  건너뛰기
                </button>
                {step.buttonText && (
                  <button
                    onClick={() => { completeStep(step.id); goNext() }}
                    className="text-xs text-blue-600 font-medium hover:text-blue-700 cursor-pointer flex items-center gap-1"
                  >
                    {step.buttonText} <ArrowRight className="w-3 h-3" />
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes spotlightPulse {
          0%, 100% { box-shadow: 0 0 20px rgba(59,130,246,0.3); }
          50% { box-shadow: 0 0 30px rgba(59,130,246,0.5); }
        }
        @keyframes tooltipIn {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </>
  )
}
