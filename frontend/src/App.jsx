import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './lib/auth'
import ErrorBoundary from './components/ErrorBoundary'
import Layout from './components/Layout'
import { SkeletonPage } from './components/Skeleton'

// Lazy load all pages — only load when navigated to
const LandingPage = lazy(() => import('./pages/LandingPage'))
const LoginPage = lazy(() => import('./pages/LoginPage'))
const SignupPage = lazy(() => import('./pages/SignupPage'))
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const ProjectDetailPage = lazy(() => import('./pages/ProjectDetailPage'))
const SettingsPage = lazy(() => import('./pages/SettingsPage'))
const PricingPage = lazy(() => import('./pages/PricingPage'))
const AnalyticsPage = lazy(() => import('./pages/AnalyticsPage'))
const SequencesPage = lazy(() => import('./pages/SequencesPage'))
const TemplatesPage = lazy(() => import('./pages/TemplatesPage'))
const PipelinePage = lazy(() => import('./pages/PipelinePage'))
const CallsPage = lazy(() => import('./pages/CallsPage'))
const ProposalsPage = lazy(() => import('./pages/ProposalsPage'))
const MeetingsPage = lazy(() => import('./pages/MeetingsPage'))
const BookingPage = lazy(() => import('./pages/BookingPage'))
const TeamPage = lazy(() => import('./pages/TeamPage'))
const ApiKeysPage = lazy(() => import('./pages/ApiKeysPage'))

function PageLoader() {
  return (
    <div className="p-8">
      <SkeletonPage />
    </div>
  )
}

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
    <Suspense fallback={<PageLoader />}>
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
    </Suspense>
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
