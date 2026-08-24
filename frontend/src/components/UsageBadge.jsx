import { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import api from '../lib/api'
import { Coins } from 'lucide-react'

export default function UsageBadge() {
  const [usage, setUsage] = useState(null)

  useEffect(() => {
    api.get('/subscription/usage')
      .then((res) => setUsage(res.data))
      .catch(() => {})
  }, [])

  if (!usage) return null

  const { emails_sent, dms_sent, prospects_collected, credits } = usage

  return (
    <div className="px-4 py-3 border-t border-gray-100">
      <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-2">오늘 사용량</p>
      <div className="space-y-1 text-xs text-gray-500 mb-3">
        <div className="flex justify-between">
          <span>수집</span>
          <span>{prospects_collected}건</span>
        </div>
        <div className="flex justify-between">
          <span>이메일</span>
          <span>{emails_sent}건</span>
        </div>
        <div className="flex justify-between">
          <span>DM</span>
          <span>{dms_sent}건</span>
        </div>
      </div>

      <NavLink
        to="/pricing"
        className="flex items-center justify-between pt-2 border-t border-gray-100 group"
      >
        <div className="flex items-center gap-1.5">
          <Coins className="w-3.5 h-3.5 text-yellow-500" />
          <span className="text-xs text-gray-500">크레딧</span>
        </div>
        <span className="text-xs font-semibold text-gray-700 group-hover:text-blue-600 transition-colors">
          {credits.toLocaleString()}
        </span>
      </NavLink>

      {credits <= 10 && (
        <NavLink
          to="/pricing"
          className="block mt-2 text-[10px] text-blue-600 font-medium hover:underline"
        >
          크레딧 충전하기
        </NavLink>
      )}
    </div>
  )
}
