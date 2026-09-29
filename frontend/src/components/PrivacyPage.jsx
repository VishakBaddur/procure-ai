import React from "react"
import { Link } from "react-router-dom"

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
        <Link to="/" className="text-xl font-bold text-gray-900">ProcureAI</Link>
        <Link to="/auth" className="text-sm text-blue-600 hover:underline">Sign in</Link>
      </nav>

      <div className="max-w-3xl mx-auto px-6 py-16">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Data Privacy</h1>
        <p className="text-gray-500 mb-10 text-sm">Last updated: September 2026</p>

        <section className="mb-10">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">What data we collect</h2>
          <p className="text-gray-600 leading-relaxed">
            ProcureAI collects only what is necessary to operate the platform: your email address and password (hashed with bcrypt), 
            the vendor documents you upload (quotes, agreements, emails), and the project and vendor metadata you create. 
            We do not collect payment information, browsing history, or any data outside of your procurement workflows.
          </p>
        </section>

        <section className="mb-10">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Where your data goes</h2>
          <ul className="space-y-4 text-gray-600">
            <li className="flex gap-3">
              <span className="font-medium text-gray-800 min-w-32">Your database</span>
              <span>All project data, vendor information, extracted pricing, and document embeddings are stored in a private PostgreSQL database (Neon) that only your account can access.</span>
            </li>
            <li className="flex gap-3">
              <span className="font-medium text-gray-800 min-w-32">Groq AI</span>
              <span>Document text is sent to Groq's API for LLM-based extraction and analysis. Groq does not train on API inputs. See <a href="https://groq.com/privacy-policy/" className="text-blue-600 hover:underline" target="_blank" rel="noreferrer">Groq's privacy policy</a>.</span>
            </li>
            <li className="flex gap-3">
              <span className="font-medium text-gray-800 min-w-32">Voyage AI</span>
              <span>Document text is sent to Voyage AI's API to generate vector embeddings for semantic search. Voyage does not train on API inputs. See <a href="https://www.voyageai.com/privacy" className="text-blue-600 hover:underline" target="_blank" rel="noreferrer">Voyage AI's privacy policy</a>.</span>
            </li>
            <li className="flex gap-3">
              <span className="font-medium text-gray-800 min-w-32">SerpAPI</span>
              <span>Vendor names are sent to SerpAPI to fetch public reputation data. No document content is sent. See <a href="https://serpapi.com/privacy" className="text-blue-600 hover:underline" target="_blank" rel="noreferrer">SerpAPI's privacy policy</a>.</span>
            </li>
          </ul>
        </section>

        <section className="mb-10">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">What we do not do</h2>
          <ul className="list-disc list-inside space-y-2 text-gray-600">
            <li>We do not sell your data to third parties.</li>
            <li>We do not use your procurement documents to train AI models.</li>
            <li>We do not share your vendor data across accounts.</li>
            <li>We do not store document files permanently — only extracted text and embeddings.</li>
          </ul>
        </section>

        <section className="mb-10">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Data isolation</h2>
          <p className="text-gray-600 leading-relaxed">
            Every project and vendor is scoped to your user account via JWT authentication. No other user can access your data. 
            Database queries are filtered by user ID at the application layer on every request.
          </p>
        </section>

        <section className="mb-10">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Data retention</h2>
          <p className="text-gray-600 leading-relaxed">
            Your data is retained for as long as your account is active. You can delete any project, vendor, or document at any time 
            from within the platform. To request full account deletion, email us and we will remove all associated data within 30 days.
          </p>
        </section>

        <section className="mb-10">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Security</h2>
          <ul className="list-disc list-inside space-y-2 text-gray-600">
            <li>Passwords hashed with bcrypt (cost factor 12).</li>
            <li>All API communication over HTTPS/TLS.</li>
            <li>JWT tokens expire after 7 days.</li>
            <li>Database connections use SSL.</li>
            <li>No credentials stored in code or version control.</li>
          </ul>
        </section>

        <section className="mb-10">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Contact</h2>
          <p className="text-gray-600">
            Questions about data handling? Email us at <a href="mailto:privacy@procureai.com" className="text-blue-600 hover:underline">privacy@procureai.com</a>.
          </p>
        </section>

        <div className="border-t border-gray-200 pt-8 text-center">
          <Link to="/auth" className="inline-block bg-gray-900 text-white px-6 py-3 rounded-lg text-sm font-medium hover:bg-gray-700 transition">
            Back to sign in
          </Link>
        </div>
      </div>
    </div>
  )
}
