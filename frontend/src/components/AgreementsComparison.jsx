import React, { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import axios from 'axios'
import { API_BASE } from '@/config'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Textarea } from './ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog'
import { Upload, AlertTriangle } from 'lucide-react'
import { cn } from '@/lib/utils'
import ProjectLayout from './ProjectLayout'

const AgreementsComparison = () => {
  const { projectId } = useParams()
  const [vendors, setVendors] = useState([])
  const [comparison, setComparison] = useState(null)
  const [selectedVendor, setSelectedVendor] = useState(null)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [uploadText, setUploadText] = useState('')
  const [uploadFile, setUploadFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    fetchVendors()
    fetchComparison()
  }, [projectId])

  const fetchVendors = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/projects/${projectId}/vendors`)
      setVendors(response.data.vendors || [])
    } catch (err) {
      setError('Failed to load vendors')
    }
  }

  const fetchComparison = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/projects/${projectId}/agreements/comparison`)
      setComparison(response.data.comparison)
    } catch (err) {
      console.error('Failed to load comparison:', err)
    }
  }

  const handleUploadAgreement = async () => {
    if (!selectedVendor) return
    if (!uploadFile && !uploadText.trim()) {
      setError('Please upload a file or enter text')
      return
    }

    setLoading(true)
    setError('')
    setSuccess('')

    try {
      const formData = new FormData()
      if (uploadFile) {
        formData.append('file', uploadFile)
      }
      if (uploadText) {
        formData.append('text_content', uploadText)
      }

      await axios.post(
        `${API_BASE}/api/projects/${projectId}/vendors/${selectedVendor.id}/agreements`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' }
        }
      )

      setUploadFile(null)
      setUploadText('')
      setShowUploadModal(false)
      setSelectedVendor(null)
      fetchComparison()
      setSuccess('Agreement uploaded and analyzed successfully')
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to upload agreement')
    } finally {
      setLoading(false)
    }
  }

  return (
    <ProjectLayout projectId={projectId} activePath="agreements">
      <div className="container mx-auto px-8 py-8 max-w-7xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight mb-2">Agreements Comparison</h1>
          <p className="text-muted-foreground">Analyze and compare vendor agreements</p>
        </div>

        {error && (
          <div className="mb-6 p-4 border border-destructive bg-destructive/10 text-destructive rounded-md text-sm">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-6 p-4 border border-foreground/20 bg-muted rounded-md text-sm">
            {success}
          </div>
        )}

        {/* Vendors List */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Vendors</CardTitle>
            <CardDescription>Upload agreements for vendors listed below</CardDescription>
          </CardHeader>
          <CardContent>
            {vendors.length === 0 ? (
              <p className="text-sm text-muted-foreground">No vendors yet. Add vendors in Quotations section first.</p>
            ) : (
              <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                {vendors.map(vendor => (
                  <div key={vendor.id} className="border rounded-lg p-4">
                    <h3 className="font-semibold mb-3">{vendor.vendor_name}</h3>
                    <Button
                      onClick={() => {
                        setSelectedVendor(vendor)
                        setShowUploadModal(true)
                      }}
                      variant="outline"
                      className="w-full"
                      size="sm"
                    >
                      <Upload className="mr-2 h-4 w-4" />
                      Upload Agreement
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Comparison */}
        {comparison && comparison.vendors.length > 0 ? (
          <>
            <div className="grid gap-4 md:grid-cols-2 mb-6">
              {comparison.best_score && (
                <Card>
                  <CardHeader className="pb-3">
                    <CardDescription>Best Overall Score</CardDescription>
                    <CardTitle>{comparison.best_score}</CardTitle>
                  </CardHeader>
                </Card>
              )}
              {comparison.lowest_risk && (
                <Card>
                  <CardHeader className="pb-3">
                    <CardDescription>Lowest Risk</CardDescription>
                    <CardTitle>{comparison.lowest_risk}</CardTitle>
                  </CardHeader>
                </Card>
              )}
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Detailed Comparison</CardTitle>
                <CardDescription>Risk analysis and key clauses</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid gap-6 md:grid-cols-2">
                  {comparison.vendors.map(vendor => (
                    <Card key={vendor.vendor_id}>
                      <CardHeader>
                        <CardTitle className="text-lg">{vendor.vendor_name}</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div>
                          <p className="text-sm text-muted-foreground">Overall Score</p>
                          <p className="text-2xl font-bold">{vendor.overall_score}/100</p>
                        </div>
                        <div>
                          <p className="text-sm text-muted-foreground">Risk Score</p>
                          <p className="text-lg font-semibold">{vendor.risk_score}</p>
                        </div>
                        
                        {vendor.key_clauses && vendor.key_clauses.length > 0 && (
                          <div>
                            <p className="text-sm text-muted-foreground mb-2">Key Clauses</p>
                            <ul className="space-y-1">
                              {vendor.key_clauses.map((clause, idx) => (
                                <li key={idx} className="text-sm">{clause}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {vendor.risk_factors && vendor.risk_factors.length > 0 && (
                          <div>
                            <p className="text-sm text-muted-foreground mb-2 flex items-center gap-2">
                              <AlertTriangle className="h-4 w-4" />
                              Risk Factors
                            </p>
                            <ul className="space-y-2">
                              {vendor.risk_factors.map((risk, idx) => (
                                <li key={idx} className={cn(
                                  "text-sm p-2 rounded border",
                                  risk.level === 'high' || risk.level === 'critical' 
                                    ? "border-destructive/50 bg-destructive/10 text-destructive"
                                    : "border-muted"
                                )}>
                                  <span className="font-medium">[{risk.level}]</span> {risk.description}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

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
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>No Agreements Yet</CardTitle>
              <CardDescription>Upload agreements for vendors to see comparison.</CardDescription>
            </CardHeader>
          </Card>
        )}

        {/* Upload Dialog */}
        <Dialog open={showUploadModal} onOpenChange={setShowUploadModal}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Upload Agreement for {selectedVendor?.vendor_name}</DialogTitle>
              <DialogDescription>Upload a document or paste agreement text</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="file-upload">Upload Document</Label>
                <Input
                  id="file-upload"
                  type="file"
                  accept=".pdf,.doc,.docx,.txt"
                  onChange={(e) => setUploadFile(e.target.files[0])}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="text-content">Or Enter Agreement Text</Label>
                <Textarea
                  id="text-content"
                  rows="10"
                  value={uploadText}
                  onChange={(e) => setUploadText(e.target.value)}
                  placeholder="Paste agreement text here..."
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => {
                setShowUploadModal(false)
                setSelectedVendor(null)
                setUploadFile(null)
                setUploadText('')
              }}>
                Cancel
              </Button>
              <Button onClick={handleUploadAgreement} disabled={loading}>
                {loading ? 'Analyzing...' : 'Upload & Analyze'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </ProjectLayout>
  )
}

export default AgreementsComparison
