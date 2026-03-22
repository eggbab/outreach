import { useState, useEffect } from 'react'
import api from '../lib/api'
import { CheckCircle, Circle, X } from 'lucide-react'

export default function OnboardingGuide() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/onboarding')
      .then((r) => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const dismiss = async () => {
    await api.post('/onboarding/dismiss')
    setData({ ...data, dismissed: true })
  }

  if (loading || !data || data.dismissed || data.is_completed) return null

  const completedCount = data.steps_completed.length
  const totalSteps = data.steps.length
  const progress = (completedCount / totalSteps) * 100

  return (
    <div className="bg-white rounded-xl border border-blue-200 p-5 mb-6">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-gray-900">시작 가이드</h3>
          <p className="text-xs text-gray-500 mt-0.5">{completedCount}/{totalSteps} 완료</p>
        </div>
        <button onClick={dismiss} className="p-1 text-gray-400 hover:text-gray-600 cursor-pointer">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="h-1.5 bg-gray-100 rounded-full mb-4 overflow-hidden">
        <div className="h-full bg-blue-600 rounded-full transition-all" style={{ width: `${progress}%` }} />
      </div>

      <div className="space-y-2">
        {data.steps.map((step) => {
          const done = data.steps_completed.includes(step.id)
          return (
            <div key={step.id} className="flex items-center gap-3">
              {done ? (
                <CheckCircle className="w-4 h-4 text-green-500 shrink-0" />
              ) : (
                <Circle className="w-4 h-4 text-gray-300 shrink-0" />
              )}
              <span className={`text-sm ${done ? 'text-gray-400 line-through' : 'text-gray-700'}`}>
                {step.label}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
