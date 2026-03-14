# Google Reviews Integration Guide

## Current Implementation

The vendor research agent currently uses Gemini AI to search for and extract Google Reviews information. However, for production use with **actual real-time Google Reviews data**, you should integrate one of the following APIs:

## Option 1: SerpAPI (Recommended - Easiest)

SerpAPI provides a simple Python API to extract Google Reviews.

### Setup:
1. Sign up at https://serpapi.com/
2. Get your API key
3. Install: `pip install google-search-results`
4. Add to `.env`: `SERPAPI_KEY=your_key_here`

### Code Integration:
```python
from serpapi import GoogleSearch

def get_google_reviews(vendor_name: str):
    params = {
        "engine": "google_maps",
        "q": vendor_name,
        "api_key": os.getenv("SERPAPI_KEY")
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    
    # Extract reviews from results
    if "local_results" in results:
        place = results["local_results"][0]
        return {
            "rating": place.get("rating"),
            "review_count": place.get("reviews"),
            "reviews": place.get("reviews_data", [])
        }
```

## Option 2: Google Custom Search API

### Setup:
1. Go to https://console.cloud.google.com/
2. Enable Custom Search API
3. Create a Custom Search Engine at https://programmablesearchengine.google.com/
4. Get API key and Search Engine ID
5. Add to `.env`: 
   - `GOOGLE_API_KEY=your_key`
   - `GOOGLE_SEARCH_ENGINE_ID=your_id`

### Code Integration:
```python
import requests

def search_google_reviews(vendor_name: str):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": os.getenv("GOOGLE_API_KEY"),
        "cx": os.getenv("GOOGLE_SEARCH_ENGINE_ID"),
        "q": f"{vendor_name} Google reviews"
    }
    response = requests.get(url, params=params)
    # Parse results...
```

## Option 3: google-maps-reviews Library

### Setup:
1. Install: `pip install google-maps-reviews`
2. Requires Google Maps API key

### Code Integration:
```python
from google_maps_reviews import GoogleMapsReviews

def get_reviews(vendor_name: str):
    reviews = GoogleMapsReviews(api_key=os.getenv("GOOGLE_MAPS_API_KEY"))
    results = reviews.get_reviews(place_name=vendor_name)
    return results
```

## Integration Steps

1. Choose one of the above options
2. Update `vendor_research_agent.py`:
   - Import the chosen library
   - Replace `_search_google_reviews()` method with actual API calls
   - Update `research_vendor()` to use the real data
3. Update `requirements.txt` with the chosen library
4. Add API keys to `.env` file

## Current Behavior

Without API integration, the system uses Gemini AI to:
- Search for vendor information based on training data
- Extract structured review information when available
- Provide Google Reviews URLs for manual verification
- Display review summaries and ratings when found

The frontend is already configured to display:
- Google Reviews ratings (out of 5 stars)
- Review counts
- Recent review snippets
- Links to Google Reviews pages
