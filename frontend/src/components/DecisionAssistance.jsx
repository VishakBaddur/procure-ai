import React, { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import axios from 'axios'
import { API_BASE } from '@/config'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Download, CheckCircle2, XCircle, AlertCircle, Loader2 } from 'lucide-react'
import ProjectLayout from './ProjectLayout'

const DecisionAssistance = () => {
  const { projectId } = useParams()
  const [recommendation, setRecommendation] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    fetchRecommendation()
  }, [projectId])

  const fetchRecommendation = async () => {
    setLoading(true)
    setError('')
    try {
      const response = await axios.get(`${API_BASE}/api/projects/${projectId}/recommendation`)
      if (response.data && response.data.recommendation) {
        setRecommendation(response.data.recommendation)
      }
    } catch (err) {
      console.error('Failed to load recommendation:', err)
      setError('Failed to load recommendation: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }

  const handleExport = async (format) => {
    setExporting(true)
    try {
      const formData = new FormData()
      formData.append('format', format)
      
      const response = await axios.post(
        `${API_BASE}/api/projects/${projectId}/recommendation/export`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        }
      )
      
      if (response.data && response.data.content) {
        // Create download link
        const blob = new Blob([response.data.content], { type: 'text/markdown' })
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `vendor-recommendation-${projectId}-${new Date().toISOString().split('T')[0]}.md`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        document.body.removeChild(a)
      }
    } catch (err) {
      console.error('Export failed:', err)
      setError('Export failed: ' + (err.response?.data?.detail || err.message))
    } finally {
      setExporting(false)
    }
  }

  const getConfidenceColor = (confidence) => {
    switch (confidence?.toLowerCase()) {
      case 'high':
        return 'text-green-600'
      case 'medium':
        return 'text-yellow-600'
      case 'low':
        return 'text-orange-600'
      default:
        return 'text-gray-600'
    }
  }

  const getConfidenceBadge = (confidence) => {
    switch (confidence?.toLowerCase()) {
      case 'high':
        return <span className="px-2 py-1 bg-green-100 text-green-800 rounded text-sm font-medium">High Confidence</span>
      case 'medium':
        return <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-sm font-medium">Medium Confidence</span>
      case 'low':
        return <span className="px-2 py-1 bg-orange-100 text-orange-800 rounded text-sm font-medium">Low Confidence</span>
      default:
        return <span className="px-2 py-1 bg-gray-100 text-gray-800 rounded text-sm font-medium">Unknown</span>
    }
  }

  return (
    <ProjectLayout projectId={projectId} activePath="decision">
      <div className="container mx-auto px-8 py-8 max-w-7xl">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight mb-2">Decision Assistance</h1>
            <p className="text-muted-foreground">AI-powered vendor recommendation with pros, cons, and confidence analysis</p>
          </div>
          <div className="flex gap-2">
            <Button
              onClick={fetchRecommendation}
              variant="outline"
              disabled={loading}
            >
              {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              Refresh
            </Button>
            {recommendation && recommendation.recommended_vendor && (
              <>
                <Button
                  onClick={() => handleExport('markdown')}
                  variant="outline"
                  disabled={exporting}
                >
                  <Download className="mr-2 h-4 w-4" />
                  {exporting ? 'Exporting...' : 'Export Markdown'}
                </Button>
              </>
            )}
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 border border-destructive bg-destructive/10 text-destructive rounded-md text-sm">
            {error}
          </div>
        )}

        {loading ? (
          <Card>
            <CardContent className="py-12">
              <div className="flex flex-col items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-primary mb-4" />
                <p className="text-muted-foreground">Generating recommendation...</p>
              </div>
            </CardContent>
          </Card>
        ) : recommendation && recommendation.recommended_vendor ? (
          <>
            {/* Main Recommendation Card */}
            <Card className="mb-6 border-primary/50">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardDescription>Recommended Vendor</CardDescription>
                    <CardTitle className="text-2xl">{recommendation.recommended_vendor}</CardTitle>
                  </div>
                  {getConfidenceBadge(recommendation.confidence)}
                </div>
              </CardHeader>
              <CardContent>
                <div className="mb-6">
                  <h3 className="text-lg font-semibold mb-2">Reasoning</h3>
                  <p className="text-muted-foreground">{recommendation.reasoning}</p>
                </div>

                <div className="grid md:grid-cols-2 gap-6">
                  {/* Pros */}
                  <div>
                    <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                      <CheckCircle2 className="h-5 w-5 text-green-600" />
                      Advantages
                    </h3>
                    <ul className="space-y-2">
                      {recommendation.pros && recommendation.pros.length > 0 ? (
                        recommendation.pros.map((pro, idx) => (
                          <li key={idx} className="flex items-start gap-2">
                            <CheckCircle2 className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                            <span className="text-sm">{pro}</span>
                          </li>
                        ))
                      ) : (
                        <li className="text-sm text-muted-foreground italic">No advantages listed</li>
                      )}
                    </ul>
                  </div>

                  {/* Cons */}
                  <div>
                    <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                      <AlertCircle className="h-5 w-5 text-orange-600" />
                      Concerns
                    </h3>
                    <ul className="space-y-2">
                      {recommendation.cons && recommendation.cons.length > 0 ? (
                        recommendation.cons.map((con, idx) => (
                          <li key={idx} className="flex items-start gap-2">
                            <XCircle className="h-4 w-4 text-orange-600 mt-0.5 flex-shrink-0" />
                            <span className="text-sm">{con}</span>
                          </li>
                        ))
                      ) : (
                        <li className="text-sm text-muted-foreground italic">No concerns identified</li>
                      )}
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Assumptions */}
            {recommendation.assumptions && recommendation.assumptions.length > 0 && (
              <Card className="mb-6">
                <CardHeader>
                  <CardTitle>Assumptions</CardTitle>
                  <CardDescription>Key assumptions made in this analysis</CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {recommendation.assumptions.map((assumption, idx) => (
                      <li key={idx} className="text-sm flex items-start gap-2">
                        <span className="text-muted-foreground">•</span>
                        <span>{assumption}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}

            {/* Alternatives */}
            {recommendation.alternatives && recommendation.alternatives.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Alternative Options</CardTitle>
                  <CardDescription>Other vendors considered</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {recommendation.alternatives.map((alt, idx) => (
                      <div key={idx} className="p-4 border rounded-lg">
                        <h4 className="font-semibold mb-1">{alt.vendor_name}</h4>
                        <p className="text-sm text-muted-foreground">{alt.comparison}</p>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </>
        ) : recommendation && !recommendation.recommended_vendor ? (
          <Card>
            <CardHeader>
              <CardTitle>No Recommendation Available</CardTitle>
              <CardDescription>{recommendation.reasoning || "Add vendors and upload quotes to generate a recommendation"}</CardDescription>
            </CardHeader>
          </Card>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>Ready to Generate Recommendation</CardTitle>
              <CardDescription>Click "Refresh" to generate an AI-powered vendor recommendation</CardDescription>
            </CardHeader>
          </Card>
        )}
      </div>
    </ProjectLayout>
  )
}

export default DecisionAssistance

