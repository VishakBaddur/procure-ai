import React, { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import axios from 'axios'
import { API_BASE } from '@/config'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell } from 'recharts'
import '../App.css'

const Analytics = ({ contextId }) => {
  const location = useLocation()
  const [analytics, setAnalytics] = useState(null)
  const [comparison, setComparison] = useState(null)
  const [tcoData, setTcoData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const COLORS = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#00f2fe']

  useEffect(() => {
    fetchAnalytics()
    fetchComparison()
  }, [contextId])

  const fetchAnalytics = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/analytics/${contextId}`)
      setAnalytics(response.data.data)
    } catch (err) {
      setError('Failed to load analytics')
    } finally {
      setLoading(false)
    }
  }

  const fetchComparison = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/comparison/${contextId}`)
      setComparison(response.data.data)
      
      // Prepare TCO analysis
      const quotes = Object.entries(response.data.data.price_comparison || {}).map(([vendor, data]) => ({
        vendor_name: vendor,
        total_price: data.total_price || 0
      }))
      
      if (quotes.length > 0) {
        const tcoResponse = await axios.post(`${API_BASE}/api/analyze/tco`, {
          context_id: contextId,
          vendor_quotes: quotes
        })
        setTcoData(tcoResponse.data.data)
      }
    } catch (err) {
      console.error('Failed to load comparison:', err)
    }
  }

  const isActive = (path) => {
    return location.pathname === path ? 'active' : ''
  }

  if (loading) {
    return (
      <div>
        <div className="navbar">
          <nav>
            <Link to="/dashboard" className={isActive('/dashboard')}>Dashboard</Link>
            <Link to="/upload-quotes" className={isActive('/upload-quotes')}>Upload Quotes</Link>
            <Link to="/upload-agreements" className={isActive('/upload-agreements')}>Upload Agreements</Link>
            <Link to="/analytics" className={isActive('/analytics')}>Analytics</Link>
          </nav>
        </div>
        <div className="loading">Loading analytics...</div>
      </div>
    )
  }

  // Prepare chart data
  const priceChartData = analytics?.price_analysis ? 
    Object.entries(analytics.price_analysis).map(([vendor, data]) => ({
      vendor,
      price: data.total_price || 0
    })) : []

  const legalChartData = comparison?.legal_scores ?
    Object.entries(comparison.legal_scores).map(([vendor, data]) => ({
      vendor,
      score: data.overall_score || 0,
      risk: (data.risk_score || 0) * 100
    })) : []

  const tcoChartData = tcoData?.vendors ? 
    tcoData.vendors.map(v => ({
      vendor: v.vendor_name,
      initial: v.initial_price || 0,
      tco: v.total_tco || 0
    })) : []

  return (
    <div>
      <div className="navbar">
        <nav>
          <Link to="/dashboard" className={isActive('/dashboard')}>Dashboard</Link>
          <Link to="/upload-quotes" className={isActive('/upload-quotes')}>Upload Quotes</Link>
          <Link to="/upload-agreements" className={isActive('/upload-agreements')}>Upload Agreements</Link>
          <Link to="/analytics" className={isActive('/analytics')}>Analytics</Link>
        </nav>
      </div>

      <div className="container">
        <h1 style={{ color: 'white', marginBottom: '2rem' }}>Analytics Dashboard</h1>

        {error && <div className="error">{error}</div>}

        {analytics && (
          <div className="card">
            <h2 style={{ color: '#667eea', marginBottom: '1rem' }}>Summary</h2>
            <div className="grid">
              <div className="stat-card">
                <h3>{analytics.summary?.item || 'N/A'}</h3>
                <p>Item Being Procured</p>
              </div>
              <div className="stat-card">
                <h3>{analytics.summary?.vendors_count || 0}</h3>
                <p>Vendors Compared</p>
              </div>
            </div>
          </div>
        )}

        {priceChartData.length > 0 && (
          <div className="card">
            <h2 style={{ color: '#667eea', marginBottom: '1rem' }}>Price Comparison</h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={priceChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="vendor" />
                <YAxis />
                <Tooltip formatter={(value) => `$${value.toFixed(2)}`} />
                <Legend />
                <Bar dataKey="price" fill="#667eea" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {legalChartData.length > 0 && (
          <div className="card">
            <h2 style={{ color: '#667eea', marginBottom: '1rem' }}>Legal Agreement Scores</h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={legalChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="vendor" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="score" fill="#4facfe" name="Overall Score" />
                <Bar dataKey="risk" fill="#f093fb" name="Risk Score" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {tcoChartData.length > 0 && (
          <div className="card">
            <h2 style={{ color: '#667eea', marginBottom: '1rem' }}>Total Cost of Ownership (5 Years)</h2>
            <p style={{ marginBottom: '1rem', color: '#666' }}>
              Comparing initial cost vs. long-term total cost including support, maintenance, and repairs
            </p>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={tcoChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="vendor" />
                <YAxis />
                <Tooltip formatter={(value) => `$${value.toFixed(2)}`} />
                <Legend />
                <Bar dataKey="initial" fill="#667eea" name="Initial Cost" />
                <Bar dataKey="tco" fill="#764ba2" name="Total Cost (5yr)" />
              </BarChart>
            </ResponsiveContainer>
            
            {tcoData?.best_long_term_value && (
              <div style={{ marginTop: '1.5rem', padding: '1rem', background: '#f0f2ff', borderRadius: '8px' }}>
                <h3 style={{ color: '#667eea', marginBottom: '0.5rem' }}>💡 Recommendation</h3>
                <p><strong>Best Long-term Value:</strong> {tcoData.best_long_term_value}</p>
                {tcoData.recommendations && tcoData.recommendations.map((rec, idx) => (
                  <p key={idx} style={{ marginTop: '0.5rem' }}>{rec}</p>
                ))}
              </div>
            )}

            {tcoData?.vendors && (
              <div style={{ marginTop: '1.5rem' }}>
                <h3 style={{ color: '#667eea', marginBottom: '1rem' }}>Detailed TCO Breakdown</h3>
                <div className="grid">
                  {tcoData.vendors.map((vendor, idx) => (
                    <div key={idx} className="vendor-card">
                      <h3>{vendor.vendor_name}</h3>
                      <p><strong>Initial:</strong> ${vendor.initial_price?.toFixed(2)}</p>
                      <p><strong>5-Year TCO:</strong> ${vendor.total_tco?.toFixed(2)}</p>
                      <p><strong>Annual Cost:</strong> ${vendor.annual_cost?.toFixed(2)}</p>
                      <p><strong>Durability Score:</strong> {vendor.durability_score}/100</p>
                      {vendor.breakdown && (
                        <div style={{ marginTop: '1rem', fontSize: '0.9rem' }}>
                          <strong>Breakdown:</strong>
                          <ul style={{ marginTop: '0.5rem', paddingLeft: '1.5rem' }}>
                            <li>Support: ${vendor.breakdown.support_cost_5yr?.toFixed(2)}</li>
                            <li>Maintenance: ${vendor.breakdown.maintenance_cost_5yr?.toFixed(2)}</li>
                            <li>Repairs: ${vendor.breakdown.repair_cost_5yr?.toFixed(2)}</li>
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {comparison?.research_flags && Object.keys(comparison.research_flags).length > 0 && (
          <div className="card">
            <h2 style={{ color: '#667eea', marginBottom: '1rem' }}>Vendor Research & Red Flags</h2>
            <div className="grid">
              {Object.entries(comparison.research_flags).map(([vendor, data]) => (
                <div key={vendor} className="vendor-card">
                  <h3>{vendor}</h3>
                  <p><strong>Reputation Score:</strong> {data.reputation_score || 'N/A'}/100</p>
                  <p><strong>Red Flags:</strong> {data.red_flags?.length || 0}</p>
                  {data.red_flags && data.red_flags.length > 0 && (
                    <div style={{ marginTop: '1rem' }}>
                      <strong style={{ color: '#c33' }}>⚠️ Red Flags:</strong>
                      <ul style={{ marginTop: '0.5rem', paddingLeft: '1.5rem' }}>
                        {data.red_flags.map((flag, idx) => (
                          <li key={idx} style={{ color: '#c33' }}>
                            {flag.type}: {flag.description}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        <div style={{ textAlign: 'center', marginTop: '2rem' }}>
          <Link to="/dashboard" className="btn btn-primary">
            Back to Dashboard
          </Link>
        </div>
      </div>
    </div>
  )
}

export default Analytics

