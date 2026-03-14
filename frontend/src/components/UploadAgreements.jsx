import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import axios from 'axios'
import { API_BASE } from '@/config'
import '../App.css'

const UploadAgreements = ({ contextId }) => {
  const location = useLocation()
  const [vendorName, setVendorName] = useState('')
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')
  const [uploadedAgreements, setUploadedAgreements] = useState([])

  const isActive = (path) => {
    return location.pathname === path ? 'active' : ''
  }

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      setFile(selectedFile)
      setError('')
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile) {
      setFile(droppedFile)
      setError('')
    }
  }

  const handleDragOver = (e) => {
    e.preventDefault()
  }

  const handleUpload = async () => {
    if (!vendorName || !file) {
      setError('Please provide vendor name and select a file')
      return
    }

    setUploading(true)
    setError('')
    setSuccess('')

    const formData = new FormData()
    formData.append('file', file)
    formData.append('vendor_name', vendorName)
    formData.append('context_id', contextId)

    try {
      const response = await axios.post(
        `${API_BASE}/api/upload/agreement`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        }
      )

      setSuccess(`Agreement analyzed successfully for ${vendorName}`)
      setUploadedAgreements([...uploadedAgreements, { vendor: vendorName, data: response.data.data }])
      setVendorName('')
      setFile(null)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to upload agreement')
    } finally {
      setUploading(false)
    }
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
        <h1 style={{ color: 'white', marginBottom: '2rem' }}>Upload Legal Agreements</h1>

        <div className="card">
          <h2 style={{ color: '#667eea', marginBottom: '1rem' }}>Upload Agreement</h2>
          <p style={{ marginBottom: '1.5rem', color: '#666' }}>
            Upload vendor legal agreements in PDF format. Our AI will analyze terms, identify risks, and provide recommendations.
          </p>

          {error && <div className="error">{error}</div>}
          {success && <div className="success">{success}</div>}

          <div className="input-group">
            <label htmlFor="vendor_name">Vendor Name *</label>
            <input
              type="text"
              id="vendor_name"
              value={vendorName}
              onChange={(e) => setVendorName(e.target.value)}
              placeholder="Enter vendor name"
              required
            />
          </div>

          <div className="input-group">
            <label>Upload Agreement File *</label>
            <div
              className="upload-area"
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onClick={() => document.getElementById('file-input').click()}
            >
              <input
                type="file"
                id="file-input"
                accept=".pdf,.doc,.docx"
                onChange={handleFileChange}
              />
              {file ? (
                <div>
                  <p style={{ fontSize: '1.1rem', fontWeight: '600', color: '#667eea' }}>
                    {file.name}
                  </p>
                  <p style={{ color: '#666', marginTop: '0.5rem' }}>
                    Click to change file
                  </p>
                </div>
              ) : (
                <div>
                  <p style={{ fontSize: '1.2rem', marginBottom: '0.5rem' }}>
                    📄 Drag & drop your agreement file here
                  </p>
                  <p style={{ color: '#666' }}>
                    or click to browse (PDF or Word document)
                  </p>
                </div>
              )}
            </div>
          </div>

          <button
            onClick={handleUpload}
            className="btn btn-primary"
            disabled={uploading || !vendorName || !file}
            style={{ width: '100%' }}
          >
            {uploading ? 'Analyzing...' : 'Upload & Analyze Agreement'}
          </button>
        </div>

        {uploadedAgreements.length > 0 && (
          <div className="card">
            <h2 style={{ color: '#667eea', marginBottom: '1rem' }}>Analyzed Agreements</h2>
            {uploadedAgreements.map((agreement, idx) => (
              <div key={idx} className="vendor-card">
                <h3>{agreement.vendor}</h3>
                <p><strong>Overall Score:</strong> {agreement.data.overall_score || 'N/A'}/100</p>
                <p><strong>Risk Score:</strong> {agreement.data.risk_score || 'N/A'}</p>
                <p><strong>Favorable Terms:</strong> {agreement.data.has_favorable_terms ? '✅ Yes' : '❌ No'}</p>
                {agreement.data.recommendations && agreement.data.recommendations.length > 0 && (
                  <div style={{ marginTop: '1rem' }}>
                    <strong>Recommendations:</strong>
                    <ul style={{ marginTop: '0.5rem', paddingLeft: '1.5rem' }}>
                      {agreement.data.recommendations.map((rec, recIdx) => (
                        <li key={recIdx}>{rec}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        <div style={{ textAlign: 'center', marginTop: '2rem' }}>
          <button
            onClick={async () => {
              // Research vendors button
              const vendors = [...new Set(uploadedAgreements.map(a => a.vendor))]
              for (const vendor of vendors) {
                try {
                  await axios.post(`${API_BASE}/api/research/vendor`, null, {
                    params: {
                      vendor_name: vendor,
                      context_id: contextId
                    }
                  })
                } catch (err) {
                  console.error(`Failed to research ${vendor}:`, err)
                }
              }
              alert('Vendor research initiated! Check the dashboard for results.')
            }}
            className="btn btn-secondary"
            style={{ marginRight: '1rem' }}
          >
            Research All Vendors
          </button>
          <Link to="/analytics" className="btn btn-primary">
            View Analytics & Comparison
          </Link>
        </div>
      </div>
    </div>
  )
}

export default UploadAgreements

