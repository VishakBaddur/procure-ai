# Procure AI

An AI-powered procurement intelligence platform for procurement officers to manage vendors, compare quotes, analyze legal agreements, research vendor reputation, and calculate Total Cost of Ownership — organized around **Projects** for multi-vendor, multi-document workflows.

Live demo: https://procure-ai-byk5.onrender.com

---

## Features

### AI Agents

- **Price Comparison Agent** — Extracts and compares pricing from vendor quotes (PDF, image, text)
- **Legal Analysis Agent** — Analyzes vendor agreements for risks, terms, and recommendations
- **Vendor Research Agent** — Reputation scoring, red flag detection, sourced recommendations via Groq AI
- **TCO Agent** — 5-year Total Cost of Ownership projections including hidden costs
- **Decision Agent** — Final vendor recommendation with reasoning across all collected signals
- **Email Agent** — Fetches and processes vendor quotes directly from email (IMAP/POP)
- **Embedding Agent** — Chunks and embeds all vendor documents using Groq nomic-embed-text-v1.5 (768d)

### Core Features

- **Project-based workflow** — All procurement activity organized under Projects; each project tracks multiple vendors
- **JWT authentication** — Secure register/login with bcrypt password hashing and 7-day tokens
- **Semantic search** — Natural language search across all vendor documents using pgvector cosine similarity with HNSW index
- **Auto-embedding** — Every uploaded document is automatically chunked and embedded in the background
- **Quote uploads** — PDF, image, text per vendor; AI extracts and structures pricing
- **Agreement uploads** — Legal agreements per vendor; AI scores risk and surfaces key terms
- **TCO analysis** — 5-year cost projections
- **What-if analysis** — Model cost scenarios with adjustable assumptions
- **Decision assistance** — AI-generated final vendor recommendation
- **Analytics dashboard** — Side-by-side comparisons across quotes, agreements, reviews, and TCO
- **Email integration** (optional) — Connect IMAP/POP mailbox to auto-fetch vendor quotes

---

## Tech Stack

### Backend
- **FastAPI** — Python web framework
- **PostgreSQL** — Production database via SQLAlchemy ORM
- **pgvector** — Vector similarity search extension (HNSW index, cosine distance)
- **Groq AI** — Primary LLM for all agents + nomic-embed-text-v1.5 embeddings
- **pdfplumber** — PDF text extraction
- **pytesseract + Pillow** — OCR for image-based quotes
- **python-docx** — Word document support
- **JWT (python-jose + bcrypt)** — Authentication
- **python-dotenv** — Environment variable management

### Frontend
- **React 18** — UI framework
- **Vite** — Build tool
- **React Router v6** — Navigation with protected routes
- **Recharts** — Data visualization
- **Tailwind CSS** — Styling
- **Radix UI** — Accessible component primitives
- **Lucide React** — Icons

### Infrastructure
- **Render** — Backend + frontend deployment (single Docker container)
- **Render PostgreSQL** — Managed PostgreSQL with pgvector

---

## Architecture

    User → React Frontend (Vite/Tailwind)
              ↓ JWT-authenticated requests
    FastAPI Backend
              ↓
    ┌─────────────────────────────────────┐
    │  Agents (Groq AI)                   │
    │  - Price Comparison                 │
    │  - Legal Analysis                   │
    │  - Vendor Research                  │
    │  - TCO                              │
    │  - Decision                         │
    │  - Embedding (nomic-embed-text)     │
    └─────────────────────────────────────┘
              ↓
    PostgreSQL + pgvector
    - Projects / Vendors / Documents
    - Parsed data (JSON)
    - Document embeddings (768d, HNSW index)
    - Users (bcrypt hashed)

---

## Project Structure

    procure ai cursor/
    ├── backend/
    │   ├── agents/
    │   │   ├── price_comparison_agent.py
    │   │   ├── legal_analysis_agent.py
    │   │   ├── vendor_research_agent.py
    │   │   ├── tco_agent.py
    │   │   ├── decision_agent.py
    │   │   ├── email_agent.py
    │   │   └── embedding_agent.py
    │   ├── database.py          # SQLAlchemy ORM + pgvector + auth helpers
    │   ├── main.py              # FastAPI app, all endpoints
    │   ├── models.py
    │   ├── requirements.txt
    │   └── uploads/
    ├── frontend/
    │   ├── src/
    │   │   ├── components/
    │   │   │   ├── AuthPage.jsx
    │   │   │   ├── SemanticSearch.jsx
    │   │   │   ├── ProjectList.jsx
    │   │   │   ├── CreateProject.jsx
    │   │   │   ├── ProjectDashboard.jsx
    │   │   │   ├── ProjectLayout.jsx
    │   │   │   ├── Dashboard.jsx
    │   │   │   ├── Questionnaire.jsx
    │   │   │   ├── UploadQuotes.jsx
    │   │   │   ├── UploadAgreements.jsx
    │   │   │   ├── QuotationComparison.jsx
    │   │   │   ├── AgreementsComparison.jsx
    │   │   │   ├── ReviewsComparison.jsx
    │   │   │   ├── TCOComparison.jsx
    │   │   │   ├── DecisionAssistance.jsx
    │   │   │   └── WhatIfAnalysis.jsx
    │   │   ├── AuthContext.jsx
    │   │   ├── config.js
    │   │   ├── App.jsx
    │   │   └── main.jsx
    │   ├── package.json
    │   └── vite.config.js
    ├── docker-compose.yml
    ├── Dockerfile
    ├── start_backend.sh
    ├── start_frontend.sh
    └── README.md

---

## Setup Instructions

### Prerequisites

- Python 3.8+
- Node.js 16+
- PostgreSQL 14+ with pgvector extension
- Groq API Key — free at https://console.groq.com

### Install pgvector (macOS)

    git clone --branch v0.8.2 https://github.com/pgvector/pgvector.git /tmp/pgvector
    cd /tmp/pgvector
    make PG_CONFIG=/opt/homebrew/opt/postgresql@14/bin/pg_config
    make install PG_CONFIG=/opt/homebrew/opt/postgresql@14/bin/pg_config

### Backend Setup

    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

Create a .env file in backend/:

    GROQ_API_KEY=your_groq_api_key_here
    DATABASE_URL=postgresql://localhost/procureai
    SECRET_KEY=your_random_secret_key

    # Optional
    GEMINI_API_KEY=your_gemini_api_key
    SERPAPI_KEY=your_serpapi_key
    EMAIL_ADDRESS=your_email@example.com
    EMAIL_PASSWORD=your_password
    EMAIL_IMAP_SERVER=imap.gmail.com

Start the backend:

    python3 main.py

API available at http://localhost:8000

### Frontend Setup

    cd frontend
    npm install
    npm run dev

Frontend available at http://localhost:3000

---

## API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/register | Register a new user |
| POST | /api/auth/login | Login and get JWT token |
| GET | /api/auth/me | Get current user |

### Search
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/search | Semantic search across vendor documents |

### Projects
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/projects | Create a new project |
| GET | /api/projects | List all projects |
| GET | /api/projects/{project_id} | Get project details |
| DELETE | /api/projects/{project_id} | Delete a project |
| GET | /api/projects/{project_id}/dashboard | Get project dashboard |

### Vendors
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/projects/{project_id}/vendors | List vendors |
| POST | /api/projects/{project_id}/vendors | Add a vendor |
| DELETE | /api/projects/{project_id}/vendors/{vendor_id} | Remove a vendor |

### Quotes and Agreements
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/projects/{project_id}/vendors/{vendor_id}/quotations | Upload a quote |
| GET | /api/projects/{project_id}/quotations/comparison | Compare all quotes |
| POST | /api/projects/{project_id}/vendors/{vendor_id}/agreements | Upload an agreement |
| GET | /api/projects/{project_id}/agreements/comparison | Compare all agreements |

### Research and Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/projects/{project_id}/vendors/{vendor_id}/research | Research a vendor |
| GET | /api/projects/{project_id}/reviews/comparison | Compare vendor reviews |
| GET | /api/projects/{project_id}/tco/comparison | TCO comparison |
| GET | /api/projects/{project_id}/recommendation | Get AI recommendation |
| POST | /api/projects/{project_id}/recommendation/export | Export recommendation |
| POST | /api/projects/{project_id}/what-if | Run what-if analysis |

### Email
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/projects/{project_id}/email/fetch | Fetch quotes from email |
| POST | /api/projects/{project_id}/email/process | Process fetched emails |

---

## Semantic Search

Every uploaded vendor document is automatically chunked (512-word chunks, 64-word overlap) and embedded using Groq's nomic-embed-text-v1.5 model (768 dimensions). Embeddings are stored in PostgreSQL via pgvector with an HNSW index (m=16, ef_construction=64) for sub-millisecond cosine similarity search at scale.

Query examples:

- "vendors with overage fees"
- "warranty terms longer than 12 months"
- "SLA penalties for downtime"
- "net payment terms"
- "auto-renewal clauses"

---

## Deployment

Deployed on Render as a single Docker container (frontend + backend).

Environment variables required on Render:

    DATABASE_URL=<render-internal-postgres-url>
    SECRET_KEY=<random-hex-string>
    GROQ_API_KEY=<your-groq-key>
    SERPAPI_KEY=<your-serpapi-key>  # optional

---

## Future Enhancements

- Multi-organization support with role-based access control
- Expanded export formats (PDF reports, Excel)
- Email auto-polling with threading
- Mobile-responsive UI improvements
- Confidence scoring on extracted fields with human review queue

---

## License

MIT
