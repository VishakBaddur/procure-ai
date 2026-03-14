import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import ProjectList from './components/ProjectList'
import CreateProject from './components/CreateProject'
import ProjectDashboard from './components/ProjectDashboard'
import QuotationComparison from './components/QuotationComparison'
import AgreementsComparison from './components/AgreementsComparison'
import ReviewsComparison from './components/ReviewsComparison'
import TCOComparison from './components/TCOComparison'
import DecisionAssistance from './components/DecisionAssistance'
import WhatIfAnalysis from './components/WhatIfAnalysis'

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<ProjectList />} />
          <Route path="/projects" element={<ProjectList />} />
          <Route path="/projects/create" element={<CreateProject />} />
          <Route path="/projects/:projectId/dashboard" element={<ProjectDashboard />} />
          <Route path="/projects/:projectId/quotations" element={<QuotationComparison />} />
          <Route path="/projects/:projectId/agreements" element={<AgreementsComparison />} />
          <Route path="/projects/:projectId/reviews" element={<ReviewsComparison />} />
          <Route path="/projects/:projectId/tco" element={<TCOComparison />} />
          <Route path="/projects/:projectId/decision" element={<DecisionAssistance />} />
          <Route path="/projects/:projectId/what-if" element={<WhatIfAnalysis />} />
        </Routes>
      </div>
    </Router>
  )
}

export default App
