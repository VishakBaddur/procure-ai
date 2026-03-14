import React, { useState } from 'react'
import axios from 'axios'
import { API_BASE } from '@/config'
import { useNavigate } from 'react-router-dom'
import '../App.css'

const Questionnaire = ({ onSubmit }) => {
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    item_name: '',
    item_description: '',
    number_of_vendors: '',
    primary_focus: [],
    budget_range: '',
    timeline: ''
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const focusOptions = [
    'Cheap / Low Cost',
    'Durability / Longevity',
    'Quality / Premium',
    'Support & Maintenance',
    'Fast Delivery',
    'Warranty Coverage',
    'Brand Reputation',
    'Customization Options'
  ]

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleFocusChange = (option) => {
    setFormData(prev => {
      const newFocus = prev.primary_focus.includes(option)
        ? prev.primary_focus.filter(f => f !== option)
        : [...prev.primary_focus, option]
      return {
        ...prev,
        primary_focus: newFocus
      }
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    
    if (!formData.item_name || !formData.number_of_vendors || formData.primary_focus.length === 0) {
      setError('Please fill in all required fields')
      return
    }

    setLoading(true)
    try {
      const response = await axios.post(`${API_BASE}/api/questionnaire`, {
        ...formData,
        number_of_vendors: parseInt(formData.number_of_vendors)
      })
      
      onSubmit(formData, response.data.context_id)
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit questionnaire')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container" style={{ maxWidth: '800px', marginTop: '4rem' }}>
      <div className="card">
        <h1 style={{ marginBottom: '1rem', color: '#667eea' }}>
          Procurement AI Platform
        </h1>
        <p style={{ marginBottom: '2rem', color: '#666' }}>
          Let's start by understanding your procurement needs
        </p>

        {error && <div className="error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label htmlFor="item_name">What are you procuring? *</label>
            <input
              type="text"
              id="item_name"
              name="item_name"
              value={formData.item_name}
              onChange={handleChange}
              placeholder="e.g., Office Furniture, IT Equipment, Raw Materials"
              required
            />
          </div>

          <div className="input-group">
            <label htmlFor="item_description">Description (Optional)</label>
            <textarea
              id="item_description"
              name="item_description"
              value={formData.item_description}
              onChange={handleChange}
              rows="4"
              placeholder="Provide more details about what you're procuring..."
            />
          </div>

          <div className="input-group">
            <label htmlFor="number_of_vendors">How many vendors are you comparing? *</label>
            <input
              type="number"
              id="number_of_vendors"
              name="number_of_vendors"
              value={formData.number_of_vendors}
              onChange={handleChange}
              min="1"
              max="20"
              required
            />
          </div>

          <div className="input-group">
            <label>What is your primary focus? (Select multiple) *</label>
            <div className="checkbox-group">
              {focusOptions.map(option => (
                <div key={option} className="checkbox-item">
                  <input
                    type="checkbox"
                    id={option}
                    checked={formData.primary_focus.includes(option)}
                    onChange={() => handleFocusChange(option)}
                  />
                  <label htmlFor={option} style={{ marginBottom: 0, cursor: 'pointer' }}>
                    {option}
                  </label>
                </div>
              ))}
            </div>
          </div>

          <div className="input-group">
            <label htmlFor="budget_range">Budget Range (Optional)</label>
            <select
              id="budget_range"
              name="budget_range"
              value={formData.budget_range}
              onChange={handleChange}
            >
              <option value="">Select budget range</option>
              <option value="under-1k">Under $1,000</option>
              <option value="1k-10k">$1,000 - $10,000</option>
              <option value="10k-50k">$10,000 - $50,000</option>
              <option value="50k-100k">$50,000 - $100,000</option>
              <option value="over-100k">Over $100,000</option>
            </select>
          </div>

          <div className="input-group">
            <label htmlFor="timeline">Timeline (Optional)</label>
            <select
              id="timeline"
              name="timeline"
              value={formData.timeline}
              onChange={handleChange}
            >
              <option value="">Select timeline</option>
              <option value="urgent">Urgent (Within 1 week)</option>
              <option value="short">Short (1-2 weeks)</option>
              <option value="medium">Medium (2-4 weeks)</option>
              <option value="long">Long (1-3 months)</option>
              <option value="flexible">Flexible</option>
            </select>
          </div>

          <button 
            type="submit" 
            className="btn btn-primary"
            disabled={loading}
            style={{ width: '100%', marginTop: '1rem' }}
          >
            {loading ? 'Submitting...' : 'Continue to Dashboard'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default Questionnaire

