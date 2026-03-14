# Setting Up Gemini API for Vendor Research

## Quick Setup Guide

### 1. Get Your Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Copy the generated API key

### 2. Configure Environment Variable

**Option A: Using .env file (Recommended)**

Create a `.env` file in the `backend` directory:

```bash
cd backend
echo "GEMINI_API_KEY=your_api_key_here" > .env
```

**Option B: Export as environment variable**

```bash
export GEMINI_API_KEY=your_api_key_here
```

**Option C: Set in your shell profile**

Add to `~/.zshrc` or `~/.bashrc`:
```bash
export GEMINI_API_KEY=your_api_key_here
```

### 3. Verify Setup

Run the backend server. If the API key is correctly set, you'll see no errors. If not set, vendor research will be disabled with a clear error message.

## How It Works

The vendor research agent uses **Google Gemini AI** with web search capabilities to:

1. **Search the Web**: Automatically searches Google for vendor information
2. **Analyze Multiple Sources**: 
   - Google Reviews
   - Better Business Bureau (BBB)
   - News articles
   - Legal records
   - Social media mentions
3. **Detect Red Flags**:
   - Lawsuits and legal issues
   - Customer complaints
   - Financial problems
   - Negative press
   - Scam reports
   - Delivery/service issues
4. **Generate Reports**: Structured JSON with reputation scores, red flags, and recommendations

## API Costs

- **Free Tier**: Gemini API offers generous free tier
- **Pricing**: Check [Google AI Pricing](https://ai.google.dev/pricing) for current rates
- **Cost per Research**: Approximately $0.01-0.05 per vendor research (depending on model)

## Models Used

The system tries these models in order:
1. `gemini-1.5-pro` - Most capable, best for complex research
2. `gemini-1.5-flash` - Faster and cheaper, good for most cases
3. `gemini-pro` - Fallback option

## Troubleshooting

### Error: "GEMINI_API_KEY environment variable is required"
- Make sure you've set the API key (see step 2 above)
- Restart your backend server after setting the key

### Error: "Failed to initialize Gemini model"
- Check your API key is valid
- Verify you have internet connection
- Check [Google AI Studio](https://makersuite.google.com/app/apikey) to ensure your API key is active

### Research returns errors
- The API might be rate-limited (free tier has limits)
- Check your API quota in Google Cloud Console
- Wait a few minutes and try again

## Testing

To test if vendor research is working:

1. Start the backend server
2. Upload a vendor quote
3. Click "Research Vendor" or use the API endpoint:
   ```bash
   curl -X POST "http://localhost:8000/api/research/vendor?vendor_name=TestVendor&context_id=your_context_id"
   ```

## Security Notes

- **Never commit your API key to git**
- The `.env` file is already in `.gitignore`
- Keep your API key secure and don't share it publicly
- Rotate your API key if it's exposed

