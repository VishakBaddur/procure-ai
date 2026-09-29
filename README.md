# ProcureAI

An AI-powered procurement intelligence platform for procurement officers to manage vendors, compare quotes, analyze legal agreements, research vendor reputation, and calculate Total Cost of Ownership, organized around **Projects** for multi-vendor, multi-document workflows.

**Live demo:** https://procure-ai-byk5.onrender.com
**Demo login:** demo@procureai.com / demo1234
**Privacy policy:** https://procure-ai-byk5.onrender.com/privacy

---

## Evaluation Results

### Price Extraction Eval

| Quote Format | Items Found | Unit Price Accuracy | Line Total Accuracy |
|---|---|---|---|
| Structured PDF | 3/3 | 100% | 100% |
| Malformatted PDF (hidden fees, ambiguous qty) | 3/3 | 100% | 100% |
| Informal email (approximate language) | 3/3 | 100% | 100% |

Overall: **100% unit price accuracy** across 9 labeled line items.

Run: `cd backend && python3 eval_price_extraction.py`

### Retrieval Eval

| Strategy | Chunks | Recall@1 | Recall@3 | Recall@5 | MRR@3 |
|---|---|---|---|---|---|
| words_512_64 | 3 | 40% | 100% | 100% | 0.644 |
| words_256_32 | 3 | 40% | 100% | 100% | 0.644 |
| words_128_16 | 6 | 20% | 67% | 80% | 0.378 |
| sentence | 11 | 53% | 80% | 87% | 0.633 |

512-word chunks (words_512_64) selected for production: 100% Recall@3 on 15 labeled queries.

Run: `cd backend && python3 eval_retrieval.py`

---

## Features

### AI Agents (7 total)
- **Price Comparison Agent** - Extracts and normalizes pricing from PDFs, scanned images, Word docs, and email quotes. Confidence scores on every extraction.
- **Legal Analysis Agent** - Risk scores vendor agreements, surfaces key terms and recommendations.
- **Vendor Research Agent** - Reputation scoring and red flag detection via Groq and SerpAPI.
- **TCO Agent** - 5-year Total Cost of Ownership projections including hidden costs.
- **Decision Agent** - Final vendor recommendation with reasoning across all signals.
- **Email Agent** - Fetches and processes vendor quotes from IMAP/POP mailboxes.
- **Embedding Agent** - Chunks and embeds documents using Voyage AI voyage-3-lite (512d).

### Core Features
- **Project-based workflow** - All procurement activity organized under Projects; each project tracks multiple vendors
- **JWT authentication** - bcrypt password hashing, 7-day tokens, per-user project isolation
- **Semantic search** - Natural language search across all vendor documents via pgvector (HNSW, cosine similarity)
- **Auto-embedding** - Every uploaded document chunked and embedded automatically in the background
- **Confidence scoring** - Every extracted price tagged high/medium/low with inline badge
- **Audit trail** - Every login, upload, and vendor action logged with timestamp
- **Supplier qualification** - FDA registration, GMP certification, DEA registration, audit dates per vendor
- **Privacy page** - Public data handling disclosure at /privacy

---

## Tech Stack

### Backend
- **FastAPI** - Python web framework
- **PostgreSQL** - Production database (Neon) via SQLAlchemy ORM
- **pgvector** - Vector similarity search (HNSW index, m=16, ef_construction=64, cosine ops)
- **Voyage AI** - voyage-3-lite embeddings (512d); replaced Groq nomic-embed-text-v1.5 after provider deprecation
- **Groq AI** - LLM for all 7 agents (llama-3.3-70b-versatile)
- **pdfplumber** - PDF text extraction
- **pytesseract + Pillow** - OCR for scanned image quotes
- **python-docx** - Word document support
- **python-jose + bcrypt** - JWT authentication
- **SerpAPI** - Vendor reputation research

### Frontend
- **React 18**, **Vite**, **React Router v6**
- **Tailwind CSS**, **Radix UI**, **Recharts**, **Lucide React**

### Infrastructure
- **Render** - Single Docker container (frontend + backend served together)
- **Neon** - Managed PostgreSQL with pgvector (free tier, no expiry)
- **Docker image** - ~300MB (sentence-transformers replaced with API-based embeddings)

---

## Local Setup

### Prerequisites

- Python 3.8+, Node.js 16+, PostgreSQL 14+ with pgvector

### Install pgvector (macOS)

    git clone --branch v0.8.2 https://github.com/pgvector/pgvector.git /tmp/pgvector
    cd /tmp/pgvector
    make PG_CONFIG=/opt/homebrew/opt/postgresql@14/bin/pg_config
    make install PG_CONFIG=/opt/homebrew/opt/postgresql@14/bin/pg_config

### Backend

    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt

Create `backend/.env`:

    GROQ_API_KEY=your_groq_api_key
    VOYAGE_API_KEY=your_voyage_api_key
    DATABASE_URL=postgresql://localhost/procureai
    SECRET_KEY=your_random_secret_key

    # Optional
    SERPAPI_KEY=your_serpapi_key
    EMAIL_ADDRESS=your_email@example.com
    EMAIL_PASSWORD=your_password
    EMAIL_IMAP_SERVER=imap.gmail.com

Run:

    python3 main.py

API at http://localhost:8000

### Frontend

    cd frontend
    npm install
    npm run dev

Frontend at http://localhost:3000

---

## API Reference

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/register | Register a new user |
| POST | /api/auth/login | Login and get JWT token |
| GET | /api/auth/me | Get current user |

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
| POST | /api/projects/{project_id}/what-if | Run what-if analysis |

### Search and Audit
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/search | Semantic search across vendor documents |
| GET | /api/audit | Audit log (auth required) |

### Supplier Qualification
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/projects/{project_id}/vendors/{vendor_id}/qualification | Get qualification data |
| POST | /api/projects/{project_id}/vendors/{vendor_id}/qualification | Save qualification data |

### Email
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/projects/{project_id}/email/fetch | Fetch quotes from email |
| POST | /api/projects/{project_id}/email/process | Process fetched emails |

---

## Semantic Search

Every uploaded vendor document is automatically chunked (512-word chunks, 64-word overlap) and embedded using Voyage AI voyage-3-lite (512 dimensions). Embeddings are stored in PostgreSQL via pgvector with an HNSW index (m=16, ef_construction=64) for cosine similarity search.

Query examples:

- "vendors with overage fees"
- "warranty terms longer than 12 months"
- "SLA penalties for downtime"
- "net payment terms"
- "auto-renewal clauses"

---

## Deployment

Deployed on Render as a single Docker container (frontend + backend).

Environment variables required:

    DATABASE_URL=postgresql+psycopg2://neondb_owner:password@host.neon.tech/neondb?sslmode=require
    SECRET_KEY=your_random_secret_key
    GROQ_API_KEY=your_groq_key
    VOYAGE_API_KEY=your_voyage_key
    SERPAPI_KEY=your_serpapi_key

---

## License

MIT
