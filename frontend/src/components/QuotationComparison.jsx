import React, { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import axios from 'axios'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Label } from './ui/label'
import { Textarea } from './ui/textarea'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from './ui/table'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog'
import { Plus, Upload, Trash2, ChevronDown, ChevronUp } from 'lucide-react'
import { cn } from '@/lib/utils'
import { API_BASE } from '@/config'
import ProjectLayout from './ProjectLayout'

const QuotationComparison = () => {
  const { projectId } = useParams()
  const [vendors, setVendors] = useState([])
  const [comparison, setComparison] = useState(null)
  const [showAddVendor, setShowAddVendor] = useState(false)
  const [newVendorName, setNewVendorName] = useState('')
  const [selectedVendor, setSelectedVendor] = useState(null)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [uploadText, setUploadText] = useState('')
  const [uploadFile, setUploadFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [expandedProducts, setExpandedProducts] = useState({})
  const [selectedPaymentTerm, setSelectedPaymentTerm] = useState('all')
  const [selectedQuantity, setSelectedQuantity] = useState(null)

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
      const response = await axios.get(`${API_BASE}/api/projects/${projectId}/quotations/comparison`)
      if (response.data && response.data.comparison) {
        setComparison(response.data.comparison)
      } else {
        setComparison(null)
      }
    } catch (err) {
      setComparison(null)
    }
  }

  const toggleProductExpansion = (vendorId, productId) => {
    const key = `${vendorId}_${productId}`
    setExpandedProducts(prev => ({
      ...prev,
      [key]: !prev[key]
    }))
  }

  const handleAddVendor = async () => {
    if (!newVendorName.trim()) {
      setError('Please enter vendor name')
      return
    }

    setError('')
    try {
      const formData = new FormData()
      formData.append('vendor_name', newVendorName)
      
      await axios.post(`${API_BASE}/api/projects/${projectId}/vendors`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 30000,
      })
      setNewVendorName('')
      setShowAddVendor(false)
      setSuccess('Vendor added successfully')
      setTimeout(() => setSuccess(''), 4000)
      setTimeout(() => { fetchVendors(); fetchComparison(); }, 400)
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Failed to add vendor'
      setError(msg)
    }
  }

  const handleDeleteVendor = async (vendorId) => {
    if (!window.confirm('Are you sure you want to delete this vendor?')) return

    try {
      await axios.delete(`${API_BASE}/api/projects/${projectId}/vendors/${vendorId}`)
      fetchVendors()
      fetchComparison()
      setSuccess('Vendor deleted successfully')
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete vendor')
    }
  }

  const handleUploadQuotation = async () => {
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

      const res = await axios.post(
        `${API_BASE}/api/projects/${projectId}/vendors/${selectedVendor.id}/quotations`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
          timeout: 60000, // 60s so upload + quick response don't hit default timeout
        }
      )

      setUploadFile(null)
      setUploadText('')
      setShowUploadModal(false)
      setSelectedVendor(null)
      setSuccess(res.data?.message || 'Quotation uploaded. Refresh in a few seconds to see extracted pricing.')
      setTimeout(() => setSuccess(''), 6000)
      setTimeout(() => fetchComparison(), 800)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to upload quotation')
    } finally {
      setLoading(false)
    }
  }

  const openUploadModal = (vendor) => {
    setSelectedVendor(vendor)
    setShowUploadModal(true)
  }

  const renderProductPricing = (product, vendorId) => {
    const pricingMatrix = product.pricing_matrix || []
    const isExpanded = expandedProducts[`${vendorId}_${product.product_id}`]
    
    if (pricingMatrix.length === 0) {
      return <span className="text-muted-foreground text-sm">No pricing data</span>
    }

    if (pricingMatrix.length === 1) {
      const price = pricingMatrix[0]
      return (
        <div className="text-sm">
          <div className="font-semibold">{price.currency} {price.unit_price?.toFixed(2)}/{price.quantity_unit}</div>
          {price.payment_terms && price.payment_terms !== 'Standard' && (
            <div className="text-xs text-muted-foreground">Payment: {price.payment_terms}</div>
          )}
          {price.quantity_min && (
            <div className="text-xs text-muted-foreground">
              Qty: {price.quantity_min}{price.quantity_max ? `-${price.quantity_max}` : '+'}
            </div>
          )}
        </div>
      )
    }

    // Multiple pricing options
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold">
            {pricingMatrix.length} pricing option{pricingMatrix.length > 1 ? 's' : ''}
          </span>
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0"
            onClick={() => toggleProductExpansion(vendorId, product.product_id)}
          >
            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
        </div>
        
        {isExpanded && (
          <div className="mt-2 space-y-2 border-t pt-2">
            {pricingMatrix.map((price, idx) => (
              <div key={idx} className="text-xs space-y-1 p-2 border rounded">
                <div className="flex justify-between">
                  <span className="font-medium">{price.currency} {price.unit_price?.toFixed(2)}/{price.quantity_unit}</span>
                  {price.total_price && (
                    <span className="text-muted-foreground">Total: {price.currency} {price.total_price?.toFixed(2)}</span>
                  )}
                </div>
                <div className="flex gap-3 text-muted-foreground">
                  {price.quantity_min && (
                    <span>Qty: {price.quantity_min}{price.quantity_max ? `-${price.quantity_max}` : '+'}</span>
                  )}
                  {price.payment_terms && (
                    <span>Payment: {price.payment_terms}</span>
                  )}
                </div>
                {price.notes && (
                  <div className="text-muted-foreground italic">{price.notes}</div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  return (
    <ProjectLayout projectId={projectId} activePath="quotations">
      <div className="container mx-auto px-8 py-8 max-w-7xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight mb-2">Quotation Comparison</h1>
          <p className="text-muted-foreground">Compare vendor quotations with detailed product breakdown</p>
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

        {/* Vendors Management */}
        <div className="mb-8">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Vendors</CardTitle>
                  <CardDescription>Manage vendors and upload quotations</CardDescription>
                </div>
                <Button onClick={() => setShowAddVendor(true)} size="sm">
                  <Plus className="mr-2 h-4 w-4" />
                  Add Vendor
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {vendors.length === 0 ? (
                <p className="text-sm text-muted-foreground">No vendors yet. Add your first vendor.</p>
              ) : (
                <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                  {vendors.map(vendor => (
                    <div key={vendor.id} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between mb-3">
                        <h3 className="font-semibold">{vendor.vendor_name}</h3>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDeleteVendor(vendor.id)}
                          className="h-8 w-8"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                      <Button
                        onClick={() => openUploadModal(vendor)}
                        variant="outline"
                        className="w-full"
                        size="sm"
                      >
                        <Upload className="mr-2 h-4 w-4" />
                        Upload Quote
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Detailed Comparison Table */}
        {comparison && comparison.vendors && comparison.vendors.length > 0 ? (
          <>
            {/* Summary Cards */}
            <div className="grid gap-4 md:grid-cols-3 mb-6">
              {comparison.cheapest && (
                <Card>
                  <CardHeader className="pb-3">
                    <CardDescription>Cheapest Vendor</CardDescription>
                    <CardTitle>{comparison.cheapest}</CardTitle>
                  </CardHeader>
                </Card>
              )}
              {comparison.most_items && (
                <Card>
                  <CardHeader className="pb-3">
                    <CardDescription>Most Products</CardDescription>
                    <CardTitle>{comparison.most_items}</CardTitle>
                  </CardHeader>
                </Card>
              )}
              <Card>
                <CardHeader className="pb-3">
                  <CardDescription>Total Vendors</CardDescription>
                  <CardTitle>{comparison.vendors.length}</CardTitle>
                </CardHeader>
              </Card>
            </div>

            {/* Individual Vendor Details */}
            <div className="space-y-6">
              {comparison.vendors.map(vendor => {
                const products = vendor.products || []
                return (
                  <Card key={vendor.vendor_id} className="border-2">
                    <CardHeader className="border-b">
                      <div className="flex items-center justify-between">
                        <div>
                          <CardTitle className="text-2xl mb-2">{vendor.vendor_name}</CardTitle>
                          <CardDescription>
                            Total: {vendor.currency} {vendor.total_price?.toFixed(2)} • {vendor.product_count || vendor.item_count || 0} product{(vendor.product_count || vendor.item_count || 0) !== 1 ? 's' : ''}
                          </CardDescription>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="pt-6">
                      <div className="space-y-6">
                        {/* Products Section */}
                        <div>
                          <h3 className="text-lg font-semibold mb-4">Products Offered</h3>
                          {products.length > 0 ? (
                            <div className="space-y-4">
                              {products.map((product, idx) => (
                                <div key={idx} className="border rounded-lg p-4">
                                  <div className="mb-3">
                                    <h4 className="font-semibold text-base mb-1">
                                      Product {idx + 1}: {product.name}
                                    </h4>
                                    {product.description && (
                                      <p className="text-sm text-muted-foreground">{product.description}</p>
                                    )}
                                  </div>
                                  
                                  {/* Pricing Options */}
                                  <div className="mt-3">
                                    <p className="text-sm font-medium mb-2">Pricing Options:</p>
                                    {product.pricing_matrix && product.pricing_matrix.length > 0 ? (
                                      <div className="space-y-2">
                                        {product.pricing_matrix.map((price, priceIdx) => (
                                          <div key={priceIdx} className="bg-muted/50 rounded p-3 border">
                                            <div className="flex items-center justify-between mb-2">
                                              <span className="font-semibold">
                                                {price.currency && price.currency !== 'Not specified' ? price.currency : 'USD'} {price.unit_price?.toFixed(2) || '0.00'}/{price.quantity_unit || 'unit'}
                                              </span>
                                              {price.total_price && (
                                                <span className="text-sm text-muted-foreground">
                                                  Total: {price.currency || 'USD'} {price.total_price?.toFixed(2)}
                                                </span>
                                              )}
                                            </div>
                                            <div className="flex gap-4 text-sm text-muted-foreground">
                                              {price.quantity_min && (
                                                <span>
                                                  Quantity: {price.quantity_min}
                                                  {price.quantity_max ? ` - ${price.quantity_max}` : '+'}
                                                </span>
                                              )}
                                              {price.payment_terms && price.payment_terms !== 'Not specified' && (
                                                <span>Payment: {price.payment_terms}</span>
                                              )}
                                            </div>
                                            {price.notes && price.notes !== 'Not specified' && (
                                              <div className="text-xs text-muted-foreground mt-2 italic">
                                                {price.notes}
                                              </div>
                                            )}
                                          </div>
                                        ))}
                                      </div>
                                    ) : (
                                      <p className="text-sm text-muted-foreground italic">Not specified</p>
                                    )}
                                  </div>

                                  {/* Product-specific warranty */}
                                  <div className="mt-3 pt-3 border-t">
                                    <p className="text-sm font-medium mb-1">Warranty:</p>
                                    {product.warranty && product.warranty !== 'Not specified' ? (
                                      <p className="text-sm">{product.warranty}</p>
                                    ) : (
                                      <p className="text-sm text-muted-foreground italic">Not specified</p>
                                    )}
                                  </div>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p className="text-sm text-muted-foreground">No products listed</p>
                          )}
                        </div>

                        {/* Warranties Section */}
                        <div className="border-t pt-6">
                          <h3 className="text-lg font-semibold mb-4">Warranty Options</h3>
                          {vendor.warranties && vendor.warranties.length > 0 && vendor.warranties[0] !== 'Not specified' ? (
                            <div className="space-y-2">
                              {vendor.warranties.map((warranty, idx) => (
                                warranty !== 'Not specified' && (
                                  <div key={idx} className="border rounded p-3 bg-muted/30">
                                    <p className="text-sm">{warranty}</p>
                                  </div>
                                )
                              ))}
                            </div>
                          ) : (
                            <p className="text-sm text-muted-foreground italic">Not specified</p>
                          )}
                        </div>

                        {/* Payment Terms / Cost Options */}
                        <div className="border-t pt-6">
                          <h3 className="text-lg font-semibold mb-4">Payment Terms / Cost Options</h3>
                          {vendor.payment_terms_available && vendor.payment_terms_available.length > 0 && vendor.payment_terms_available[0] !== 'Not specified' ? (
                            <div className="flex flex-wrap gap-2">
                              {vendor.payment_terms_available.map((term, idx) => (
                                term !== 'Not specified' && (
                                  <span key={idx} className="px-3 py-2 border rounded-md bg-background text-sm font-medium">
                                    {term}
                                  </span>
                                )
                              ))}
                            </div>
                          ) : (
                            <p className="text-sm text-muted-foreground italic">Not specified</p>
                          )}
                        </div>

                        {/* Additional Info */}
                        <div className="border-t pt-6">
                          <h3 className="text-lg font-semibold mb-4">Additional Information</h3>
                          <div className="grid grid-cols-2 gap-4 text-sm mb-4">
                            <div>
                              <span className="text-muted-foreground">Currency:</span>
                              <span className="ml-2 font-medium">{vendor.currency || 'USD'}</span>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Total Items:</span>
                              <span className="ml-2 font-medium">{vendor.item_count || vendor.product_count || 0}</span>
                            </div>
                          </div>
                          {vendor.other_info && (
                            <div className="space-y-3 mt-4">
                              {vendor.other_info.delivery_terms && vendor.other_info.delivery_terms !== 'Not specified' && (
                                <div className="border rounded p-3 bg-muted/30">
                                  <span className="text-sm font-medium">Delivery Terms: </span>
                                  <span className="text-sm">{vendor.other_info.delivery_terms}</span>
                                </div>
                              )}
                              {vendor.other_info.return_policy && vendor.other_info.return_policy !== 'Not specified' && (
                                <div className="border rounded p-3 bg-muted/30">
                                  <span className="text-sm font-medium">Return Policy: </span>
                                  <span className="text-sm">{vendor.other_info.return_policy}</span>
                                </div>
                              )}
                              {vendor.other_info.support_services && vendor.other_info.support_services !== 'Not specified' && (
                                <div className="border rounded p-3 bg-muted/30">
                                  <span className="text-sm font-medium">Support Services: </span>
                                  <span className="text-sm">{vendor.other_info.support_services}</span>
                                </div>
                              )}
                              {vendor.other_info.additional_notes && vendor.other_info.additional_notes !== 'Not specified' && (
                                <div className="border rounded p-3 bg-muted/30">
                                  <span className="text-sm font-medium">Additional Notes: </span>
                                  <span className="text-sm">{vendor.other_info.additional_notes}</span>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>

          </>
        ) : comparison && comparison.vendors && comparison.vendors.length === 0 ? (
          <Card>
            <CardHeader>
              <CardTitle>No Quotations Yet</CardTitle>
              <CardDescription>Add vendors and upload their quotations to see comparison.</CardDescription>
            </CardHeader>
          </Card>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>Loading Comparison...</CardTitle>
              <CardDescription>Processing quotation data...</CardDescription>
            </CardHeader>
          </Card>
        )}

        {/* Add Vendor Dialog */}
        <Dialog open={showAddVendor} onOpenChange={setShowAddVendor}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Vendor</DialogTitle>
              <DialogDescription>Enter the vendor name to add to this project.</DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="vendor-name">Vendor Name</Label>
                <Input
                  id="vendor-name"
                  value={newVendorName}
                  onChange={(e) => setNewVendorName(e.target.value)}
                  placeholder="Enter vendor name"
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowAddVendor(false)}>
                Cancel
              </Button>
              <Button onClick={handleAddVendor}>Add</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Upload Quotation Dialog */}
        <Dialog open={showUploadModal} onOpenChange={setShowUploadModal}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>
                Upload Quotation for {selectedVendor?.vendor_name}
              </DialogTitle>
              <DialogDescription>
                Upload a document or paste quotation text. The AI will extract products, pricing tiers, and payment terms.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="file-upload">Upload Document</Label>
                <Input
                  id="file-upload"
                  type="file"
                  accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg"
                  onChange={(e) => setUploadFile(e.target.files[0])}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="text-content">Or Enter Quotation Text</Label>
                <Textarea
                  id="text-content"
                  rows="10"
                  value={uploadText}
                  onChange={(e) => setUploadText(e.target.value)}
                  placeholder="Paste quotation text here. Include product names, quantities, prices, and payment terms..."
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
              <Button onClick={handleUploadQuotation} disabled={loading}>
                {loading ? 'Processing...' : 'Upload & Process'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </ProjectLayout>
  )
}

export default QuotationComparison
