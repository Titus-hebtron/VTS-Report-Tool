import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { Login } from './pages/Login'
import { Dashboard } from './pages/Dashboard'
import { IncidentReport } from './pages/IncidentReport'
import { IdleAnalyzer } from './pages/IdleAnalyzer'
import { BreaksPickups } from './pages/BreaksPickups'
import { ReportSearch } from './pages/ReportSearch'
import { GPSTracking } from './pages/GPSTracking'
import { AccidentAnalysis } from './pages/AccidentAnalysis'
import { Layout } from './components/Layout'
import { ProtectedRoute } from './components/ProtectedRoute'

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/incidents" element={<IncidentReport />} />
            <Route path="/idle-analyzer" element={<IdleAnalyzer />} />
            <Route path="/breaks-pickups" element={<BreaksPickups />} />
            <Route path="/reports" element={<ReportSearch />} />
            <Route path="/tracking" element={<GPSTracking />} />
            <Route path="/accident-analysis" element={<AccidentAnalysis />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App