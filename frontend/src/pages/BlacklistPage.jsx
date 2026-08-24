import { useState, useEffect } from 'react'
import api from '../lib/api'
import { ShieldX, Plus, Trash2, Search, Loader2 } from 'lucide-react'

export default function BlacklistPage() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [q, setQ] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ company_name: '', email: '', phone: '', instagram: '', reason: '' })

  const fetchItems = (search = '') => {
    setLoading(true)
    const params = search ? { q: search } : {}
    api.get('/blacklist', { params }).then(r => setItems(r.data)).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { fetchItems() }, [])

  const handleSearch = (e) => { e.preventDefault(); fetchItems(q) }

  const addItem = async (e) => {
    e.preventDefault()
    if (!form.email && !form.phone && !form.instagram) { alert('이메일, 전화번호, 인스타그램 중 하나는 입력해주세요'); return }
    try {
      await api.post('/blacklist', form)
      setForm({ company_name: '', email: '', phone: '', instagram: '', reason: '' })
      setShowForm(false)
      fetchItems(q)
    } catch (err) { alert(err.response?.data?.detail || '추가 실패') }
  }

  const removeItem = async (id) => {
    if (!confirm('블랙리스트에서 제거하시겠습니까?')) return
    try { await api.delete(`/blacklist/${id}`); fetchItems(q) } catch { alert('삭제 실패') }
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <ShieldX className="w-7 h-7 text-red-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">블랙리스트</h1>
            <p className="text-sm text-gray-500">총 {items.length}건</p>
          </div>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          추가
        </button>
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="mb-6">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="업체명, 이메일, 인스타그램으로 검색..."
              className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2.5 bg-gray-100 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-200 transition-colors cursor-pointer"
          >
            검색
          </button>
        </div>
      </form>

      {/* Add Form */}
      {showForm && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">블랙리스트 추가</h3>
          <form onSubmit={addItem} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">업체명</label>
                <input
                  type="text"
                  value={form.company_name}
                  onChange={(e) => setForm({ ...form, company_name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  placeholder="업체명"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">이메일</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  placeholder="email@example.com"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">전화번호</label>
                <input
                  type="text"
                  value={form.phone}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  placeholder="010-0000-0000"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">인스타그램</label>
                <input
                  type="text"
                  value={form.instagram}
                  onChange={(e) => setForm({ ...form, instagram: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  placeholder="@username"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">사유</label>
              <input
                type="text"
                value={form.reason}
                onChange={(e) => setForm({ ...form, reason: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
                placeholder="블랙리스트 추가 사유"
              />
            </div>
            <div className="flex gap-3">
              <button
                type="submit"
                className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors cursor-pointer"
              >
                추가
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors cursor-pointer"
              >
                취소
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Table */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      ) : items.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <ShieldX className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 text-sm">블랙리스트가 비어있습니다</p>
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="text-left px-4 py-3 font-medium text-gray-600">업체명</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">이메일</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">전화번호</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">인스타그램</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">사유</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">등록일</th>
                  <th className="text-center px-4 py-3 font-medium text-gray-600">작업</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {items.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{item.company_name || '-'}</td>
                    <td className="px-4 py-3 text-gray-600">{item.email || '-'}</td>
                    <td className="px-4 py-3 text-gray-600">{item.phone || '-'}</td>
                    <td className="px-4 py-3 text-gray-600">{item.instagram || '-'}</td>
                    <td className="px-4 py-3 text-gray-600">{item.reason || '-'}</td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
                      {item.created_at ? new Date(item.created_at).toLocaleDateString('ko-KR') : '-'}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => removeItem(item.id)}
                        className="p-1.5 text-red-600 hover:bg-red-50 rounded transition-colors cursor-pointer"
                        title="삭제"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
