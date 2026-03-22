import { useState, useEffect } from 'react'
import api from '../lib/api'
import { X, Plus, Send, Phone, MessageSquare, Tag, Clock } from 'lucide-react'

export default function ProspectDetail({ prospect, projectId, onClose }) {
  const [notes, setNotes] = useState([])
  const [newNote, setNewNote] = useState('')
  const [timeline, setTimeline] = useState([])
  const [tags, setTags] = useState([])
  const [prospectTags, setProspectTags] = useState([])
  const [tab, setTab] = useState('info')

  useEffect(() => {
    if (!prospect) return
    api.get(`/projects/${projectId}/prospects/${prospect.id}/notes`).then((r) => setNotes(r.data)).catch(() => {})
    api.get(`/projects/${projectId}/prospects/${prospect.id}/timeline`).then((r) => setTimeline(r.data)).catch(() => {})
    api.get('/tags').then((r) => {
      setTags(r.data)
      const ptags = (prospect.tags || []).map((t) => t.tag_id || t.id)
      setProspectTags(ptags)
    }).catch(() => {})
  }, [prospect])

  if (!prospect) return null

  const addNote = async () => {
    if (!newNote.trim()) return
    try {
      const res = await api.post(`/projects/${projectId}/prospects/${prospect.id}/notes`, { content: newNote })
      setNotes([res.data, ...notes])
      setNewNote('')
    } catch {}
  }

  const toggleTag = async (tagId) => {
    if (prospectTags.includes(tagId)) {
      await api.post('/tags/detach', { prospect_id: prospect.id, tag_id: tagId })
      setProspectTags(prospectTags.filter((t) => t !== tagId))
    } else {
      await api.post('/tags/attach', { prospect_id: prospect.id, tag_id: tagId })
      setProspectTags([...prospectTags, tagId])
    }
  }

  const activityIcon = (type) => {
    if (type.includes('email')) return <Send className="w-3.5 h-3.5 text-blue-500" />
    if (type.includes('dm')) return <MessageSquare className="w-3.5 h-3.5 text-purple-500" />
    if (type.includes('call')) return <Phone className="w-3.5 h-3.5 text-green-500" />
    return <Clock className="w-3.5 h-3.5 text-gray-400" />
  }

  const tabs = [
    { id: 'info', label: '정보' },
    { id: 'notes', label: '메모' },
    { id: 'tags', label: '태그' },
    { id: 'timeline', label: '타임라인' },
  ]

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="relative w-full max-w-md bg-white shadow-xl flex flex-col h-full">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <div>
            <h2 className="font-semibold text-gray-900">{prospect.name || '이름 없음'}</h2>
            <p className="text-xs text-gray-500">{prospect.email || ''}</p>
          </div>
          <button onClick={onClose} className="p-1 text-gray-400 hover:text-gray-600 cursor-pointer">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex-1 py-2.5 text-xs font-medium transition-colors cursor-pointer ${
                tab === t.id ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {tab === 'info' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between py-1.5">
                <span className="text-sm text-gray-500">스코어</span>
                <span className="text-sm font-semibold text-gray-900">{prospect.score || 0}점</span>
              </div>
              {[
                ['전화', prospect.phone],
                ['인스타', prospect.instagram],
                ['웹사이트', prospect.website],
                ['소스', prospect.source],
                ['카테고리', prospect.category],
                ['상태', prospect.status],
              ].map(([label, value]) => (
                <div key={label} className="flex items-center justify-between py-1.5">
                  <span className="text-sm text-gray-500">{label}</span>
                  <span className="text-sm text-gray-900">{value || '-'}</span>
                </div>
              ))}
            </div>
          )}

          {tab === 'notes' && (
            <div>
              <div className="flex gap-2 mb-4">
                <input
                  type="text"
                  value={newNote}
                  onChange={(e) => setNewNote(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && addNote()}
                  placeholder="메모 추가..."
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm"
                />
                <button
                  onClick={addNote}
                  className="px-3 py-2 bg-blue-600 text-white rounded-lg text-sm cursor-pointer"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>
              <div className="space-y-3">
                {notes.map((note) => (
                  <div key={note.id} className="p-3 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-700">{note.content}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      {new Date(note.created_at).toLocaleString('ko-KR')}
                    </p>
                  </div>
                ))}
                {notes.length === 0 && (
                  <p className="text-sm text-gray-400 text-center py-4">메모가 없습니다</p>
                )}
              </div>
            </div>
          )}

          {tab === 'tags' && (
            <div className="flex flex-wrap gap-2">
              {tags.map((tag) => (
                <button
                  key={tag.id}
                  onClick={() => toggleTag(tag.id)}
                  className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-medium transition-colors cursor-pointer ${
                    prospectTags.includes(tag.id)
                      ? 'text-white'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                  style={prospectTags.includes(tag.id) ? { backgroundColor: tag.color } : {}}
                >
                  <Tag className="w-3 h-3" />
                  {tag.name}
                </button>
              ))}
              {tags.length === 0 && (
                <p className="text-sm text-gray-400 text-center py-4 w-full">태그를 먼저 생성하세요 (설정에서 관리)</p>
              )}
            </div>
          )}

          {tab === 'timeline' && (
            <div className="space-y-3">
              {timeline.map((activity) => (
                <div key={activity.id} className="flex items-start gap-3">
                  <div className="mt-1">{activityIcon(activity.activity_type)}</div>
                  <div className="flex-1">
                    <p className="text-sm text-gray-700">{activity.description}</p>
                    <p className="text-xs text-gray-400">
                      {new Date(activity.created_at).toLocaleString('ko-KR')}
                    </p>
                  </div>
                </div>
              ))}
              {timeline.length === 0 && (
                <p className="text-sm text-gray-400 text-center py-4">활동 기록이 없습니다</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
