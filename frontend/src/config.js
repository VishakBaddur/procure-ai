/**
 * API base URL for backend. Set VITE_API_URL at build time for production.
 * Empty = same origin (when backend serves frontend). Default http://localhost:8000 for local dev.
 */
export const API_BASE = (
  import.meta.env.VITE_API_URL !== undefined && String(import.meta.env.VITE_API_URL).trim() !== ''
    ? String(import.meta.env.VITE_API_URL).replace(/\/$/, '')
    : import.meta.env.DEV
      ? 'http://localhost:8000'
      : ''
)
