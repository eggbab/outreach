import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Error message translation map
const ERROR_MESSAGES = {
  'Incorrect email or password': '이메일 또는 비밀번호가 올바르지 않습니다',
  'Email already registered': '이미 등록된 이메일입니다',
  'Invalid or expired token': '로그인이 만료되었습니다. 다시 로그인해주세요',
  'User not found': '사용자를 찾을 수 없습니다',
  'Project not found': '프로젝트를 찾을 수 없습니다',
  'Prospect not found': '잠재고객을 찾을 수 없습니다',
  'Not a team member': '팀 멤버가 아닙니다',
  'Admin access required': '관리자 권한이 필요합니다',
  'Can only upgrade to a higher plan': '현재 플랜보다 높은 플랜으로만 업그레이드할 수 있습니다',
  'Can only downgrade to a lower plan': '현재 플랜보다 낮은 플랜으로만 다운그레이드할 수 있습니다',
  'Password must be at least 8 characters': '비밀번호는 8자 이상이어야 합니다',
}

function translateError(detail) {
  if (!detail) return '오류가 발생했습니다'
  if (typeof detail !== 'string') return '오류가 발생했습니다'
  return ERROR_MESSAGES[detail] || detail
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }

    // Translate error message
    if (error.response?.data?.detail) {
      error.response.data.detail = translateError(error.response.data.detail)
    }

    // Network error (no response)
    if (!error.response) {
      error.message = '네트워크 연결을 확인해주세요'
    }

    return Promise.reject(error)
  }
)

export default api
