import { useState } from 'react'
import { Link, useNavigate, Navigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import Logo from '../components/Logo'

export default function SignupPage() {
  const { signup, user, loading } = useAuth()
  const navigate = useNavigate()
  // 크몽 등에서 키를 받은 고객에게 ?key=sk_... 링크를 주면 자동으로 채워진다.
  const [searchParams] = useSearchParams()
  const [serviceKey, setServiceKey] = useState(searchParams.get('key') || '')
  const keyFromLink = Boolean(searchParams.get('key'))
  const [showKeyField, setShowKeyField] = useState(false)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [acceptTerms, setAcceptTerms] = useState(false)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (user) {
    // 이미 로그인된 상태로 가입링크를 열었다면 키를 대시보드로 넘겨 바로 등록되게 한다
    return <Navigate to={serviceKey ? `/dashboard?key=${serviceKey}` : '/dashboard'} replace />
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (password !== confirmPassword) {
      setError('비밀번호가 일치하지 않습니다.')
      return
    }

    if (password.length < 8) {
      setError('비밀번호는 8자 이상이어야 합니다.')
      return
    }

    if (!acceptTerms) {
      setError('이용약관과 개인정보처리방침에 동의해주세요.')
      return
    }

    setSubmitting(true)
    try {
      await signup(email, password, name, serviceKey.trim() || null, acceptTerms)
      navigate('/dashboard')
    } catch (err) {
      const detail = err.response?.data?.detail || '회원가입에 실패했습니다.'
      setError(detail.includes('서비스 키')
        ? `${detail} — 키를 지우고 가입한 뒤 나중에 등록할 수도 있습니다.`
        : detail)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-2">
            <Logo size={32} />
            <span className="text-3xl font-bold text-gray-900">Outreach</span>
          </div>
          <p className="text-gray-500">B2B 영업 자동화 플랫폼</p>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">회원가입</h2>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="signup-name" className="block text-sm font-medium text-gray-700 mb-1">이름</label>
              <input
                id="signup-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                autoComplete="name"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                placeholder="홍길동"
              />
            </div>
            <div>
              <label htmlFor="signup-email" className="block text-sm font-medium text-gray-700 mb-1">이메일</label>
              <input
                id="signup-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                placeholder="email@example.com"
              />
            </div>
            <div>
              <label htmlFor="signup-password" className="block text-sm font-medium text-gray-700 mb-1">비밀번호</label>
              <input
                id="signup-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="new-password"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                placeholder="8자 이상"
              />
            </div>
            <div>
              <label htmlFor="signup-confirm-password" className="block text-sm font-medium text-gray-700 mb-1">비밀번호 확인</label>
              <input
                id="signup-confirm-password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                autoComplete="new-password"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                placeholder="비밀번호 재입력"
              />
            </div>

            {/* 서비스 키 — 크몽 등에서 구매한 고객은 여기 넣으면 가입 즉시 충전.
                링크(?key=...)로 왔으면 이미 채워져 있고, 아니면 접힌 상태로 방해하지 않는다. */}
            {keyFromLink || showKeyField ? (
              <div>
                <label htmlFor="signup-service-key" className="block text-sm font-medium text-gray-700 mb-1">
                  서비스 키 <span className="text-gray-400 font-normal">(선택)</span>
                </label>
                <input
                  id="signup-service-key"
                  type="text"
                  value={serviceKey}
                  onChange={(e) => setServiceKey(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm font-mono"
                  placeholder="sk_..."
                />
                <p className="mt-1 text-xs text-gray-500">
                  {keyFromLink
                    ? '구매하신 키가 자동으로 입력되었습니다. 가입하면 바로 충전됩니다.'
                    : '구매하고 받으신 키를 입력하면 가입하는 순간 크레딧이 충전됩니다.'}
                </p>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setShowKeyField(true)}
                className="text-xs text-blue-600 hover:underline cursor-pointer"
              >
                서비스 키를 구매하셨나요? 여기서 입력
              </button>
            )}

            <label className="flex items-start gap-2 cursor-pointer pt-1">
              <input
                type="checkbox"
                checked={acceptTerms}
                onChange={(e) => setAcceptTerms(e.target.checked)}
                className="mt-0.5 w-4 h-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500 cursor-pointer"
              />
              <span className="text-sm text-gray-600 leading-snug">
                <Link to="/terms" target="_blank" className="text-blue-600 hover:underline">이용약관</Link>과{' '}
                <Link to="/privacy" target="_blank" className="text-blue-600 hover:underline">개인정보처리방침</Link>에 동의합니다 (필수)
              </span>
            </label>

            <button
              type="submit"
              disabled={submitting}
              className="w-full py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {submitting ? '가입 중...' : '회원가입'}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-gray-500">
            이미 계정이 있으신가요?{' '}
            <Link to="/login" className="text-blue-600 hover:underline font-medium">
              로그인
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
