import { useState, useEffect } from 'react'
import api from '../lib/api'
import {
  Mail, Eye, MousePointer, TrendingUp, BarChart3,
  Lightbulb, Target, Clock,
} from 'lucide-react'

const TABS = [
  { id: 'email', label: '이메일 성과' },
  { id: 'benchmark', label: '업종 벤치마크' },
  { id: 'roi', label: 'ROI 분석' },
  { id: 'recommend', label: '추천' },
]

const DAY_NAMES = ['월', '화', '수', '목', '금', '토', '일']

function ComparisonBar({ label, myValue, avgValue, unit = '%' }) {
  const max = Math.max(myValue, avgValue, 1)
  const isAbove = myValue >= avgValue
  return (
    <div className="mb-4">
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-600">{label}</span>
      </div>
      <div className="space-y-1.5">
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500 w-16">내 성과</span>
          <div className="flex-1 h-5 bg-gray-100 rounded overflow-hidden">
            <div
              className={`h-full rounded ${isAbove ? 'bg-green-500' : 'bg-red-400'}`}
              style={{ width: `${(myValue / max) * 100}%` }}
            />
          </div>
          <span className={`text-xs font-medium w-14 text-right ${isAbove ? 'text-green-600' : 'text-red-500'}`}>
            {myValue.toFixed(1)}{unit}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500 w-16">업종 평균</span>
          <div className="flex-1 h-5 bg-gray-100 rounded overflow-hidden">
            <div className="h-full rounded bg-gray-400" style={{ width: `${(avgValue / max) * 100}%` }} />
          </div>
          <span className="text-xs font-medium text-gray-500 w-14 text-right">{avgValue.toFixed(1)}{unit}</span>
        </div>
      </div>
    </div>
  )
}

export default function AnalyticsPage() {
  const [tab, setTab] = useState('email')
  const [stats, setStats] = useState(null)
  const [daily, setDaily] = useState([])
  const [funnel, setFunnel] = useState(null)
  const [comparison, setComparison] = useState(null)
  const [benchmarks, setBenchmarks] = useState([])
  const [keywordRoi, setKeywordRoi] = useState([])
  const [sourceRoi, setSourceRoi] = useState([])
  const [recommendations, setRecommendations] = useState([])
  const [loading, setLoading] = useState(true)
  const [projects, setProjects] = useState([])
  const [selectedProject, setSelectedProject] = useState('')

  useEffect(() => {
    api.get('/projects').then(res => {
      setProjects(res.data)
      if (res.data.length > 0) setSelectedProject(String(res.data[0].id))
    }).catch(() => {})
    api.get('/benchmarks').then(r => setBenchmarks(r.data)).catch(() => {})
  }, [])

  useEffect(() => {
    if (!selectedProject) return
    setLoading(true)
    const pid = selectedProject
    const fetches = [
      api.get(`/projects/${pid}/analytics/email-stats`),
      api.get(`/projects/${pid}/analytics/email-stats/daily`),
      api.get(`/projects/${pid}/analytics/funnel`),
    ]
    if (tab === 'benchmark') {
      fetches.push(api.get(`/projects/${pid}/analytics/comparison`))
    } else if (tab === 'roi') {
      fetches.push(
        api.get(`/projects/${pid}/analytics/keyword-roi`),
        api.get(`/projects/${pid}/analytics/source-roi`),
      )
    } else if (tab === 'recommend') {
      fetches.push(api.get(`/projects/${pid}/analytics/recommendations`))
    }
    Promise.all(fetches).then(results => {
      setStats(results[0].data)
      setDaily(results[1].data)
      setFunnel(results[2].data)
      if (tab === 'benchmark' && results[3]) setComparison(results[3].data)
      if (tab === 'roi') {
        if (results[3]) setKeywordRoi(results[3].data)
        if (results[4]) setSourceRoi(results[4].data)
      }
      if (tab === 'recommend' && results[3]) setRecommendations(results[3].data)
    }).catch(() => {}).finally(() => setLoading(false))
  }, [selectedProject, tab])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  const maxDailySent = Math.max(...daily.map(d => d.sent), 1)

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">분석</h1>
          <p className="text-gray-500 mt-1 text-sm">이메일 성과, 벤치마크, ROI를 확인하세요</p>
        </div>
        <select
          value={selectedProject}
          onChange={e => setSelectedProject(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
        >
          {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-gray-100 rounded-lg p-1 w-fit">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors cursor-pointer ${
              tab === t.id ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Email Stats Tab */}
      {tab === 'email' && (
        <>
          {stats && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              {[
                { label: '총 발송', value: stats.total_sent, icon: Mail, color: 'text-blue-600 bg-blue-50' },
                { label: '열람', value: stats.total_opened, icon: Eye, color: 'text-green-600 bg-green-50' },
                { label: '클릭', value: stats.total_clicked, icon: MousePointer, color: 'text-purple-600 bg-purple-50' },
                { label: '열람률', value: `${stats.open_rate}%`, icon: TrendingUp, color: 'text-orange-600 bg-orange-50' },
              ].map(card => (
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
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-sm font-semibold text-gray-900 mb-4">일별 발송</h2>
              {daily.length === 0 ? (
                <p className="text-sm text-gray-400 py-8 text-center">데이터가 없습니다</p>
              ) : (
                <div className="space-y-2">
                  {daily.slice(-14).map(d => (
                    <div key={d.date} className="flex items-center gap-3">
                      <span className="text-xs text-gray-400 w-20 shrink-0">{d.date.slice(5)}</span>
                      <div className="flex-1 h-4 bg-gray-50 rounded overflow-hidden">
                        <div className="h-full bg-blue-500 rounded" style={{ width: `${(d.sent / maxDailySent) * 100}%` }} />
                      </div>
                      <span className="text-xs text-gray-500 w-8 text-right">{d.sent}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
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
                  ].map(step => {
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
        </>
      )}

      {/* Benchmark Tab */}
      {tab === 'benchmark' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {comparison && comparison.industry ? (
            <>
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <div className="flex items-center gap-2 mb-4">
                  <BarChart3 className="w-5 h-5 text-blue-600" />
                  <h2 className="text-sm font-semibold text-gray-900">내 성과 vs 업종 평균</h2>
                  <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full">{comparison.industry}</span>
                </div>
                <ComparisonBar label="오픈율" myValue={comparison.my_open_rate} avgValue={comparison.industry_avg_open_rate} />
                <ComparisonBar label="클릭율" myValue={comparison.my_click_rate} avgValue={comparison.industry_avg_click_rate} />
                {comparison.best_send_hour !== null && (
                  <div className="mt-4 p-3 bg-blue-50 rounded-lg flex items-center gap-2">
                    <Clock className="w-4 h-4 text-blue-600" />
                    <span className="text-sm text-blue-700 font-medium">
                      최적 발송 시간: {comparison.best_send_day !== null ? `${DAY_NAMES[comparison.best_send_day]}요일 ` : ''}
                      {comparison.best_send_hour}시
                    </span>
                  </div>
                )}
              </div>
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h2 className="text-sm font-semibold text-gray-900 mb-4">전체 업종 벤치마크</h2>
                {benchmarks.length === 0 ? (
                  <p className="text-sm text-gray-400 py-8 text-center">아직 벤치마크 데이터가 없습니다</p>
                ) : (
                  <div className="space-y-3">
                    {benchmarks.map(b => (
                      <div key={b.industry} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                        <span className="text-sm text-gray-700 font-medium">{b.industry}</span>
                        <div className="flex items-center gap-4 text-xs text-gray-500">
                          <span>오픈 {b.avg_open_rate.toFixed(1)}%</span>
                          <span>클릭 {b.avg_click_rate.toFixed(1)}%</span>
                          <span className="text-gray-400">{b.total_sent.toLocaleString()}건</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="col-span-2 bg-white rounded-xl border border-gray-200 p-12 text-center">
              <BarChart3 className="w-10 h-10 text-gray-300 mx-auto mb-3" />
              <p className="text-sm text-gray-400">이메일을 발송하면 업종 벤치마크와 비교할 수 있습니다</p>
            </div>
          )}
        </div>
      )}

      {/* ROI Tab */}
      {tab === 'roi' && (
        <div className="space-y-6">
          {/* Source ROI */}
          {sourceRoi.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-sm font-semibold text-gray-900 mb-4">소스별 ROI 비교</h2>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
                {sourceRoi.map(s => {
                  const maxVal = Math.max(...sourceRoi.map(x => x.total_deal_value), 1)
                  return (
                    <div key={s.source} className="text-center">
                      <div className="h-32 flex items-end justify-center mb-2">
                        <div
                          className="w-12 bg-blue-500 rounded-t"
                          style={{ height: `${(s.total_deal_value / maxVal) * 100}%`, minHeight: '4px' }}
                        />
                      </div>
                      <p className="text-xs font-medium text-gray-700">{s.source}</p>
                      <p className="text-xs text-gray-400">{s.total_deal_value.toLocaleString()}원</p>
                      <p className="text-xs text-gray-400">{s.total_collected}건 수집</p>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Keyword ROI Table */}
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-sm font-semibold text-gray-900">키워드별 ROI</h2>
            </div>
            {keywordRoi.length === 0 ? (
              <div className="p-12 text-center">
                <Target className="w-10 h-10 text-gray-300 mx-auto mb-3" />
                <p className="text-sm text-gray-400">키워드 성과 데이터가 아직 없습니다</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b border-gray-200">
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">키워드</th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">소스</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">수집</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">발송</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">열람</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">딜</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">계약금액</th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">전환율</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {keywordRoi.map((k, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium text-gray-900">{k.keyword_text}</td>
                        <td className="px-4 py-3 text-gray-500">{k.source || '-'}</td>
                        <td className="px-4 py-3 text-right text-gray-600">{k.total_collected}</td>
                        <td className="px-4 py-3 text-right text-gray-600">{k.total_emailed}</td>
                        <td className="px-4 py-3 text-right text-gray-600">{k.total_opened}</td>
                        <td className="px-4 py-3 text-right text-gray-600">{k.total_deals}</td>
                        <td className="px-4 py-3 text-right text-gray-900 font-medium">{k.total_deal_value.toLocaleString()}원</td>
                        <td className="px-4 py-3 text-right">
                          <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                            k.conversion_rate > 0.05 ? 'bg-green-100 text-green-700' :
                            k.conversion_rate > 0 ? 'bg-yellow-100 text-yellow-700' :
                            'bg-gray-100 text-gray-500'
                          }`}>
                            {(k.conversion_rate * 100).toFixed(1)}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Recommendations Tab */}
      {tab === 'recommend' && (
        <div>
          {recommendations.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
              <Lightbulb className="w-10 h-10 text-gray-300 mx-auto mb-3" />
              <p className="text-sm text-gray-500">더 많은 데이터가 쌓이면 맞춤 추천을 제공합니다</p>
              <p className="text-xs text-gray-400 mt-1">키워드 수집, 이메일 발송, 딜 생성 후 확인해보세요</p>
            </div>
          ) : (
            <div className="space-y-4">
              {recommendations.map((rec, i) => {
                const iconMap = { keyword: Target, source: BarChart3, timing: Clock }
                const Icon = iconMap[rec.type] || Lightbulb
                const impactColor = {
                  high: 'bg-red-100 text-red-700',
                  medium: 'bg-yellow-100 text-yellow-700',
                  low: 'bg-gray-100 text-gray-500',
                }
                return (
                  <div key={i} className="bg-white rounded-xl border border-gray-200 p-5 flex items-start gap-4">
                    <div className="p-2.5 rounded-lg bg-blue-50 text-blue-600 shrink-0">
                      <Icon className="w-5 h-5" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-sm font-semibold text-gray-900">{rec.title}</h3>
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${impactColor[rec.impact]}`}>
                          {rec.impact === 'high' ? '높음' : rec.impact === 'medium' ? '보통' : '낮음'}
                        </span>
                      </div>
                      <p className="text-sm text-gray-500">{rec.description}</p>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
