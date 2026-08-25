import { useState } from 'react'
import api from '../lib/api'
import { ShieldCheck, ShieldAlert, ShieldX, Loader2 } from 'lucide-react'

const STATUS_UI = {
  ok: { icon: ShieldCheck, color: 'text-green-600', label: '정상' },
  warn: { icon: ShieldAlert, color: 'text-yellow-600', label: '주의' },
  missing: { icon: ShieldX, color: 'text-red-600', label: '없음' },
  unknown: { icon: ShieldAlert, color: 'text-gray-400', label: '확인 불가' },
}

function Row({ name, data }) {
  const ui = STATUS_UI[data.status] || STATUS_UI.unknown
  const Icon = ui.icon
  return (
    <div className="flex items-start gap-3 py-2 border-b border-gray-50 last:border-0">
      <Icon className={`w-4 h-4 mt-0.5 flex-shrink-0 ${ui.color}`} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-800">{name}</span>
          <span className={`text-xs ${ui.color}`}>{ui.label}</span>
        </div>
        <p className="text-xs text-gray-400 mt-0.5">{data.detail}</p>
      </div>
    </div>
  )
}

export default function DomainAuthCheck() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [checked, setChecked] = useState(false)

  const run = async () => {
    setLoading(true)
    try {
      const res = await api.get('/deliverability/domain-auth')
      setResult(res.data)
      setChecked(true)
    } catch {
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  const scoreColor = (s) => (s >= 80 ? 'text-green-600' : s >= 40 ? 'text-yellow-600' : 'text-red-600')

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-1">
        <h2 className="text-base font-semibold text-gray-900">발신 도메인 인증</h2>
        <button
          onClick={run}
          disabled={loading}
          className="text-sm px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1.5"
        >
          {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
          {checked ? '다시 검사' : '인증 검사'}
        </button>
      </div>
      <p className="text-xs text-gray-400 mb-4">
        SPF·DKIM·DMARC는 이메일이 스팸함이 아닌 받은편지함에 도달하게 하는 핵심 인증입니다.
      </p>

      {result && (
        <div>
          <div className="flex items-center gap-3 mb-3">
            <span className={`text-3xl font-bold ${scoreColor(result.score)}`}>{result.score}</span>
            <span className="text-sm text-gray-500">/ 100 · {result.domain}</span>
          </div>
          <p className="text-sm text-gray-600 mb-3">{result.summary}</p>
          {!result.google_managed && (
            <div className="rounded-lg border border-gray-100 px-4 py-1">
              <Row name="SPF" data={result.spf} />
              <Row name="DKIM" data={result.dkim} />
              <Row name="DMARC" data={result.dmarc} />
            </div>
          )}
          {!result.google_managed && result.score < 100 && (
            <p className="text-xs text-gray-400 mt-3">
              커스텀 도메인을 Gmail로 발송한다면 도메인 DNS에 SPF(<code>include:_spf.google.com</code>),
              Google DKIM, DMARC(<code>p=quarantine</code> 이상)를 설정하세요.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
