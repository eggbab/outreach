import { useState, useEffect } from 'react'
import { useAuth } from '../lib/auth'
import { NavLink } from 'react-router-dom'
import api from '../lib/api'
import { Coins } from 'lucide-react'

export default function UsageBadge() {
  const { user } = useAuth()
  const [usage, setUsage] = useState(null)

  useEffect(() => {
    api.get('/subscription/usage')
      .then((res) => setUsage(res.data))
      .catch(() => {})
  }, [])

  if (!usage) return null

  const { emails_sent, dms_sent, limits, credits } = usage
  const emailLimit = limits.daily_emails === -1 ? '무제한' : limits.daily_emails
  const dmLimit = limits.daily_dms === -1 ? '무제한' : limits.daily_dms

  const emailPct = limits.daily_emails === -1 ? 0 : (emails_sent / limits.daily_emails) * 100
  const dmPct = limits.daily_dms === -1 ? 0 : (dms_sent / limits.daily_dms) * 100
  const isFree = user?.plan === 'free' || user?.plan === 'personal'

  return (
    <div className="px-4 py-3 border-t border-gray-100">
      <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-2">오늘 사용량</p>
      <div className="space-y-2">
        <div>
          <div className="flex justify-between text-xs text-gray-500 mb-0.5">
            <span>이메일</span>
            <span>{emails_sent}/{emailLimit}</span>
          </div>
          {limits.daily_emails !== -1 && (
            <div className="h-1 bg-gray-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${emailPct > 100 ? 'bg-orange-500' : emailPct > 80 ? 'bg-red-500' : 'bg-blue-500'}`}
                style={{ width: `${Math.min(emailPct, 100)}%` }}
              />
            </div>
          )}
        </div>
        <div>
          <div className="flex justify-between text-xs text-gray-500 mb-0.5">
            <span>DM</span>
            <span>{dms_sent}/{dmLimit}</span>
          </div>
          {limits.daily_dms !== -1 && (
            <div className="h-1 bg-gray-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${dmPct > 100 ? 'bg-orange-500' : dmPct > 80 ? 'bg-red-500' : 'bg-purple-500'}`}
                style={{ width: `${Math.min(dmPct, 100)}%` }}
              />
            </div>
          )}
        </div>
      </div>

      {/* Credits */}
      {!isFree && (
        <NavLink
          to="/pricing"
          className="flex items-center justify-between mt-3 pt-2 border-t border-gray-100 group"
        >
          <div className="flex items-center gap-1.5">
            <Coins className="w-3.5 h-3.5 text-yellow-500" />
            <span className="text-xs text-gray-500">크레딧</span>
          </div>
          <span className="text-xs font-semibold text-gray-700 group-hover:text-blue-600 transition-colors">
            {credits.toLocaleString()}
          </span>
        </NavLink>
      )}

      {isFree && (
        <NavLink
          to="/pricing"
          className="block mt-3 pt-2 border-t border-gray-100 text-[10px] text-blue-600 font-medium hover:underline"
        >
          유료 플랜으로 업그레이드
        </NavLink>
      )}
    </div>
  )
}
