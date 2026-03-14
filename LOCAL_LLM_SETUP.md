# Local LLM Setup for Procurement AI

## Overview
The project now supports **local LLM parsing** using Ollama, which eliminates the need for rule-based word detection and provides more accurate parsing across all document types.

## Supported File Types
The system can now parse:
- ✅ **PDFs** (.pdf)
- ✅ **Word Documents** (.docx, .doc)
- ✅ **Text Files** (.txt)
- ✅ **Emails** (.eml, .msg, or text content)
- ✅ **Images** (via OCR)

## Local LLM Setup (Ollama)

### 1. Install Ollama
Visit https://ollama.ai and install Ollama for your operating system.

### 2. Pull a Model
```bash
# Recommended model (smaller, faster)
ollama pull llama3.2

# Or use a larger model for better accuracy
ollama pull llama3.1:70b
```

### 3. Configure Environment Variables (Optional)
```bash
# In your .env file or environment
export OLLAMA_URL=http://localhost:11434  # Default
export OLLAMA_MODEL=llama3.2              # Default
```

### 4. Start Ollama
Ollama runs automatically when you start the service. Make sure it's running:
```bash
ollama serve
```

## How It Works

1. **Automatic Detection**: The system automatically detects if Ollama is available
2. **Fallback**: If Ollama is not available, it falls back to Groq (if API key is set) or regex parsing
3. **LLM Parsing**: Uses the local LLM to intelligently extract:
   - Products and their names
   - Pricing information (unit prices, totals, quantity tiers)
   - Payment terms
   - Warranties
   - Delivery information
   - Fees and additional charges

## Benefits

- ✅ **No API Costs**: Runs completely locally
- ✅ **Privacy**: All data stays on your machine
- ✅ **Better Accuracy**: LLM understands context better than regex
- ✅ **Handles All Formats**: Works with emails, PDFs, Word docs, and text
- ✅ **No Rule-Based Limitations**: Adapts to different quote formats automatically

## Testing

The system will automatically use Ollama if available. Check the backend logs to see:
- `✓ Using local LLM (Ollama) with model: llama3.2` - Local LLM is active
- `✓ Using Groq AI as fallback` - Using cloud-based Groq
- `⚠️ No LLM available - will use regex fallback only` - Using basic regex parsing

## Troubleshooting

### Ollama not detected?
1. Make sure Ollama is running: `ollama serve`
2. Check if the model is downloaded: `ollama list`
3. Verify the URL: `curl http://localhost:11434/api/tags`

### Slow parsing?
- Use a smaller model: `ollama pull llama3.2` (instead of 70b)
- The system will still work, just slower

### Want to use Groq instead?
- Set `GROQ_API_KEY` in your environment
- The system will automatically use Groq if Ollama is not available

