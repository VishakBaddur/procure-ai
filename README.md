# Procure AI

A comprehensive AI-powered procurement platform for procurement officers to manage vendors, compare quotes, analyze legal agreements, research vendor reputation, and calculate Total Cost of Ownership (TCO) — organized around **Projects** for multi-vendor, multi-document workflows.

---

## Features

### 🤖 AI Agents

- **Price Comparison Agent** — Extracts and compares pricing from vendor quotes (PDF, images, text)
- **Legal Analysis Agent** — Analyzes vendor agreements for risks, terms, and recommendations
- **Vendor Research Agent** — Researches vendors for reviews, reputation scores, and red flags using Groq AI
- **TCO Agent** — Calculates Total Cost of Ownership including support, maintenance, and long-term costs
- **Decision Agent** — Generates final vendor recommendations based on all collected data
- **Email Agent** — Fetches and processes vendor quotes directly from email (IMAP/POP)

### 📊 Core Features

- **Project-based workflow** — All procurement activity is organized under Projects; each project tracks multiple vendors
- **Vendor management** — Add, remove, and track vendors per project
- **Quote uploads** — Upload vendor quotations (PDF, image, text) per vendor; AI extracts and structures pricing
- **Agreement uploads** — Upload legal agreements per vendor; AI scores risk and surfaces key terms
- **Vendor research** — AI-powered reputation scoring, red flag detection, and sourced recommendations
- **TCO analysis** — 5-year cost projections including hidden costs (support, maintenance, training)
- **What-if analysis** — Model cost scenarios with adjustable assumptions
- **Decision assistance** — Final AI-generated vendor recommendation with reasoning
- **Analytics dashboard** — Side-by-side comparisons across quotes, agreements, reviews, and TCO
- **Export** — Export procurement recommendations as structured reports
- **Email integration** *(optional)* — Connect an IMAP/POP mailbox to auto-fetch vendor quotes

---

## Tech Stack

### Backend
- **FastAPI** — Python web framework
- **SQLite** — Local database (`procurement.db`) via SQLAlchemy ORM
- **pdfplumber** — PDF text extraction
- **pytesseract + Pillow** — OCR for image-based quotes
- **python-docx** — Word document support
- **Groq AI** — Primary LLM for all agents (fast inference via `groq` SDK)
- **Google Generative AI** — Optional fallback / vendor research enrichment
- **python-dotenv** — Environment variable management

### Frontend
- **React 18** — UI framework
- **Vite** — Build tool
- **React Router v6** — Navigation
- **Recharts** — Data visualization
- **Tailwind CSS** — Styling
- **Radix UI** — Accessible component primitives (Dialog, Tabs, Select, etc.)
- **Lucide React** — Icons

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
    │   │   └── email_agent.py
    │   ├── database.py
    │   ├── main.py
    │   ├── models.py
    │   ├── requirements.txt
    │   └── uploads/
    ├── frontend/
    │   ├── src/
    │   │   ├── components/
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
    │   │   │   ├── Analytics.jsx
    │   │   │   ├── DecisionAssistance.jsx
    │   │   │   └── WhatIfAnalysis.jsx
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
- Tesseract OCR (for image-based quote extraction)
- Groq API Key — free at https://console.groq.com

### Backend Setup

1. Navigate to the backend directory and activate the virtual environment:

        cd backend
        source venv/bin/activate

2. Install dependencies:

        pip install -r requirements.txt

3. Install Tesseract OCR:
   - macOS: `brew install tesseract`
   - Ubuntu: `sudo apt-get install tesseract-ocr`
   - Windows: https://github.com/UB-Mannheim/tesseract/wiki

4. Create a `.env` file in the `backend/` directory:

        GROQ_API_KEY=your_groq_api_key_here

        # Optional: Google Gemini for additional vendor research enrichment
        GEMINI_API_KEY=your_gemini_api_key_here

        # Optional: SerpAPI for web search grounding
        SERPAPI_KEY=your_serpapi_key_here

        # Optional: Email integration
        EMAIL_ADDRESS=your_email@example.com
        EMAIL_PASSWORD=your_password
        EMAIL_IMAP_SERVER=imap.gmail.com

5. Start the backend:

        python3 main.py

   API available at http://localhost:8000

### Frontend Setup

1. Navigate to the frontend directory:

        cd frontend

2. Install dependencies and start the dev server:

        npm install
        npm run dev

   Frontend available at http://localhost:3000

---

## Usage

1. **Create a Project** — Start by creating a procurement project (e.g. "Office Laptops Q3")
2. **Add Vendors** — Add the vendors you are evaluating to the project
3. **Upload Quotes** — Upload quotation documents (PDF, image, or text) per vendor
4. **Upload Agreements** — Upload legal agreements per vendor for risk analysis
5. **Research Vendors** — Trigger AI-powered vendor research for reputation scores and red flags
6. **View Comparisons** — Compare quotes, agreements, reviews, and TCO side by side
7. **What-If Analysis** — Model different cost scenarios with adjustable parameters
8. **Get Recommendation** — Let the Decision Agent generate a final vendor recommendation
9. **Export** — Export the recommendation report

---

## API Endpoints

### Projects
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/projects | Create a new project |
| GET | /api/projects | List all projects |
| GET | /api/projects/{project_id} | Get project details |
| DELETE | /api/projects/{project_id} | Delete a project |
| GET | /api/projects/{project_id}/dashboard | Get project dashboard data |

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
| GET | /api/projects/{project_id}/vendors/{vendor_id}/quotations | List quotes |
| DELETE | /api/projects/{project_id}/vendors/{vendor_id}/quotations/{doc_id} | Delete a quote |
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

## AI Configuration

The platform uses **Groq AI** as the primary LLM for all agents. Groq provides fast inference and a generous free tier.

- If Groq is unavailable, the system checks for a local **Ollama** instance at `localhost:11434` as a fallback
- **Google Gemini** (`GEMINI_API_KEY`) can be added for additional vendor research enrichment
- **SerpAPI** (`SERPAPI_KEY`) can be added for real-time web search grounding in vendor research

Get your free Groq API key at https://console.groq.com

---

## Docker

A `docker-compose.yml` is included for containerized deployment:

    docker-compose up --build

---

## Future Enhancements

- PostgreSQL support for production deployments (migration script included: `migrate_to_postgres.py`)
- Multi-user support with authentication
- Advanced ML-based scoring models
- Deeper email integration (auto-polling, threading)
- Mobile-responsive UI improvements
- Expanded export formats (PDF reports, Excel)

---

## License

MIT
