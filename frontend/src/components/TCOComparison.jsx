import React, { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import axios from 'axios'
import { API_BASE } from '@/config'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { TrendingUp } from 'lucide-react'
import ProjectLayout from './ProjectLayout'

const TCOComparison = () => {
  const { projectId } = useParams()
  const [comparison, setComparison] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchComparison()
  }, [projectId])

  const fetchComparison = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/projects/${projectId}/tco/comparison`)
      setComparison(response.data.comparison)
    } catch (err) {
      setError('Failed to load TCO comparison')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <ProjectLayout projectId={projectId} activePath="tco">
        <div className="container mx-auto px-8 py-8 max-w-7xl">
          <p className="text-muted-foreground">Loading TCO analysis...</p>
        </div>
      </ProjectLayout>
    )
  }

  if (error || !comparison) {
    return (
      <ProjectLayout projectId={projectId} activePath="tco">
        <div className="container mx-auto px-8 py-8 max-w-7xl">
          <Card>
            <CardContent className="pt-6">
              <p className="text-destructive">{error || 'TCO data not available'}</p>
            </CardContent>
          </Card>
        </div>
      </ProjectLayout>
    )
  }

  const chartData = comparison.vendors ? comparison.vendors.map(v => ({
    vendor: v.vendor_name,
    CAPEX: v.capex?.total_capex || 0,
    OPEX: v.opex?.total_opex || 0,
    Total: v.total_tco || 0
  })) : []

  return (
    <ProjectLayout projectId={projectId} activePath="tco">
      <div className="container mx-auto px-8 py-8 max-w-7xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight mb-2">Total Cost of Ownership</h1>
          <p className="text-muted-foreground">5-year cost analysis comparison</p>
        </div>

        {comparison.best_long_term_value && (
          <Card className="mb-6 bg-muted/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                Recommendation
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="font-semibold mb-2">Best Long-term Value: {comparison.best_long_term_value}</p>
              {comparison.recommendations && comparison.recommendations.map((rec, idx) => (
                <p key={idx} className="text-sm text-muted-foreground">{rec}</p>
              ))}
            </CardContent>
          </Card>
        )}

        {chartData.length > 0 && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>CAPEX vs OPEX Comparison</CardTitle>
              <CardDescription>Capital vs Operational Expenditure</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(0 0% 14.9%)" opacity={0.1} />
                  <XAxis dataKey="vendor" stroke="hsl(0 0% 45.1%)" />
                  <YAxis stroke="hsl(0 0% 45.1%)" />
                  <Tooltip 
                    formatter={(value) => `$${value.toFixed(2)}`}
                    contentStyle={{ backgroundColor: 'hsl(0 0% 100%)', border: '1px solid hsl(0 0% 14.9%)' }}
                  />
                  <Legend />
                  <Bar dataKey="CAPEX" fill="hsl(0 0% 9%)" />
                  <Bar dataKey="OPEX" fill="hsl(0 0% 45.1%)" />
                  <Bar dataKey="Total" fill="hsl(0 0% 70%)" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}

        {comparison.vendors && comparison.vendors.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Detailed TCO Breakdown</CardTitle>
              <CardDescription>Cost analysis by vendor</CardDescription>
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
                        <p className="text-sm text-muted-foreground mb-1">CAPEX (Capital Expenditure)</p>
                        <div className="space-y-1 text-sm ml-4">
                          <div>Initial: ${vendor.capex?.initial_cost?.toFixed(2)}</div>
                          <div>Training: ${vendor.capex?.training_cost?.toFixed(2)}</div>
                          <div>Replacement: ${vendor.capex?.replacement_cost?.toFixed(2)}</div>
                          <div className="font-semibold pt-2 border-t">
                            Total CAPEX: ${vendor.capex?.total_capex?.toFixed(2)}
                          </div>
                        </div>
                      </div>

                      <div>
                        <p className="text-sm text-muted-foreground mb-1">OPEX (Operational Expenditure)</p>
                        <div className="space-y-1 text-sm ml-4">
                          <div>Support: ${vendor.opex?.support_cost?.toFixed(2)}</div>
                          <div>Maintenance: ${vendor.opex?.maintenance_cost?.toFixed(2)}</div>
                          <div>Repairs: ${vendor.opex?.repair_cost?.toFixed(2)}</div>
                          <div>Downtime: ${vendor.opex?.downtime_cost?.toFixed(2)}</div>
                          <div className="font-semibold pt-2 border-t">
                            Total OPEX: ${vendor.opex?.total_opex?.toFixed(2)}
                          </div>
                        </div>
                      </div>

                      <div className="p-4 bg-muted rounded-lg space-y-2">
                        <div>
                          <p className="text-sm text-muted-foreground">Total TCO ({vendor.years_analyzed} years)</p>
                          <p className="text-2xl font-bold">${vendor.total_tco?.toFixed(2)}</p>
                        </div>
                        <div>
                          <p className="text-sm text-muted-foreground">Annual Cost</p>
                          <p className="text-lg font-semibold">${vendor.annual_cost?.toFixed(2)}</p>
                        </div>
                        <div>
                          <p className="text-sm text-muted-foreground">Durability Score</p>
                          <p className="text-lg font-semibold">{vendor.durability_score}/100</p>
                        </div>
                      </div>

                      {vendor.specifications && (
                        <div className="text-xs text-muted-foreground space-y-1">
                          <p className="font-medium">Specifications:</p>
                          <div className="ml-2 space-y-1">
                            <div>Warranty: {vendor.specifications.warranty_years} years</div>
                            <div>Maintenance: {vendor.specifications.maintenance_frequency_per_year} times/year</div>
                            <div>Replacement Cycle: {vendor.specifications.replacement_cycle_years} years</div>
                            <div>Failure Rate: {(vendor.specifications.failure_rate_per_year * 100).toFixed(1)}%/year</div>
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {comparison.item_specifications && (
          <Card className="mt-6">
            <CardHeader>
              <CardTitle>Item Specifications</CardTitle>
              <CardDescription>Used for TCO calculations</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-4">
                <div>
                  <p className="text-sm text-muted-foreground">Standard Warranty</p>
                  <p className="font-semibold">{comparison.item_specifications.standard_warranty_years} years</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Maintenance Frequency</p>
                  <p className="font-semibold">{comparison.item_specifications.maintenance_frequency_per_year} times/year</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Replacement Cycle</p>
                  <p className="font-semibold">{comparison.item_specifications.replacement_cycle_years} years</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Failure Rate</p>
                  <p className="font-semibold">{(comparison.item_specifications.failure_rate_per_year * 100).toFixed(1)}%/year</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </ProjectLayout>
  )
}

export default TCOComparison
