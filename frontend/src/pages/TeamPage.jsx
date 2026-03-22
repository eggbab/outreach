import { useState, useEffect } from 'react'
import api from '../lib/api'
import { Plus, Users, Trash2, X, UserPlus, Shield } from 'lucide-react'

export default function TeamPage() {
  const [teams, setTeams] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [selectedTeam, setSelectedTeam] = useState(null)
  const [members, setMembers] = useState([])
  const [showInvite, setShowInvite] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('member')
  const [toast, setToast] = useState(null)

  const showToast = (msg, type = 'success') => { setToast({ message: msg, type }); setTimeout(() => setToast(null), 3000) }

  useEffect(() => { fetchTeams() }, [])

  const fetchTeams = () => {
    api.get('/teams').then((r) => setTeams(r.data)).catch(() => {}).finally(() => setLoading(false))
  }

  const createTeam = async () => {
    if (!newName.trim()) return
    try {
      await api.post('/teams', { name: newName.trim() })
      setNewName('')
      setShowCreate(false)
      fetchTeams()
      showToast('팀이 생성되었습니다')
    } catch (err) { showToast(err.response?.data?.detail || '실패', 'error') }
  }

  const selectTeam = async (team) => {
    setSelectedTeam(team)
    const res = await api.get(`/teams/${team.id}/members`)
    setMembers(res.data)
  }

  const inviteMember = async () => {
    if (!inviteEmail.trim()) return
    try {
      await api.post(`/teams/${selectedTeam.id}/invite`, { email: inviteEmail, role: inviteRole })
      setShowInvite(false)
      setInviteEmail('')
      const res = await api.get(`/teams/${selectedTeam.id}/members`)
      setMembers(res.data)
      showToast('멤버가 추가되었습니다')
    } catch (err) { showToast(err.response?.data?.detail || '실패', 'error') }
  }

  const removeMember = async (userId) => {
    try {
      await api.delete(`/teams/${selectedTeam.id}/members/${userId}`)
      setMembers(members.filter((m) => m.user_id !== userId))
    } catch (err) { showToast(err.response?.data?.detail || '실패', 'error') }
  }

  const deleteTeam = async (id) => {
    await api.delete(`/teams/${id}`)
    if (selectedTeam?.id === id) { setSelectedTeam(null); setMembers([]) }
    fetchTeams()
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div></div>
  }

  return (
    <div>
      {toast && <div className={`fixed top-6 right-6 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium ${toast.type === 'error' ? 'bg-red-600 text-white' : 'bg-green-600 text-white'}`}>{toast.message}</div>}

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">팀</h1>
          <p className="text-gray-500 mt-1 text-sm">팀을 만들고 프로젝트를 공유하세요</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg cursor-pointer">
          <Plus className="w-4 h-4" /> 새 팀
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="space-y-3">
          {teams.map((team) => (
            <div
              key={team.id}
              onClick={() => selectTeam(team)}
              className={`bg-white rounded-xl border p-4 cursor-pointer transition-all ${selectedTeam?.id === team.id ? 'border-blue-300 ring-1 ring-blue-100' : 'border-gray-200 hover:border-gray-300'}`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Users className="w-4 h-4 text-gray-400" />
                  <span className="font-medium text-gray-900 text-sm">{team.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400">{team.member_count}명</span>
                  <button onClick={(e) => { e.stopPropagation(); deleteTeam(team.id) }} className="p-1 text-gray-400 hover:text-red-600 cursor-pointer">
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
          {teams.length === 0 && <p className="text-sm text-gray-400 text-center py-8">팀이 없습니다</p>}
        </div>

        <div className="lg:col-span-2">
          {selectedTeam ? (
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-base font-semibold text-gray-900">{selectedTeam.name} 멤버</h2>
                <button onClick={() => setShowInvite(true)} className="inline-flex items-center gap-1 px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-lg cursor-pointer">
                  <UserPlus className="w-3.5 h-3.5" /> 초대
                </button>
              </div>
              <div className="space-y-3">
                {members.map((m) => (
                  <div key={m.id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{m.name}</p>
                      <p className="text-xs text-gray-500">{m.email}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${m.role === 'admin' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-600'}`}>
                        {m.role === 'admin' ? '관리자' : '멤버'}
                      </span>
                      <button onClick={() => removeMember(m.user_id)} className="p-1 text-gray-400 hover:text-red-600 cursor-pointer">
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-64 text-sm text-gray-400">팀을 선택하세요</div>
          )}
        </div>
      </div>

      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">새 팀</h3>
              <button onClick={() => setShowCreate(false)} className="text-gray-400 cursor-pointer"><X className="w-5 h-5" /></button>
            </div>
            <input type="text" value={newName} onChange={(e) => setNewName(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && createTeam()} placeholder="팀 이름" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm mb-4" autoFocus />
            <div className="flex justify-end gap-3">
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-sm text-gray-700 cursor-pointer">취소</button>
              <button onClick={createTeam} className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg cursor-pointer">생성</button>
            </div>
          </div>
        </div>
      )}

      {showInvite && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">멤버 초대</h3>
              <button onClick={() => setShowInvite(false)} className="text-gray-400 cursor-pointer"><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-3">
              <input type="email" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} placeholder="이메일 주소" className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm" />
              <select value={inviteRole} onChange={(e) => setInviteRole(e.target.value)} className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
                <option value="member">멤버</option>
                <option value="admin">관리자</option>
              </select>
            </div>
            <div className="flex justify-end gap-3 mt-4">
              <button onClick={() => setShowInvite(false)} className="px-4 py-2 text-sm text-gray-700 cursor-pointer">취소</button>
              <button onClick={inviteMember} className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg cursor-pointer">초대</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
