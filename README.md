# Procurement AI Platform

A comprehensive AI-powered platform for procurement officers to compare vendors, analyze quotes, review legal agreements, research vendors, and calculate Total Cost of Ownership (TCO).

## Features

### 🤖 AI Agents

1. **Price Comparison Agent**: Extracts and compares pricing from vendor quotes (PDF, images, text)
2. **Legal Analysis Agent**: Analyzes vendor agreements for risks, terms, and recommendations
3. **Vendor Research Agent**: Researches vendors for reviews and red flags
4. **TCO Agent**: Calculates Total Cost of Ownership including support, maintenance, and long-term costs

### 📊 Features

- **Initial Questionnaire**: Captures procurement context (item, vendors, priorities)
- **Document Upload**: Support for PDF, images, and text files
- **Price Comparison**: Visual comparison of vendor quotes
- **Legal Analysis**: Risk scoring and term analysis for agreements
- **Vendor Research**: Reputation scoring and red flag detection
- **TCO Analysis**: Long-term cost analysis (5-year projections)
- **Analytics Dashboard**: Comprehensive visualizations and recommendations

## Tech Stack

### Backend
- **FastAPI**: Python web framework
- **SQLite**: Database for storing procurement data
- **PDF Processing**: pdfplumber for PDF extraction
- **OCR**: pytesseract for image text extraction
- **AI/LLM**: **Google Gemini API** with web search for vendor research (real-time web search + AI analysis)

### Frontend
- **React**: UI framework
- **Vite**: Build tool
- **Recharts**: Data visualization
- **React Router**: Navigation

## Setup Instructions

### Prerequisites

- Python 3.8+
- Node.js 16+
- Tesseract OCR (for image processing)
- **Google Gemini API Key** (for vendor research) - Get it free from [Google AI Studio](https://makersuite.google.com/app/apikey)

### Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Set up environment variables:
```bash
# Create .env file in backend directory
echo "GEMINI_API_KEY=your_api_key_here" > backend/.env
```
   Get your Gemini API key from: https://makersuite.google.com/app/apikey

4. Install dependencies:
```bash
pip install -r requirements.txt
```

5. Install Tesseract OCR:
   - **macOS**: `brew install tesseract`
   - **Ubuntu**: `sudo apt-get install tesseract-ocr`
   - **Windows**: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)

6. Run the backend server:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Usage

1. **Start with Questionnaire**: Fill out the initial questionnaire about your procurement needs
2. **Upload Quotes**: Upload vendor quotes in PDF, image, or text format
3. **Upload Agreements**: Upload legal agreements for analysis
4. **Research Vendors**: Trigger vendor research to get reviews and red flags
5. **View Analytics**: Check the analytics dashboard for comprehensive comparisons and TCO analysis

## API Endpoints

### Questionnaire
- `POST /api/questionnaire` - Submit procurement context

### Uploads
- `POST /api/upload/quote` - Upload vendor quote
- `POST /api/upload/agreement` - Upload legal agreement

### Analysis
- `POST /api/research/vendor` - Research vendor
- `POST /api/analyze/tco` - Analyze Total Cost of Ownership

### Data Retrieval
- `GET /api/comparison/{context_id}` - Get vendor comparison
- `GET /api/analytics/{context_id}` - Get analytics dashboard data

## Project Structure

```
procure ai cursor/
├── backend/
│   ├── agents/
│   │   ├── price_comparison_agent.py
│   │   ├── legal_analysis_agent.py
│   │   ├── vendor_research_agent.py
│   │   └── tco_agent.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Questionnaire.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── UploadQuotes.jsx
│   │   │   ├── UploadAgreements.jsx
│   │   │   └── Analytics.jsx
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## Future Enhancements

- Integration with OpenAI GPT-4 for better document parsing
- Real vendor research API integration (Google Reviews, BBB, etc.)
- Email integration for automatic quote extraction
- Multi-language support
- Advanced analytics and machine learning recommendations
- Export reports (PDF, Excel)
- User authentication and multi-user support

## Vendor Research with Gemini AI

The vendor research agent uses **Google Gemini API with Google Search grounding** to:
- Search the web in real-time for vendor information
- Analyze reviews from multiple sources (Google Reviews, BBB, Trustpilot)
- Detect red flags (lawsuits, complaints, fraud reports, etc.)
- Calculate reputation scores based on real data
- Provide actionable recommendations

### How It Works

1. **Web Search**: Gemini searches Google for vendor information
2. **Multi-Source Analysis**: Gathers data from reviews, news, BBB, and other sources
3. **Red Flag Detection**: AI analyzes content for:
   - Legal issues and lawsuits
   - Customer complaints
   - Financial instability
   - Negative press coverage
   - Scam reports
   - Delivery/service issues
4. **Structured Output**: Returns JSON with reputation scores, red flags, and recommendations

### Getting Your Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key and add it to your `.env` file

**Note**: Gemini API has a free tier with generous limits. Check [pricing](https://ai.google.dev/pricing) for details.

## Notes

- Vendor research requires a Gemini API key. Without it, the research feature will be disabled.
- The current implementation uses rule-based parsing for document extraction. For production, you can integrate with OpenAI API for better accuracy.
- TCO calculations use estimated percentages. Adjust based on your industry standards.

## License

MIT

