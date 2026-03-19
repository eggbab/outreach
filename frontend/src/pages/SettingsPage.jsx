import { useState, useEffect } from 'react'
import api from '../lib/api'
import { Save, Loader2 } from 'lucide-react'

export default function SettingsPage() {
  const [settings, setSettings] = useState({
    gmail_email: '',
    gmail_app_password: '',
    email_template: `안녕하세요, {company_name} 담당자님.\n\n마트/슈퍼마켓 업계 최대 커뮤니티 '마트마트' 카페에서 광고 파트너십을 제안드립니다.\n\n22,000명 이상의 마트/슈퍼 업계 종사자가 활동하는 네이버 카페로, 업계 타겟 광고에 최적화된 채널입니다.\n\n관심이 있으시면 편하게 회신 부탁드립니다.\n\n감사합니다.`,
    dm_template: `안녕하세요! 마트/슈퍼 업계 커뮤니티 '마트마트'입니다. 22,000+ 회원 대상 광고 파트너십에 관심 있으시면 DM 주세요!`,
    daily_email_limit: 80,
    daily_dm_limit: 15,
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState(null)

  const showToast = (message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  useEffect(() => {
    api.get('/settings')
      .then((res) => setSettings((prev) => ({ ...prev, ...res.data })))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleChange = (key, value) => {
    setSettings((prev) => ({ ...prev, [key]: value }))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await api.put('/settings', settings)
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

      <div className="space-y-6 max-w-2xl">
        {/* Gmail Settings */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
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

        {/* Email Template */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-4">이메일 템플릿</h2>
          <textarea
            value={settings.email_template}
            onChange={(e) => handleChange('email_template', e.target.value)}
            rows={8}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm font-mono resize-y"
            placeholder="이메일 본문 템플릿"
          />
          <p className="text-xs text-gray-400 mt-2">
            사용 가능한 변수: {'{company_name}'}, {'{email}'}, {'{phone}'}
          </p>
        </div>

        {/* DM Template */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-4">인스타 DM 템플릿</h2>
          <textarea
            value={settings.dm_template}
            onChange={(e) => handleChange('dm_template', e.target.value)}
            rows={4}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm font-mono resize-y"
            placeholder="DM 메시지 템플릿"
          />
          <p className="text-xs text-gray-400 mt-2">
            사용 가능한 변수: {'{company_name}'}, {'{instagram}'}
          </p>
        </div>

        {/* Daily Limits */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-base font-semibold text-gray-900 mb-4">일일 발송 한도</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">이메일 (건/일)</label>
              <input
                type="number"
                min={1}
                max={200}
                value={settings.daily_email_limit}
                onChange={(e) => handleChange('daily_email_limit', parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">DM (건/일)</label>
              <input
                type="number"
                min={1}
                max={50}
                value={settings.daily_dm_limit}
                onChange={(e) => handleChange('daily_dm_limit', parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
              />
            </div>
          </div>
        </div>

        {/* Save */}
        <div className="flex justify-end pb-8">
          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-2 px-6 py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 cursor-pointer"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            {saving ? '저장 중...' : '설정 저장'}
          </button>
        </div>
      </div>
    </div>
  )
}
