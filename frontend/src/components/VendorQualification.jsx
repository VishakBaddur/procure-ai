import React, { useEffect, useState } from "react"
import axios from "axios"
import { API_BASE } from "../config"

const AUDIT_OUTCOMES = ["passed", "failed", "observations", "not_audited"]
const GMP_OPTIONS = ["yes", "no", "pending", "not_applicable"]

export default function VendorQualification({ projectId, vendorId, vendorName }) {
  const [data, setData] = useState({
    fda_registration_number: "",
    gmp_certified: "",
    gmp_certificate_number: "",
    last_audit_date: "",
    audit_outcome: "",
    dea_registration: "",
    iso_certifications: "",
    notes: ""
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem("token")
    axios.get(`${API_BASE}/api/projects/${projectId}/vendors/${vendorId}/qualification`, {
      headers: { Authorization: `Bearer ${token}` }
    }).then(res => {
      if (res.data.qualification) {
        setData(prev => ({ ...prev, ...res.data.qualification }))
      }
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [vendorId])

  const handleSave = async () => {
    setSaving(true)
    const token = localStorage.getItem("token")
    await axios.post(`${API_BASE}/api/projects/${projectId}/vendors/${vendorId}/qualification`, data, {
      headers: { Authorization: `Bearer ${token}` }
    })
    setSaving(false)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  if (loading) return <p className="text-sm text-gray-400">Loading...</p>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-gray-700">Supplier Qualification — {vendorName}</h3>
        {saved && <span className="text-xs text-green-600 font-medium">Saved</span>}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-xs font-medium text-gray-600 block mb-1">FDA Registration Number</label>
          <input
            className="w-full border border-gray-200 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
            placeholder="e.g. 1234567"
            value={data.fda_registration_number || ""}
            onChange={e => setData(d => ({ ...d, fda_registration_number: e.target.value }))}
          />
        </div>

        <div>
          <label className="text-xs font-medium text-gray-600 block mb-1">DEA Registration</label>
          <input
            className="w-full border border-gray-200 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
            placeholder="e.g. AB1234567"
            value={data.dea_registration || ""}
            onChange={e => setData(d => ({ ...d, dea_registration: e.target.value }))}
          />
        </div>

        <div>
          <label className="text-xs font-medium text-gray-600 block mb-1">GMP Certified</label>
          <select
            className="w-full border border-gray-200 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
            value={data.gmp_certified || ""}
            onChange={e => setData(d => ({ ...d, gmp_certified: e.target.value }))}
          >
            <option value="">Select...</option>
            {GMP_OPTIONS.map(o => <option key={o} value={o}>{o.charAt(0).toUpperCase() + o.slice(1).replace("_", " ")}</option>)}
          </select>
        </div>

        <div>
          <label className="text-xs font-medium text-gray-600 block mb-1">GMP Certificate Number</label>
          <input
            className="w-full border border-gray-200 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
            placeholder="e.g. GMP-2024-001"
            value={data.gmp_certificate_number || ""}
            onChange={e => setData(d => ({ ...d, gmp_certificate_number: e.target.value }))}
          />
        </div>

        <div>
          <label className="text-xs font-medium text-gray-600 block mb-1">Last Audit Date</label>
          <input
            type="date"
            className="w-full border border-gray-200 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
            value={data.last_audit_date || ""}
            onChange={e => setData(d => ({ ...d, last_audit_date: e.target.value }))}
          />
        </div>

        <div>
          <label className="text-xs font-medium text-gray-600 block mb-1">Audit Outcome</label>
          <select
            className="w-full border border-gray-200 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
            value={data.audit_outcome || ""}
            onChange={e => setData(d => ({ ...d, audit_outcome: e.target.value }))}
          >
            <option value="">Select...</option>
            {AUDIT_OUTCOMES.map(o => <option key={o} value={o}>{o.charAt(0).toUpperCase() + o.slice(1).replace("_", " ")}</option>)}
          </select>
        </div>

        <div className="col-span-2">
          <label className="text-xs font-medium text-gray-600 block mb-1">ISO Certifications</label>
          <input
            className="w-full border border-gray-200 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
            placeholder="e.g. ISO 9001:2015, ISO 13485"
            value={data.iso_certifications || ""}
            onChange={e => setData(d => ({ ...d, iso_certifications: e.target.value }))}
          />
        </div>

        <div className="col-span-2">
          <label className="text-xs font-medium text-gray-600 block mb-1">Notes</label>
          <textarea
            className="w-full border border-gray-200 rounded px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
            rows={3}
            placeholder="Any additional qualification notes..."
            value={data.notes || ""}
            onChange={e => setData(d => ({ ...d, notes: e.target.value }))}
          />
        </div>
      </div>

      <button
        onClick={handleSave}
        disabled={saving}
        className="w-full bg-gray-900 text-white text-sm py-2 rounded hover:bg-gray-700 transition disabled:opacity-50"
      >
        {saving ? "Saving..." : "Save Qualification Data"}
      </button>
    </div>
  )
}
