from typing import Dict, Any, List
import json
import os
from groq import Groq


class TCOAgent:
    """Agent for analyzing Total Cost of Ownership (TCO)"""
    
    def __init__(self):
        # Initialize Groq AI for enhanced TCO analysis
        api_key = os.getenv("GROQ_API_KEY")
        if api_key:
            try:
                self.client = Groq(api_key=api_key)
                self.use_ai = True
            except Exception as e:
                print(f"Warning: Groq AI not available for TCO: {e}")
                self.use_ai = False
        else:
            self.use_ai = False
    
    async def analyze_tco(self, vendor_quotes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze Total Cost of Ownership for multiple vendors"""
        
        tco_analysis = {
            "vendors": [],
            "best_long_term_value": None,
            "recommendations": []
        }
        
        for quote in vendor_quotes:
            vendor_tco = self._calculate_tco(quote)
            tco_analysis["vendors"].append(vendor_tco)
        
        # Find best long-term value
        best_value = None
        lowest_tco = float('inf')
        
        for vendor in tco_analysis["vendors"]:
            total_tco = vendor.get("total_tco", float('inf'))
            if total_tco < lowest_tco:
                lowest_tco = total_tco
                best_value = vendor.get("vendor_name")
        
        tco_analysis["best_long_term_value"] = best_value
        
        # Generate recommendations
        if best_value:
            tco_analysis["recommendations"].append(
                f"Best long-term value: {best_value} (Total TCO: ${lowest_tco:,.2f})"
            )
        
        # Compare initial vs long-term costs
        initial_costs = [(v.get("vendor_name"), v.get("initial_price", 0)) 
                        for v in tco_analysis["vendors"]]
        initial_costs.sort(key=lambda x: x[1])
        
        if initial_costs:
            cheapest_initial = initial_costs[0][0]
            if cheapest_initial != best_value:
                tco_analysis["recommendations"].append(
                    f"Note: {cheapest_initial} has the lowest initial cost, "
                    f"but {best_value} offers better long-term value."
                )
        
        return tco_analysis
    
    def _calculate_tco(self, quote: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate TCO for a single vendor quote - extracts data from documents"""
        
        from database import get_vendor_parsed_data
        
        vendor_name = quote.get("vendor_name", "Unknown")
        vendor_id = quote.get("vendor_id")
        initial_price = quote.get("total_price", 0)
        
        # Get quote data to extract warranty and other info
        warranty_years = 1  # Default
        has_extended_warranty = False
        
        if vendor_id:
            quote_data = get_vendor_parsed_data(vendor_id, "quote")
            if quote_data:
                quote_full = quote_data[0]["data"]
                # Extract warranty period
                warranties = quote_full.get("warranties", [])
                for warranty in warranties:
                    if isinstance(warranty, str):
                        import re
                        # Look for "X year" or "X years"
                        match = re.search(r'(\d+)\s*(?:year|yr)', warranty.lower())
                        if match:
                            warranty_years = int(match.group(1))
                            has_extended_warranty = warranty_years > 1
                            break
        
        # Get vendor reputation to adjust risk
        reputation_score = 50  # Default
        risk_multiplier = 1.0
        
        if vendor_id:
            research_data = get_vendor_parsed_data(vendor_id, "research")
            if research_data:
                research = research_data[0]["data"]
                reputation_score = research.get("reputation_score", 50)
                # Lower reputation = higher risk = higher costs
                # Reputation 0-100, convert to risk multiplier 1.0-1.5
                risk_multiplier = 1.0 + ((100 - reputation_score) / 200)
        
        # Calculate costs with extracted data and risk adjustment
        years = 5
        
        # CAPEX (Capital Expenditure)
        initial_cost = initial_price
        training_cost = initial_price * 0.03  # 3% for training (one-time)
        replacement_cost = 0  # Only if warranty doesn't cover full period
        
        # If warranty is shorter than analysis period, factor replacement
        if warranty_years < years:
            # Replacement cost at end of warranty (80% of original)
            replacement_cost = initial_price * 0.8
        
        total_capex = initial_cost + training_cost + replacement_cost
        
        # OPEX (Operational Expenditure) - adjusted by risk
        # Support costs (annual) - lower if extended warranty
        support_base = initial_price * 0.15
        if has_extended_warranty:
            support_base *= 0.7  # 30% reduction with extended warranty
        support_cost_per_year = support_base * risk_multiplier
        
        # Maintenance costs (annual) - varies by product type
        # Higher for complex products, lower for simple commodities
        maintenance_base = initial_price * 0.10
        # Adjust based on price point (premium items need less maintenance)
        if initial_price > 10000:
            maintenance_base *= 0.8
        elif initial_price < 1000:
            maintenance_base *= 1.2
        maintenance_cost_per_year = maintenance_base * risk_multiplier
        
        # Repair costs (annual) - inversely related to warranty
        repair_base = initial_price * 0.08
        if has_extended_warranty:
            repair_base *= 0.5  # 50% reduction with warranty coverage
        # Higher repair rate for lower reputation vendors
        repair_cost_per_year = repair_base * risk_multiplier
        
        # Downtime costs (annual) - higher for low reputation vendors
        downtime_base = initial_price * 0.05
        downtime_cost_per_year = downtime_base * risk_multiplier
        
        # Calculate totals over analysis period
        total_support = support_cost_per_year * years
        total_maintenance = maintenance_cost_per_year * years
        total_repairs = repair_cost_per_year * years
        total_downtime = downtime_cost_per_year * years
        
        total_opex = total_support + total_maintenance + total_repairs + total_downtime
        
        # Total TCO
        total_tco = total_capex + total_opex
        
        # Annual cost
        annual_cost = total_tco / years if years > 0 else total_tco
        
        # Durability score (based on warranty, reputation, and repair costs)
        durability_score = 50  # Base
        durability_score += warranty_years * 5  # +5 per warranty year
        durability_score += (reputation_score - 50) * 0.3  # Adjust by reputation
        durability_score -= (repair_cost_per_year / initial_price * 100) if initial_price > 0 else 0
        durability_score = max(0, min(100, durability_score))  # Clamp 0-100
        
        return {
            "vendor_name": vendor_name,
            "vendor_id": vendor_id,
            "initial_price": round(initial_price, 2),
            "capex": {
                "initial_cost": round(initial_cost, 2),
                "training_cost": round(training_cost, 2),
                "replacement_cost": round(replacement_cost, 2),
                "total_capex": round(total_capex, 2)
            },
            "opex": {
                "support_cost": round(total_support, 2),
                "maintenance_cost": round(total_maintenance, 2),
                "repair_cost": round(total_repairs, 2),
                "downtime_cost": round(total_downtime, 2),
                "total_opex": round(total_opex, 2)
            },
            "total_tco": round(total_tco, 2),
            "annual_cost": round(annual_cost, 2),
            "durability_score": round(durability_score, 1),
            "years_analyzed": years,
            "specifications": {
                "warranty_years": warranty_years,
                "reputation_score": round(reputation_score, 1),
                "risk_multiplier": round(risk_multiplier, 2)
            }
        }
    
    def compare_tco(self, tco_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare TCO across vendors"""
        if not tco_data:
            return {"error": "No TCO data to compare"}
        
        comparison = {
            "vendors": tco_data,
            "cheapest_initial": None,
            "cheapest_tco": None,
            "best_durability": None,
            "savings_analysis": {}
        }
        
        cheapest_initial_price = float('inf')
        cheapest_tco_price = float('inf')
        best_durability = -1
        
        for vendor in tco_data:
            vendor_name = vendor.get("vendor_name")
            initial = vendor.get("initial_price", float('inf'))
            tco = vendor.get("total_tco", float('inf'))
            durability = vendor.get("durability_score", 0)
            
            if initial < cheapest_initial_price:
                cheapest_initial_price = initial
                comparison["cheapest_initial"] = vendor_name
            
            if tco < cheapest_tco_price:
                cheapest_tco_price = tco
                comparison["cheapest_tco"] = vendor_name
            
            if durability > best_durability:
                best_durability = durability
                comparison["best_durability"] = vendor_name
        
        # Calculate savings
        if len(tco_data) >= 2:
            tco_sorted = sorted(tco_data, key=lambda x: x.get("total_tco", float('inf')))
            cheapest = tco_sorted[0]
            most_expensive = tco_sorted[-1]
            
            savings = most_expensive.get("total_tco", 0) - cheapest.get("total_tco", 0)
            comparison["savings_analysis"] = {
                "cheapest_vendor": cheapest.get("vendor_name"),
                "most_expensive_vendor": most_expensive.get("vendor_name"),
                "potential_savings": round(savings, 2),
                "savings_percentage": round((savings / most_expensive.get("total_tco", 1)) * 100, 2) if most_expensive.get("total_tco", 0) > 0 else 0
            }
        
        return comparison
    
    async def analyze_tco_enhanced(
        self, 
        vendor_quotes: List[Dict[str, Any]], 
        item_name: str,
        project_id: str
    ) -> Dict[str, Any]:
        """Enhanced TCO analysis with failure rates, maintenance, replacement cycle"""
        
        # Get item-specific data from LLM/web search
        item_data = await self._get_item_specifications(item_name)
        
        tco_analysis = {
            "vendors": [],
            "best_long_term_value": None,
            "recommendations": [],
            "item_specifications": item_data
        }
        
        for quote in vendor_quotes:
            vendor_tco = await self._calculate_tco_enhanced(quote, item_data, project_id)
            tco_analysis["vendors"].append(vendor_tco)
        
        # Find best long-term value
        best_value = None
        lowest_tco = float('inf')
        
        for vendor in tco_analysis["vendors"]:
            total_tco = vendor.get("total_tco", float('inf'))
            if total_tco < lowest_tco:
                lowest_tco = total_tco
                best_value = vendor.get("vendor_name")
        
        tco_analysis["best_long_term_value"] = best_value
        
        if best_value:
            tco_analysis["recommendations"].append(
                f"Best long-term value: {best_value} (Total TCO: ${lowest_tco:,.2f})"
            )
        
        return tco_analysis
    
    async def _get_item_specifications(self, item_name: str) -> Dict[str, Any]:
        """Get item specifications using Groq LLM"""
        
        if not self.use_ai:
            # Return default values
            return {
                "failure_rate_per_year": 0.10,  # 10% annual failure rate
                "replacement_cycle_years": 5,
                "maintenance_frequency_per_year": 2,  # 2 times per year
                "standard_warranty_years": 1
            }
        
        prompt = f"""
        Research specifications for: "{item_name}"
        
        Find information about:
        1. Typical failure rate (percentage per year)
        2. Replacement cycle (how many years before replacement needed)
        3. Maintenance frequency (how many times per year maintenance is typically needed)
        4. Standard warranty period (in years)
        
        Return JSON format:
        {{
            "failure_rate_per_year": <0.0 to 1.0>,
            "replacement_cycle_years": <number>,
            "maintenance_frequency_per_year": <number>,
            "standard_warranty_years": <number>
        }}
        
        Use web search to find accurate, industry-standard information.
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
            
            # Extract JSON
            json_str = self._extract_json(response_text)
            return json.loads(json_str)
        except Exception as e:
            print(f"Failed to get item specifications: {e}")
            return {
                "failure_rate_per_year": 0.10,
                "replacement_cycle_years": 5,
                "maintenance_frequency_per_year": 2,
                "standard_warranty_years": 1
            }
    
    async def _calculate_tco_enhanced(
        self, 
        quote: Dict[str, Any], 
        item_data: Dict[str, Any],
        project_id: str
    ) -> Dict[str, Any]:
        """Calculate enhanced TCO with real data extracted from documents"""
        
        from database import get_vendor_parsed_data
        
        vendor_name = quote.get("vendor_name", "Unknown")
        vendor_id = quote.get("vendor_id")
        initial_price = quote.get("total_price", 0)
        
        # Get warranty info from quote if available
        warranty_years = item_data.get("standard_warranty_years", 1)
        has_extended_warranty = False
        
        if vendor_id:
            quote_data = get_vendor_parsed_data(vendor_id, "quote")
            if quote_data:
                quote_data_full = quote_data[0]["data"]
                warranties = quote_data_full.get("warranties", [])
                for warranty in warranties:
                    if isinstance(warranty, str):
                        import re
                        match = re.search(r'(\d+)\s*(?:year|yr)', warranty.lower())
                        if match:
                            warranty_years = int(match.group(1))
                            has_extended_warranty = warranty_years > 1
                            break
        
        # Get vendor reputation to adjust risk
        reputation_score = 50  # Default
        risk_multiplier = 1.0
        
        if vendor_id:
            research_data = get_vendor_parsed_data(vendor_id, "research")
            if research_data:
                research = research_data[0]["data"]
                reputation_score = research.get("reputation_score", 50)
                # Lower reputation = higher risk = higher costs
                risk_multiplier = 1.0 + ((100 - reputation_score) / 200)
        
        # Get item specifications (use defaults if not available)
        maintenance_freq = item_data.get("maintenance_frequency_per_year", 2)
        replacement_cycle = item_data.get("replacement_cycle_years", 5)
        failure_rate = item_data.get("failure_rate_per_year", 0.10)
        
        # Calculate costs
        years = replacement_cycle  # Use replacement cycle as analysis period
        
        # CAPEX (Capital Expenditure)
        initial_cost = initial_price
        training_cost = initial_price * 0.03  # 3% for training (one-time)
        replacement_cost = 0
        
        # If warranty is shorter than analysis period, factor replacement
        if warranty_years < years:
            replacement_cost = initial_price * 0.8  # 80% of original cost
        
        total_capex = initial_cost + training_cost + replacement_cost
        
        # OPEX (Operational Expenditure) - adjusted by risk and warranty
        # Support costs (annual) - lower if extended warranty
        support_base = initial_price * 0.15
        if has_extended_warranty:
            support_base *= 0.7  # 30% reduction with extended warranty
        support_cost_per_year = support_base * risk_multiplier
        
        # Maintenance costs (based on frequency and risk)
        maintenance_cost_per_visit = initial_price * 0.05
        maintenance_cost_per_year = (maintenance_cost_per_visit * maintenance_freq) * risk_multiplier
        
        # Repair costs (based on failure rate, warranty, and risk)
        repair_cost_per_failure = initial_price * 0.20
        repair_base = repair_cost_per_failure * failure_rate
        if has_extended_warranty:
            repair_base *= 0.5  # 50% reduction with warranty coverage
        repair_cost_per_year = repair_base * risk_multiplier
        
        # Downtime costs (higher for low reputation vendors)
        downtime_base = initial_price * 0.05
        downtime_cost_per_year = downtime_base * risk_multiplier
        
        # Calculate total OPEX over analysis period
        total_support = support_cost_per_year * years
        total_maintenance = maintenance_cost_per_year * years
        total_repairs = repair_cost_per_year * years
        total_downtime = downtime_cost_per_year * years
        
        total_opex = total_support + total_maintenance + total_repairs + total_downtime
        
        # Total TCO = CAPEX + OPEX
        total_tco = total_capex + total_opex
        
        # Annual cost
        annual_cost = total_tco / years if years > 0 else total_tco
        
        # Durability score (based on warranty, reputation, failure rate)
        durability_score = 50  # Base
        durability_score += warranty_years * 5  # +5 per warranty year
        durability_score += (reputation_score - 50) * 0.3  # Adjust by reputation
        durability_score -= (failure_rate * 100)  # Reduce by failure rate
        durability_score = max(0, min(100, durability_score))  # Clamp 0-100
        
        return {
            "vendor_name": vendor_name,
            "vendor_id": vendor_id,
            "capex": {
                "initial_cost": round(initial_cost, 2),
                "training_cost": round(training_cost, 2),
                "replacement_cost": round(replacement_cost, 2),
                "total_capex": round(total_capex, 2)
            },
            "opex": {
                "support_cost": round(total_support, 2),
                "maintenance_cost": round(total_maintenance, 2),
                "repair_cost": round(total_repairs, 2),
                "downtime_cost": round(total_downtime, 2),
                "total_opex": round(total_opex, 2)
            },
            "total_tco": round(total_tco, 2),
            "annual_cost": round(annual_cost, 2),
            "specifications": {
                "warranty_years": warranty_years,
                "maintenance_frequency_per_year": maintenance_freq,
                "replacement_cycle_years": replacement_cycle,
                "failure_rate_per_year": failure_rate,
                "reputation_score": round(reputation_score, 1),
                "risk_multiplier": round(risk_multiplier, 2)
            },
            "durability_score": round(durability_score, 1),
            "years_analyzed": years
        }
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from AI response"""
        if "```json" in text:
            json_start = text.find("```json") + 7
            json_end = text.find("```", json_start)
            return text[json_start:json_end].strip()
        elif "```" in text:
            json_start = text.find("```") + 3
            json_end = text.find("```", json_start)
            return text[json_start:json_end].strip()
        else:
            json_start = text.find("{")
            json_end = text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                return text[json_start:json_end]
        return text

