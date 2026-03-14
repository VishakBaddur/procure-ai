import React, { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import axios from 'axios'
import { API_BASE } from '@/config'
import '../App.css'

const Dashboard = ({ contextId, procurementContext }) => {
  const location = useLocation()
  const [comparison, setComparison] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (contextId) {
      fetchComparison()
    }
  }, [contextId])

  const fetchComparison = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/comparison/${contextId}`)
      setComparison(response.data.data)
    } catch (err) {
      setError('Failed to load comparison data')
    } finally {
      setLoading(false)
    }
  }

  const isActive = (path) => {
    return location.pathname === path ? 'active' : ''
  }

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
        <h1 style={{ color: 'white', marginBottom: '2rem' }}>Procurement Dashboard</h1>

        {procurementContext && (
          <div className="card" style={{ marginBottom: '2rem' }}>
            <h2 style={{ color: '#667eea', marginBottom: '1rem' }}>Procurement Context</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem' }}>
              <div>
                <strong>Item:</strong> {procurementContext.item_name}
              </div>
              <div>
                <strong>Vendors:</strong> {procurementContext.number_of_vendors}
              </div>
              <div>
                <strong>Primary Focus:</strong> {procurementContext.primary_focus.join(', ')}
              </div>
            </div>
          </div>
        )}

        {loading && <div className="loading">Loading...</div>}
        {error && <div className="error">{error}</div>}

        {comparison && (
          <>
            {Object.keys(comparison.price_comparison).length > 0 && (
              <div className="card">
                <h2 style={{ color: '#667eea', marginBottom: '1rem' }}>Price Comparison</h2>
                <div className="grid">
                  {Object.entries(comparison.price_comparison).map(([vendor, data]) => (
                    <div key={vendor} className="vendor-card">
                      <h3>{vendor}</h3>
                      <p><strong>Total Price:</strong> ${data.total_price?.toFixed(2) || 'N/A'}</p>
                      <p><strong>Items:</strong> {data.item_count || 0}</p>
                      {data.items && data.items.length > 0 && (
                        <div style={{ marginTop: '1rem' }}>
                          <strong>Items:</strong>
                          <ul style={{ marginTop: '0.5rem', paddingLeft: '1.5rem' }}>
                            {data.items.slice(0, 3).map((item, idx) => (
                              <li key={idx}>{item.name}: ${item.price?.toFixed(2)}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {Object.keys(comparison.legal_scores || {}).length > 0 && (
              <div className="card">
                <h2 style={{ color: '#667eea', marginBottom: '1rem' }}>Legal Agreement Analysis</h2>
                <div className="grid">
                  {Object.entries(comparison.legal_scores).map(([vendor, data]) => (
                    <div key={vendor} className="vendor-card">
                      <h3>{vendor}</h3>
                      <p><strong>Overall Score:</strong> {data.overall_score || 'N/A'}/100</p>
                      <p><strong>Risk Score:</strong> {data.risk_score || 'N/A'}</p>
                      <p><strong>Favorable Terms:</strong> {data.has_favorable_terms ? 'Yes' : 'No'}</p>
                      {data.recommendations && data.recommendations.length > 0 && (
                        <div style={{ marginTop: '1rem' }}>
                          <strong>Recommendations:</strong>
                          <ul style={{ marginTop: '0.5rem', paddingLeft: '1.5rem' }}>
                            {data.recommendations.map((rec, idx) => (
                              <li key={idx}>{rec}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {Object.keys(comparison.research_flags || {}).length > 0 && (
              <div className="card">
                <h2 style={{ color: '#667eea', marginBottom: '1rem' }}>Vendor Research</h2>
                <div className="grid">
                  {Object.entries(comparison.research_flags).map(([vendor, data]) => (
                    <div key={vendor} className="vendor-card">
                      <h3>{vendor}</h3>
                      <p><strong>Reputation Score:</strong> {data.reputation_score || 'N/A'}/100</p>
                      <p><strong>Red Flags:</strong> {data.red_flags?.length || 0}</p>
                      {data.red_flags && data.red_flags.length > 0 && (
                        <div style={{ marginTop: '1rem' }}>
                          <strong>Red Flags:</strong>
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
          </>
        )}

        {!loading && comparison && Object.keys(comparison.price_comparison).length === 0 && (
          <div className="card">
            <h2 style={{ color: '#667eea', marginBottom: '1rem' }}>Get Started</h2>
            <p style={{ marginBottom: '1rem' }}>
              Start by uploading vendor quotes and agreements to begin your analysis.
            </p>
            <Link to="/upload-quotes" className="btn btn-primary" style={{ marginRight: '1rem' }}>
              Upload Quotes
            </Link>
            <Link to="/upload-agreements" className="btn btn-secondary">
              Upload Agreements
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}

export default Dashboard

