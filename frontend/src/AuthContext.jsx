import React, { createContext, useContext, useState, useEffect } from "react"
import axios from "axios"
import { API_BASE } from "@/config"

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(() => localStorage.getItem("token"))
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common["Authorization"] = `Bearer ${token}`
      axios.get(`${API_BASE}/api/auth/me`)
        .then(res => setUser(res.data))
        .catch(() => logout())
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = async (email, password) => {
    const res = await axios.post(`${API_BASE}/api/auth/login`, { email, password })
    const { access_token, user } = res.data
    localStorage.setItem("token", access_token)
    axios.defaults.headers.common["Authorization"] = `Bearer ${access_token}`
    setToken(access_token)
    setUser(user)
    return user
  }

  const register = async (email, password, full_name) => {
    const res = await axios.post(`${API_BASE}/api/auth/register`, { email, password, full_name })
    const { access_token, user } = res.data
    localStorage.setItem("token", access_token)
    axios.defaults.headers.common["Authorization"] = `Bearer ${access_token}`
    setToken(access_token)
    setUser(user)
    return user
  }

  const logout = () => {
    localStorage.removeItem("token")
    delete axios.defaults.headers.common["Authorization"]
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
