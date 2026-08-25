import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import api from '../lib/api'
import { useAuth } from '../lib/auth'
import { Save, Loader2, Key, AlertTriangle, Shield, ShieldAlert } from 'lucide-react'
import DeliverabilityChecker from '../components/DeliverabilityChecker'
import TagManager from '../components/TagManager'

const RISK_CONFIG = {
  safe: { label: '안전', color: 'text-green-700 bg-green-100', icon: Shield },
  moderate: { label: '주의', color: 'text-yellow-700 bg-yellow-100', icon: AlertTriangle },
  risky: { label: '위험', color: 'text-red-700 bg-red-100', icon: ShieldAlert },
}

const DEFAULT_SETTINGS = {
  gmail_email: '',
  gmail_app_password: '',
  email_subject: '안녕하세요, {company_name}님께 제안 드립니다',
  email_template: `안녕하세요, {company_name} 담당자님.\n\n저희 서비스를 소개해드리고자 연락드립니다.\n\n관심 있으시면 편하게 회신 부탁드립니다.\n\n감사합니다.`,
  dm_template: `안녕하세요 {name}님! 좋은 기회로 연락드립니다.`,
  daily_email_limit: 80,
  daily_dm_limit: 15,
  ad_prefix_enabled: true,
  sender_info: '',
}

function normalizeSettings(data = {}) {
  return {
    gmail_email: data.gmail_email ?? DEFAULT_SETTINGS.gmail_email,
    gmail_app_password: data.gmail_app_password ?? DEFAULT_SETTINGS.gmail_app_password,
    email_subject: data.email_subject ?? DEFAULT_SETTINGS.email_subject,
    email_template: data.email_template ?? DEFAULT_SETTINGS.email_template,
    dm_template: data.dm_template ?? DEFAULT_SETTINGS.dm_template,
    daily_email_limit: Number(data.daily_email_limit ?? DEFAULT_SETTINGS.daily_email_limit),
    daily_dm_limit: Number(data.daily_dm_limit ?? DEFAULT_SETTINGS.daily_dm_limit),
    ad_prefix_enabled: data.ad_prefix_enabled ?? DEFAULT_SETTINGS.ad_prefix_enabled,
    sender_info: data.sender_info ?? DEFAULT_SETTINGS.sender_info,
  }
}

function SafetyGuide({ settings, onChange }) {
  const [guide, setGuide] = useState(null)

  useEffect(() => {
    api.get('/settings/safety-guide').then(r => setGuide(r.data)).catch(() => {})
  }, [])

  if (!guide) return null

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h2 className="text-base font-semibold text-gray-900 mb-1">발송 속도 설정</h2>
      <p className="text-xs text-gray-400 mb-5">
        계정 보호를 위한 권장치가 표시됩니다. 직접 조정할 수 있지만 초과 시 책임은 사용자에게 있습니다.
      </p>

      {guide.email.warmup_remaining_days > 0 && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-700">
          <span className="font-medium">워밍업 기간</span> — 계정 생성 후 {guide.account_age_days}일차입니다.
          안전을 위해 {guide.email.warmup_remaining_days}일간 발송량을 서서히 늘리세요.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-5">
        {/* Email */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-900">이메일</h3>
            {(() => {
              const r = RISK_CONFIG[guide.email.risk_level]
              const Icon = r.icon
              return (
                <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${r.color}`}>
                  <Icon className="w-3 h-3" /> {r.label}
                </span>
              )
            })()}
          </div>
          <div>
            <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
              <span>일일 한도</span>
              <span className="text-gray-400">권장: {guide.email.recommended}건 / 최대: {guide.email.max_allowed}건</span>
            </div>
            <input
              type="number"
              min={1}
              max={guide.email.max_allowed}
              value={settings.daily_email_limit}
              onChange={(e) => onChange('daily_email_limit', parseInt(e.target.value) || 0)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          {guide.email.warning && (
            <p className="text-xs text-yellow-600">{guide.email.warning}</p>
          )}
        </div>

        {/* DM */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-900">인스타 DM</h3>
            {(() => {
              const r = RISK_CONFIG[guide.dm.risk_level]
              const Icon = r.icon
              return (
                <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${r.color}`}>
                  <Icon className="w-3 h-3" /> {r.label}
                </span>
              )
            })()}
          </div>
          <div>
            <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
              <span>일일 한도</span>
              <span className="text-gray-400">권장: {guide.dm.recommended}건 / 최대: {guide.dm.max_allowed}건</span>
            </div>
            <input
              type="number"
              min={1}
              max={guide.dm.max_allowed}
              value={settings.daily_dm_limit}
              onChange={(e) => onChange('daily_dm_limit', parseInt(e.target.value) || 0)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          {guide.dm.warning && (
            <p className="text-xs text-yellow-600">{guide.dm.warning}</p>
          )}
        </div>
      </div>

      {/* Tips */}
      <details className="group">
        <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700 select-none">
          계정 보호 가이드 보기
        </summary>
        <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <p className="text-xs font-semibold text-gray-700 mb-2">이메일 (Gmail)</p>
            <ul className="space-y-1.5">
              {guide.email.guide.tips.map((tip, i) => (
                <li key={i} className="text-xs text-gray-500 flex items-start gap-1.5">
                  <span className="text-gray-300 mt-0.5">•</span>{tip}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-xs font-semibold text-gray-700 mb-2">인스타그램 DM</p>
            <ul className="space-y-1.5">
              {guide.dm.guide.tips.map((tip, i) => (
                <li key={i} className="text-xs text-gray-500 flex items-start gap-1.5">
                  <span className="text-gray-300 mt-0.5">•</span>{tip}
                </li>
              ))}
            </ul>
          </div>
        </div>
        <p className="mt-3 text-[10px] text-gray-400">{guide.disclaimer}</p>
      </details>
    </div>
  )
}

export default function SettingsPage() {
  const { user } = useAuth()
  const [serviceKey, setServiceKey] = useState('')
  const [keyActivating, setKeyActivating] = useState(false)
  const [keyMessage, setKeyMessage] = useState(null)
  const [settings, setSettings] = useState(DEFAULT_SETTINGS)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState(null)

  const showToast = (message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  useEffect(() => {
    api.get('/settings')
      .then((res) => setSettings((prev) => normalizeSettings({ ...prev, ...res.data })))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleChange = (key, value) => {
    setSettings((prev) => ({ ...prev, [key]: value }))
  }

  const handleSave = async () => {
    setSaving(true)
    // 백엔드 SettingsUpdate 화이트리스트만 전송
    const allowed = [
      'gmail_email', 'gmail_app_password', 'email_subject', 'email_template',
      'dm_template',
      'daily_email_limit', 'daily_dm_limit',
      'ad_prefix_enabled', 'sender_info',
    ]
    const payload = {}
    for (const k of allowed) {
      const v = settings[k]
      // 빈 비밀번호는 보내지 않음 (저장된 값 유지)
      if (k === 'gmail_app_password' && !v) continue
      if (v !== undefined && v !== null) payload[k] = v
    }
    try {
      await api.put('/settings', payload)
      showToast('설정이 저장되었습니다.')
    } catch (err) {
      showToast(err.response?.data?.detail || '설정 저장 실패', 'error')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

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

      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">설정</h1>
        <p className="text-gray-500 mt-1">이메일 및 DM 발송 설정을 관리합니다.</p>
      </div>

      <div className="space-y-6">
        {/* Service Key */}
        {user?.plan === 'free' && (
          <div className="bg-white rounded-xl border border-blue-200 p-6">
            <h2 className="text-base font-semibold text-gray-900 mb-1 flex items-center gap-2">
              <Key className="w-4 h-4 text-blue-600" />
              서비스 키 등록
            </h2>
            <p className="text-sm text-gray-500 mb-4">서비스 키를 등록하면 Pro 플랜으로 업그레이드됩니다.</p>
            {keyMessage && (
              <div className={`mb-3 p-3 rounded-lg text-sm ${keyMessage.type === 'error' ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
                {keyMessage.text}
              </div>
            )}
            <div className="flex gap-3">
              <input
                type="text"
                value={serviceKey}
                onChange={(e) => setServiceKey(e.target.value)}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm font-mono"
                placeholder="sk_xxxxxxxxxxxxxxxx"
              />
              <button
                onClick={async () => {
                  if (!serviceKey.trim()) return
                  setKeyActivating(true)
                  setKeyMessage(null)
                  try {
                    const res = await api.post('/auth/activate-key', { service_key: serviceKey.trim() })
                    setKeyMessage({ type: 'success', text: res.data.message })
                    setServiceKey('')
                    window.location.reload()
                  } catch (err) {
                    setKeyMessage({ type: 'error', text: err.response?.data?.detail || '등록 실패' })
                  } finally {
                    setKeyActivating(false)
                  }
                }}
                disabled={keyActivating || !serviceKey.trim()}
                className="px-5 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 text-sm cursor-pointer"
              >
                {keyActivating ? '등록 중...' : '등록'}
              </button>
            </div>
          </div>
        )}

        {/* Gmail Settings */}
        <div data-onboarding="gmail-section" className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-4">Gmail 설정</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Gmail 주소</label>
              <input
                type="email"
                value={settings.gmail_email}
                onChange={(e) => handleChange('gmail_email', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                placeholder="your-email@gmail.com"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">앱 비밀번호</label>
              <input
                type="password"
                value={settings.gmail_app_password}
                onChange={(e) => handleChange('gmail_app_password', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                placeholder="Google 앱 비밀번호"
              />
              <p className="text-xs text-gray-400 mt-1">
                Google 계정 &gt; 보안 &gt; 2단계 인증 &gt; 앱 비밀번호에서 생성
              </p>
            </div>
          </div>
        </div>

        {/* Email Subject */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-4">이메일 제목</h2>
          <input
            type="text"
            value={settings.email_subject || ''}
            onChange={(e) => handleChange('email_subject', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
            placeholder="안녕하세요, {company_name}님께 제안 드립니다"
          />
          <p className="text-xs text-gray-400 mt-2">
            변수: {'{name}'}, {'{company_name}'}, {'{category}'}, {'{sender_name}'}
          </p>
        </div>

        {/* Email Template */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-4">이메일 본문 템플릿</h2>
          <textarea
            value={settings.email_template}
            onChange={(e) => handleChange('email_template', e.target.value)}
            rows={8}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm font-mono resize-y"
            placeholder="이메일 본문 템플릿"
          />
          <p className="text-xs text-gray-400 mt-2">
            변수: {'{name}'}, {'{company_name}'}, {'{category}'}, {'{sender_name}'} (HTML 사용 가능)
          </p>
        </div>

        {/* 정보통신망법 컴플라이언스 */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-1 flex items-center gap-2">
            <Shield className="w-4 h-4 text-green-600" />
            법적 준수 (정보통신망법)
          </h2>
          <p className="text-xs text-gray-400 mb-4">
            광고성 이메일에 필수 표기를 자동 삽입합니다. 수신거부 링크와 One-Click 수신거부 헤더는 항상 자동 포함됩니다.
          </p>
          <div className="space-y-4">
            <label className="flex items-center justify-between cursor-pointer">
              <div>
                <div className="text-sm font-medium text-gray-700">제목에 (광고) 자동 표기</div>
                <div className="text-xs text-gray-400 mt-0.5">
                  정보통신망법 §50 필수 표기 — 끄면 법 위반 위험은 사용자 책임입니다.
                </div>
              </div>
              <input
                type="checkbox"
                checked={settings.ad_prefix_enabled}
                onChange={(e) => handleChange('ad_prefix_enabled', e.target.checked)}
                className="w-5 h-5 accent-blue-600 cursor-pointer"
              />
            </label>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">전송자 정보 (푸터에 표기)</label>
              <textarea
                value={settings.sender_info}
                onChange={(e) => handleChange('sender_info', e.target.value)}
                rows={3}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm resize-y"
                placeholder={'주식회사 OO\n서울시 강남구 테헤란로 123\n02-1234-5678'}
              />
              <p className="text-xs text-gray-400 mt-1">
                회사명·주소·연락처를 입력하면 모든 발송 메일 하단에 자동 표기됩니다.
              </p>
            </div>
          </div>
        </div>

        {/* Instagram DM = 크롬 확장 설치 안내 */}
        <div data-onboarding="instagram-section" className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-2">인스타그램 DM 자동화</h2>
          <p className="text-sm text-gray-500 mb-4">
            인스타 DM은 <strong>크롬 확장</strong>을 통해 본인 브라우저에서 직접 발송됩니다.
            (서버에서 자동 로그인하면 인스타가 즉시 정지하기 때문에, 본인 브라우저 세션 사용이 가장 안전합니다.)
          </p>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4 text-sm">
            <div className="font-semibold text-blue-900 mb-2">📨 한 눈에 보는 흐름</div>
            <ol className="space-y-1 text-blue-800 list-decimal list-inside">
              <li>크롬 확장 설치 (한 번만)</li>
              <li>크롬에서 본인 인스타에 로그인 (평소처럼)</li>
              <li>확장 팝업에서 우리 사이트 계정으로 로그인</li>
              <li>아래 "DM 메시지" 작성 → 프로젝트에서 잠재고객 수집·승인</li>
              <li>확장 팝업에서 "발송 시작" 클릭 → 자동으로 천천히 발송</li>
            </ol>
          </div>
          <Link to="/extension" className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 cursor-pointer">
            크롬 확장 설치 가이드 보기 →
          </Link>
        </div>

        {/* DM Template */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-4">인스타 DM 메시지</h2>
          <textarea
            value={settings.dm_template}
            onChange={(e) => handleChange('dm_template', e.target.value)}
            rows={4}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm font-mono resize-y"
            placeholder="DM 메시지 템플릿"
          />
          <p className="text-xs text-gray-400 mt-2">
            변수: {'{name}'}, {'{company_name}'}, {'{username}'} · 변형: <code className="bg-gray-100 px-1 rounded">{'{안녕하세요|반갑습니다}'}</code> 처럼 쓰면 수신자마다 다른 문구가 나갑니다. 변형을 안 넣어도 인사말·마무리가 자동으로 조금씩 바뀝니다.
          </p>
        </div>

        {/* 발송 속도 & 안전 가이드 */}
        <SafetyGuide settings={settings} onChange={handleChange} />

        {/* Save */}
        <div className="flex justify-end">
          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-2 px-6 py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 cursor-pointer"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {saving ? '저장 중...' : '설정 저장'}
          </button>
        </div>

        {/* Tag Manager */}
        <TagManager />

        {/* Deliverability Checker */}
        <DeliverabilityChecker />

        {/* Kakao messaging - roadmap */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-2 flex items-center gap-2">
            카카오톡 발송
            <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">로드맵</span>
          </h2>
          <p className="text-sm text-gray-400">
            카카오톡 알림톡/친구톡 발송은 아직 지원하지 않습니다 (개발 예정).
            현재 카카오는 <strong>업체 수집 채널</strong>로만 사용됩니다.
          </p>
        </div>

        <div className="pb-8" />
      </div>
    </div>
  )
}
