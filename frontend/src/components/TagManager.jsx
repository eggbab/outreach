import { useState, useEffect } from 'react'
import api from '../lib/api'
import { Plus, X, Tag } from 'lucide-react'

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#6B7280', '#14B8A6']

export default function TagManager() {
  const [tags, setTags] = useState([])
  const [newName, setNewName] = useState('')
  const [newColor, setNewColor] = useState(COLORS[0])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/tags').then((r) => setTags(r.data)).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const createTag = async () => {
    if (!newName.trim()) return
    try {
      const res = await api.post('/tags', { name: newName.trim(), color: newColor })
      setTags([...tags, res.data])
      setNewName('')
    } catch {}
  }

  const deleteTag = async (id) => {
    try {
      await api.delete(`/tags/${id}`)
      setTags(tags.filter((t) => t.id !== id))
    } catch {}
  }

  if (loading) return null

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h2 className="text-base font-semibold text-gray-900 mb-4">태그 관리</h2>

      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && createTag()}
          placeholder="태그 이름"
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm"
        />
        <div className="flex gap-1 items-center">
          {COLORS.map((c) => (
            <button
              key={c}
              onClick={() => setNewColor(c)}
              className={`w-5 h-5 rounded-full cursor-pointer ${newColor === c ? 'ring-2 ring-offset-1 ring-gray-400' : ''}`}
              style={{ backgroundColor: c }}
            />
          ))}
        </div>
        <button onClick={createTag} className="px-3 py-2 bg-blue-600 text-white rounded-lg text-sm cursor-pointer">
          <Plus className="w-4 h-4" />
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        {tags.map((tag) => (
          <span
            key={tag.id}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium text-white"
            style={{ backgroundColor: tag.color }}
          >
            <Tag className="w-3 h-3" />
            {tag.name}
            <button onClick={() => deleteTag(tag.id)} className="hover:opacity-70 cursor-pointer">
              <X className="w-3 h-3" />
            </button>
          </span>
        ))}
        {tags.length === 0 && <p className="text-sm text-gray-400">태그가 없습니다</p>}
      </div>
    </div>
  )
}
