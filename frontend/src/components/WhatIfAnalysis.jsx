import React, { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import axios from 'axios'
import { API_BASE } from '@/config'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Calculator, TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react'
import ProjectLayout from './ProjectLayout'

const WhatIfAnalysis = () => {
  const { projectId } = useParams()
  const [vendors, setVendors] = useState([])
  const [selectedVendor, setSelectedVendor] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  
  // Input states
  const [quantity, setQuantity] = useState('')
  const [paymentTerms, setPaymentTerms] = useState('')
  const [contractYears, setContractYears] = useState('5')

  useEffect(() => {
    fetchVendors()
  }, [projectId])

  const fetchVendors = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/projects/${projectId}/vendors`)
      if (response.data && response.data.vendors) {
        setVendors(response.data.vendors)
        if (response.data.vendors.length > 0 && !selectedVendor) {
          setSelectedVendor(response.data.vendors[0].id)
        }
      }
    } catch (err) {
      console.error('Failed to load vendors:', err)
      setError('Failed to load vendors: ' + (err.response?.data?.detail || err.message))
    }
  }

  const runAnalysis = async () => {
    if (!selectedVendor) {
      setError('Please select a vendor')
      return
    }

    setLoading(true)
    setError('')
    try {
      const response = await axios.post(
        `${API_BASE}/api/projects/${projectId}/what-if`,
        {
          vendor_id: selectedVendor,
          quantity: quantity ? parseFloat(quantity) : null,
          payment_terms: paymentTerms || null,
          contract_years: contractYears ? parseInt(contractYears) : null
        }
      )
      
      if (response.data && response.data.analysis) {
        setAnalysis(response.data.analysis)
      }
    } catch (err) {
      console.error('What-if analysis failed:', err)
      setError('Analysis failed: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }

  const resetAnalysis = () => {
    setQuantity('')
    setPaymentTerms('')
    setContractYears('5')
    setAnalysis(null)
  }

  const selectedVendorName = vendors.find(v => v.id === selectedVendor)?.vendor_name || ''

  return (
    <ProjectLayout projectId={projectId} activePath="what-if">
      <div className="container mx-auto px-8 py-8 max-w-7xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight mb-2">What-If Analysis</h1>
          <p className="text-muted-foreground">Recalculate costs, TCO, and risk with modified parameters</p>
        </div>

        {error && (
          <div className="mb-6 p-4 border border-destructive bg-destructive/10 text-destructive rounded-md text-sm">
            {error}
          </div>
        )}

        <div className="grid md:grid-cols-2 gap-6">
          {/* Input Panel */}
          <Card>
            <CardHeader>
              <CardTitle>Modify Parameters</CardTitle>
              <CardDescription>Adjust quantities, payment terms, or contract length</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="vendor-select">Vendor</Label>
                <select
                  id="vendor-select"
                  className="w-full mt-1 px-3 py-2 border rounded-md"
                  value={selectedVendor || ''}
                  onChange={(e) => setSelectedVendor(parseInt(e.target.value))}
                >
                  <option value="">Select a vendor...</option>
                  {vendors.map(vendor => (
                    <option key={vendor.id} value={vendor.id}>
                      {vendor.vendor_name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <Label htmlFor="quantity">Quantity</Label>
                <Input
                  id="quantity"
                  type="number"
                  placeholder="Enter new quantity"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                />
                <p className="text-xs text-muted-foreground mt-1">Leave empty to keep original</p>
              </div>

              <div>
                <Label htmlFor="payment-terms">Payment Terms</Label>
                <Input
                  id="payment-terms"
                  type="text"
                  placeholder="e.g., Net 30, Full Advance"
                  value={paymentTerms}
                  onChange={(e) => setPaymentTerms(e.target.value)}
                />
                <p className="text-xs text-muted-foreground mt-1">Leave empty to keep original</p>
              </div>

              <div>
                <Label htmlFor="contract-years">Contract Length (Years)</Label>
                <Input
                  id="contract-years"
                  type="number"
                  placeholder="5"
                  value={contractYears}
                  onChange={(e) => setContractYears(e.target.value)}
                  min="1"
                  max="20"
                />
                <p className="text-xs text-muted-foreground mt-1">Default: 5 years</p>
              </div>

              <div className="flex gap-2 pt-4">
                <Button
                  onClick={runAnalysis}
                  disabled={loading || !selectedVendor}
                  className="flex-1"
                >
                  <Calculator className="mr-2 h-4 w-4" />
                  {loading ? 'Calculating...' : 'Calculate'}
                </Button>
                <Button
                  onClick={resetAnalysis}
                  variant="outline"
                  disabled={loading}
                >
                  Reset
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Results Panel */}
          <Card>
            <CardHeader>
              <CardTitle>Analysis Results</CardTitle>
              <CardDescription>
                {selectedVendorName ? `For ${selectedVendorName}` : 'Select a vendor to see results'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {analysis ? (
                <div className="space-y-6">
                  {/* Price Comparison */}
                  <div>
                    <h3 className="text-lg font-semibold mb-3">Price Impact</h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-3 border rounded-lg">
                        <p className="text-xs text-muted-foreground mb-1">Original Price</p>
                        <p className="text-xl font-bold">${analysis.original_price?.toLocaleString() || 'N/A'}</p>
                      </div>
                      <div className={`p-3 border rounded-lg ${analysis.price_change >= 0 ? 'bg-red-50 border-red-200' : 'bg-green-50 border-green-200'}`}>
                        <p className="text-xs text-muted-foreground mb-1">New Price</p>
                        <p className="text-xl font-bold">${analysis.new_price?.toLocaleString() || 'N/A'}</p>
                      </div>
                    </div>
                    {analysis.price_change !== 0 && (
                      <div className={`mt-3 flex items-center gap-2 ${analysis.price_change >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                        {analysis.price_change >= 0 ? (
                          <TrendingUp className="h-4 w-4" />
                        ) : (
                          <TrendingDown className="h-4 w-4" />
                        )}
                        <span className="text-sm font-medium">
                          {analysis.price_change >= 0 ? '+' : ''}${Math.abs(analysis.price_change).toLocaleString()} 
                          ({analysis.price_change_percent >= 0 ? '+' : ''}{analysis.price_change_percent.toFixed(2)}%)
                        </span>
                      </div>
                    )}
                  </div>

                  {/* TCO Breakdown */}
                  {analysis.tco && Object.keys(analysis.tco).length > 0 && (
                    <div>
                      <h3 className="text-lg font-semibold mb-3">Total Cost of Ownership</h3>
                      <div className="space-y-2">
                        <div className="flex justify-between p-2 bg-muted rounded">
                          <span className="text-sm">Total TCO ({analysis.contract_years || 5} years)</span>
                          <span className="font-bold">${analysis.tco.total_tco?.toLocaleString() || 'N/A'}</span>
                        </div>
                        <div className="flex justify-between p-2 border rounded text-sm">
                          <span>Annual Cost</span>
                          <span>${analysis.tco.annual_cost?.toLocaleString() || 'N/A'}</span>
                        </div>
                        {analysis.tco.capex && (
                          <div className="pl-4 border-l-2">
                            <p className="text-xs font-medium text-muted-foreground mb-1">CAPEX</p>
                            <div className="text-xs space-y-1">
                              <div className="flex justify-between">
                                <span>Initial Cost</span>
                                <span>${analysis.tco.capex.initial_cost?.toLocaleString() || 'N/A'}</span>
                              </div>
                              <div className="flex justify-between">
                                <span>Training</span>
                                <span>${analysis.tco.capex.training_cost?.toLocaleString() || 'N/A'}</span>
                              </div>
                              {analysis.tco.capex.replacement_cost > 0 && (
                                <div className="flex justify-between">
                                  <span>Replacement</span>
                                  <span>${analysis.tco.capex.replacement_cost?.toLocaleString() || 'N/A'}</span>
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                        {analysis.tco.opex && (
                          <div className="pl-4 border-l-2">
                            <p className="text-xs font-medium text-muted-foreground mb-1">OPEX</p>
                            <div className="text-xs space-y-1">
                              <div className="flex justify-between">
                                <span>Support</span>
                                <span>${analysis.tco.opex.support_cost?.toLocaleString() || 'N/A'}</span>
                              </div>
                              <div className="flex justify-between">
                                <span>Maintenance</span>
                                <span>${analysis.tco.opex.maintenance_cost?.toLocaleString() || 'N/A'}</span>
                              </div>
                              <div className="flex justify-between">
                                <span>Repairs</span>
                                <span>${analysis.tco.opex.repair_cost?.toLocaleString() || 'N/A'}</span>
                              </div>
                              <div className="flex justify-between">
                                <span>Downtime</span>
                                <span>${analysis.tco.opex.downtime_cost?.toLocaleString() || 'N/A'}</span>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Risk Score */}
                  <div>
                    <h3 className="text-lg font-semibold mb-3">Risk Assessment</h3>
                    <div className="grid grid-cols-3 gap-3">
                      <div className="p-3 border rounded-lg text-center">
                        <p className="text-xs text-muted-foreground mb-1">Risk Score</p>
                        <p className={`text-xl font-bold ${analysis.risk_score >= 70 ? 'text-red-600' : analysis.risk_score >= 40 ? 'text-yellow-600' : 'text-green-600'}`}>
                          {analysis.risk_score?.toFixed(1) || 'N/A'}
                        </p>
                        <p className="text-xs text-muted-foreground">/100</p>
                      </div>
                      <div className="p-3 border rounded-lg text-center">
                        <p className="text-xs text-muted-foreground mb-1">Reputation</p>
                        <p className="text-xl font-bold">{analysis.reputation_score?.toFixed(1) || 'N/A'}</p>
                        <p className="text-xs text-muted-foreground">/100</p>
                      </div>
                      <div className="p-3 border rounded-lg text-center">
                        <p className="text-xs text-muted-foreground mb-1">Red Flags</p>
                        <p className={`text-xl font-bold ${analysis.red_flags_count > 0 ? 'text-red-600' : 'text-green-600'}`}>
                          {analysis.red_flags_count || 0}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Parameters Used */}
                  <div>
                    <h3 className="text-lg font-semibold mb-3">Parameters</h3>
                    <div className="space-y-2 text-sm">
                      {analysis.quantity && (
                        <div className="flex justify-between p-2 bg-muted rounded">
                          <span>Quantity</span>
                          <span className="font-medium">{analysis.quantity}</span>
                        </div>
                      )}
                      {analysis.payment_terms && (
                        <div className="flex justify-between p-2 bg-muted rounded">
                          <span>Payment Terms</span>
                          <span className="font-medium">{analysis.payment_terms}</span>
                        </div>
                      )}
                      <div className="flex justify-between p-2 bg-muted rounded">
                        <span>Contract Length</span>
                        <span className="font-medium">{analysis.contract_years || 5} years</span>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12">
                  <Calculator className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">
                    Enter parameters and click "Calculate" to see analysis results
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </ProjectLayout>
  )
}

export default WhatIfAnalysis

