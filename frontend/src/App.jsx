import React from "react"
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom"
import { AuthProvider, useAuth } from "./AuthContext"
import AuthPage from "./components/AuthPage"
import ProjectList from "./components/ProjectList"
import CreateProject from "./components/CreateProject"
import ProjectDashboard from "./components/ProjectDashboard"
import QuotationComparison from "./components/QuotationComparison"
import AgreementsComparison from "./components/AgreementsComparison"
import ReviewsComparison from "./components/ReviewsComparison"
import TCOComparison from "./components/TCOComparison"
import DecisionAssistance from "./components/DecisionAssistance"
import WhatIfAnalysis from "./components/WhatIfAnalysis"

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="min-h-screen flex items-center justify-center text-gray-500">Loading...</div>
  if (!user) return <Navigate to="/auth" replace />
  return children
}

function AppRoutes() {
  const { user, loading } = useAuth()
  if (loading) return <div className="min-h-screen flex items-center justify-center text-gray-500">Loading...</div>
  return (
    <Routes>
      <Route path="/auth" element={user ? <Navigate to="/projects" replace /> : <AuthPage />} />
      <Route path="/" element={<Navigate to={user ? "/projects" : "/auth"} replace />} />
      <Route path="/projects" element={<ProtectedRoute><ProjectList /></ProtectedRoute>} />
      <Route path="/projects/create" element={<ProtectedRoute><CreateProject /></ProtectedRoute>} />
      <Route path="/projects/:projectId/dashboard" element={<ProtectedRoute><ProjectDashboard /></ProtectedRoute>} />
      <Route path="/projects/:projectId/quotations" element={<ProtectedRoute><QuotationComparison /></ProtectedRoute>} />
      <Route path="/projects/:projectId/agreements" element={<ProtectedRoute><AgreementsComparison /></ProtectedRoute>} />
      <Route path="/projects/:projectId/reviews" element={<ProtectedRoute><ReviewsComparison /></ProtectedRoute>} />
      <Route path="/projects/:projectId/tco" element={<ProtectedRoute><TCOComparison /></ProtectedRoute>} />
      <Route path="/projects/:projectId/decision" element={<ProtectedRoute><DecisionAssistance /></ProtectedRoute>} />
      <Route path="/projects/:projectId/what-if" element={<ProtectedRoute><WhatIfAnalysis /></ProtectedRoute>} />
    </Routes>
  )
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="App">
          <AppRoutes />
        </div>
      </Router>
    </AuthProvider>
  )
}

export default App
