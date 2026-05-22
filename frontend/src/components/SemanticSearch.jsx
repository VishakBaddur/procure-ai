import React, { useState } from "react"
import axios from "axios"
import { API_BASE } from "@/config"
import { Search, FileText, X } from "lucide-react"
import { Button } from "./ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card"

export default function SemanticSearch({ projectId }) {
  const [query, setQuery] = useState("")
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [searched, setSearched] = useState(false)

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setError("")
    setSearched(true)
    try {
      const res = await axios.post(`${API_BASE}/api/search`, {
        project_id: projectId,
        query: query.trim(),
        top_k: 5
      })
      setResults(res.data.results || [])
    } catch (err) {
      setError(err.response?.data?.detail || "Search failed")
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const clear = () => {
    setQuery("")
    setResults([])
    setSearched(false)
    setError("")
  }

  return (
    <Card className="mb-6">
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <Search className="h-4 w-4" />
          Semantic Search
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          Search across all vendor documents using natural language
        </p>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSearch} className="flex gap-2 mb-4">
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="e.g. vendors with overage fees, warranty terms, SLA penalties..."
            className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {searched && (
            <Button type="button" variant="outline" size="icon" onClick={clear}>
              <X className="h-4 w-4" />
            </Button>
          )}
          <Button type="submit" disabled={loading || !query.trim()}>
            {loading ? "Searching..." : "Search"}
          </Button>
        </form>

        {error && <p className="text-sm text-red-600 mb-3">{error}</p>}

        {searched && !loading && results.length === 0 && !error && (
          <p className="text-sm text-muted-foreground text-center py-4">
            No relevant passages found. Try uploading vendor documents first.
          </p>
        )}

        {results.length > 0 && (
          <div className="space-y-3">
            {results.map((r, i) => (
              <div key={i} className="border border-gray-200 rounded-md p-3 bg-gray-50">
                <div className="flex items-center gap-2 mb-2">
                  <FileText className="h-3 w-3 text-muted-foreground" />
                  <span className="text-xs font-medium text-blue-700">{r.vendor_name}</span>
                  <span className="text-xs text-muted-foreground">chunk {r.chunk_index + 1}</span>
                </div>
                <p className="text-xs text-gray-700 leading-relaxed line-clamp-4">{r.chunk_text}</p>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
