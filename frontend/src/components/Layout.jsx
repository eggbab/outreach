import { useState } from 'react'
import { NavLink, useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import {
  LayoutDashboard, Settings, LogOut, CreditCard,
  BarChart3, Mail, FileText, Kanban, Phone,
  FileCheck, Calendar, Users, Key, Menu, X,
} from 'lucide-react'
import Logo from './Logo'
import UsageBadge from './UsageBadge'

export default function Layout({ children }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [mobileOpen, setMobileOpen] = useState(false)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const navLinkClass = ({ isActive }) =>
    `flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
      isActive
        ? 'bg-blue-50 text-blue-700'
        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
    }`

  const navSectionClass = 'text-[10px] font-semibold text-gray-400 uppercase tracking-wider px-4 mt-5 mb-2'

  const closeMobile = () => setMobileOpen(false)

  const sidebarContent = (
    <>
      <div className="p-6 border-b border-gray-200 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2" onClick={closeMobile}>
          <Logo size={26} />
          <span className="text-xl font-bold text-gray-900">Outreach</span>
        </Link>
        <button onClick={closeMobile} className="lg:hidden p-1 text-gray-400 hover:text-gray-600 cursor-pointer">
          <X className="w-5 h-5" />
        </button>
      </div>

      <nav className="flex-1 p-4 space-y-0.5 overflow-y-auto">
        <NavLink to="/dashboard" end className={navLinkClass} onClick={closeMobile}>
          <LayoutDashboard className="w-5 h-5" />
          대시보드
        </NavLink>

        <p className={navSectionClass}>영업</p>
        <NavLink to="/pipeline" className={navLinkClass} onClick={closeMobile}>
          <Kanban className="w-5 h-5" />
          파이프라인
        </NavLink>
        <NavLink to="/calls" className={navLinkClass} onClick={closeMobile}>
          <Phone className="w-5 h-5" />
          통화 기록
        </NavLink>
        <NavLink to="/proposals" className={navLinkClass} onClick={closeMobile}>
          <FileCheck className="w-5 h-5" />
          제안서
        </NavLink>
        <NavLink to="/meetings" className={navLinkClass} onClick={closeMobile}>
          <Calendar className="w-5 h-5" />
          미팅
        </NavLink>

        <p className={navSectionClass}>발송</p>
        <NavLink to="/sequences" className={navLinkClass} onClick={closeMobile}>
          <Mail className="w-5 h-5" />
          시퀀스
        </NavLink>
        <NavLink to="/templates" className={navLinkClass} onClick={closeMobile}>
          <FileText className="w-5 h-5" />
          템플릿
        </NavLink>

        <p className={navSectionClass}>데이터</p>
        <NavLink to="/analytics" className={navLinkClass} onClick={closeMobile}>
          <BarChart3 className="w-5 h-5" />
          분석
        </NavLink>

        <p className={navSectionClass}>설정</p>
        <NavLink to="/teams" className={navLinkClass} onClick={closeMobile}>
          <Users className="w-5 h-5" />
          팀
        </NavLink>
        <NavLink to="/api-keys" className={navLinkClass} onClick={closeMobile}>
          <Key className="w-5 h-5" />
          API Keys
        </NavLink>
        <NavLink to="/pricing" className={navLinkClass} onClick={closeMobile}>
          <CreditCard className="w-5 h-5" />
          요금제
        </NavLink>
        <NavLink to="/settings" className={navLinkClass} onClick={closeMobile}>
          <Settings className="w-5 h-5" />
          설정
        </NavLink>
      </nav>

      <UsageBadge />

      <div className="p-4 border-t border-gray-200">
        <div className="flex items-center gap-3 px-3 py-2">
          <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 font-medium text-sm">
            {user?.name?.charAt(0) || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-900 truncate">{user?.name || '사용자'}</p>
            <p className="text-xs text-gray-500 truncate">{user?.email}</p>
          </div>
          <button
            onClick={handleLogout}
            className="p-1.5 text-gray-400 hover:text-red-500 transition-colors cursor-pointer"
            title="로그아웃"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </>
  )

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-40 bg-white border-b border-gray-200 px-4 h-14 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2">
          <Logo size={22} />
          <span className="text-lg font-bold text-gray-900">Outreach</span>
        </Link>
        <button onClick={() => setMobileOpen(true)} className="p-2 text-gray-600 cursor-pointer">
          <Menu className="w-5 h-5" />
        </button>
      </div>

      {/* Mobile sidebar overlay */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-50">
          <div className="absolute inset-0 bg-black/30" onClick={closeMobile} />
          <aside className="relative w-72 bg-white h-full flex flex-col shadow-xl">
            {sidebarContent}
          </aside>
        </div>
      )}

      {/* Desktop sidebar */}
      <aside className="hidden lg:flex w-64 bg-white border-r border-gray-200 flex-col fixed h-full overflow-y-auto">
        {sidebarContent}
      </aside>

      {/* Main content */}
      <main className="lg:ml-64 p-6 pt-20 lg:pt-8 lg:p-8">
        {children}
      </main>
    </div>
  )
}
