import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import api from '../lib/api'
import { Calendar, Clock, CheckCircle } from 'lucide-react'

const DAYS = ['월', '화', '수', '목', '금', '토', '일']

export default function BookingPage() {
  const { userId } = useParams()
  const [slots, setSlots] = useState([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState({ booker_name: '', booker_email: '', scheduled_at: '', title: '미팅 예약' })
  const [booked, setBooked] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.get(`/book/${userId}/slots`)
      .then((r) => setSlots(r.data))
      .catch(() => setError('예약 페이지를 찾을 수 없습니다'))
      .finally(() => setLoading(false))
  }, [userId])

  const handleBook = async (e) => {
    e.preventDefault()
    try {
      await api.post(`/book/${userId}`, form)
      setBooked(true)
    } catch {
      setError('예약에 실패했습니다')
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-gray-500">{error}</p>
      </div>
    )
  }

  if (booked) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">예약 완료!</h1>
          <p className="text-gray-500">미팅이 예약되었습니다. 확인 이메일을 보내드리겠습니다.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4">
      <div className="max-w-md mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-gray-900">미팅 예약</h1>
          <p className="text-gray-500 mt-1">편한 시간을 선택해주세요</p>
        </div>

        {/* Available slots */}
        {slots.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">가용 시간</h2>
            <div className="space-y-2">
              {slots.map((s, i) => (
                <div key={i} className="flex items-center gap-3 text-sm text-gray-600">
                  <Calendar className="w-4 h-4 text-gray-400" />
                  <span>{DAYS[s.day_of_week]}요일</span>
                  <span>{s.start_time} - {s.end_time}</span>
                  <span className="text-gray-400">({s.duration_minutes}분)</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Booking form */}
        <form onSubmit={handleBook} className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">이름</label>
            <input
              type="text"
              required
              value={form.booker_name}
              onChange={(e) => setForm({ ...form, booker_name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">이메일</label>
            <input
              type="email"
              required
              value={form.booker_email}
              onChange={(e) => setForm({ ...form, booker_email: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">희망 일시</label>
            <input
              type="datetime-local"
              required
              value={form.scheduled_at}
              onChange={(e) => setForm({ ...form, scheduled_at: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
          </div>
          <button type="submit" className="w-full py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors cursor-pointer">
            예약하기
          </button>
        </form>
      </div>
    </div>
  )
}
