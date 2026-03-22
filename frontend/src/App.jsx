import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './lib/auth'
import ErrorBoundary from './components/ErrorBoundary'
import Layout from './components/Layout'
import LandingPage from './pages/LandingPage'
import LoginPage from './pages/LoginPage'
import SignupPage from './pages/SignupPage'
import DashboardPage from './pages/DashboardPage'
import ProjectDetailPage from './pages/ProjectDetailPage'
import SettingsPage from './pages/SettingsPage'
import PricingPage from './pages/PricingPage'
import AnalyticsPage from './pages/AnalyticsPage'
import SequencesPage from './pages/SequencesPage'
import TemplatesPage from './pages/TemplatesPage'
import PipelinePage from './pages/PipelinePage'
import CallsPage from './pages/CallsPage'
import ProposalsPage from './pages/ProposalsPage'
import MeetingsPage from './pages/MeetingsPage'
import BookingPage from './pages/BookingPage'
import TeamPage from './pages/TeamPage'
import ApiKeysPage from './pages/ApiKeysPage'

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <Layout>{children}</Layout>
}

function AppRoutes() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/book/:userId" element={<BookingPage />} />
      {/* Protected routes */}
      <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
      <Route path="/projects/:id" element={<ProtectedRoute><ProjectDetailPage /></ProtectedRoute>} />
      <Route path="/pricing" element={<ProtectedRoute><PricingPage /></ProtectedRoute>} />
      <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
      <Route path="/analytics" element={<ProtectedRoute><AnalyticsPage /></ProtectedRoute>} />
      <Route path="/sequences" element={<ProtectedRoute><SequencesPage /></ProtectedRoute>} />
      <Route path="/templates" element={<ProtectedRoute><TemplatesPage /></ProtectedRoute>} />
      <Route path="/pipeline" element={<ProtectedRoute><PipelinePage /></ProtectedRoute>} />
      <Route path="/calls" element={<ProtectedRoute><CallsPage /></ProtectedRoute>} />
      <Route path="/proposals" element={<ProtectedRoute><ProposalsPage /></ProtectedRoute>} />
      <Route path="/meetings" element={<ProtectedRoute><MeetingsPage /></ProtectedRoute>} />
      <Route path="/teams" element={<ProtectedRoute><TeamPage /></ProtectedRoute>} />
      <Route path="/api-keys" element={<ProtectedRoute><ApiKeysPage /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </ErrorBoundary>
  )
}
