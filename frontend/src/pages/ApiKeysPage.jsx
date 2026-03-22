import { useState, useEffect } from 'react'
import api from '../lib/api'
import { Plus, Key, Trash2, X, Copy, CheckCircle } from 'lucide-react'

export default function ApiKeysPage() {
  const [keys, setKeys] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [createdKey, setCreatedKey] = useState(null)
  const [copied, setCopied] = useState(false)
  const [toast, setToast] = useState(null)

  const showToast = (msg) => { setToast(msg); setTimeout(() => setToast(null), 3000) }

  useEffect(() => {
    api.get('/api-keys').then((r) => setKeys(r.data)).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const createKey = async () => {
    if (!newName.trim()) return
    try {
      const res = await api.post('/api-keys', { name: newName.trim() })
      setCreatedKey(res.data.key)
      setKeys([res.data, ...keys])
      setNewName('')
      setShowCreate(false)
    } catch {}
  }

  const revokeKey = async (id) => {
    await api.delete(`/api-keys/${id}`)
    setKeys(keys.map((k) => k.id === id ? { ...k, is_active: false } : k))
    showToast('API 키가 비활성화되었습니다')
  }

  const copyKey = () => {
    navigator.clipboard.writeText(createdKey)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div></div>
  }

  return (
    <div>
      {toast && <div className="fixed top-6 right-6 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium bg-green-600 text-white">{toast}</div>}

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">API Keys</h1>
          <p className="text-gray-500 mt-1 text-sm">외부 연동을 위한 API 키를 관리하세요</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg cursor-pointer">
          <Plus className="w-4 h-4" /> 새 API 키
        </button>
      </div>

      {/* Created key banner */}
      {createdKey && (
        <div className="bg-green-50 border border-green-200 rounded-xl p-4 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-green-800">API 키가 생성되었습니다. 이 키는 다시 표시되지 않습니다.</p>
              <code className="text-xs text-green-700 mt-1 block font-mono">{createdKey}</code>
            </div>
            <button onClick={copyKey} className="flex items-center gap-1 px-3 py-1.5 bg-green-600 text-white text-xs rounded-lg cursor-pointer">
              {copied ? <><CheckCircle className="w-3.5 h-3.5" /> 복사됨</> : <><Copy className="w-3.5 h-3.5" /> 복사</>}
            </button>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-4 py-3 font-medium text-gray-600">이름</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">키</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">상태</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">마지막 사용</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">생성일</th>
              <th className="text-center px-4 py-3 font-medium text-gray-600">작업</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {keys.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-12 text-center text-gray-400">API 키가 없습니다</td></tr>
            ) : keys.map((k) => (
              <tr key={k.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-900">{k.name}</td>
                <td className="px-4 py-3 font-mono text-gray-500">{k.key_prefix}...</td>
                <td className="px-4 py-3">
                  <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${k.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                    {k.is_active ? '활성' : '비활성'}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-500">{k.last_used_at ? new Date(k.last_used_at).toLocaleString('ko-KR') : '-'}</td>
                <td className="px-4 py-3 text-gray-500">{new Date(k.created_at).toLocaleDateString('ko-KR')}</td>
                <td className="px-4 py-3 text-center">
                  {k.is_active && (
                    <button onClick={() => revokeKey(k.id)} className="p-1 text-gray-400 hover:text-red-600 cursor-pointer" title="비활성화">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">새 API 키</h3>
              <button onClick={() => setShowCreate(false)} className="text-gray-400 cursor-pointer"><X className="w-5 h-5" /></button>
            </div>
            <input type="text" value={newName} onChange={(e) => setNewName(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && createKey()} placeholder="키 이름 (예: 외부 CRM 연동)" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm mb-4" autoFocus />
            <div className="flex justify-end gap-3">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-gray-700 cursor-pointer">취소</button>
              <button onClick={createKey} className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg cursor-pointer">생성</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
