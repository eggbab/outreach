import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import api from '../lib/api'
import { Mail, Eye, MousePointer, TrendingUp } from 'lucide-react'

export default function AnalyticsPage() {
  const { id } = useParams()
  const [stats, setStats] = useState(null)
  const [daily, setDaily] = useState([])
  const [funnel, setFunnel] = useState(null)
  const [loading, setLoading] = useState(true)
  const [projects, setProjects] = useState([])
  const [selectedProject, setSelectedProject] = useState(id || '')

  useEffect(() => {
    api.get('/projects').then((res) => {
      setProjects(res.data)
      if (!selectedProject && res.data.length > 0) {
        setSelectedProject(String(res.data[0].id))
      }
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (!selectedProject) return
    setLoading(true)
    Promise.all([
      api.get(`/projects/${selectedProject}/analytics/email-stats`),
      api.get(`/projects/${selectedProject}/analytics/email-stats/daily`),
      api.get(`/projects/${selectedProject}/analytics/funnel`),
    ]).then(([statsRes, dailyRes, funnelRes]) => {
      setStats(statsRes.data)
      setDaily(dailyRes.data)
      setFunnel(funnelRes.data)
    }).catch(() => {}).finally(() => setLoading(false))
  }, [selectedProject])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  const maxDailySent = Math.max(...daily.map((d) => d.sent), 1)

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">분석</h1>
          <p className="text-gray-500 mt-1 text-sm">이메일 성과와 전환 퍼널을 확인하세요</p>
        </div>
        <select
          value={selectedProject}
          onChange={(e) => setSelectedProject(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
        >
          {projects.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[
            { label: '총 발송', value: stats.total_sent, icon: Mail, color: 'text-blue-600 bg-blue-50' },
            { label: '열람', value: stats.total_opened, icon: Eye, color: 'text-green-600 bg-green-50' },
            { label: '클릭', value: stats.total_clicked, icon: MousePointer, color: 'text-purple-600 bg-purple-50' },
            { label: '열람률', value: `${stats.open_rate}%`, icon: TrendingUp, color: 'text-orange-600 bg-orange-50' },
          ].map((card) => (
            <div key={card.label} className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center gap-3">
                <div className={`p-2.5 rounded-lg ${card.color}`}>
                  <card.icon className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-sm text-gray-500">{card.label}</p>
                  <p className="text-2xl font-bold text-gray-900">{card.value}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Daily Chart */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">일별 발송</h2>
          {daily.length === 0 ? (
            <p className="text-sm text-gray-400 py-8 text-center">데이터가 없습니다</p>
          ) : (
            <div className="space-y-2">
              {daily.slice(-14).map((d) => (
                <div key={d.date} className="flex items-center gap-3">
                  <span className="text-xs text-gray-400 w-20 shrink-0">{d.date.slice(5)}</span>
                  <div className="flex-1 h-4 bg-gray-50 rounded overflow-hidden">
                    <div
                      className="h-full bg-blue-500 rounded"
                      style={{ width: `${(d.sent / maxDailySent) * 100}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-500 w-8 text-right">{d.sent}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Funnel */}
        {funnel && (
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-sm font-semibold text-gray-900 mb-4">전환 퍼널</h2>
            <div className="space-y-3">
              {[
                { label: '수집', value: funnel.collected, color: 'bg-gray-400' },
                { label: '승인', value: funnel.approved, color: 'bg-blue-500' },
                { label: '이메일 발송', value: funnel.email_sent, color: 'bg-purple-500' },
                { label: '열람', value: funnel.opened, color: 'bg-green-500' },
                { label: '클릭', value: funnel.clicked, color: 'bg-orange-500' },
              ].map((step) => {
                const pct = funnel.collected > 0 ? (step.value / funnel.collected) * 100 : 0
                return (
                  <div key={step.label}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-600">{step.label}</span>
                      <span className="text-gray-900 font-medium">{step.value}건 ({pct.toFixed(1)}%)</span>
                    </div>
                    <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full ${step.color}`} style={{ width: `${Math.max(pct, 1)}%` }} />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
