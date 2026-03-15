from typing import Dict, Any, List
import os
import json
import requests
from urllib.parse import quote_plus
from serpapi import GoogleSearch


class VendorResearchAgent:
    """Agent for researching vendors, reviews, and identifying red flags using LLM (Local/Ollama or Groq) with web search"""
    
    def __init__(self):
        # Initialize SerpAPI for Google Reviews (required)
        self.serpapi_key = os.getenv("SERPAPI_KEY")
        if not self.serpapi_key:
            raise ValueError("SERPAPI_KEY environment variable is required for Google Reviews")
        
        # Initialize LLM (Local/Ollama or Groq) - same infrastructure as price parsing
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
        self.use_local_llm = False
        self.use_groq = False
        
        # Try to connect to Ollama first (local LLM)
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            if response.status_code == 200:
                self.use_local_llm = True
                print(f"✓ Vendor Research: Using local LLM (Ollama) with model: {self.ollama_model}")
        except Exception:
            self.use_local_llm = False
        
        # Fallback to Groq if Ollama is not available
        if not self.use_local_llm:
            api_key = os.getenv("GROQ_API_KEY")
            if api_key:
                try:
                    from groq import Groq
                    self.groq_client = Groq(api_key=api_key)
                    self.use_groq = True
                    print("✓ Vendor Research: Using Groq AI as fallback")
                except Exception as e:
                    print(f"Warning: Groq AI not available: {e}")
                    self.use_groq = False
            else:
                self.use_groq = False
                print("⚠️ Vendor Research: No LLM available - will use review text analysis only")
        
        self.use_llm = self.use_local_llm or self.use_groq
    
    def _search_google_reviews(self, vendor_name: str) -> Dict[str, Any]:
        """
        Search Google for vendor reviews using SerpAPI
        """
        if not self.serpapi_key:
            return {
                "found": False,
                "rating": None,
                "review_count": None,
                "reviews": [],
                "error": "SERPAPI_UNAVAILABLE",
                "research_unavailable": True,
            }
        
        try:
            # Step 1: Search for the business/company, not just a location
            # Try multiple search strategies to find the actual company
            search_queries = [
                f"{vendor_name} company",
                f"{vendor_name} business reviews",
                f"{vendor_name} vendor",
                vendor_name  # Fallback to original
            ]
            
            place = None
            maps_results = None
            
            # Try each search query until we find relevant results
            for query in search_queries:
                search_params = {
                    "engine": "google_maps",
                    "q": query,
                    "api_key": self.serpapi_key,
                    "type": "search"  # Search for businesses, not just locations
                }
                
                search = GoogleSearch(search_params)
                maps_results = search.get_dict()
                
                # Extract place information
                if "local_results" in maps_results and maps_results["local_results"]:
                    # Filter results to prefer businesses over physical addresses
                    # Look for results that have business info (website, phone, etc.)
                    for result in maps_results["local_results"]:
                        # Prefer results that look like businesses (have website, phone, or business category)
                        has_business_info = result.get("website") or result.get("phone") or result.get("type")
                        # Avoid results that are just addresses without business context
                        is_just_address = result.get("address") and not (result.get("website") or result.get("phone"))
                        
                        if has_business_info and not is_just_address:
                            place = result
                            break
                    
                    # If no business-like result found, use first result but note it might be a location
                    if not place and maps_results["local_results"]:
                        place = maps_results["local_results"][0]
                    
                    if place:
                        break
            
            # If still no results, try regular Google search for reviews
            if not place:
                # Try Google search engine instead of Maps
                web_search_params = {
                    "engine": "google",
                    "q": f"{vendor_name} reviews company",
                    "api_key": self.serpapi_key
                }
                web_search = GoogleSearch(web_search_params)
                web_results = web_search.get_dict()
                
                # Check if we got any useful results
                if "organic_results" in web_results and web_results["organic_results"]:
                    # Found web results but not Maps - return with note
                    return {
                        "found": False,
                        "rating": None,
                        "review_count": None,
                        "reviews": [],
                        "error": f"Found web results for '{vendor_name}' but no Google Maps business listing. The vendor may not have a physical location or Google Maps presence."
                    }
                
                return {
                    "found": False,
                    "rating": None,
                    "review_count": None,
                    "reviews": [],
                    "error": f"No Google Maps business found for '{vendor_name}'. Try searching with the full company name or check if the vendor has a Google Business profile."
                }
            place_id = place.get("data_id") or place.get("place_id")
            
            if not place_id:
                # If no place_id, return basic info from search results
                rating = place.get("rating")
                review_count = place.get("reviews")
                gps_coordinates = place.get("gps_coordinates", {})
                
                return {
                    "found": True,
                    "rating": rating,
                    "review_count": review_count,
                    "reviews": [],
                    "url": place.get("website") or place.get("gps_coordinates"),
                    "location": place.get("address"),
                    "note": "Basic info found, detailed reviews require place_id"
                }
            
            # Step 2: Get detailed reviews using place_id
            reviews_params = {
                "engine": "google_maps_reviews",
                "data_id": place_id,
                "api_key": self.serpapi_key,
                "sort_by": "newestFirst",  # Get newest reviews first
                "hl": "en"  # Language
            }
            
            reviews_search = GoogleSearch(reviews_params)
            reviews_results = reviews_search.get_dict()
            
            # Extract review data
            reviews_data = reviews_results.get("reviews", [])
            recent_reviews = []
            
            # Get up to 5 recent reviews
            for review in reviews_data[:5]:
                review_text = review.get("snippet", "")
                if review_text:
                    recent_reviews.append(review_text)
            
            # Get overall rating and review count
            rating = place.get("rating") or reviews_results.get("rating")
            review_count = place.get("reviews") or reviews_results.get("total_reviews")
            
            # Build Google Maps URL
            gps = place.get("gps_coordinates", {})
            if gps:
                lat = gps.get("latitude")
                lng = gps.get("longitude")
                maps_url = f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
            else:
                maps_url = f"https://www.google.com/maps/search/?api=1&query={quote_plus(vendor_name)}"
            
            # Get business name from place to verify it matches vendor
            business_name = place.get("title") or place.get("name", "")
            address = place.get("address", "")
            
            # Warn if the found business doesn't seem to match the vendor name
            # (e.g., if vendor is "A" but found "Emandal Farm" - that's a mismatch)
            warning = None
            if business_name and vendor_name.lower() not in business_name.lower() and business_name.lower() not in vendor_name.lower():
                # Check if it's a very short vendor name (like "A" or "B") - those will always mismatch
                if len(vendor_name) <= 2:
                    warning = f"Note: Found business '{business_name}' - verify this matches vendor '{vendor_name}'"
                elif len(business_name) > len(vendor_name) * 2:
                    # Found business name is much longer - might be wrong match
                    warning = f"Note: Found business '{business_name}' - verify this matches vendor '{vendor_name}'"
            
            return {
                "found": True,
                "rating": rating,
                "review_count": review_count,
                "reviews": recent_reviews,
                "url": maps_url,
                "location": address,
                "place_id": place_id,
                "business_name": business_name,  # Include business name for verification
                "warning": warning  # Include warning if mismatch detected
            }
            
        except Exception as e:
            import traceback
            err_msg = str(e).lower()
            is_connection_error = (
                "connection" in err_msg or "refused" in err_msg or "timeout" in err_msg
                or "errno" in err_msg or "network" in err_msg or "unavailable" in err_msg
            )
            print(f"Error searching Google reviews with SerpAPI: {e}")
            traceback.print_exc()
            return {
                "found": False,
                "rating": None,
                "review_count": None,
                "reviews": [],
                "error": "SERPAPI_UNAVAILABLE" if is_connection_error else str(e),
                "research_unavailable": is_connection_error,
            }
    
    def _detect_red_flags_from_reviews(self, review_texts: List[str], rating: float = None) -> List[Dict[str, Any]]:
        """Detect red flags from review text analysis"""
        red_flags = []
        
        if not review_texts:
            return red_flags
        
        # Combine all review text
        all_reviews_text = " ".join(review_texts).lower()
        
        # Red flag patterns to detect
        red_flag_patterns = {
            "Customer Complaints": {
                "keywords": ["complaint", "disappointed", "terrible", "awful", "horrible", "worst", "never again", "avoid", "scam", "fraud", "ripoff", "waste of money"],
                "severity": "medium"
            },
            "Service Quality Issues": {
                "keywords": ["poor service", "bad service", "slow", "delayed", "late delivery", "broken", "defective", "damaged", "doesn't work", "not working"],
                "severity": "medium"
            },
            "Communication Problems": {
                "keywords": ["no response", "ignored", "unresponsive", "poor communication", "can't reach", "no reply"],
                "severity": "low"
            },
            "Financial Concerns": {
                "keywords": ["overcharged", "hidden fees", "billing issue", "refund", "chargeback", "dispute"],
                "severity": "medium"
            },
            "Legal/Regulatory Issues": {
                "keywords": ["lawsuit", "sued", "legal action", "violation", "investigation", "regulatory"],
                "severity": "high"
            },
            "Security/Privacy Issues": {
                "keywords": ["data breach", "hacked", "privacy", "security issue", "leaked"],
                "severity": "high"
            }
        }
        
        # Check for each red flag type
        for flag_type, pattern_info in red_flag_patterns.items():
            keywords = pattern_info["keywords"]
            severity = pattern_info["severity"]
            
            # Count how many keywords appear in reviews
            matches = [kw for kw in keywords if kw in all_reviews_text]
            
            if matches:
                # Count occurrences
                match_count = sum(all_reviews_text.count(kw) for kw in matches)
                
                # Flag if:
                # 1. It appears multiple times (2+), OR
                # 2. It's a high-severity keyword (even once), OR
                # 3. It appears at least once (we want to catch isolated issues too)
                if match_count >= 1:  # Changed from 2 to 1 - catch even isolated issues
                    # Find specific review snippets mentioning this
                    relevant_reviews = []
                    for review in review_texts:
                        review_lower = review.lower()
                        if any(kw in review_lower for kw in matches):
                            relevant_reviews.append(review[:200])  # First 200 chars
                    
                    # Adjust severity based on frequency and type
                    # High/critical severity keywords are always high/critical
                    # But if it only appears once and is medium/low severity, make it low severity
                    final_severity = severity
                    if match_count == 1 and severity not in ["high", "critical"]:
                        final_severity = "low"  # Isolated issue gets lower severity
                    elif match_count >= 3 and severity == "low":
                        final_severity = "medium"  # Multiple occurrences of low-severity issue becomes medium
                    
                    red_flags.append({
                        "type": flag_type,
                        "severity": final_severity,
                        "description": f"Found {match_count} mention(s) of {flag_type.lower()} in customer reviews. Keywords detected: {', '.join(matches[:3])}",
                        "source": "Google Reviews Analysis",
                        "review_snippets": relevant_reviews[:3]  # Up to 3 relevant snippets
                    })
        
        # Check for low ratings as a red flag
        # Note: We analyze review text regardless of rating, but low ratings are additional red flags
        if rating and rating < 3.0:
            red_flags.append({
                "type": "Low Rating",
                "severity": "medium",
                "description": f"Very low Google rating: {rating}/5 stars. This indicates significant customer dissatisfaction.",
                "source": "Google Reviews",
            })
        elif rating and rating < 3.5:
            red_flags.append({
                "type": "Below Average Rating",
                "severity": "low",
                "description": f"Below average Google rating: {rating}/5 stars. Review customer feedback carefully.",
                "source": "Google Reviews",
            })
        # Even high ratings can have red flags in review text - we analyze text regardless of rating
        
        return red_flags
    
    def _create_research_result_from_serpapi(self, vendor_name: str, google_reviews_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create research result using only SerpAPI Google Reviews data (no LLM)"""
        
        reviews = []
        
        # Add Google Reviews data from SerpAPI
        if google_reviews_data.get("found"):
            rating = google_reviews_data.get("rating")
            review_count = google_reviews_data.get("review_count")
            
            # Build summary with business name if available, location only if relevant
            business_name = google_reviews_data.get("business_name", "")
            location = google_reviews_data.get("location", "")
            warning = google_reviews_data.get("warning", "")
            
            # Create summary - prefer business name over location
            if business_name:
                summary = f"Found business: {business_name}"
                if warning:
                    summary += f" ({warning})"
            elif location:
                summary = f"Found on Google Maps at {location}"
            else:
                summary = "Found on Google Maps"
            
            google_review_entry = {
                "source": "Google Reviews",
                "rating": rating,
                "review_count": review_count,
                "summary": summary,
                "recent_reviews": google_reviews_data.get("reviews", []),
                "url": google_reviews_data.get("url", f"https://www.google.com/search?q={quote_plus(vendor_name + ' reviews')}"),
                "business_name": business_name,
                "warning": warning
            }
            reviews.append(google_review_entry)
            
            # Calculate reputation score from Google rating (convert 5-star to 0-100)
            if rating:
                reputation_score = int((rating / 5) * 100)
            else:
                reputation_score = 50
        else:
            error_msg = google_reviews_data.get("error", "Google Reviews not found")
            research_unavailable = google_reviews_data.get("research_unavailable") or "SERPAPI_UNAVAILABLE" in str(error_msg)
            reviews.append({
                "source": "Google Reviews",
                "rating": None,
                "review_count": None,
                "summary": "Vendor research unavailable — add SerpAPI key to enable" if research_unavailable else f"Search performed: {error_msg}",
                "recent_reviews": [],
                "url": f"https://www.google.com/search?q={quote_plus(vendor_name + ' reviews')}"
            })
            reputation_score = 50
        
        # Detect red flags from review text
        red_flags = self._detect_red_flags_from_reviews(google_reviews_data.get("reviews", []), google_reviews_data.get("rating"))
        
        # Create recommendations based on Google Reviews
        recommendations = []
        if google_reviews_data.get("found"):
            rating = google_reviews_data.get("rating")
            if rating:
                if rating >= 4.5:
                    recommendations.append(f"✅ Excellent Google rating: {rating}/5 stars")
                elif rating >= 4.0:
                    recommendations.append(f"✅ Good Google rating: {rating}/5 stars")
                elif rating >= 3.5:
                    recommendations.append(f"⚠️ Moderate Google rating: {rating}/5 stars - review carefully")
                else:
                    recommendations.append(f"⚠️ Low Google rating: {rating}/5 stars - consider alternatives")
            
            review_count = google_reviews_data.get("review_count")
            if review_count:
                recommendations.append(f"Based on {review_count} Google reviews")
            
            # Add red flag recommendations
            if red_flags:
                high_severity = [f for f in red_flags if f.get("severity") in ["high", "critical"]]
                if high_severity:
                    recommendations.insert(0, f"⚠️ CRITICAL: {len(high_severity)} high-severity red flags detected from reviews.")
                else:
                    recommendations.insert(0, f"⚠️ {len(red_flags)} red flag(s) detected from customer reviews.")
            else:
                recommendations.insert(0, "✅ No red flags detected in customer reviews.")
        else:
            recommendations.append("⚠️ Google Reviews not found. Please verify vendor information manually.")
        
        research_unavailable = google_reviews_data.get("research_unavailable") or "SERPAPI_UNAVAILABLE" in str(google_reviews_data.get("error", ""))
        return {
            "vendor_name": vendor_name,
            "reputation_score": reputation_score,
            "reviews": reviews,
            "red_flags": red_flags,
            "research_unavailable": research_unavailable,
            "research_unavailable_message": "Vendor research unavailable — add SerpAPI key to enable" if research_unavailable else None,
            "business_info": {
                "location": google_reviews_data.get("location", "Not specified"),
                "years_in_business": "Not specified",
                "company_size": "Not specified",
                "industry": "Not specified"
            },
            "recent_news": [],
            "recommendations": recommendations
        }
    
    async def research_vendor(self, vendor_name: str) -> Dict[str, Any]:
        """Research vendor for reviews and red flags using SerpAPI for Google Reviews"""
        
        # First, get real Google Reviews using SerpAPI
        google_reviews_data = self._search_google_reviews(vendor_name)
        
        # If LLM is not available, return results based only on SerpAPI data with review analysis
        if not self.use_llm:
            return self._create_research_result_from_serpapi(vendor_name, google_reviews_data)
        
        # Use LLM (Local/Ollama or Groq) for enhanced red flags detection and analysis
        # Create focused research prompt based on actual review data
        review_text = "\n".join([f"- {review}" for review in google_reviews_data.get('reviews', [])[:15]])
        
        research_prompt = f"""
You are a procurement research assistant. Analyze the following vendor's Google Reviews and identify red flags.

Vendor: "{vendor_name}"
Google Rating: {google_reviews_data.get('rating', 'Not available')}/5 stars
Review Count: {google_reviews_data.get('review_count', 'Not available')}
Location: {google_reviews_data.get('location', 'Not available')}

Customer Reviews:
{review_text}

Analyze these reviews and identify red flags. Look for:
- Customer complaints and unresolved issues
- Service quality problems (delays, defects, poor service)
- Communication issues (unresponsive, ignored)
- Financial concerns (overcharging, billing issues, refund problems)
- Legal/regulatory issues (lawsuits, violations, investigations)
- Security/privacy issues (data breaches, hacks)
- Patterns of negative feedback

Return ONLY a JSON object with this structure:
{{
    "red_flags": [
        {{
            "type": "<flag type, e.g., 'Customer Complaints', 'Service Quality Issues', 'Legal Issues'>",
            "severity": "<low|medium|high|critical>",
            "description": "<detailed description with evidence from reviews>",
            "source": "Google Reviews Analysis"
        }}
    ],
    "reputation_score": <0-100 based on rating and review sentiment>,
    "recommendations": [
        "<recommendation 1>",
        "<recommendation 2>"
    ]
}}

IMPORTANT:
- Only report red flags if there's clear evidence in the reviews
- Be factual and specific - cite what reviews say
- Severity: "low" for minor issues, "medium" for significant problems, "high" for serious concerns, "critical" for deal-breakers
- Calculate reputation_score: (rating/5)*100, then adjust down for negative reviews
- Return ONLY valid JSON, no markdown, no code blocks
"""
        
        try:
            # Use Local LLM (Ollama) or Groq
            if self.use_local_llm:
                # Call Ollama API
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": research_prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.2,
                            "num_predict": 3000  # Increased to handle longer responses
                        }
                    },
                    timeout=90  # Increased timeout for longer responses
                )
                
                if response.status_code != 200:
                    raise Exception(f"Ollama API error: {response.status_code}")
                
                response_data = response.json()
                response_text = response_data.get("response", "")
            else:
                # Use Groq
                response = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "You are a procurement research assistant. Analyze vendor reviews and identify red flags. Return only valid JSON."},
                        {"role": "user", "content": research_prompt}
                    ],
                    temperature=0.2
                )
                response_text = response.choices[0].message.content
            
            # Extract JSON from response
            json_str = None
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_str = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                if json_end > json_start:
                    json_str = response_text[json_start:json_end].strip()
            
            if not json_str:
                # Try to find JSON object in the text
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
            
            # If JSON is incomplete (cut off), try to fix it
            if json_str:
                # Check if JSON is incomplete (missing closing braces)
                open_braces = json_str.count("{")
                close_braces = json_str.count("}")
                if open_braces > close_braces:
                    # Add missing closing braces
                    json_str += "}" * (open_braces - close_braces)
                # Check for incomplete arrays
                open_brackets = json_str.count("[")
                close_brackets = json_str.count("]")
                if open_brackets > close_brackets:
                    json_str += "]" * (open_brackets - close_brackets)
                # Remove any trailing incomplete strings
                # If ends with incomplete quote, remove it
                if json_str.count('"') % 2 != 0:
                    # Find last unclosed quote and remove everything after it
                    last_quote = json_str.rfind('"')
                    if last_quote > 0:
                        # Check if it's inside a string (has odd number of quotes before it)
                        quotes_before = json_str[:last_quote].count('"')
                        if quotes_before % 2 == 0:  # This quote starts a string
                            # Find the start of this incomplete string value
                            # Look backwards for the colon or comma before this
                            for i in range(last_quote - 1, -1, -1):
                                if json_str[i] in [':', ',']:
                                    json_str = json_str[:i+1] + '"' + json_str[last_quote+1:]
                                    break
            
            if not json_str:
                raise ValueError("No JSON found in response")
            
            # Parse JSON with better error handling
            try:
                llm_analysis = json.loads(json_str)
            except json.JSONDecodeError as parse_error:
                import sys
                print(f"[Vendor Research] JSON parse error for {vendor_name}: {parse_error}", file=sys.stderr, flush=True)
                print(f"[Vendor Research] Attempted to parse: {json_str[:500]}...", file=sys.stderr, flush=True)
                # If JSON parsing fails, fall back to pattern-based detection only
                print(f"[Vendor Research] Falling back to pattern-based detection for {vendor_name}", file=sys.stderr, flush=True)
                return self._create_research_result_from_serpapi(vendor_name, google_reviews_data)
            
            # Merge LLM analysis with SerpAPI data
            # Start with base result from SerpAPI
            base_result = self._create_research_result_from_serpapi(vendor_name, google_reviews_data)
            
            # Enhance with LLM-detected red flags (merge with pattern-based detection)
            llm_red_flags = llm_analysis.get("red_flags", [])
            existing_red_flags = base_result.get("red_flags", [])
            
            # Combine red flags, avoiding duplicates
            all_red_flags = existing_red_flags.copy()
            for llm_flag in llm_red_flags:
                # Check if similar flag already exists
                flag_type = llm_flag.get("type", "")
                if not any(f.get("type") == flag_type for f in all_red_flags):
                    all_red_flags.append(llm_flag)
            
            base_result["red_flags"] = all_red_flags
            
            # Use LLM reputation score if provided, otherwise keep SerpAPI score
            if llm_analysis.get("reputation_score") is not None:
                base_result["reputation_score"] = llm_analysis.get("reputation_score")
            
            # Merge recommendations
            llm_recommendations = llm_analysis.get("recommendations", [])
            base_result["recommendations"].extend(llm_recommendations)
            
            return base_result
            
        except json.JSONDecodeError as e:
            # If JSON parsing fails, create a structured response from text
            return {
                "vendor_name": vendor_name,
                "reputation_score": 50,
                "reviews": [],
                "red_flags": [],
                "recommendations": [
                    "⚠️ Unable to parse AI response. Please review manually.",
                    f"Raw response: {response_text[:500]}"
                ],
                "raw_response": response_text,
                "error": str(e)
            }
        except Exception as e:
            # Fallback response
            return {
                "vendor_name": vendor_name,
                "reputation_score": 50,
                "reviews": [],
                "red_flags": [{
                    "type": "Research Error",
                    "severity": "medium",
                    "description": f"Failed to research vendor: {str(e)}",
                    "source": "System",
                    "recommendation": "Please research this vendor manually."
                }],
                "recommendations": [
                    f"⚠️ Error during research: {str(e)}",
                    "Please verify vendor information manually."
                ],
                "error": str(e)
            }
    
    def compare_vendors(self, research_data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare research data for multiple vendors"""
        if not research_data_list:
            return {"error": "No vendor research data to compare"}
        
        comparison = {
            "vendors": [],
            "highest_reputation": None,
            "lowest_reputation": None,
            "most_red_flags": None,
            "least_red_flags": None,
            "recommendations": []
        }
        
        highest_score = -1
        lowest_score = 101
        most_flags_count = -1
        least_flags_count = float('inf')
        
        for research in research_data_list:
            vendor_name = research.get("vendor_name", "Unknown")
            reputation = research.get("reputation_score", 0)
            red_flags = research.get("red_flags", [])
            red_flags_count = len(red_flags)
            high_severity_count = len([f for f in red_flags if f.get("severity") in ["high", "critical"]])
            
            comparison["vendors"].append({
                "name": vendor_name,
                "reputation_score": reputation,
                "red_flags_count": red_flags_count,
                "high_severity_flags": high_severity_count,
                "red_flags": red_flags,
                "reviews_summary": research.get("reviews", [])
            })
            
            if reputation > highest_score:
                highest_score = reputation
                comparison["highest_reputation"] = vendor_name
            
            if reputation < lowest_score:
                lowest_score = reputation
                comparison["lowest_reputation"] = vendor_name
            
            if red_flags_count > most_flags_count:
                most_flags_count = red_flags_count
                comparison["most_red_flags"] = vendor_name
            
            if red_flags_count < least_flags_count:
                least_flags_count = red_flags_count
                comparison["least_red_flags"] = vendor_name
        
        # Generate recommendations
        if comparison["highest_reputation"]:
            comparison["recommendations"].append(
                f"✅ Highest reputation: {comparison['highest_reputation']} ({highest_score}/100)"
            )
        
        if comparison["most_red_flags"]:
            comparison["recommendations"].append(
                f"⚠️ Most red flags: {comparison['most_red_flags']} ({most_flags_count} flags)"
            )
        
        if comparison["least_red_flags"]:
            comparison["recommendations"].append(
                f"✅ Least red flags: {comparison['least_red_flags']} ({least_flags_count} flags)"
            )
        
        # Overall recommendation
        best_vendor = None
        best_score = -1
        
        for vendor_data in comparison["vendors"]:
            # Calculate composite score: reputation - (red_flags * 10) - (high_severity_flags * 20)
            composite_score = (
                vendor_data["reputation_score"] - 
                (vendor_data["red_flags_count"] * 10) - 
                (vendor_data["high_severity_flags"] * 20)
            )
            
            if composite_score > best_score:
                best_score = composite_score
                best_vendor = vendor_data["name"]
        
        if best_vendor:
            comparison["recommendations"].insert(0,
                f"🏆 Recommended vendor based on reputation and red flags: {best_vendor}")
        
        return comparison
