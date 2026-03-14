/**
 * API base URL for backend. Set VITE_API_URL at build time for production (e.g. Render).
 * Default http://localhost:8000 for local dev.
 */
export const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')
