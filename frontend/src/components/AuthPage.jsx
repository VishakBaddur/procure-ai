import React, { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useAuth } from "@/AuthContext"
import { Button } from "./ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card"

export default function AuthPage() {
  const [mode, setMode] = useState("login")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [fullName, setFullName] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const { login, register } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError("")
    setLoading(true)
    try {
      if (mode === "login") {
        await login(email, password)
      } else {
        if (!fullName.trim()) { setError("Full name is required"); setLoading(false); return }
        await register(email, password, fullName)
      }
      navigate("/projects")
    } catch (err) {
      setError(err.response?.data?.detail || "Something went wrong")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">ProcureAI</h1>
          <p className="text-gray-500 mt-2">AI-powered procurement intelligence</p>
        </div>
        <Card>
          <CardHeader>
            <CardTitle>{mode === "login" ? "Sign in" : "Create account"}</CardTitle>
            <CardDescription>
              {mode === "login" ? "Welcome back. Enter your credentials to continue." : "Get started with ProcureAI."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              {mode === "register" && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Full name</label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={e => setFullName(e.target.value)}
                    className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Jane Smith"
                    required
                  />
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="you@company.com"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="••••••••"
                  required
                />
              </div>
              {error && <p className="text-sm text-red-600">{error}</p>}
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? "Please wait..." : mode === "login" ? "Sign in" : "Create account"}
              </Button>
            </form>
            <div className="mt-4 text-center text-sm text-gray-500">
              {mode === "login" ? (
                <>No account?{" "}
                  <button onClick={() => { setMode("register"); setError("") }} className="text-blue-600 hover:underline font-medium">Sign up</button>
                </>
              ) : (
                <>Already have an account?{" "}
                  <button onClick={() => { setMode("login"); setError("") }} className="text-blue-600 hover:underline font-medium">Sign in</button>
                </>
              )}
            </div>
            <div className="mt-4 pt-4 border-t border-gray-100 text-center">
              <p className="text-xs text-gray-400 mb-2">Demo account</p>
              <button
                onClick={() => { setEmail("demo@procureai.com"); setPassword("demo1234"); setMode("login") }}
                className="text-xs text-blue-500 hover:underline"
              >
                Fill demo credentials
              </button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
