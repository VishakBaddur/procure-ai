import pdfplumber
from pathlib import Path
from typing import Dict, Any, List
import re
import os
import json
from groq import Groq


class LegalAnalysisAgent:
    """Agent for analyzing legal agreements and contracts using AI"""
    
    def __init__(self):
        # Initialize Groq AI for intelligent legal analysis
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            try:
                self.client = Groq(api_key=api_key)
                self.use_ai = True
            except Exception as e:
                print(f"Warning: Groq AI not available for legal analysis: {e}")
                self.use_ai = False
        else:
            self.use_ai = False
    
    async def analyze_agreement(self, file_path: Path, vendor_name: str) -> Dict[str, Any]:
        """Analyze legal agreement document"""
        
        # Extract text from PDF
        text = self._extract_text(file_path)
        
        # Analyze agreement - use AI if available, fallback to keyword matching
        if self.use_ai:
            try:
                return await self._analyze_with_ai(text, vendor_name)
            except Exception as e:
                print(f"AI analysis failed, falling back to keyword matching: {e}")
        
        # Fallback to keyword-based analysis
        return self._analyze_terms(text, vendor_name)
    
    def _extract_text(self, file_path: Path) -> str:
        """Extract text from agreement document"""
        text = ""
        try:
            if str(file_path).endswith(".pdf"):
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        text += page.extract_text() or ""
            else:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
        except Exception as e:
            print(f"Error extracting agreement: {e}")
        return text
    
    async def _analyze_with_ai(self, text: str, vendor_name: str) -> Dict[str, Any]:
        """Use Groq AI to intelligently analyze legal agreement"""
        
        prompt = f"""
        Analyze this legal agreement/contract document for a vendor named "{vendor_name}".
        
        Document text (first 8000 characters):
        {text[:8000]}
        
        Analyze the document and identify:
        1. **Key Clauses**: Termination, liability, warranty, payment terms, IP, confidentiality, dispute resolution
        2. **Risk Factors**: Look for concerning terms like unlimited liability, no warranty, binding arbitration, etc.
        3. **Missing Clauses**: Important clauses that should be present but aren't
        4. **Contract Duration**: How long is the contract valid?
        5. **Overall Risk Assessment**: Rate the risk level
        
        Return a JSON object with this exact structure:
        {{
            "risk_score": <0.0 to 1.0, where 1.0 is highest risk>,
            "overall_score": <0 to 100, where 100 is best>,
            "key_clauses": ["clause1", "clause2", ...],
            "risk_factors": [
                {{
                    "level": "low|medium|high|critical",
                    "keyword": "the term or phrase",
                    "description": "why this is a risk",
                    "context": "relevant text from document"
                }}
            ],
            "missing_clauses": ["clause1", "clause2", ...],
            "contract_length": "duration if found, else 'Not specified'",
            "recommendations": [
                "recommendation 1",
                "recommendation 2"
            ],
            "has_favorable_terms": <true|false>
        }}
        
        Be thorough and understand context. Don't just match keywords - understand the meaning.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            response_text = response.choices[0].message.content
            
            # Extract JSON from response
            json_str = self._extract_json_from_response(response_text)
            analysis = json.loads(json_str)
            
            # Validate and normalize
            risk_score = float(analysis.get("risk_score", 0.5))
            risk_score = max(0.0, min(1.0, risk_score))  # Clamp between 0 and 1
            
            overall_score = analysis.get("overall_score")
            if overall_score is None:
                overall_score = (1 - risk_score) * 100
            
            return {
                "vendor_name": vendor_name,
                "risk_score": round(risk_score, 2),
                "overall_score": round(float(overall_score), 2),
                "key_clauses": analysis.get("key_clauses", []),
                "risk_factors": analysis.get("risk_factors", [])[:10],  # Top 10
                "missing_clauses": analysis.get("missing_clauses", []),
                "recommendations": analysis.get("recommendations", []),
                "contract_length": analysis.get("contract_length", "Not specified"),
                "has_favorable_terms": analysis.get("has_favorable_terms", risk_score < 0.5),
                "analysis_method": "AI"
            }
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse AI response as JSON: {e}")
            return self._analyze_terms(text, vendor_name)
        except Exception as e:
            print(f"AI analysis error: {e}")
            return self._analyze_terms(text, vendor_name)
    
    def _extract_json_from_response(self, response_text: str) -> str:
        """Extract JSON from AI response"""
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            return response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            return response_text[json_start:json_end].strip()
        else:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                return response_text[json_start:json_end]
        return response_text
    
    def _analyze_terms(self, text: str, vendor_name: str) -> Dict[str, Any]:
        """Analyze legal terms and clauses"""
        
        # Key terms to look for
        key_clauses = []
        risk_factors = []
        risk_score = 0.0
        
        text_lower = text.lower()
        
        # Check for important clauses
        clause_patterns = {
            "termination_clause": r"termination|cancel|cancel.*?contract",
            "liability": r"liability|damages|indemnif",
            "warranty": r"warranty|guarantee|warrant",
            "payment_terms": r"payment|due.*?date|invoice",
            "intellectual_property": r"intellectual.*?property|ip|copyright|patent",
            "confidentiality": r"confidential|nda|non.*?disclosure",
            "dispute_resolution": r"dispute|arbitration|litigation|jurisdiction"
        }
        
        for clause_name, pattern in clause_patterns.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                key_clauses.append(clause_name.replace("_", " ").title())
        
        # Risk assessment
        risk_keywords = {
            "high_risk": ["unlimited liability", "no warranty", "no refund", "binding arbitration"],
            "medium_risk": ["limited warranty", "partial refund", "dispute resolution"],
            "low_risk": ["full warranty", "money back guarantee", "flexible terms"]
        }
        
        for risk_level, keywords in risk_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    risk_factors.append({
                        "level": risk_level,
                        "keyword": keyword
                    })
                    if risk_level == "high_risk":
                        risk_score += 0.3
                    elif risk_level == "medium_risk":
                        risk_score += 0.15
                    else:
                        risk_score += 0.05
        
        # Normalize risk score (0-1 scale)
        risk_score = min(risk_score, 1.0)
        
        # Generate recommendations
        recommendations = []
        
        if risk_score > 0.7:
            recommendations.append("High risk detected. Review carefully before signing.")
        elif risk_score > 0.4:
            recommendations.append("Moderate risk. Consider negotiating terms.")
        else:
            recommendations.append("Low risk. Terms appear reasonable.")
        
        if "termination" not in text_lower:
            recommendations.append("Consider adding clear termination clause.")
        
        if "warranty" not in text_lower:
            recommendations.append("Warranty terms may be missing. Clarify warranty coverage.")
        
        # Calculate overall score (inverse of risk)
        overall_score = (1 - risk_score) * 100
        
        return {
            "vendor_name": vendor_name,
            "risk_score": round(risk_score, 2),
            "overall_score": round(overall_score, 2),
            "key_clauses": key_clauses,
            "risk_factors": risk_factors[:5],  # Top 5 risk factors
            "recommendations": recommendations,
            "contract_length": self._estimate_contract_length(text),
            "has_favorable_terms": risk_score < 0.5,
            "analysis_method": "keyword_matching"
        }
    
    def _estimate_contract_length(self, text: str) -> str:
        """Estimate contract duration"""
        # Look for duration mentions
        duration_patterns = [
            r"(\d+)\s*(?:year|years|yr)",
            r"(\d+)\s*(?:month|months)",
            r"(\d+)\s*(?:day|days)"
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return "Not specified"
    
    def compare_agreements(self, agreements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare multiple vendor agreements"""
        if not agreements:
            return {"error": "No agreements to compare"}
        
        comparison = {
            "vendors": [],
            "best_score": None,
            "lowest_risk": None,
            "recommendations": []
        }
        
        best_score = -1
        lowest_risk = 1.0
        
        for agreement in agreements:
            vendor_name = agreement.get("vendor_name", "Unknown")
            risk_score = agreement.get("risk_score", 1.0)
            overall_score = agreement.get("overall_score", 0)
            
            comparison["vendors"].append({
                "name": vendor_name,
                "risk_score": risk_score,
                "overall_score": overall_score,
                "has_favorable_terms": agreement.get("has_favorable_terms", False)
            })
            
            if overall_score > best_score:
                best_score = overall_score
                comparison["best_score"] = vendor_name
            
            if risk_score < lowest_risk:
                lowest_risk = risk_score
                comparison["lowest_risk"] = vendor_name
        
        # Generate overall recommendation
        if comparison["best_score"]:
            comparison["recommendations"].append(
                f"Best overall agreement: {comparison['best_score']}"
            )
        
        return comparison

