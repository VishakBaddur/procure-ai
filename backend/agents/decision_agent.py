from typing import Dict, Any, List
import json
import os
import requests


class DecisionAgent:
    """Agent for generating vendor recommendations and decision assistance"""
    
    def __init__(self):
        # Initialize LLM (Local/Ollama or Groq) - same infrastructure as other agents
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
        self.use_local_llm = False
        self.use_groq = False
        
        # Try to connect to Ollama first (local LLM)
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            if response.status_code == 200:
                self.use_local_llm = True
                print(f"✓ Decision Agent: Using local LLM (Ollama) with model: {self.ollama_model}")
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
                    print("✓ Decision Agent: Using Groq AI as fallback")
                except Exception as e:
                    print(f"Warning: Groq AI not available: {e}")
                    self.use_groq = False
            else:
                self.use_groq = False
                print("⚠️ Decision Agent: No LLM available - will use rule-based recommendations")
        
        self.use_llm = self.use_local_llm or self.use_groq
    
    async def generate_recommendation(
        self,
        vendors_data: List[Dict[str, Any]],
        project_name: str,
        item_name: str
    ) -> Dict[str, Any]:
        """
        Generate comprehensive vendor recommendation with pros/cons, confidence, and assumptions
        
        Args:
            vendors_data: List of vendor data including pricing, reviews, red flags, TCO
            project_name: Name of the procurement project
            item_name: Item being procured
        """
        
        if not vendors_data:
            return {
                "recommended_vendor": None,
                "confidence": "low",
                "reasoning": "No vendor data available",
                "pros": [],
                "cons": [],
                "assumptions": [],
                "alternatives": []
            }
        
        # If LLM is available, use it for intelligent recommendation
        if self.use_llm:
            return await self._generate_llm_recommendation(vendors_data, project_name, item_name)
        else:
            # Fallback to rule-based recommendation
            return self._generate_rule_based_recommendation(vendors_data)
    
    async def _generate_llm_recommendation(
        self,
        vendors_data: List[Dict[str, Any]],
        project_name: str,
        item_name: str
    ) -> Dict[str, Any]:
        """Use LLM to generate intelligent recommendation"""
        
        # Prepare vendor summary data
        vendor_summaries = []
        for vendor in vendors_data:
            pricing = vendor.get("pricing", {})
            reviews = vendor.get("reviews", {})
            tco = vendor.get("tco", {})
            
            summary = {
                "vendor_name": vendor.get("vendor_name", "Unknown"),
                "initial_price": pricing.get("total_price", 0),
                "reputation_score": reviews.get("reputation_score", 50),
                "red_flags_count": len(reviews.get("red_flags", [])),
                "red_flags": reviews.get("red_flags", []),
                "total_tco": tco.get("total_tco", 0),
                "durability_score": tco.get("durability_score", 50),
                "review_count": sum(r.get("review_count", 0) or 0 for r in reviews.get("reviews", [])),
                "average_rating": self._calculate_average_rating(reviews.get("reviews", []))
            }
            vendor_summaries.append(summary)
        
        prompt = f"""
You are a procurement decision assistant. Analyze the following vendors and recommend the best overall vendor for this procurement.

Project: {project_name}
Item: {item_name}

Vendor Data:
{json.dumps(vendor_summaries, indent=2)}

Analyze each vendor considering:
1. **Pricing**: Initial cost vs Total Cost of Ownership (TCO)
2. **Risk**: Reputation score, red flags, review quality
3. **Value**: Balance of cost, quality, and risk
4. **Reliability**: Durability score, warranty, vendor stability

Generate a comprehensive recommendation with:
- **Recommended Vendor**: The best overall choice
- **Confidence Level**: "high", "medium", or "low" based on data quality and vendor differences
- **Reasoning**: 2-3 sentence explanation of why this vendor was chosen
- **Pros**: 3-5 key advantages of the recommended vendor
- **Cons**: 2-3 potential concerns or limitations
- **Assumptions**: Key assumptions made in the analysis (e.g., "Assumed 5-year usage period", "Based on available review data")
- **Alternatives**: If another vendor is close, mention them with brief comparison

Return ONLY a JSON object with this structure:
{{
    "recommended_vendor": "<vendor name>",
    "confidence": "<high|medium|low>",
    "reasoning": "<2-3 sentence explanation>",
    "pros": [
        "<advantage 1>",
        "<advantage 2>",
        "<advantage 3>"
    ],
    "cons": [
        "<concern 1>",
        "<concern 2>"
    ],
    "assumptions": [
        "<assumption 1>",
        "<assumption 2>"
    ],
    "alternatives": [
        {{
            "vendor_name": "<vendor name>",
            "comparison": "<brief comparison>"
        }}
    ]
}}

IMPORTANT:
- Be objective and data-driven
- Consider both short-term cost and long-term value
- Factor in risk (red flags, reputation)
- If vendors are very close, confidence should be "medium" or "low"
- Return ONLY valid JSON, no markdown, no code blocks
"""
        
        try:
            if self.use_local_llm:
                # Call Ollama API
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 2000
                        }
                    },
                    timeout=60
                )
                
                if response.status_code != 200:
                    raise Exception(f"Ollama API error: {response.status_code}")
                
                response_data = response.json()
                response_text = response_data.get("response", "")
            else:
                # Use Groq
                response = self.groq_client.chat.completions.create(
                    model="llama-3.1-70b-versatile",
                    messages=[
                        {"role": "system", "content": "You are a procurement decision assistant. Analyze vendor data and provide recommendations. Return only valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3
                )
                response_text = response.choices[0].message.content
            
            # Extract JSON from response
            json_str = self._extract_json(response_text)
            recommendation = json.loads(json_str)
            
            # Validate and enhance recommendation
            recommendation.setdefault("confidence", "medium")
            recommendation.setdefault("pros", [])
            recommendation.setdefault("cons", [])
            recommendation.setdefault("assumptions", [])
            recommendation.setdefault("alternatives", [])
            
            return recommendation
            
        except Exception as e:
            import sys
            print(f"[Decision Agent] LLM recommendation failed: {e}", file=sys.stderr, flush=True)
            # Fallback to rule-based
            return self._generate_rule_based_recommendation(vendors_data)
    
    def _generate_rule_based_recommendation(
        self,
        vendors_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate recommendation using rule-based logic"""
        
        if not vendors_data:
            return {
                "recommended_vendor": None,
                "confidence": "low",
                "reasoning": "No vendor data available",
                "pros": [],
                "cons": [],
                "assumptions": [],
                "alternatives": []
            }
        
        # Calculate composite scores for each vendor
        vendor_scores = []
        for vendor in vendors_data:
            pricing = vendor.get("pricing", {})
            reviews = vendor.get("reviews", {})
            tco = vendor.get("tco", {})
            
            initial_price = pricing.get("total_price", float('inf'))
            total_tco = tco.get("total_tco", initial_price)
            reputation = reviews.get("reputation_score", 50)
            red_flags_count = len(reviews.get("red_flags", []))
            durability = tco.get("durability_score", 50)
            
            # Composite score: lower TCO is better, higher reputation is better, fewer red flags is better
            # Normalize: TCO (lower = better), Reputation (higher = better), Red flags (fewer = better)
            # Score = (reputation/100) * 40 + (100-durability)/100 * 20 - (red_flags_count * 5) - (total_tco/max_tco * 40)
            max_tco = max([v.get("tco", {}).get("total_tco", 0) for v in vendors_data] + [total_tco])
            if max_tco == 0:
                max_tco = 1
            
            score = (
                (reputation / 100) * 40 +
                (durability / 100) * 20 -
                (red_flags_count * 5) -
                ((total_tco / max_tco) * 40)
            )
            
            vendor_scores.append({
                "vendor_name": vendor.get("vendor_name", "Unknown"),
                "score": score,
                "initial_price": initial_price,
                "total_tco": total_tco,
                "reputation": reputation,
                "red_flags_count": red_flags_count,
                "durability": durability
            })
        
        # Sort by score (highest is best)
        vendor_scores.sort(key=lambda x: x["score"], reverse=True)
        best = vendor_scores[0]
        second_best = vendor_scores[1] if len(vendor_scores) > 1 else None
        
        # Determine confidence based on score difference
        score_diff = best["score"] - (second_best["score"] if second_best else best["score"] - 10)
        if score_diff > 15:
            confidence = "high"
        elif score_diff > 5:
            confidence = "medium"
        else:
            confidence = "low"
        
        # Generate pros/cons
        pros = []
        cons = []
        
        if best["total_tco"] < sum(v["total_tco"] for v in vendor_scores) / len(vendor_scores):
            pros.append(f"Best Total Cost of Ownership (${best['total_tco']:,.2f})")
        if best["reputation"] >= 80:
            pros.append(f"High reputation score ({best['reputation']}/100)")
        if best["red_flags_count"] == 0:
            pros.append("No red flags detected")
        if best["durability"] >= 70:
            pros.append(f"High durability score ({best['durability']:.1f}/100)")
        
        if best["red_flags_count"] > 0:
            cons.append(f"{best['red_flags_count']} red flag(s) detected")
        if best["reputation"] < 70:
            cons.append(f"Moderate reputation score ({best['reputation']}/100)")
        
        alternatives = []
        if second_best:
            alternatives.append({
                "vendor_name": second_best["vendor_name"],
                "comparison": f"Close second choice with TCO ${second_best['total_tco']:,.2f} vs ${best['total_tco']:,.2f}"
            })
        
        return {
            "recommended_vendor": best["vendor_name"],
            "confidence": confidence,
            "reasoning": f"{best['vendor_name']} offers the best balance of cost (TCO: ${best['total_tco']:,.2f}), reputation ({best['reputation']}/100), and risk ({best['red_flags_count']} red flags).",
            "pros": pros,
            "cons": cons if cons else ["No significant concerns identified"],
            "assumptions": [
                "Analysis based on 5-year TCO period",
                "Risk multiplier applied based on reputation score",
                "Red flags weighted in decision"
            ],
            "alternatives": alternatives
        }
    
    def _calculate_average_rating(self, reviews: List[Dict[str, Any]]) -> float:
        """Calculate average rating from reviews"""
        ratings = []
        for review in reviews:
            rating = review.get("rating")
            if rating is not None:
                ratings.append(rating)
        
        if not ratings:
            return 0.0
        
        return sum(ratings) / len(ratings)
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from AI response"""
        if "```json" in text:
            json_start = text.find("```json") + 7
            json_end = text.find("```", json_start)
            return text[json_start:json_end].strip()
        elif "```" in text:
            json_start = text.find("```") + 3
            json_end = text.find("```", json_start)
            if json_end > json_start:
                return text[json_start:json_end].strip()
        
        # Try to find JSON object
        json_start = text.find("{")
        json_end = text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            return text[json_start:json_end]
        
        return text

