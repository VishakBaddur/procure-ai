import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import axios from 'axios'
import { API_BASE } from '@/config'
import '../App.css'

const UploadQuotes = ({ contextId }) => {
  const location = useLocation()
  const [vendorName, setVendorName] = useState('')
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')
  const [uploadedQuotes, setUploadedQuotes] = useState([])

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
        `${API_BASE}/api/upload/quote`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        }
      )

      setSuccess(`Quote uploaded successfully for ${vendorName}`)
      setUploadedQuotes([...uploadedQuotes, { vendor: vendorName, data: response.data.data }])
      setVendorName('')
      setFile(null)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to upload quote')
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
        <h1 style={{ color: 'white', marginBottom: '2rem' }}>Upload Vendor Quotes</h1>

        <div className="card">
          <h2 style={{ color: '#667eea', marginBottom: '1rem' }}>Upload Quote</h2>
          <p style={{ marginBottom: '1.5rem', color: '#666' }}>
            Upload vendor quotes in PDF, image, or text format. Our AI will extract pricing information automatically.
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
            <label>Upload Quote File *</label>
            <div
              className="upload-area"
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onClick={() => document.getElementById('file-input').click()}
            >
              <input
                type="file"
                id="file-input"
                accept=".pdf,.png,.jpg,.jpeg,.txt"
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
                    📄 Drag & drop your quote file here
                  </p>
                  <p style={{ color: '#666' }}>
                    or click to browse (PDF, Image, or Text)
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
            {uploading ? 'Uploading...' : 'Upload Quote'}
          </button>
        </div>

        {uploadedQuotes.length > 0 && (
          <div className="card">
            <h2 style={{ color: '#667eea', marginBottom: '1rem' }}>Uploaded Quotes</h2>
            {uploadedQuotes.map((quote, idx) => (
              <div key={idx} className="vendor-card">
                <h3>{quote.vendor}</h3>
                <p><strong>Total Price:</strong> ${quote.data.total_price?.toFixed(2) || 'N/A'}</p>
                <p><strong>Items Found:</strong> {quote.data.item_count || 0}</p>
              </div>
            ))}
          </div>
        )}

        <div style={{ textAlign: 'center', marginTop: '2rem' }}>
          <Link to="/analytics" className="btn btn-primary">
            View Analytics & Comparison
          </Link>
        </div>
      </div>
    </div>
  )
}

export default UploadQuotes

