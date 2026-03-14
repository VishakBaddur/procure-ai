import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { API_BASE } from '@/config'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Textarea } from './ui/textarea'
import { Checkbox } from './ui/checkbox'

const CreateProject = () => {
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    name: '',
    item_name: '',
    item_description: '',
    primary_focus: []
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const focusOptions = [
    { value: 'pricing', label: 'Pricing' },
    { value: 'service', label: 'Service' },
    { value: 'warranty', label: 'Warranty' },
    { value: 'seller_rating', label: 'Seller Rating' }
  ]

  const handleChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleFocusChange = (value) => {
    setFormData(prev => {
      const newFocus = prev.primary_focus.includes(value)
        ? prev.primary_focus.filter(f => f !== value)
        : [...prev.primary_focus, value]
      return {
        ...prev,
        primary_focus: newFocus
      }
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    
    if (!formData.name || !formData.item_name || formData.primary_focus.length === 0) {
      setError('Please fill in all required fields')
      return
    }

    setLoading(true)
    try {
      const response = await axios.post(`${API_BASE}/api/projects`, formData)
      navigate(`/projects/${response.data.project_id}/dashboard`)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create project')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center py-12">
      <div className="container max-w-2xl px-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl">Create New Project</CardTitle>
            <CardDescription>
              Start a new procurement project. Each project is for a specific sourcing item.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {error && (
              <div className="mb-6 p-4 border border-destructive bg-destructive/10 text-destructive rounded-md text-sm">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-2">
                <Label htmlFor="name">Project Name *</Label>
                <Input
                  id="name"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="e.g., Aluminium Sourcing 2024"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="item_name">What are you sourcing? *</Label>
                <Input
                  id="item_name"
                  name="item_name"
                  value={formData.item_name}
                  onChange={handleChange}
                  placeholder="e.g., Aluminium, Office Furniture, IT Equipment"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="item_description">Description (Optional)</Label>
                <Textarea
                  id="item_description"
                  name="item_description"
                  value={formData.item_description}
                  onChange={handleChange}
                  rows="4"
                  placeholder="Provide more details about what you're sourcing..."
                />
              </div>

              <div className="space-y-3">
                <Label>What are the main things important to you? (Select multiple) *</Label>
                <div className="grid grid-cols-2 gap-3">
                  {focusOptions.map(option => (
                    <div key={option.value} className="flex items-center space-x-2">
                      <Checkbox
                        id={option.value}
                        checked={formData.primary_focus.includes(option.value)}
                        onCheckedChange={() => handleFocusChange(option.value)}
                      />
                      <Label
                        htmlFor={option.value}
                        className="text-sm font-normal cursor-pointer"
                      >
                        {option.label}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex gap-3 pt-4">
                <Button
                  type="submit"
                  disabled={loading}
                  className="flex-1"
                >
                  {loading ? 'Creating...' : 'Create Project'}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => navigate('/projects')}
                >
                  Cancel
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default CreateProject
