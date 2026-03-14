# SerpAPI Setup Instructions

## Quick Setup

1. **Install the SerpAPI library:**
   ```bash
   cd backend
   pip install google-search-results
   ```

2. **Add your SerpAPI key to `.env` file:**
   
   Open `backend/.env` and add:
   ```
   SERPAPI_KEY=091ab814702d6c04abb1b4eb3bbb8328f4878e7fee10e5030658f4437245ad06
   ```

3. **Restart the backend server:**
   ```bash
   python main.py
   ```

## How It Works

The system now uses SerpAPI to fetch **real Google Reviews** for vendors:

1. When you click "Refresh" on a vendor in the Reviews Comparison page
2. The system searches Google Maps for the vendor name
3. Extracts the Google rating (out of 5 stars)
4. Gets the review count
5. Fetches up to 5 recent review snippets
6. Provides a direct link to Google Maps/Reviews

## What You'll See

- **Google Reviews Rating**: Real rating from Google (e.g., 4.5/5 stars)
- **Review Count**: Actual number of reviews (e.g., "1,234 reviews")
- **Recent Reviews**: Up to 5 recent customer review snippets
- **Google Maps Link**: Direct link to view all reviews

## Testing

1. Go to the Reviews Comparison page
2. Click "Refresh" on any vendor
3. You should see real Google Reviews data appear!

## Notes

- SerpAPI has usage limits based on your plan
- Free tier: 100 searches/month
- The system will fall back to Gemini AI if SerpAPI fails
