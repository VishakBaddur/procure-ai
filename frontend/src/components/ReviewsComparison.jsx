import React, { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import axios from 'axios'
import { API_BASE } from '@/config'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { AlertTriangle, RefreshCw, Star, ChevronDown, ChevronUp } from 'lucide-react'
import ProjectLayout from './ProjectLayout'

const isSerpAPIUnavailable = (msg) => {
  if (!msg || typeof msg !== 'string') return false
  const s = msg.toLowerCase()
  return /serpapi|connection|research not available|503|key to enable/.test(s)
}

const ReviewsComparison = () => {
  const { projectId } = useParams()
  const [comparison, setComparison] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showRedFlags, setShowRedFlags] = useState({})

  useEffect(() => {
    fetchComparison()
  }, [projectId])

  const fetchComparison = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/projects/${projectId}/reviews/comparison`)
      console.log('Reviews comparison response:', response.data)
      
      if (response.data && response.data.comparison) {
        setComparison(response.data.comparison)
        console.log('Comparison data:', response.data.comparison)
        console.log('Vendors count:', response.data.comparison.vendors?.length || 0)
      } else {
        console.error('Invalid response structure:', response.data)
        setComparison({ vendors: [] })
      }
    } catch (err) {
      console.error('Failed to load reviews comparison:', err)
      setError('Failed to load reviews comparison: ' + (err.response?.data?.detail || err.message))
      setComparison({ vendors: [] })
    }
  }

  const triggerResearch = async (vendorId) => {
    setLoading(true)
    try {
      await axios.post(`${API_BASE}/api/projects/${projectId}/vendors/${vendorId}/research`)
      fetchComparison()
      setError('')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to research vendor')
    } finally {
      setLoading(false)
    }
  }

  const toggleRedFlags = (vendorName) => {
    setShowRedFlags(prevState => ({
      ...prevState,
      [vendorName]: !prevState[vendorName]
    }))
  }

  return (
    <ProjectLayout projectId={projectId} activePath="reviews">
      <div className="container mx-auto px-8 py-8 max-w-7xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight mb-2">Rating & Review Comparison</h1>
          <p className="text-muted-foreground">Vendor reputation and red flags</p>
        </div>

        {error && (
          <div className={`mb-6 p-4 rounded-md text-sm ${isSerpAPIUnavailable(error) ? 'border border-muted-foreground/30 bg-muted/30 text-muted-foreground' : 'border border-destructive bg-destructive/10 text-destructive'}`}>
            {isSerpAPIUnavailable(error) ? 'Vendor research unavailable — add SerpAPI key to enable' : error}
          </div>
        )}

        {comparison && comparison.vendors && comparison.vendors.length > 0 ? (
          <>
            <div className="grid gap-4 md:grid-cols-2 mb-6">
              {comparison.highest_rated && (
                <Card>
                  <CardHeader className="pb-3">
                    <CardDescription>Highest Rated</CardDescription>
                    <CardTitle>{comparison.highest_rated}</CardTitle>
                  </CardHeader>
                </Card>
              )}
              {comparison.most_red_flags && (
                <Card className="border-destructive/50">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <div 
                        className="flex-1 cursor-pointer"
                        onClick={() => comparison.most_red_flags_data && comparison.most_red_flags_data.length > 0 && setShowRedFlags(!showRedFlags)}
                      >
                        <CardDescription className="text-destructive flex items-center gap-2">
                          Most Red Flags
                          {comparison.most_red_flags_data && comparison.most_red_flags_data.length > 0 && (
                            showRedFlags ? (
                              <ChevronUp className="h-4 w-4" />
                            ) : (
                              <ChevronDown className="h-4 w-4" />
                            )
                          )}
                        </CardDescription>
                        <CardTitle>{comparison.most_red_flags}</CardTitle>
                        {comparison.most_red_flags_data && comparison.most_red_flags_data.length > 0 && (
                          <p className="text-xs text-muted-foreground mt-1">
                            {comparison.most_red_flags_data.length} flag{comparison.most_red_flags_data.length !== 1 ? 's' : ''} - Click to view details
                          </p>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                  {showRedFlags && comparison.most_red_flags_data && comparison.most_red_flags_data.length > 0 && (
                    <CardContent className="pt-0">
                      <div className="space-y-2">
                        <p className="text-sm font-medium text-destructive mb-2">Red Flags Details:</p>
                        <ul className="space-y-2">
                          {comparison.most_red_flags_data.map((flag, idx) => (
                            <li key={idx} className="text-sm p-2 border border-destructive/50 bg-destructive/10 rounded">
                              <span className="font-medium">[{flag.severity || 'medium'}]</span> {flag.type || 'Issue'}: {flag.description || flag}
                              {flag.source && (
                                <div className="text-xs text-muted-foreground mt-1">Source: {flag.source}</div>
                              )}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </CardContent>
                  )}
                </Card>
              )}
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Detailed Comparison</CardTitle>
                <CardDescription>Reputation scores and risk analysis</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-6 md:grid-cols-2">
                  {comparison.vendors.map(vendor => (
                    <Card key={vendor.vendor_id}>
                      <CardHeader>
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-lg">{vendor.vendor_name}</CardTitle>
                          <Button
                            onClick={() => triggerResearch(vendor.vendor_id)}
                            variant="outline"
                            size="sm"
                            disabled={loading}
                          >
                            <RefreshCw className="mr-2 h-4 w-4" />
                            Refresh
                          </Button>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div>
                          <p className="text-sm text-muted-foreground">Reputation Score</p>
                          <p className="text-2xl font-bold">{vendor.reputation_score}/100</p>
                        </div>
                        
                        {vendor.research_unavailable ? (
                          <div className="text-sm text-muted-foreground p-3 border border-muted-foreground/20 rounded-lg bg-muted/20">
                            {vendor.research_unavailable_message || 'Vendor research unavailable — add SerpAPI key to enable'}
                          </div>
                        ) : vendor.reviews && vendor.reviews.length > 0 ? (
                          <div>
                            <p className="text-sm text-muted-foreground mb-2">Reviews & Ratings</p>
                            {vendor.reviews.map((review, idx) => (
                              <div key={idx} className="mb-3 p-3 border rounded-lg bg-muted/30">
                                <div className="flex items-center gap-2 mb-2">
                                  <Star className="h-4 w-4 fill-yellow-500 text-yellow-500" />
                                  <span className="font-semibold">{review.source}</span>
                                  {review.rating !== null && review.rating !== undefined ? (
                                    <>
                                      <span className="font-bold text-lg">{review.rating}</span>
                                      <span className="text-muted-foreground">/5</span>
                                    </>
                                  ) : (
                                    <span className="text-muted-foreground text-xs">Rating not available</span>
                                  )}
                                  {review.review_count && (
                                    <span className="text-muted-foreground text-sm">({review.review_count.toLocaleString()} reviews)</span>
                                  )}
                                </div>
                                {review.summary && (
                                  <p className="text-sm text-muted-foreground mb-2">{review.summary}</p>
                                )}
                                {review.recent_reviews && review.recent_reviews.length > 0 && (
                                  <div className="mt-2 space-y-2">
                                    <p className="text-xs font-medium text-muted-foreground">Recent Reviews:</p>
                                    {review.recent_reviews.slice(0, 3).map((rev, revIdx) => (
                                      <div key={revIdx} className="text-xs p-2 bg-background rounded border-l-2 border-primary">
                                        <p className="italic">"{rev}"</p>
                                      </div>
                                    ))}
                                  </div>
                                )}
                                {review.url && (
                                  <a 
                                    href={review.url} 
                                    target="_blank" 
                                    rel="noopener noreferrer"
                                    className="text-xs text-primary hover:underline mt-2 inline-block"
                                  >
                                    View on {review.source} →
                                  </a>
                                )}
                              </div>
                            ))}
                          </div>
                        ) : !vendor.research_unavailable && vendor.reputation_score === 0 && vendor.reviews.length === 0 ? (
                          <div className="text-sm text-muted-foreground italic p-3 border rounded-lg bg-muted/20">
                            Research not started yet. Click "Refresh" to search for reviews and ratings.
                          </div>
                        ) : (
                          <div className="text-sm text-muted-foreground italic p-3 border rounded-lg bg-muted/20">
                            No reviews found. Click "Refresh" to search again.
                          </div>
                        )}

                        {vendor.red_flags && vendor.red_flags.length > 0 ? (
                          <div className="space-y-2">
                            <div 
                              className="flex items-center gap-2 cursor-pointer" 
                              onClick={() => toggleRedFlags(vendor.vendor_name)}
                            >
                              <AlertTriangle className="h-4 w-4 text-destructive" />
                              <p className="text-sm text-muted-foreground">
                                Red Flags ({vendor.red_flags.length} flags)
                              </p>
                              {showRedFlags[vendor.vendor_name] ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                            </div>
                            {showRedFlags[vendor.vendor_name] && (
                              <ul className="space-y-2">
                                {vendor.red_flags.map((flag, idx) => (
                                  <li key={idx} className="text-sm p-2 border border-destructive/50 bg-destructive/10 rounded">
                                    <span className="font-medium">[{flag.severity || 'medium'}]</span> {flag.type || 'Issue'}: {flag.description || flag}
                                    {flag.source && (
                                      <div className="text-xs text-muted-foreground mt-1">Source: {flag.source}</div>
                                    )}
                                    {flag.review_snippets && flag.review_snippets.length > 0 && (
                                      <div className="text-xs text-muted-foreground mt-1">
                                        <p className="font-medium">Relevant review:</p>
                                        <p className="italic">"{flag.review_snippets[0]}"</p>
                                      </div>
                                    )}
                                  </li>
                                ))}
                              </ul>
                            )}
                          </div>
                        ) : vendor.reviews && vendor.reviews.length > 0 && vendor.reputation_score > 0 ? (
                          <div className="text-sm text-muted-foreground italic p-3 border rounded-lg bg-green-50 border-green-200">
                            <div className="flex items-center gap-2">
                              <span className="text-green-600">✓</span>
                              <span>No red flags detected in customer reviews</span>
                            </div>
                          </div>
                        ) : null}

                        {vendor.recommendations && vendor.recommendations.length > 0 && (
                          <div>
                            <p className="text-sm text-muted-foreground mb-2">Recommendations</p>
                            <ul className="space-y-1">
                              {vendor.recommendations.map((rec, idx) => (
                                <li key={idx} className="text-sm">{rec}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </CardContent>
            </Card>
          </>
        ) : comparison && comparison.vendors && comparison.vendors.length === 0 ? (
          <Card>
            <CardHeader>
              <CardTitle>No Vendors Yet</CardTitle>
              <CardDescription>
                Add vendors to your project first. Vendor research will be automatically triggered when you add vendors.
              </CardDescription>
            </CardHeader>
          </Card>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>No Reviews Yet</CardTitle>
              <CardDescription>
                Vendor research is automatically triggered when you add vendors or upload quotations. 
                If you don't see reviews, try clicking "Refresh" on individual vendors to start research.
              </CardDescription>
            </CardHeader>
            {error && (
              <CardContent>
                <p className={`text-sm ${isSerpAPIUnavailable(error) ? 'text-muted-foreground' : 'text-destructive'}`}>
                  {isSerpAPIUnavailable(error) ? 'Vendor research unavailable — add SerpAPI key to enable' : error}
                </p>
              </CardContent>
            )}
          </Card>
        )}
      </div>
    </ProjectLayout>
  )
}

export default ReviewsComparison
