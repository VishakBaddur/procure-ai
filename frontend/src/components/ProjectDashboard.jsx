import React, { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import axios from 'axios'
import { API_BASE } from '@/config'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { AlertTriangle, CheckCircle2 } from 'lucide-react'
import ProjectLayout from './ProjectLayout'

const ProjectDashboard = () => {
  const { projectId } = useParams()
  const [dashboard, setDashboard] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchDashboard()
  }, [projectId])

  const fetchDashboard = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/projects/${projectId}/dashboard`)
      setDashboard(response.data.dashboard)
    } catch (err) {
      setError('Failed to load dashboard')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <ProjectLayout projectId={projectId} activePath="dashboard">
        <div className="container mx-auto px-8 py-8 max-w-7xl">
          <p className="text-muted-foreground">Loading dashboard...</p>
        </div>
      </ProjectLayout>
    )
  }

  if (error || !dashboard) {
    return (
      <ProjectLayout projectId={projectId} activePath="dashboard">
        <div className="container mx-auto px-8 py-8 max-w-7xl">
          <Card>
            <CardContent className="pt-6">
              <p className="text-destructive">{error || 'Dashboard not found'}</p>
            </CardContent>
          </Card>
        </div>
      </ProjectLayout>
    )
  }

  const project = dashboard.project
  const summary = dashboard.summary

  return (
    <ProjectLayout projectId={projectId} activePath="dashboard">
      <div className="container mx-auto px-8 py-8 max-w-7xl">
          <div className="mb-8">
            <h1 className="text-3xl font-bold tracking-tight mb-2">Dashboard</h1>
            <p className="text-muted-foreground">Overview of your procurement project</p>
          </div>

          {/* Summary Cards */}
          <div className="grid gap-4 md:grid-cols-3 mb-8">
            <Card>
              <CardHeader className="pb-3">
                <CardDescription>Vendors</CardDescription>
                <CardTitle className="text-3xl">{dashboard.vendors.length}</CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-3">
                <CardDescription>Quotes Received</CardDescription>
                <CardTitle className="text-3xl">
                  {Object.keys(summary.price_comparison).length}
                </CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-3">
                <CardDescription>Vendors Researched</CardDescription>
                <CardTitle className="text-3xl">
                  {Object.keys(summary.ratings).length}
                </CardTitle>
              </CardHeader>
            </Card>
          </div>

          {/* Price Comparison */}
          {Object.keys(summary.price_comparison).length > 0 && (
            <Card className="mb-6">
              <CardHeader>
                <CardTitle>Price Comparison</CardTitle>
                <CardDescription>Total prices from each vendor</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {Object.entries(summary.price_comparison).map(([vendor, data]) => (
                    <div key={vendor} className="border rounded-lg p-4">
                      <h3 className="font-semibold mb-2">{vendor}</h3>
                      <p className="text-2xl font-bold">${data.total_price?.toFixed(2) || '0.00'}</p>
                      <p className="text-sm text-muted-foreground">{data.item_count || 0} items</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Warranties */}
          {Object.keys(summary.warranties).length > 0 && (
            <Card className="mb-6">
              <CardHeader>
                <CardTitle>Warranties Offered</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {Object.entries(summary.warranties).map(([vendor, warranties]) => (
                    <div key={vendor} className="border rounded-lg p-4">
                      <h3 className="font-semibold mb-2">{vendor}</h3>
                      <ul className="space-y-1">
                        {warranties.map((w, idx) => (
                          <li key={idx} className="text-sm flex items-center gap-2">
                            <CheckCircle2 className="h-3 w-3" />
                            {w}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Ratings */}
          {Object.keys(summary.ratings).length > 0 && (
            <Card className="mb-6">
              <CardHeader>
                <CardTitle>Vendor Ratings</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {Object.entries(summary.ratings).map(([vendor, rating]) => (
                    <div key={vendor} className="border rounded-lg p-4">
                      <h3 className="font-semibold mb-2">{vendor}</h3>
                      <p className="text-2xl font-bold">{rating}/100</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Red Flags */}
          {Object.keys(summary.red_flags).length > 0 && (
            <Card className="mb-6 border-destructive/50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-destructive" />
                  Red Flags
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {Object.entries(summary.red_flags).map(([vendor, flags]) => (
                    <div key={vendor} className="border border-destructive/50 rounded-lg p-4">
                      <h3 className="font-semibold mb-2">{vendor}</h3>
                      <ul className="space-y-2">
                        {flags.slice(0, 3).map((flag, idx) => (
                          <li key={idx} className="text-sm text-destructive">
                            <span className="font-medium">{flag.type}:</span> {flag.description}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Recommendations */}
          {dashboard.recommendations && dashboard.recommendations.length > 0 && (
            <Card className="bg-muted/50">
              <CardHeader>
                <CardTitle>Recommendations</CardTitle>
                <CardDescription>Based on your primary focus</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {dashboard.recommendations.map((rec, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <CheckCircle2 className="h-4 w-4 mt-0.5 flex-shrink-0" />
                      <span className="text-sm">{rec}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>
      </ProjectLayout>
  )
}

export default ProjectDashboard
