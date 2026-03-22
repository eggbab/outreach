import { useState, useEffect } from 'react'
import api from '../lib/api'
import { Plus, X, Calendar, Clock, Link as LinkIcon, Trash2 } from 'lucide-react'

const DAYS = ['월', '화', '수', '목', '금', '토', '일']
const statusColors = { scheduled: 'bg-blue-100 text-blue-700', completed: 'bg-green-100 text-green-700', cancelled: 'bg-gray-100 text-gray-600' }

export default function MeetingsPage() {
  const [slots, setSlots] = useState([])
  const [meetings, setMeetings] = useState([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState('meetings')
  const [showSlotForm, setShowSlotForm] = useState(false)
  const [slotForm, setSlotForm] = useState({ day_of_week: 0, start_time: '09:00', end_time: '17:00', duration_minutes: 30 })
  const [showMeetingForm, setShowMeetingForm] = useState(false)
  const [meetingForm, setMeetingForm] = useState({ title: '', scheduled_at: '', duration_minutes: 30 })
  const [toast, setToast] = useState(null)

  const showToast = (msg) => { setToast(msg); setTimeout(() => setToast(null), 3000) }

  useEffect(() => {
    Promise.all([
      api.get('/meeting-slots'),
      api.get('/meetings'),
    ]).then(([slotsR, meetingsR]) => {
      setSlots(slotsR.data)
      setMeetings(meetingsR.data)
    }).catch(() => {}).finally(() => setLoading(false))
  }, [])

  const createSlot = async () => {
    try {
      const res = await api.post('/meeting-slots', slotForm)
      setSlots([...slots, res.data])
      setShowSlotForm(false)
      showToast('슬롯이 추가되었습니다')
    } catch {}
  }

  const deleteSlot = async (id) => {
    await api.delete(`/meeting-slots/${id}`)
    setSlots(slots.filter((s) => s.id !== id))
  }

  const createMeeting = async () => {
    if (!meetingForm.title || !meetingForm.scheduled_at) return
    try {
      const res = await api.post('/meetings', meetingForm)
      setMeetings([res.data, ...meetings])
      setShowMeetingForm(false)
      setMeetingForm({ title: '', scheduled_at: '', duration_minutes: 30 })
      showToast('미팅이 생성되었습니다')
    } catch {}
  }

  const cancelMeeting = async (id) => {
    await api.put(`/meetings/${id}/cancel`)
    setMeetings(meetings.map((m) => m.id === id ? { ...m, status: 'cancelled' } : m))
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div></div>
  }

  return (
    <div>
      {toast && <div className="fixed top-6 right-6 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium bg-green-600 text-white">{toast}</div>}

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">미팅</h1>
          <p className="text-gray-500 mt-1 text-sm">가용 시간을 설정하고 미팅을 관리하세요</p>
        </div>
        <button onClick={() => setShowMeetingForm(true)} className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg cursor-pointer">
          <Plus className="w-4 h-4" /> 새 미팅
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 mb-6">
        {[{ id: 'meetings', label: '미팅 목록' }, { id: 'slots', label: '가용 시간' }].map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)} className={`px-4 py-2.5 text-sm font-medium transition-colors cursor-pointer ${tab === t.id ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500'}`}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'meetings' && (
        <div className="space-y-3">
          {meetings.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-200 p-12 text-center text-gray-400">미팅이 없습니다</div>
          ) : meetings.map((m) => (
            <div key={m.id} className="bg-white rounded-xl border border-gray-200 p-4 flex items-center justify-between">
              <div>
                <h3 className="font-medium text-gray-900">{m.title}</h3>
                <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                  <span className="flex items-center gap-1"><Calendar className="w-3 h-3" />{new Date(m.scheduled_at).toLocaleString('ko-KR')}</span>
                  <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{m.duration_minutes}분</span>
                  {m.booker_name && <span>{m.booker_name} ({m.booker_email})</span>}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusColors[m.status]}`}>{m.status === 'scheduled' ? '예정' : m.status === 'completed' ? '완료' : '취소'}</span>
                {m.status === 'scheduled' && (
                  <button onClick={() => cancelMeeting(m.id)} className="p-1 text-gray-400 hover:text-red-600 cursor-pointer"><X className="w-4 h-4" /></button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === 'slots' && (
        <div>
          <div className="flex justify-end mb-4">
            <button onClick={() => setShowSlotForm(true)} className="inline-flex items-center gap-2 px-3 py-1.5 bg-gray-900 text-white text-xs font-medium rounded-lg cursor-pointer">
              <Plus className="w-3.5 h-3.5" /> 슬롯 추가
            </button>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="text-left px-4 py-3 font-medium text-gray-600">요일</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">시작</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">종료</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">시간</th>
                  <th className="text-center px-4 py-3 font-medium text-gray-600">작업</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {slots.map((s) => (
                  <tr key={s.id}>
                    <td className="px-4 py-3">{DAYS[s.day_of_week]}</td>
                    <td className="px-4 py-3">{s.start_time}</td>
                    <td className="px-4 py-3">{s.end_time}</td>
                    <td className="px-4 py-3">{s.duration_minutes}분</td>
                    <td className="px-4 py-3 text-center">
                      <button onClick={() => deleteSlot(s.id)} className="p-1 text-gray-400 hover:text-red-600 cursor-pointer"><Trash2 className="w-4 h-4" /></button>
                    </td>
                  </tr>
                ))}
                {slots.length === 0 && <tr><td colSpan={5} className="px-4 py-12 text-center text-gray-400">가용 시간이 없습니다</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Slot form */}
      {showSlotForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">슬롯 추가</h3>
              <button onClick={() => setShowSlotForm(false)} className="text-gray-400 cursor-pointer"><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">요일</label>
                <select value={slotForm.day_of_week} onChange={(e) => setSlotForm({ ...slotForm, day_of_week: parseInt(e.target.value) })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
                  {DAYS.map((d, i) => <option key={i} value={i}>{d}요일</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">시작</label>
                  <input type="time" value={slotForm.start_time} onChange={(e) => setSlotForm({ ...slotForm, start_time: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">종료</label>
                  <input type="time" value={slotForm.end_time} onChange={(e) => setSlotForm({ ...slotForm, end_time: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-4">
              <button onClick={() => setShowSlotForm(false)} className="px-4 py-2 text-sm text-gray-700 cursor-pointer">취소</button>
              <button onClick={createSlot} className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg cursor-pointer">추가</button>
            </div>
          </div>
        </div>
      )}

      {/* Meeting form */}
      {showMeetingForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">새 미팅</h3>
              <button onClick={() => setShowMeetingForm(false)} className="text-gray-400 cursor-pointer"><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">제목</label>
                <input type="text" value={meetingForm.title} onChange={(e) => setMeetingForm({ ...meetingForm, title: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" placeholder="미팅 제목" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">일시</label>
                <input type="datetime-local" value={meetingForm.scheduled_at} onChange={(e) => setMeetingForm({ ...meetingForm, scheduled_at: e.target.value })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">시간 (분)</label>
                <input type="number" value={meetingForm.duration_minutes} onChange={(e) => setMeetingForm({ ...meetingForm, duration_minutes: parseInt(e.target.value) })} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-4">
              <button onClick={() => setShowMeetingForm(false)} className="px-4 py-2 text-sm text-gray-700 cursor-pointer">취소</button>
              <button onClick={createMeeting} className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg cursor-pointer">생성</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
