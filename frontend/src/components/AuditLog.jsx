import React, { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import axios from "axios"
import { API_BASE_URL } from "../config"

const ACTION_LABELS = {
  login: { label: "Signed in", color: "bg-blue-100 text-blue-700" },
  vendor_added: { label: "Vendor added", color: "bg-green-100 text-green-700" },
  document_uploaded: { label: "Document uploaded", color: "bg-purple-100 text-purple-700" },
  project_created: { label: "Project created", color: "bg-yellow-100 text-yellow-700" },
  search: { label: "Search performed", color: "bg-gray-100 text-gray-700" },
}

function formatDate(iso) {
  if (!iso) return ""
  const d = new Date(iso)
  return d.toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" })
}

export default function AuditLog() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    const token = localStorage.getItem("token")
    if (!token) { navigate("/auth"); return }
    axios.get(`${API_BASE_URL}/api/audit`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(res => { setLogs(res.data.logs || []); setLoading(false) })
      .catch(() => { setError("Failed to load audit log"); setLoading(false) })
  }, [])

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <button onClick={() => navigate("/projects")} className="text-xl font-bold text-gray-900">ProcureAI</button>
        <button onClick={() => navigate("/projects")} className="text-sm text-blue-600 hover:underline">Back to projects</button>
      </nav>

      <div className="max-w-4xl mx-auto px-6 py-12">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Audit Log</h1>
          <p className="text-gray-500 text-sm mt-1">All actions performed on your account, newest first.</p>
        </div>

        {loading && <p className="text-gray-400">Loading...</p>}
        {error && <p className="text-red-500">{error}</p>}

        {!loading && !error && logs.length === 0 && (
          <p className="text-gray-400">No activity recorded yet.</p>
        )}

        {!loading && logs.length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 divide-y divide-gray-100">
            {logs.map(log => {
              const meta = ACTION_LABELS[log.action] || { label: log.action, color: "bg-gray-100 text-gray-600" }
              return (
                <div key={log.id} className="flex items-start gap-4 px-6 py-4">
                  <span className={`text-xs px-2 py-1 rounded-full font-medium whitespace-nowrap mt-0.5 ${meta.color}`}>
                    {meta.label}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-700">{log.detail || "-"}</p>
                    {log.resource_type && (
                      <p className="text-xs text-gray-400 mt-0.5">{log.resource_type} {log.resource_id ? `#${log.resource_id}` : ""}</p>
                    )}
                  </div>
                  <span className="text-xs text-gray-400 whitespace-nowrap">{formatDate(log.created_at)}</span>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
