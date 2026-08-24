import { useState, useEffect } from 'react'
import api from '../lib/api'
import { Search, Download, Database, ChevronLeft, ChevronRight } from 'lucide-react'

export default function DiscoverPage() {
  const [results, setResults] = useState({ items: [], total: 0, total_pages: 1 })
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [q, setQ] = useState('')
  const [industry, setIndustry] = useState('')
  const [region, setRegion] = useState('')
  const [hasEmail, setHasEmail] = useState(false)
  const [minValidity, setMinValidity] = useState(0)
  const [sort, setSort] = useState('popular')
  const [selected, setSelected] = useState(new Set())
  const [projects, setProjects] = useState([])
  const [targetProject, setTargetProject] = useState('')
  const [importing, setImporting] = useState(false)

  useEffect(() => {
    api.get('/discover/stats').then(r => setStats(r.data)).catch(() => {})
    api.get('/projects').then(r => {
      setProjects(r.data)
      if (r.data.length > 0) setTargetProject(String(r.data[0].id))
    }).catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true)
    const params = { page, page_size: 20 }
    if (q) params.q = q
    if (industry) params.industry = industry
    if (region) params.region = region
    if (hasEmail) params.has_email = true
    if (minValidity > 0) params.min_validity = minValidity / 100  // 백엔드는 0~1 스케일
    params.sort = sort
    api.get('/discover', { params }).then(r => {
      setResults(r.data)
    }).catch(() => {}).finally(() => setLoading(false))
  }, [page, q, industry, region, hasEmail, minValidity, sort])

  const handleSearch = (e) => {
    e.preventDefault()
    setPage(1)
    const formData = new FormData(e.target)
    setQ(formData.get('q') || '')
  }

  const toggleSelect = (id) => {
    setSelected(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const toggleAll = () => {
    if (selected.size === results.items.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(results.items.map(i => i.id)))
    }
  }

  const handleImport = async () => {
    if (selected.size === 0 || !targetProject) return
    setImporting(true)
    try {
      const res = await api.post('/discover/import', {
        global_prospect_ids: [...selected],
        project_id: parseInt(targetProject),
      })
      alert(res.data.message)
      setSelected(new Set())
    } catch (err) {
      alert(err.response?.data?.detail || '가져오기 실패')
    } finally {
      setImporting(false)
    }
  }

  const industries = stats?.by_industry?.map(i => i.industry) || []
  const regions = stats?.by_region?.map(r => r.region) || []

  return (
    <div>
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-1">
          <h1 className="text-2xl font-bold text-gray-900">잠재고객 데이터베이스</h1>
          {stats && (
            <span className="px-2.5 py-0.5 bg-blue-100 text-blue-700 text-sm font-medium rounded-full">
              {stats.total_prospects.toLocaleString()}건
            </span>
          )}
        </div>
        <p className="text-gray-500 text-sm">전체 사용자가 수집한 잠재고객을 검색하고 프로젝트로 가져오세요</p>
      </div>

      {/* Search & Filters */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
        <form onSubmit={handleSearch} className="flex gap-3 mb-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              name="q"
              type="text"
              placeholder="업체명 또는 카테고리 검색..."
              defaultValue={q}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
            검색
          </button>
        </form>
        <div className="flex flex-wrap gap-3">
          <select
            value={industry}
            onChange={e => { setIndustry(e.target.value); setPage(1) }}
            className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
          >
            <option value="">전체 업종</option>
            {industries.map(i => <option key={i} value={i}>{i}</option>)}
          </select>
          <select
            value={region}
            onChange={e => { setRegion(e.target.value); setPage(1) }}
            className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
          >
            <option value="">전체 지역</option>
            {regions.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
          <label className="flex items-center gap-1.5 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={hasEmail}
              onChange={e => { setHasEmail(e.target.checked); setPage(1) }}
              className="rounded border-gray-300"
            />
            이메일 있는 것만
          </label>
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <span>유효성 {minValidity}%+</span>
            <input
              type="range"
              min="0" max="100" step="10"
              value={minValidity}
              onChange={e => { setMinValidity(Number(e.target.value)); setPage(1) }}
              className="w-24"
            />
          </div>
          <select
            value={sort}
            onChange={e => { setSort(e.target.value); setPage(1) }}
            className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
          >
            <option value="popular">많이 수집된 순</option>
            <option value="quality">품질 순 (답장·검증 데이터)</option>
          </select>
        </div>
      </div>

      {/* Import bar */}
      {selected.size > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-4 flex items-center justify-between">
          <span className="text-sm text-blue-700 font-medium">{selected.size}건 선택됨</span>
          <div className="flex items-center gap-3">
            <select
              value={targetProject}
              onChange={e => setTargetProject(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
            >
              {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <button
              onClick={handleImport}
              disabled={importing}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              <Download className="w-4 h-4" />
              {importing ? '가져오는 중...' : '프로젝트로 가져오기'}
            </button>
          </div>
        </div>
      )}

      {/* Results Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center h-48">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          </div>
        ) : results.items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 text-gray-400">
            <Database className="w-10 h-10 mb-2" />
            <p className="text-sm">검색 결과가 없습니다</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="px-4 py-3 text-left">
                    <input type="checkbox" onChange={toggleAll} checked={selected.size === results.items.length && results.items.length > 0} className="rounded border-gray-300" />
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">업체명</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">업종</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">지역</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">이메일</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">유효성</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">반응</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">수집횟수</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">소스</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {results.items.map(item => (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <input type="checkbox" checked={selected.has(item.id)} onChange={() => toggleSelect(item.id)} className="rounded border-gray-300" />
                    </td>
                    <td className="px-4 py-3 font-medium text-gray-900">{item.company_name || '-'}</td>
                    <td className="px-4 py-3 text-gray-600">{item.industry || '-'}</td>
                    <td className="px-4 py-3 text-gray-600">{item.region || '-'}</td>
                    <td className="px-4 py-3 text-gray-500 font-mono text-xs">{item.email_masked || '-'}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                        item.validity_score >= 0.7 ? 'bg-green-100 text-green-700' :
                        item.validity_score >= 0.3 ? 'bg-yellow-100 text-yellow-700' :
                        'bg-gray-100 text-gray-500'
                      }`}>
                        {(item.validity_score * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-600 whitespace-nowrap">
                      {item.times_replied > 0 && (
                        <span className="inline-block px-1.5 py-0.5 mr-1 bg-emerald-100 text-emerald-700 rounded font-medium">
                          답장 {item.times_replied}
                        </span>
                      )}
                      {item.times_opened > 0 && <span className="text-gray-500">열람 {item.times_opened}</span>}
                      {!item.times_replied && !item.times_opened && '-'}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{item.times_collected}</td>
                    <td className="px-4 py-3 text-gray-500">{item.source || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {results.total_pages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200">
            <span className="text-sm text-gray-500">총 {results.total.toLocaleString()}건</span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-30"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-sm text-gray-700">{page} / {results.total_pages}</span>
              <button
                onClick={() => setPage(p => Math.min(results.total_pages, p + 1))}
                disabled={page === results.total_pages}
                className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-30"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
