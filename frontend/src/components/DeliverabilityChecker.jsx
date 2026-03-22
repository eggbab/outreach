import { useState } from 'react'
import api from '../lib/api'
import { Shield, AlertTriangle, CheckCircle, Loader2 } from 'lucide-react'

export default function DeliverabilityChecker() {
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  const check = async () => {
    setLoading(true)
    try {
      const res = await api.post('/deliverability/check', { subject, body })
      setResult(res.data)
    } catch {}
    setLoading(false)
  }

  const getScoreColor = (score) => {
    if (score >= 80) return 'text-green-600'
    if (score >= 50) return 'text-yellow-600'
    return 'text-red-600'
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h2 className="text-base font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <Shield className="w-5 h-5 text-blue-600" />
        발송 건강도 체크
      </h2>

      <div className="space-y-3 mb-4">
        <input
          type="text"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          placeholder="이메일 제목"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
        />
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={4}
          placeholder="이메일 본문"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm resize-y"
        />
        <button
          onClick={check}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 cursor-pointer"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin inline" /> : '점수 확인'}
        </button>
      </div>

      {result && (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className={`text-3xl font-bold ${getScoreColor(result.score)}`}>{result.score}</span>
            <span className="text-sm text-gray-500">/100점</span>
          </div>

          {result.issues.length > 0 && (
            <div className="space-y-1">
              {result.issues.map((issue, i) => (
                <div key={i} className="flex items-start gap-2 text-sm">
                  <AlertTriangle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                  <span className="text-gray-700">{issue}</span>
                </div>
              ))}
            </div>
          )}

          {result.suggestions.length > 0 && (
            <div className="space-y-1">
              {result.suggestions.map((sug, i) => (
                <div key={i} className="flex items-start gap-2 text-sm">
                  <CheckCircle className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
                  <span className="text-gray-600">{sug}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
