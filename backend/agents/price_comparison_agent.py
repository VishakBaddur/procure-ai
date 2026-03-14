import pdfplumber
from PIL import Image
import pytesseract
import re
from pathlib import Path
from typing import Dict, Any, List
import json
import os
import requests
from docx import Document


class PriceComparisonAgent:
    """Agent for extracting and comparing prices from vendor quotes using AI"""
    
    def __init__(self):
        # Initialize Local LLM (Ollama) for intelligent price extraction
        # Check if Ollama is available, fallback to Groq if needed
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
        
        # Try to connect to Ollama
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            if response.status_code == 200:
                self.use_local_llm = True
                print(f"✓ Using local LLM (Ollama) with model: {self.ollama_model}")
            else:
                self.use_local_llm = False
        except Exception as e:
            print(f"Warning: Ollama not available, checking for Groq fallback: {e}")
            self.use_local_llm = False
        
        # Fallback to Groq if Ollama is not available
        if not self.use_local_llm:
            api_key = os.getenv("GROQ_API_KEY")
            if api_key:
                try:
                    from groq import Groq
                    self.client = Groq(api_key=api_key)
                    self.use_ai = True
                    print("✓ Using Groq AI as fallback")
                except Exception as e:
                    print(f"Warning: Groq AI not available: {e}")
                    self.use_ai = False
            else:
                self.use_ai = False
                print("⚠️ No LLM available - will use regex fallback only")
        else:
            self.use_ai = True  # Use local LLM
    
    async def process_quote(self, file_path: Path, vendor_name: str, content_type: str) -> Dict[str, Any]:
        """Process quote file and extract pricing information"""
        # Base result structure so callers always get a predictable shape
        base_result: Dict[str, Any] = {
            "vendor_name": vendor_name,
            "products": [],
            "items": [],
            "total_price": 0,
            "currency": "USD",
            "warranties": [],
            "warnings": [],
            "success": True,
            "error": None,
        }
        
        extracted_text = ""
        
        # Extract text based on file type
        try:
            if content_type == "application/pdf" or str(file_path).endswith(".pdf"):
                extracted_text = self._extract_from_pdf(file_path)
            elif content_type.startswith("image/"):
                extracted_text = self._extract_from_image(file_path)
            elif content_type in [
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/msword",
            ] or str(file_path).endswith((".docx", ".doc")):
                extracted_text = self._extract_from_word(file_path)
            elif content_type == "text/plain" or str(file_path).endswith(".txt"):
                with open(file_path, "r", encoding="utf-8") as f:
                    extracted_text = f.read()
            elif content_type == "message/rfc822" or "email" in content_type.lower() or str(file_path).endswith((".eml", ".msg")):
                # Email file - extract text content
                extracted_text = self._extract_from_email(file_path)
            else:
                # Try to detect file type by extension
                file_ext = str(file_path).lower()
                if file_ext.endswith(".docx") or file_ext.endswith(".doc"):
                    extracted_text = self._extract_from_word(file_path)
                elif file_ext.endswith(".txt"):
                    with open(file_path, "r", encoding="utf-8") as f:
                        extracted_text = f.read()
                else:
                    # Default: try to read as text
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            extracted_text = f.read()
                    except Exception:
                        extracted_text = ""
        except Exception as e:
            # Hard failure during extraction – return a clear, user-facing error
            base_result["success"] = False
            base_result["error"] = (
                "We couldn't read this file reliably. "
                "Please upload a clearer PDF/Doc or paste the quote text manually."
            )
            base_result["warnings"].append(f"text_extraction_error: {str(e)}")
            base_result["raw_text_preview"] = ""
            return base_result
        
        # If we could not extract any text at all, fail gracefully
        if not extracted_text or not extracted_text.strip():
            base_result["success"] = False
            base_result["error"] = (
                "We couldn't extract any readable text from this document. "
                "Please check the file (e.g., scanned image, password-protected PDF) "
                "or paste the quote text manually."
            )
            base_result["warnings"].append("no_text_extracted")
            base_result["raw_text_preview"] = ""
            return base_result
        
        # Parse pricing information
        pricing_data = await self._parse_pricing(extracted_text, vendor_name)
        
        # Ensure a stable envelope and attach basic diagnostics
        if not isinstance(pricing_data, dict):
            base_result["success"] = False
            base_result["error"] = (
                "The AI parser returned an unexpected response. "
                "Please review the extracted data manually."
            )
            base_result["warnings"].append("invalid_pricing_data_type")
            base_result["raw_text_preview"] = extracted_text[:500]
            return base_result
        
        # Merge pricing data into the base envelope
        merged: Dict[str, Any] = {**base_result, **pricing_data}
        
        # If no products/items were parsed, mark as low-confidence and surface that to the caller
        has_items = bool(merged.get("products") or merged.get("items"))
        if not has_items:
            merged["success"] = False
            if not merged.get("error"):
                merged["error"] = (
                    "We couldn't confidently extract any line items from this quote. "
                    "Please double-check the numbers and update them manually if needed."
                )
            merged.setdefault("warnings", []).append("no_items_parsed")
        
        # Always include a short preview of the raw text to help debugging / UI hints
        if "raw_text_preview" not in merged:
            merged["raw_text_preview"] = extracted_text[:500]
        
        return merged
    
    def _extract_from_pdf(self, file_path: Path) -> str:
        """Extract text from PDF"""
        text = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
        except Exception as e:
            print(f"Error extracting PDF: {e}")
        return text
    
    def _extract_from_image(self, file_path: Path) -> str:
        """Extract text from image using OCR"""
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            print(f"Error extracting image: {e}")
            return ""
    
    def _extract_from_word(self, file_path: Path) -> str:
        """Extract text from Word document (.docx)"""
        text = ""
        try:
            doc = Document(file_path)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            # Also extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        text += cell.text + " "
                    text += "\n"
        except Exception as e:
            print(f"Error extracting Word document: {e}")
        return text
    
    def _extract_from_email(self, file_path: Path) -> str:
        """Extract text from email file (.eml or .msg)"""
        text = ""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                # Try to extract email body (simple extraction)
                # Look for common email patterns
                if "Content-Type: text/plain" in content:
                    parts = content.split("Content-Type: text/plain")
                    if len(parts) > 1:
                        body = parts[1].split("\n\n", 1)
                        if len(body) > 1:
                            text = body[1]
                elif "Content-Type: text/html" in content:
                    parts = content.split("Content-Type: text/html")
                    if len(parts) > 1:
                        body = parts[1].split("\n\n", 1)
                        if len(body) > 1:
                            # Simple HTML stripping
                            html_text = body[1]
                            # Remove HTML tags (basic)
                            text = re.sub(r'<[^>]+>', '', html_text)
                else:
                    # Fallback: extract everything after headers
                    lines = content.split("\n")
                    in_body = False
                    for line in lines:
                        if line.strip() == "" and not in_body:
                            in_body = True
                            continue
                        if in_body:
                            text += line + "\n"
        except Exception as e:
            print(f"Error extracting email: {e}")
            # Fallback: try to read as plain text
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except:
                pass
        return text
    
    async def _parse_pricing(self, text: str, vendor_name: str) -> Dict[str, Any]:
        """Parse pricing information from extracted text using AI for better accuracy"""
        
        # For email-style / informal quotes: use dedicated LLM prompt or regex fallback (any product type)
        if self._is_email_style_quote(text):
            result = await self._extract_email_style_and_build_result(text, vendor_name)
            if result is not None:
                return result
        
        # Try AI parsing first if available
        if self.use_ai:
            try:
                return await self._parse_with_ai(text, vendor_name)
            except Exception as e:
                print(f"AI parsing failed, falling back to regex: {e}")
        
        # Fallback to regex-based parsing
        return self._parse_with_regex(text, vendor_name)
    
    async def _parse_with_ai(self, text: str, vendor_name: str) -> Dict[str, Any]:
        """Use Groq AI to intelligently extract pricing information with products, payment terms, and quantity tiers"""
        
        prompt = f"""
        You are a procurement data extraction specialist. Extract ALL information from this vendor quote and return it in a structured JSON format.
        Vendor: {vendor_name}
        
        Document text:
        {text[:8000]}
        
        CRITICAL REQUIREMENTS - YOU MUST FOLLOW THESE EXACTLY:
        
        **SPECIAL HANDLING FOR EMAIL/INFORMAL QUOTES:**
        - Email quotes are often conversational and informal - extract information even if not perfectly structured
        - Handle approximate values: "~$75k" → 75000, "31–32 oz" → use midpoint (31.5) or range
        - Calculate totals from unit prices × quantities when totals are not explicitly stated
        - Extract fees separately (setup fees, storage fees, etc.) as additional line items
        - Products may be mentioned in natural language: "Gold American Eagles" and "Silver Eagles" are TWO separate products
        
        **EXAMPLE EMAIL QUOTE HANDLING:**
        Text: "Gold American Eagles: $2,395/oz, ~31-32 oz for ~$75k. Silver Eagles: $31.80/oz, ~780-800 oz for ~$25k. Setup: $200. Storage: $150-200/year."
        
        Expected extraction:
        - Product 1: "Gold American Eagles"
          * Unit price: $2,395 per oz
          * Quantity: 31.5 oz (midpoint of 31-32)
          * Total: $75,000 (or calculate: 2395 × 31.5 = $75,442.50)
        - Product 2: "Silver Eagles"  
          * Unit price: $31.80 per oz
          * Quantity: 790 oz (midpoint of 780-800)
          * Total: $25,000 (or calculate: 31.80 × 790 = $25,122)
        - Additional fees: Setup $200, Storage $150-200/year
        
        1. **EXTRACT EVERY PRODUCT MENTIONED**: 
           - If text says "five different products" or lists products (e.g., "including X, Y, Z"), create a SEPARATE entry for EACH product
           - In emails, products may be mentioned as: "Gold American Eagles" and "Silver Eagles" - these are TWO products
           - Look for product names followed by pricing: "Gold Eagles: $2,395/oz" → Product: "Gold Eagles", unit_price: 2395, unit: "oz"
           - Each product gets its own object in the "products" array
           - DO NOT combine products into one entry
           - If no products are mentioned, return empty products array
        
        2. **EXTRACT ALL PRICING COMBINATIONS**:
           - For EACH product, create pricing_matrix entries for EVERY combination of:
             * Quantity tier (e.g., 1-5 kg, 6-20 kg)
             * Payment term (e.g., full advance, 50% advance, LC at sight)
           - If pricing applies to all products, replicate it for each product
           - If pricing is NOT specified for a product, set pricing_matrix to empty array [] and add note: "Pricing not specified"
        
        3. **EXTRACT WARRANTIES FOR EACH PRODUCT**:
           - For EACH product, extract warranty information if mentioned
           - If warranty is NOT specified for a product, set warranty field to "Not specified"
           - Also extract general warranties in the top-level "warranties" array
        
        4. **PAYMENT TERMS** - Extract exactly as mentioned:
           - "full advance payment" → "Full Advance"
           - "50% advance with balance on delivery" → "50% Advance, Balance on Delivery"
           - "LC at sight" → "LC at Sight"
           - If not specified, use "Not specified"
        
        5. **QUANTITY TIERS** - Extract ranges exactly:
           - "1–5 kg" → quantity_min: 1, quantity_max: 5, quantity_unit: "kg"
           - "6–20 kg" → quantity_min: 6, quantity_max: 20, quantity_unit: "kg"
        
        6. **PRICES** - Extract unit prices COMPLETELY:
           - "USD 68,500 per kg" → unit_price: 68500, quantity_unit: "kg", currency: "USD"
           - "$2,395/oz" → unit_price: 2395, quantity_unit: "oz", currency: "USD"
           - "$31.80/oz" → unit_price: 31.80, quantity_unit: "oz", currency: "USD"
           - "~$75k" or "approximately $75,000" → extract as 75000
           - DO NOT extract partial prices like "USD 68," or "USD 500" when the full price is "USD 68,500"
           - ALWAYS extract the COMPLETE price including all digits
           - If you see "USD 68,500", extract 68500, NOT 68 or 500
           - Handle approximate values: use the stated approximate value or calculate from unit_price × quantity
           
        6a. **CALCULATE TOTALS FROM UNIT PRICES × QUANTITIES**:
           - If text says "Gold Eagles: $2,395/oz, ~31-32 oz for ~$75k"
           - Extract: unit_price=2395, quantity_min=31, quantity_max=32
           - Calculate total: Use the stated total ($75,000) OR calculate (2395 × 31.5 = $75,442.50)
           - Prefer stated totals when available, but calculate if needed
           - For ranges like "31–32 oz", use midpoint (31.5) for calculations
        
        7. **EXTRACT FEES AND ADDITIONAL COSTS**:
           - Setup fees: "Account setup: $200" → add as separate product or note
           - Storage fees: "Storage: $150-200/year" → extract and note
           - Shipping costs: "No shipping costs" → note as "Included" or "Free"
           - These can be added as separate line items with product name like "Setup Fee" or "Storage Fee"
           
        8. **MISSING INFORMATION HANDLING**:
           - If ANY field is not specified in the text, use "Not specified" as the value
           - Do NOT leave fields empty or null unless explicitly allowed
           - Be explicit about what information is missing
           - For approximate values, extract the best estimate (use midpoint for ranges)
        
        EXAMPLE EXTRACTION:
        Text: "Aurum Precious Metals offers five different gold products, including 24K cast gold bars, 24K minted gold bars, 24K gold coins, 22K gold biscuits, and 24K gold grain. 
               For 1-5 kg: USD 68,500/kg (full advance), USD 69,200/kg (50% advance), USD 69,800/kg (LC at sight).
               For 6-20 kg: USD 67,800/kg (full advance), USD 68,400/kg (50% advance), USD 69,000/kg (LC at sight).
               Warranty: 1 year on all products."
        
        Expected output: EXACTLY 5 separate products:
        - Product 1: name="24K cast gold bars" (NOT "Aurum Precious Metals offers five different gold products, including 24K cast gold bars...")
        - Product 2: name="24K minted gold bars"
        - Product 3: name="24K gold coins"
        - Product 4: name="22K gold biscuits"
        - Product 5: name="24K gold grain"
        
        Each product should have 6 pricing_matrix entries (2 quantity tiers × 3 payment terms) and warranty: "1 year"
        
        WRONG OUTPUT (DO NOT DO THIS):
        - Product 1: name="Aurum Precious Metals offers five different gold products, including 24K cast gold bars, 24K minted gold bars, 24K gold coins, 22K gold biscuits, and 24K gold grain"
        
        This is WRONG because it combines all 5 products into one entry!
        
        IMPORTANT SCENARIOS TO HANDLE:
        - Vendor offers 5 different product varieties, each with 3 payment terms, and 2 quantity tiers = 30 price points
        - Vendor offers 1 product with different pricing for different quantities
        - Mixed scenarios with some products having more options than others
        - Products mentioned in lists (e.g., "including X, Y, Z products")
        - Products without pricing information → mark as "Not specified"
        - Products without warranty information → mark as "Not specified"
        
        CRITICAL: DO NOT CREATE PRODUCTS FROM PRICING TIERS!
        - If text says "1–3 kg: USD 69,000 per kg", this is a PRICING TIER, NOT a product
        - If text says "Product: 24K Minted Gold Bar" with pricing "1–3 kg: USD 69,000", create:
          * ONE product: "24K Minted Gold Bar"
          * With pricing_matrix containing the tier "1–3 kg: USD 69,000"
        - DO NOT create separate products for each pricing tier
        - Pricing tiers go in the pricing_matrix array, NOT as separate products
        
        Return a JSON object with this exact structure:
        {{
            "products": [
                {{
                    "product_id": "unique identifier (e.g., 'PROD001' or 'Aluminium-Sheet-Type-A')",
                    "name": "product name/variety/model",
                    "description": "detailed description if available, or 'Not specified'",
                    "category": "product category if mentioned, or 'Not specified'",
                    "pricing_matrix": [
                        {{
                            "quantity_min": <minimum quantity or null>,
                            "quantity_max": <maximum quantity or null for unlimited>,
                            "quantity_unit": "unit type (e.g., 'units', 'pieces', 'kg', 'lb') or 'Not specified'",
                            "payment_terms": "payment term (e.g., 'Net 30', 'Upfront', '50% Advance', 'Net 60') or 'Not specified'",
                            "unit_price": <price per unit or null if not specified>,
                            "total_price": <total price for this quantity tier or null>,
                            "currency": "currency code (e.g., 'USD', 'EUR') or 'Not specified'",
                            "notes": "any special notes (e.g., 'bulk discount', 'early payment discount') or 'Not specified'"
                        }}
                    ],
                    "default_payment_term": "most common payment term if applicable, or 'Not specified'",
                    "warranty": "warranty information if mentioned, or 'Not specified'",
                    "delivery_time": "delivery time if mentioned, or 'Not specified'"
                }}
            ],
            "summary": {{
                "total_products": <number of different products>,
                "currency": "primary currency (USD, EUR, etc.) or 'Not specified'",
                "payment_terms_available": ["list of all payment terms found, or ['Not specified'] if none"],
                "quantity_tiers": ["list of quantity ranges found, or ['Not specified'] if none"],
                "total_price_range": {{
                    "min": <minimum total price or null>,
                    "max": <maximum total price or null>
                }}
            }},
            "general_notes": "any general pricing notes, discounts, or conditions, or 'Not specified'",
            "warranties": ["list of warranty information, or ['Not specified'] if none"],
            "other_info": {{
                "delivery_terms": "delivery terms if mentioned, or 'Not specified'",
                "return_policy": "return policy if mentioned, or 'Not specified'",
                "support_services": "support services if mentioned, or 'Not specified'",
                "additional_notes": "any other relevant information, or 'Not specified'"
            }},
            "extraction_metadata": {{
                "parsing_method": "AI",
                "confidence": "high/medium/low"
            }}
        }}
        
        MANDATORY RULES - FOLLOW EXACTLY:
        1. **CRITICAL**: If text says "five different products" or lists products with commas, create EXACTLY that many separate product entries
        2. **Product names must be short**: Extract just the product name (e.g., "24K cast gold bars"), NOT the full sentence
        3. **Each product gets same pricing**: If pricing applies to all products, replicate the pricing_matrix for each product
        4. **Warranty extraction**: Extract warranty for EACH product individually. If not specified, use "Not specified"
        5. **Pricing extraction**: Extract pricing for EACH product. If not specified, use empty array [] and note it
        6. Extract payment terms exactly: "full advance payment" → "Full Advance", "50% advance with balance on delivery" → "50% Advance, Balance on Delivery", "LC at sight" → "LC at Sight"
        7. Extract quantity ranges: "1–5 kg" → quantity_min: 1, quantity_max: 5, quantity_unit: "kg"
        8. Extract unit prices: "USD 68,500 per kg" → unit_price: 68500, currency: "USD"
        9. **DO NOT** create one product with the entire text as the name
        10. **DO NOT** combine multiple products into one entry
        11. **ALWAYS** use "Not specified" for missing information - never leave fields empty or null
        
        VALIDATION CHECKLIST before returning:
        - If text mentions "5 products", verify you have exactly 5 entries in products array
        - Each product name should be 2-8 words, not a full sentence
        - Each product should have warranty field (even if "Not specified")
        - Each product should have pricing_matrix (even if empty)
        - All missing fields should say "Not specified"
        
        Return ONLY valid JSON. No markdown, no code blocks, no explanatory text. Just the JSON object.
        """
        
        try:
            import sys
            print(f"[Price Agent] Processing quote for {vendor_name}, text length: {len(text)}", file=sys.stderr, flush=True)
            print(f"[Price Agent] First 500 chars: {text[:500]}", file=sys.stderr, flush=True)
            
            # Use local LLM (Ollama) or Groq for extraction
            if self.use_local_llm:
                return await self._parse_with_local_llm(text, vendor_name)
            
            # Use Groq (fallback)
            # Use a more capable model for complex extraction
            system_message = """You are an expert at extracting structured procurement data from vendor quotations.

CRITICAL RULES YOU MUST FOLLOW - THESE ARE MANDATORY:

1. **PRODUCT COUNTING**: If text says "five different products" or "5 products" or lists products with commas (e.g., "including X, Y, Z, and W"), you MUST create EXACTLY that many separate product entries in the "products" array. Count the products mentioned!

2. **PRODUCT NAMES MUST BE SHORT**: Extract ONLY the product name itself (2-8 words maximum)
   - CORRECT: "24K cast gold bars"
   - CORRECT: "24K minted gold bars"
   - CORRECT: "22K gold biscuits"
   - WRONG: "Aurum Precious Metals offers five different gold products, including 24K cast gold bars, 24K minted gold bars..."
   - WRONG: "24K cast gold bars, 24K minted gold bars, 24K gold coins" (this is 3 products, not 1!)

3. **SPLIT PRODUCTS**: When you see "including X, Y, Z, and W", create SEPARATE entries:
   - Text: "including 24K cast gold bars, 24K minted gold bars, 24K gold coins, 22K gold biscuits, and 24K gold grain"
   - Create 5 products:
     * Product 1: name="24K cast gold bars"
     * Product 2: name="24K minted gold bars"
     * Product 3: name="24K gold coins"
     * Product 4: name="22K gold biscuits"
     * Product 5: name="24K gold grain"
   - NOT: One product with name="24K cast gold bars, 24K minted gold bars, 24K gold coins, 22K gold biscuits, and 24K gold grain"

4. **PRICING REPLICATION**: If pricing applies to all products equally, replicate the SAME pricing_matrix for EACH product

5. **NEVER COMBINE**: NEVER combine multiple products into one entry. Each product gets its own object.

6. **NEVER USE FULL SENTENCES**: NEVER use the entire sentence or description as a product name. Extract just the product name.

7. **PRICING TIERS ARE NOT PRODUCTS**: Pricing tiers (like "1–3 kg: USD 69,000") go in the pricing_matrix, NOT as separate products. Only actual product names are products.

8. **EXTRACT COMPLETE PRICES**: When you see "USD 68,500 per kg", extract the FULL price: 68500. Do NOT extract partial prices like 68 or 500.

9. **HANDLE EMAIL/INFORMAL QUOTES**:
   - Products may be mentioned conversationally: "We're recommending Gold American Eagles and Silver Eagles" → TWO products
   - Extract unit prices even if written as "$2,395/oz" (no space)
   - Handle approximate quantities: "31–32 oz" → quantity_min: 31, quantity_max: 32, or use midpoint 31.5
   - Calculate totals: If "~$75k for 31-32 oz at $2,395/oz", verify: 2395 × 31.5 ≈ 75,442 (close to $75k)
   - Extract fees: "Setup: $200" → create product "Setup Fee" with price 200, or add to notes
   - Look for patterns: "Product: price/unit, quantity, total" or "Product: price/unit (quantity for total)"

10. **QUANTITY EXTRACTION FROM EMAILS**:
    - "~31–32 oz" → quantity_min: 31, quantity_max: 32
    - "780–800 oz" → quantity_min: 780, quantity_max: 800
    - "around 40 oz" → quantity: 40 (or range 38-42 if context suggests)
    - Use midpoint for calculations when range is given

VALIDATION: Before returning, count your products. If text says "5 products" and you only have 1 product entry, you made an error!
VALIDATION: For email quotes, verify totals make sense: unit_price × quantity should approximately equal stated total.
"""
            
            response = self.client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=[
                    {
                        "role": "system", 
                        "content": system_message
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1  # Very low temperature for consistent extraction
            )
            response_text = response.choices[0].message.content
            import sys
            print(f"[Price Agent] AI Response (first 500 chars): {response_text[:500]}", file=sys.stderr, flush=True)
            
            # Extract JSON from response
            json_str = self._extract_json_from_response(response_text)
            pricing_data = json.loads(json_str)
            
            # Process the same way as local LLM version
            result = self._process_ai_response(pricing_data, text, vendor_name)
            result["parsing_method"] = "AI (Groq)"  # Mark as Groq
            return result
            
        except json.JSONDecodeError as e:
            # If JSON parsing fails, try regex fallback
            import sys
            print(f"[Price Agent] Failed to parse AI response as JSON: {e}", file=sys.stderr, flush=True)
            print(f"[Price Agent] Response was: {response_text[:500] if 'response_text' in locals() else 'N/A'}", file=sys.stderr, flush=True)
            return self._parse_with_regex(text, vendor_name)
        except Exception as e:
            import sys
            print(f"[Price Agent] AI parsing error: {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc(file=sys.stderr)
            return self._parse_with_regex(text, vendor_name)
    
    async def _parse_with_local_llm(self, text: str, vendor_name: str) -> Dict[str, Any]:
        """Use local LLM (Ollama) to intelligently extract pricing information"""
        import sys
        
        try:
            print(f"[Price Agent] Using local LLM (Ollama) for parsing", file=sys.stderr, flush=True)
            
            # Use the same prompt as Groq version
            prompt = f"""
You are a procurement data extraction specialist. Extract ALL information from this vendor quote and return it in a structured JSON format.
Vendor: {vendor_name}

Document text:
{text[:8000]}

CRITICAL REQUIREMENTS - YOU MUST FOLLOW THESE EXACTLY:

1. **EXTRACT EVERY PRODUCT MENTIONED**: 
   - If text says "five different products" or lists products (e.g., "including X, Y, Z"), create a SEPARATE entry for EACH product
   - Each product gets its own object in the "products" array
   - DO NOT combine products into one entry
   - If no products are mentioned, return empty products array

2. **EXTRACT ALL PRICING COMBINATIONS**:
   - For EACH product, create pricing_matrix entries for EVERY combination of:
     * Quantity tier (e.g., 1-5 kg, 6-20 kg)
     * Payment term (e.g., full advance, 50% advance, LC at sight)
   - If pricing applies to all products, replicate it for each product
   - If pricing is NOT specified for a product, set pricing_matrix to empty array [] and add note: "Pricing not specified"

3. **EXTRACT WARRANTIES FOR EACH PRODUCT**:
   - For EACH product, extract warranty information if mentioned
   - If warranty is NOT specified for a product, set warranty field to "Not specified"
   - Also extract general warranties in the top-level "warranties" array

4. **PAYMENT TERMS** - Extract exactly as mentioned:
   - "full advance payment" → "Full Advance"
   - "50% advance with balance on delivery" → "50% Advance, Balance on Delivery"
   - "LC at sight" → "LC at Sight"
   - If not specified, use "Not specified"

5. **QUANTITY TIERS** - Extract ranges exactly:
   - "1–5 kg" → quantity_min: 1, quantity_max: 5, quantity_unit: "kg"
   - "6–20 kg" → quantity_min: 6, quantity_max: 20, quantity_unit: "kg"

6. **PRICES** - Extract unit prices COMPLETELY:
   - "USD 68,500 per kg" → unit_price: 68500, quantity_unit: "kg", currency: "USD"
   - "USD 69,200 per kg" → unit_price: 69200, quantity_unit: "kg", currency: "USD"
   - DO NOT extract partial prices like "USD 68," or "USD 500" when the full price is "USD 68,500"
   - ALWAYS extract the COMPLETE price including all digits
   - If you see "USD 68,500", extract 68500, NOT 68 or 500

7. **MISSING INFORMATION HANDLING**:
   - If ANY field is not specified in the text, use "Not specified" as the value
   - Do NOT leave fields empty or null unless explicitly allowed
   - Be explicit about what information is missing

8. **HANDLE APPROXIMATE VALUES**:
   - If quantities or prices are approximate (e.g., "~$75k", "31–32 oz", "around $100,000"), extract the numerical range or the approximate value.
   - For ranges like "31–32 oz", use `quantity_min` and `quantity_max`.
   - For approximate monetary values, extract the number and note the approximation.

9. **FEES EXTRACTION**:
   - Extract any explicit fees mentioned (e.g., "Account setup: $200", "Storage: $150–$200 annually") as separate products with category "Fee".
   - Specify if they are one-time or annual.

Return a JSON object with this exact structure:
{{
    "products": [
        {{
            "product_id": "unique identifier",
            "name": "product name/variety/model",
            "description": "detailed description if available, or 'Not specified'",
            "category": "product category if mentioned, or 'Not specified'",
            "pricing_matrix": [
                {{
                    "quantity_min": <minimum quantity or null>,
                    "quantity_max": <maximum quantity or null for unlimited>,
                    "quantity_unit": "unit type (e.g., 'units', 'pieces', 'kg', 'lb', 'oz', 'one-time', 'year') or 'Not specified'",
                    "payment_terms": "payment term (e.g., 'Net 30', 'Upfront', '50% Advance', 'Net 60') or 'Not specified'",
                    "unit_price": <price per unit or null if not specified>,
                    "total_price": <total price for this quantity tier or null>,
                    "currency": "currency code (e.g., 'USD', 'EUR') or 'Not specified'",
                    "notes": "any special notes (e.g., 'bulk discount', 'early payment discount', 'approximate pricing') or 'Not specified'"
                }}
            ],
            "default_payment_term": "most common payment term if applicable, or 'Not specified'",
            "warranty": "warranty information if mentioned, or 'Not specified'",
            "delivery_time": "delivery time if mentioned, or 'Not specified'"
        }}
    ],
    "summary": {{
        "total_products": <number of different products>,
        "currency": "primary currency (USD, EUR, etc.) or 'Not specified'",
        "payment_terms_available": ["list of all payment terms found, or ['Not specified'] if none"],
        "quantity_tiers": ["list of quantity ranges found, or ['Not specified'] if none"],
        "total_price_range": {{
            "min": <minimum total price or null>,
            "max": <maximum total price or null>
        }}
    }},
    "general_notes": "any general pricing notes, discounts, or conditions, or 'Not specified'",
    "warranties": ["list of warranty information, or ['Not specified'] if none"],
    "other_info": {{
        "delivery_terms": "delivery terms if mentioned, or 'Not specified'",
        "return_policy": "return policy if mentioned, or 'Not specified'",
        "support_services": "support services if mentioned, or 'Not specified'",
        "additional_notes": "any other relevant information, or 'Not specified'"
    }},
    "extraction_metadata": {{
        "parsing_method": "AI",
        "confidence": "high/medium/low"
    }}
}}

Return ONLY valid JSON. No markdown, no code blocks, no explanatory text. Just the JSON object.
"""
            
            # Call Ollama API
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for consistent extraction
                        "num_predict": 4000  # Allow longer responses
                    }
                },
                timeout=120  # 2 minute timeout
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama API error: {response.status_code} - {response.text}")
            
            response_data = response.json()
            response_text = response_data.get("response", "")
            
            print(f"[Price Agent] Local LLM Response (first 500 chars): {response_text[:500]}", file=sys.stderr, flush=True)
            
            # Extract JSON from response
            json_str = self._extract_json_from_response(response_text)
            pricing_data = json.loads(json_str)
            
            # Process the same way as Groq version
            return self._process_ai_response(pricing_data, text, vendor_name)
            
        except Exception as e:
            import sys
            print(f"[Price Agent] Local LLM parsing error: {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc(file=sys.stderr)
            # Fallback to regex
            return self._parse_with_regex(text, vendor_name)
    
    def _process_ai_response(self, pricing_data: Dict[str, Any], text: str, vendor_name: str) -> Dict[str, Any]:
        """Process AI response (shared between local LLM and Groq)"""
        import sys
        import re
        
        print(f"[Price Agent] Extracted products count: {len(pricing_data.get('products', []))}", file=sys.stderr, flush=True)
        if pricing_data.get('products'):
            print(f"[Price Agent] Product names: {[p.get('name') for p in pricing_data.get('products', [])]}", file=sys.stderr, flush=True)
        
        # Validate and normalize the new structure
        products = pricing_data.get("products", [])
        summary = pricing_data.get("summary", {})
        currency = summary.get("currency", pricing_data.get("currency", "USD"))
        
        # FIRST: Try aggressive breakdown extraction if we have a breakdown section
        breakdown_pattern = r'Breakdown[^:]*?:\s*(.*?)(?:\n\n|\n[A-Z][a-z]+\s+[A-Z]|Setup|Storage|We can|Let me|Best|$)'
        breakdown_match = re.search(breakdown_pattern, text, re.IGNORECASE | re.DOTALL)
        if breakdown_match:
            print(f"[Price Agent] Found breakdown section, attempting direct extraction...", file=sys.stderr, flush=True)
            breakdown_products = self._aggressive_email_extraction(text, currency)
            if breakdown_products and len(breakdown_products) > 0:
                # Use breakdown products if they're valid
                valid_breakdown = [p for p in breakdown_products if len(p.get('name', '')) < 100 and p.get('name', '').count('.') < 2]
                if valid_breakdown:
                    print(f"[Price Agent] Using {len(valid_breakdown)} products from breakdown extraction", file=sys.stderr, flush=True)
                    products = valid_breakdown
                    # Still add fees
                    fee_products = [p for p in products if 'fee' in p.get('category', '').lower() or 'fee' in p.get('name', '').lower()]
                    if not fee_products:
                        # Extract fees separately
                        products = self._enhance_email_quote_extraction(products, text, currency)
        
        # AGGRESSIVE VALIDATION: Always check for combined products and split them
        products = self._validate_and_split_products(products, text, currency)
        
        # FILTER OUT INVALID PRODUCTS: Remove products that are actually pricing tiers or other non-product entries
        products = self._filter_invalid_products(products, text)
        
        # FIX PRICING VALUES: Extract correct prices from text if they were incorrectly parsed
        products = self._fix_pricing_values(products, text, currency)
        
        # ENHANCE EMAIL QUOTE EXTRACTION: Better handle conversational/informal quotes (only if we don't have good products)
        if not products or len(products) == 0 or all(len(p.get('name', '')) > 80 for p in products):
            products = self._enhance_email_quote_extraction(products, text, currency)
        
        # VALIDATION: Check if products were incorrectly extracted
        product_count_match = re.search(r'(\d+)\s*(?:different\s*)?products?', text.lower())
        expected_product_count = int(product_count_match.group(1)) if product_count_match else None
        
        if expected_product_count and len(products) != expected_product_count:
            print(f"[Price Agent] WARNING: Expected {expected_product_count} products but got {len(products)}", file=sys.stderr, flush=True)
            fallback_products = self._smart_fallback_extraction(text, currency)
            if fallback_products and len(fallback_products) == expected_product_count:
                products = fallback_products
        
        if not products or len(products) == 0:
            print(f"[Price Agent] WARNING: No products extracted!", file=sys.stderr, flush=True)
            products = self._smart_fallback_extraction(text, currency)
        
        # Convert to legacy format for backward compatibility
        items = []
        total_price = 0.0
        
        for product in products:
            product_name = product.get("name", "Unknown Product")
            pricing_matrix = product.get("pricing_matrix", [])
            
            if not pricing_matrix:
                items.append({
                    "name": product_name,
                    "price": 0.0,
                    "quantity": 1.0,
                    "unit_price": 0.0,
                    "unit": "unit",
                    "product_id": product.get("product_id"),
                    "description": product.get("description", ""),
                    "payment_terms": product.get("default_payment_term", "Not specified")
                })
            else:
                product_total = None
                best_entry = None
                
                for price_entry in pricing_matrix:
                    if price_entry.get("total_price") and price_entry.get("total_price") > 0:
                        product_total = float(price_entry.get("total_price"))
                        best_entry = price_entry
                        break
                
                if not best_entry and pricing_matrix:
                    best_entry = pricing_matrix[0]
                    qty_min = best_entry.get("quantity_min", 1)
                    qty_max = best_entry.get("quantity_max")
                    unit_price = best_entry.get("unit_price", 0.0)
                    quantity = (qty_min + (qty_max or qty_min)) / 2 if qty_max else qty_min
                    product_total = unit_price * quantity if unit_price > 0 else 0.0
                
                if best_entry:
                    qty_min = best_entry.get("quantity_min", 1)
                    qty_max = best_entry.get("quantity_max")
                    unit_price = best_entry.get("unit_price", 0.0)
                    payment_term = best_entry.get("payment_terms", "Standard")
                    quantity = (qty_min + (qty_max or qty_min)) / 2 if qty_max else qty_min
                    
                    items.append({
                        "name": product_name,
                        "price": float(product_total) if product_total else float(unit_price * quantity),
                        "quantity": float(quantity),
                        "unit_price": float(unit_price),
                        "unit": best_entry.get("quantity_unit", "unit"),
                        "product_id": product.get("product_id"),
                        "description": product.get("description", ""),
                        "payment_terms": payment_term,
                        "quantity_min": qty_min,
                        "quantity_max": qty_max,
                        "notes": best_entry.get("notes", "")
                    })
                    total_price += float(product_total) if product_total else float(unit_price * quantity)
        
        if summary.get("total_price_range"):
            total_price = summary["total_price_range"].get("max", total_price)
        
        warranties = pricing_data.get("warranties", [])
        if not warranties:
            warranties = ["Not specified"]
        
        for product in products:
            if "warranty" not in product or not product.get("warranty"):
                product["warranty"] = "Not specified"
            if "pricing_matrix" not in product:
                product["pricing_matrix"] = []
        
        other_info = pricing_data.get("other_info", {})
        if not other_info:
            other_info = {
                "delivery_terms": "Not specified",
                "return_policy": "Not specified",
                "support_services": "Not specified",
                "additional_notes": "Not specified"
            }
        
        result = {
            "vendor_name": vendor_name,
            "items": items,
            "products": products,
            "total_price": float(total_price) if total_price > 0 else 0.0,
            "currency": currency.upper() if currency and currency != "Not specified" else "USD",
            "extracted_text": text[:500],
            "item_count": len(products) if products else len(items),
            "parsing_method": "AI (Local LLM)",
            "notes": pricing_data.get("general_notes", "Not specified"),
            "warranties": warranties,
            "summary": summary,
            "payment_terms_available": summary.get("payment_terms_available", ["Not specified"]),
            "quantity_tiers": summary.get("quantity_tiers", ["Not specified"]),
            "other_info": other_info
        }
        
        print(f"[Price Agent] Final result - products: {len(products)}, items: {len(items)}, total_price: {result['total_price']}", file=sys.stderr, flush=True)
        
        return result
    
    def _fix_pricing_values(self, products: List[Dict[str, Any]], text: str, currency: str) -> List[Dict[str, Any]]:
        """Fix pricing values by extracting them from the original text if they were incorrectly parsed"""
        import re
        import sys
        
        # Extract all prices from text: "USD 68,500 per kg" → 68500
        price_pattern = r'USD\s+(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s+per\s+(kg|lb|unit|piece)'
        all_prices = re.findall(price_pattern, text, re.IGNORECASE)
        
        # Extract quantity tiers: "For orders between 1–5 kg" or "1–3 kg:"
        tier_pattern = r'(\d+)[–-](\d+)\s*(?:kg|lb|units?|pieces?)'
        tiers = re.findall(tier_pattern, text, re.IGNORECASE)
        
        # Extract payment terms
        payment_terms = []
        if re.search(r'full\s+advance', text, re.IGNORECASE):
            payment_terms.append('Full Advance')
        if re.search(r'50%\s*advance', text, re.IGNORECASE):
            payment_terms.append('50% Advance, Balance on Delivery')
        if re.search(r'lc\s+at\s+sight', text, re.IGNORECASE):
            payment_terms.append('LC at Sight')
        if re.search(r'split\s+payment', text, re.IGNORECASE):
            payment_terms.append('Split Payment')
        
        # Determine unit from text
        unit = 'kg'
        if 'per kg' in text.lower() or 'per kilogram' in text.lower():
            unit = 'kg'
        elif 'per lb' in text.lower() or 'per pound' in text.lower():
            unit = 'lb'
        elif 'per unit' in text.lower():
            unit = 'unit'
        
        # Build pricing matrix for each product
        for product in products:
            pricing_matrix = product.get('pricing_matrix', [])
            
            # Check if pricing needs fixing (empty, wrong prices, or missing)
            needs_fix = False
            if not pricing_matrix:
                needs_fix = True
            elif any(p.get('unit_price', 0) < 1000 for p in pricing_matrix if p.get('unit_price')):
                # Prices seem too low (like 500 instead of 68500)
                needs_fix = True
            
            if needs_fix and all_prices:
                print(f"[Price Agent] Fixing pricing for product: {product.get('name', '')[:50]}", file=sys.stderr, flush=True)
                
                new_pricing_matrix = []
                prices = [float(p[0].replace(',', '')) for p in all_prices]
                
                # If we have tiers and prices, match them
                if tiers and prices:
                    # Group prices by tier (assuming prices are listed in order)
                    prices_per_tier = len(prices) // len(tiers) if len(tiers) > 0 else len(prices)
                    
                    for tier_idx, (qty_min, qty_max) in enumerate(tiers):
                        start_idx = tier_idx * prices_per_tier
                        tier_prices = prices[start_idx:start_idx + prices_per_tier]
                        
                        # Match prices with payment terms if available
                        if payment_terms and len(tier_prices) == len(payment_terms):
                            for price_val, payment_term in zip(tier_prices, payment_terms):
                                new_pricing_matrix.append({
                                    "quantity_min": int(qty_min),
                                    "quantity_max": int(qty_max),
                                    "quantity_unit": unit,
                                    "payment_terms": payment_term,
                                    "unit_price": price_val,
                                    "total_price": None,
                                    "currency": currency.upper() if currency and currency != "Not specified" else "USD",
                                    "notes": ""
                                })
                        else:
                            # Use first price for this tier
                            if tier_prices:
                                new_pricing_matrix.append({
                                    "quantity_min": int(qty_min),
                                    "quantity_max": int(qty_max),
                                    "quantity_unit": unit,
                                    "payment_terms": payment_terms[0] if payment_terms else "Standard",
                                    "unit_price": tier_prices[0],
                                    "total_price": None,
                                    "currency": currency.upper() if currency and currency != "Not specified" else "USD",
                                    "notes": ""
                                })
                elif prices:
                    # No tiers, just use all prices
                    if payment_terms and len(prices) == len(payment_terms):
                        for price_val, payment_term in zip(prices, payment_terms):
                            new_pricing_matrix.append({
                                "quantity_min": 1,
                                "quantity_max": None,
                                "quantity_unit": unit,
                                "payment_terms": payment_term,
                                "unit_price": price_val,
                                "total_price": None,
                                "currency": currency.upper() if currency and currency != "Not specified" else "USD",
                                "notes": ""
                            })
                    else:
                        # Use first price
                        new_pricing_matrix.append({
                            "quantity_min": 1,
                            "quantity_max": None,
                            "quantity_unit": unit,
                            "payment_terms": payment_terms[0] if payment_terms else "Standard",
                            "unit_price": prices[0],
                            "total_price": None,
                            "currency": currency.upper() if currency and currency != "Not specified" else "USD",
                            "notes": ""
                        })
                
                if new_pricing_matrix:
                    product['pricing_matrix'] = new_pricing_matrix
                    print(f"[Price Agent] Fixed pricing: {len(new_pricing_matrix)} entries with prices: {[p.get('unit_price') for p in new_pricing_matrix]}", file=sys.stderr, flush=True)
        
        return products
    
    def _enhance_email_quote_extraction(self, products: List[Dict[str, Any]], text: str, currency: str) -> List[Dict[str, Any]]:
        """Enhance extraction specifically for email/informal quotes with better product and price detection"""
        import re
        import sys
        
        text_lower = text.lower()
        
        # AGGRESSIVE EMAIL QUOTE EXTRACTION: If no products or products seem wrong, extract directly from text
        if not products or len(products) == 0 or all(not p.get('pricing_matrix') or all(pr.get('unit_price', 0) == 0 for pr in p.get('pricing_matrix', [])) for p in products):
            print(f"[Price Agent] No valid products found, attempting aggressive email extraction...", file=sys.stderr, flush=True)
            aggressive_products = self._aggressive_email_extraction(text, currency)
            if aggressive_products:
                print(f"[Price Agent] Aggressive extraction found {len(aggressive_products)} products", file=sys.stderr, flush=True)
                return aggressive_products
        
        # If we have products but they seem incomplete, try to enhance them
        if not products:
            return products
        
        # Look for email-style product mentions: "Gold American Eagles: $2,395/oz"
        # Pattern: Product name followed by colon and price
        email_product_pattern = r'([A-Z][^:]+?):\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*/?\s*(\w+)'
        email_matches = re.findall(email_product_pattern, text)
        
        # Also look for: "Product name - price/unit, quantity for total"
        # Pattern: "Gold: ~$75k (31–32 oz at $2,395/oz)"
        enhanced_pattern = r'([A-Z][^:–-]+?)[:–-]\s*(?:~|approx|approximately)?\s*\$?(\d{1,3}(?:,\d{3})*(?:k|K)?)\s*(?:for|\(|,)\s*(\d+)[–-]?(\d+)?\s*(\w+)?'
        
        # Try to match products with their pricing from email format
        for product in products:
            product_name = product.get('name', '').strip()
            pricing_matrix = product.get('pricing_matrix', [])
            
            # If product has no pricing or incomplete pricing, try to extract from text
            if not pricing_matrix or all(p.get('unit_price', 0) == 0 for p in pricing_matrix):
                # Look for this product name in the text with pricing
                # Pattern: "Gold American Eagles: $2,395/oz" or "Gold Eagles: $2,395/oz"
                product_variations = [
                    product_name,
                    product_name.replace('American ', ''),
                    product_name.replace('Gold ', '').replace('Silver ', '')
                ]
                
                for variation in product_variations:
                    if not variation or len(variation) < 3:
                        continue
                    
                    # Look for pattern: "Product: price/unit"
                    pattern = rf'{re.escape(variation)}[:\s]+?\$?(\d{{1,3}}(?:,\d{{3}})*(?:\.\d{{2}})?)\s*/?\s*(\w+)'
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        unit_price = float(match.group(1).replace(',', ''))
                        unit = match.group(2).lower()
                        
                        # Look for quantity: "31–32 oz" or "~31-32 oz"
                        qty_pattern = rf'{re.escape(variation)}[^:]*?(\d+)[–-]?(\d+)?\s*{re.escape(unit)}'
                        qty_match = re.search(qty_pattern, text, re.IGNORECASE)
                        
                        quantity_min = None
                        quantity_max = None
                        if qty_match:
                            quantity_min = int(qty_match.group(1))
                            quantity_max = int(qty_match.group(2)) if qty_match.group(2) else quantity_min
                        
                        # Look for calculation pattern: "x 40 = $96,400" first (most reliable)
                        calculation_pattern = rf'{re.escape(variation)}[^=]*?x\s*(\d+)\s*=\s*\$?(\d{{1,3}}(?:,\d{{3}})*)'
                        calc_match = re.search(calculation_pattern, text, re.IGNORECASE)
                        
                        total_price = None
                        if calc_match:
                            # Found explicit calculation: "x 40 = $96,400"
                            total_str = calc_match.group(2).replace(',', '')
                            total_price = float(total_str)
                            # Also update quantity if found
                            if not quantity_min:
                                quantity_min = int(calc_match.group(1))
                                quantity_max = quantity_min
                        else:
                            # Pattern: "for ~$75k" or "for approximately $75,000"
                            total_pattern = rf'{re.escape(variation)}[^$]*?(?:for|total|around|~|approx)\s*\$?(\d{{1,3}}(?:,\d{{3}})*(?:k|K)?)'
                            total_match = re.search(total_pattern, text, re.IGNORECASE)
                            
                            if total_match:
                                total_str = total_match.group(1).replace(',', '')
                                if 'k' in total_str.lower():
                                    total_price = float(total_str.lower().replace('k', '')) * 1000
                                else:
                                    total_price = float(total_str)
                        
                        # Create pricing matrix entry
                        if unit_price > 0:
                            pricing_matrix = [{
                                "quantity_min": quantity_min or 1,
                                "quantity_max": quantity_max,
                                "quantity_unit": unit,
                                "payment_terms": "Not specified",
                                "unit_price": unit_price,
                                "total_price": total_price,
                                "currency": currency.upper() if currency and currency != "Not specified" else "USD",
                                "notes": "Extracted from email quote"
                            }]
                            product['pricing_matrix'] = pricing_matrix
                            print(f"[Price Agent] Enhanced product {product_name} with pricing: {unit_price}/{unit}", file=sys.stderr, flush=True)
                            break
        
        # Extract fees as separate products if mentioned
        fee_patterns = [
            (r'(?:setup|account\s+setup|admin)[:\s]+(?:usually|around|approx|~)?\s*\$?(\d{1,3}(?:,\d{3})*)', 'Setup Fee'),
            (r'storage[:\s]+(?:around|approx|~)?\s*\$?(\d{1,3}(?:,\d{3})*)[–-]?(\d{1,3}(?:,\d{3})*)?\s*(?:annually|per\s+year|/year)', 'Storage Fee'),
        ]
        
        for pattern, fee_name in fee_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fee_amount = float(match.group(1).replace(',', ''))
                # Check if this fee product already exists
                existing_fee = next((p for p in products if fee_name.lower() in p.get('name', '').lower()), None)
                if not existing_fee:
                    products.append({
                        "product_id": f"fee_{len(products) + 1}",
                        "name": fee_name,
                        "description": "Fee extracted from quote",
                        "category": "Fee",
                        "pricing_matrix": [{
                            "quantity_min": 1,
                            "quantity_max": 1,
                            "quantity_unit": "one-time" if "setup" in fee_name.lower() else "year",
                            "payment_terms": "Not specified",
                            "unit_price": fee_amount,
                            "total_price": fee_amount,
                            "currency": currency.upper() if currency and currency != "Not specified" else "USD",
                            "notes": "Fee extracted from email quote"
                        }],
                        "default_payment_term": "Not specified",
                        "warranty": "Not specified",
                        "delivery_time": "Not specified"
                    })
                    print(f"[Price Agent] Added fee product: {fee_name} = ${fee_amount}", file=sys.stderr, flush=True)
        
        return products
    
    def _aggressive_email_extraction(self, text: str, currency: str) -> List[Dict[str, Any]]:
        """Aggressively extract products from email-style quotes using direct pattern matching"""
        import re
        import sys
        
        products = []
        text_lower = text.lower()
        
        # FIRST: Look for "Breakdown" sections which are very reliable
        # Pattern: "Breakdown (rough numbers):\nGold Eagles: ~$2,410 x 40 = $96,400"
        breakdown_pattern = r'Breakdown[^:]*?:\s*(.*?)(?:\n\n|\n[A-Z][a-z]+\s+[A-Z]|Setup|Storage|We can|Let me|Best|$)'
        breakdown_match = re.search(breakdown_pattern, text, re.IGNORECASE | re.DOTALL)
        
        if breakdown_match:
            breakdown_text = breakdown_match.group(1)
            print(f"[Price Agent] Found breakdown section: {breakdown_text[:300]}", file=sys.stderr, flush=True)
            
            # Extract from breakdown: "Gold Eagles: ~$2,410 x 40 = $96,400"
            # More flexible pattern to handle variations
            breakdown_line_patterns = [
                r'([A-Z][A-Za-z\s]+?(?:Eagles?|Bars?|Coins?))[:\s]+?~?\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*x\s*(\d+)\s*=\s*\$?(\d{1,3}(?:,\d{3})*)',
                r'([A-Z][A-Za-z\s]+?(?:Eagles?|Bars?|Coins?))[:\s]+?~?\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*/\s*(\w+)\s+x\s*(\d+)\s*=\s*\$?(\d{1,3}(?:,\d{3})*)',
            ]
            
            for pattern in breakdown_line_patterns:
                breakdown_lines = re.findall(pattern, breakdown_text, re.IGNORECASE)
                
                for line_match in breakdown_lines:
                    if len(line_match) == 4:
                        # Pattern 1: "Gold Eagles: ~$2,410 x 40 = $96,400"
                        product_name = line_match[0].strip()
                        unit_price = float(line_match[1].replace(',', ''))
                        quantity = int(line_match[2])
                        total_price = float(line_match[3].replace(',', ''))
                        unit = 'oz' if 'oz' in breakdown_text.lower() else 'unit'
                    elif len(line_match) == 5:
                        # Pattern 2: "Gold Eagles: ~$2,410/oz x 40 = $96,400"
                        product_name = line_match[0].strip()
                        unit_price = float(line_match[1].replace(',', ''))
                        unit = line_match[2].lower()
                        quantity = int(line_match[3])
                        total_price = float(line_match[4].replace(',', ''))
                    else:
                        continue
                    
                    # Check if product name is valid (not too long, not a sentence)
                    if len(product_name) > 50 or '.' in product_name or product_name.count(' ') > 5:
                        continue
                    
                    products.append({
                        "product_id": f"product_{len(products) + 1}",
                        "name": product_name,
                        "description": "Extracted from breakdown",
                        "category": "Not specified",
                        "pricing_matrix": [{
                            "quantity_min": quantity,
                            "quantity_max": quantity,
                            "quantity_unit": unit,
                            "payment_terms": "Not specified",
                            "unit_price": unit_price,
                            "total_price": total_price,
                            "currency": currency.upper() if currency and currency != "Not specified" else "USD",
                            "notes": "Extracted from breakdown section"
                        }],
                        "default_payment_term": "Not specified",
                        "warranty": "Not specified",
                        "delivery_time": "Not specified"
                    })
                    print(f"[Price Agent] Extracted from breakdown: {product_name} - ${unit_price}/{unit} x {quantity} = ${total_price}", file=sys.stderr, flush=True)
                    break  # Only process first match per pattern
        
        # Pattern 1: "Gold American Eagles: $2,395/oz" or "Gold Eagles: $2,395/oz"
        # Pattern 2: "Gold: ~$75k (31–32 oz at $2,395/oz)"
        # Pattern 3: "Gold American Eagles (1oz)" followed by pricing
        # Pattern 4: "Gold American Eagles are at approx $2,410/oz"
        # Pattern 5: "Gold Eagles: ~$2,410 x 40 = $96,400" (direct calculation)
        
        # Look for direct calculation pattern: "Product: price x quantity = total" (only if no breakdown products found)
        if not products:
            direct_calc_pattern = r'([A-Z][A-Za-z\s]{1,40}(?:Eagles?|Bars?|Coins?))[:\s]+?~?\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*x\s*(\d+)\s*=\s*\$?(\d{1,3}(?:,\d{3})*)'
            direct_calcs = re.findall(direct_calc_pattern, text, re.IGNORECASE)
            
            for calc_match in direct_calcs:
                product_name = calc_match[0].strip()
                # Filter out invalid product names (too long, contains periods, etc.)
                if len(product_name) > 50 or '.' in product_name or product_name.count(' ') > 5:
                    continue
                    
                unit_price = float(calc_match[1].replace(',', ''))
                quantity = int(calc_match[2])
                total_price = float(calc_match[3].replace(',', ''))
                
                # Determine unit
                unit = 'oz' if 'oz' in text.lower() else 'unit'
                
                products.append({
                    "product_id": f"product_{len(products) + 1}",
                    "name": product_name,
                    "description": "Extracted from email quote",
                    "category": "Not specified",
                    "pricing_matrix": [{
                        "quantity_min": quantity,
                        "quantity_max": quantity,
                        "quantity_unit": unit,
                        "payment_terms": "Not specified",
                        "unit_price": unit_price,
                        "total_price": total_price,
                        "currency": currency.upper() if currency and currency != "Not specified" else "USD",
                        "notes": "Extracted from direct calculation"
                    }],
                    "default_payment_term": "Not specified",
                    "warranty": "Not specified",
                    "delivery_time": "Not specified"
                })
                print(f"[Price Agent] Extracted direct calc: {product_name} - ${unit_price} x {quantity} = ${total_price}", file=sys.stderr, flush=True)
        
        # Look for product names with prices: "Product Name: $price/unit" or "Product Name are at $price/unit"
        product_price_patterns = [
            r'([A-Z][A-Za-z\s]+?(?:Eagles?|Bars?|Coins?|Biscuits?|Grain))[:\s]+?\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*/?\s*(\w+)',
            r'([A-Z][A-Za-z\s]+?(?:Eagles?|Bars?|Coins?))[^:]*?are\s+at\s+approx\s+\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*/?\s*(\w+)',
            r'([A-Z][A-Za-z\s]+?(?:Eagles?|Bars?|Coins?))[^:]*?\$?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*/?\s*(\w+)',
        ]
        
        all_matches = []
        for pattern in product_price_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            all_matches.extend(matches)
        
        print(f"[Price Agent] Found {len(all_matches)} product-price matches: {all_matches}", file=sys.stderr, flush=True)
        
        for match in all_matches:
            product_name = match[0].strip()
            unit_price_str = match[1].replace(',', '')
            unit = match[2].lower()
            
            try:
                unit_price = float(unit_price_str)
                
                # Look for quantity near this product
                # Pattern: "31–32 oz" or "~31-32 oz" or "around 40 oz"
                qty_pattern = rf'{re.escape(product_name)}[^:]*?(\d+)[–-]?(\d+)?\s*{re.escape(unit)}'
                qty_match = re.search(qty_pattern, text, re.IGNORECASE)
                
                quantity_min = None
                quantity_max = None
                if qty_match:
                    quantity_min = int(qty_match.group(1))
                    quantity_max = int(qty_match.group(2)) if qty_match.group(2) else quantity_min
                
                # Look for total: "for ~$75k" or "for approximately $75,000" or "x 40 = $96,400"
                # Pattern 1: "x 40 = $96,400" or "x 40 = 96,400"
                calculation_pattern = rf'{re.escape(product_name)}[^=]*?x\s*(\d+)\s*=\s*\$?(\d{{1,3}}(?:,\d{{3}})*)'
                calc_match = re.search(calculation_pattern, text, re.IGNORECASE)
                
                total_price = None
                if calc_match:
                    # Found explicit calculation: "x 40 = $96,400"
                    total_str = calc_match.group(2).replace(',', '')
                    total_price = float(total_str)
                    # Also update quantity if found
                    if not quantity_min:
                        quantity_min = int(calc_match.group(1))
                        quantity_max = quantity_min
                else:
                    # Pattern 2: "for ~$75k" or "for approximately $75,000"
                    total_pattern = rf'{re.escape(product_name)}[^$]*?(?:for|total|around|~|approx|approximately)\s*\$?(\d{{1,3}}(?:,\d{{3}})*(?:k|K)?)'
                    total_match = re.search(total_pattern, text, re.IGNORECASE)
                    
                    if total_match:
                        total_str = total_match.group(1).replace(',', '')
                        if 'k' in total_str.lower():
                            total_price = float(total_str.lower().replace('k', '')) * 1000
                        else:
                            total_price = float(total_str)
                    elif quantity_min and unit_price:
                        # Calculate total from unit price × quantity
                        quantity = (quantity_min + (quantity_max or quantity_min)) / 2 if quantity_max else quantity_min
                        total_price = unit_price * quantity
                
                # Create product
                pricing_matrix = [{
                    "quantity_min": quantity_min or 1,
                    "quantity_max": quantity_max,
                    "quantity_unit": unit,
                    "payment_terms": "Not specified",
                    "unit_price": unit_price,
                    "total_price": total_price,
                    "currency": currency.upper() if currency and currency != "Not specified" else "USD",
                    "notes": "Extracted from email quote"
                }]
                
                products.append({
                    "product_id": f"product_{len(products) + 1}",
                    "name": product_name,
                    "description": "Extracted from email quote",
                    "category": "Not specified",
                    "pricing_matrix": pricing_matrix,
                    "default_payment_term": "Not specified",
                    "warranty": "Not specified",
                    "delivery_time": "Not specified"
                })
                
                print(f"[Price Agent] Extracted: {product_name} - ${unit_price}/{unit}, qty: {quantity_min}-{quantity_max}, total: ${total_price}", file=sys.stderr, flush=True)
                
            except ValueError as e:
                print(f"[Price Agent] Error parsing price for {product_name}: {e}", file=sys.stderr, flush=True)
                continue
        
        # Also look for products mentioned in lists: "Gold American Eagles (1oz)" and "Silver Eagles"
        # Pattern: Look for "recommending" or "mix" followed by product list
        # Also check for "Gold American Eagles" and "Silver Eagles" mentioned separately
        if not products or len(products) < 2:
            # Try pattern: "recommending a mix for diversification: Gold American Eagles (1oz), Some silver"
            mix_pattern = r'(?:recommending|mix|including)[^:]*?:\s*([^:]+?)(?:\.|Current|Fees|Again)'
            mix_match = re.search(mix_pattern, text, re.IGNORECASE | re.DOTALL)
            
            # Also look for products mentioned separately: "Gold American Eagles" and "Silver Eagles"
            # Pattern: Look for both "Gold" and "Silver" products
            gold_pattern = r'(Gold\s+American\s+Eagles?|Gold\s+Eagles?)'
            silver_pattern = r'(Silver\s+Eagles?)'
            
            product_names = []
            if mix_match:
                product_list_text = mix_match.group(1)
                # Extract product names from the list
                product_name_pattern = r'([A-Z][A-Za-z\s]+?(?:Eagles?|Bars?|Coins?|Silver))'
                product_names = re.findall(product_name_pattern, product_list_text)
            
            # Also check for direct mentions
            gold_match = re.search(gold_pattern, text, re.IGNORECASE)
            silver_match = re.search(silver_pattern, text, re.IGNORECASE)
            
            if gold_match and "Gold" not in " ".join(product_names):
                product_names.append(gold_match.group(1))
            if silver_match and "Silver" not in " ".join(product_names):
                product_names.append(silver_match.group(1))
            
            print(f"[Price Agent] Found products in mix/direct: {product_names}", file=sys.stderr, flush=True)
            
            if product_names:
                # For each product name, find its pricing
                for prod_name in product_names:
                    prod_name = prod_name.strip()
                    # Look for pricing near this product name
                    price_pattern = rf'{re.escape(prod_name)}[^:]*?:\s*\$?(\d{{1,3}}(?:,\d{{3}})*(?:\.\d{{2}})?)\s*/?\s*(\w+)'
                    price_match = re.search(price_pattern, text, re.IGNORECASE)
                    
                    if price_match:
                        unit_price = float(price_match.group(1).replace(',', ''))
                        unit = price_match.group(2).lower()
                        
                        # Look for quantity and total
                        qty_pattern = rf'{re.escape(prod_name)}[^$]*?(\d+)[–-]?(\d+)?\s*{re.escape(unit)}'
                        qty_match = re.search(qty_pattern, text, re.IGNORECASE)
                        
                        quantity_min = None
                        quantity_max = None
                        if qty_match:
                            quantity_min = int(qty_match.group(1))
                            quantity_max = int(qty_match.group(2)) if qty_match.group(2) else quantity_min
                        
                        # Look for calculation pattern: "x 40 = $96,400"
                        calculation_pattern = rf'{re.escape(prod_name)}[^=]*?x\s*(\d+)\s*=\s*\$?(\d{{1,3}}(?:,\d{{3}})*)'
                        calc_match = re.search(calculation_pattern, text, re.IGNORECASE)
                        
                        total_price = None
                        if calc_match:
                            # Found explicit calculation
                            total_str = calc_match.group(2).replace(',', '')
                            total_price = float(total_str)
                            if not quantity_min:
                                quantity_min = int(calc_match.group(1))
                                quantity_max = quantity_min
                        else:
                            # Pattern: "for ~$75k" or "for approximately $75,000"
                            total_pattern = rf'{re.escape(prod_name)}[^$]*?(?:for|~|approx)\s*\$?(\d{{1,3}}(?:,\d{{3}})*(?:k|K)?)'
                            total_match = re.search(total_pattern, text, re.IGNORECASE)
                            
                            if total_match:
                                total_str = total_match.group(1).replace(',', '')
                                if 'k' in total_str.lower():
                                    total_price = float(total_str.lower().replace('k', '')) * 1000
                                else:
                                    total_price = float(total_str)
                            elif quantity_min and unit_price:
                                quantity = (quantity_min + (quantity_max or quantity_min)) / 2 if quantity_max else quantity_min
                                total_price = unit_price * quantity
                        
                        if unit_price > 0:
                            products.append({
                                "product_id": f"product_{len(products) + 1}",
                                "name": prod_name,
                                "description": "Extracted from email quote",
                                "category": "Not specified",
                                "pricing_matrix": [{
                                    "quantity_min": quantity_min or 1,
                                    "quantity_max": quantity_max,
                                    "quantity_unit": unit,
                                    "payment_terms": "Not specified",
                                    "unit_price": unit_price,
                                    "total_price": total_price,
                                    "currency": currency.upper() if currency and currency != "Not specified" else "USD",
                                    "notes": "Extracted from email quote"
                                }],
                                "default_payment_term": "Not specified",
                                "warranty": "Not specified",
                                "delivery_time": "Not specified"
                            })
        
        # Extract fees
        fee_patterns = [
            (r'(?:setup|account\s+setup|admin)[:\s]+(?:usually|around|approx|~)?\s*\$?(\d{1,3}(?:,\d{3})*)', 'Setup Fee'),
            (r'storage[:\s]+(?:around|approx|~)?\s*\$?(\d{1,3}(?:,\d{3})*)[–-]?(\d{1,3}(?:,\d{3})*)?\s*(?:annually|per\s+year|/year)', 'Storage Fee'),
        ]
        
        for pattern, fee_name in fee_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                fee_amount = float(match.group(1).replace(',', ''))
                existing_fee = next((p for p in products if fee_name.lower() in p.get('name', '').lower()), None)
                if not existing_fee:
                    products.append({
                        "product_id": f"fee_{len(products) + 1}",
                        "name": fee_name,
                        "description": "Fee extracted from quote",
                        "category": "Fee",
                        "pricing_matrix": [{
                            "quantity_min": 1,
                            "quantity_max": 1,
                            "quantity_unit": "one-time" if "setup" in fee_name.lower() else "year",
                            "payment_terms": "Not specified",
                            "unit_price": fee_amount,
                            "total_price": fee_amount,
                            "currency": currency.upper() if currency and currency != "Not specified" else "USD",
                            "notes": "Fee extracted from email quote"
                        }],
                        "default_payment_term": "Not specified",
                        "warranty": "Not specified",
                        "delivery_time": "Not specified"
                    })
        
        return products
    
    def _is_email_style_quote(self, text: str) -> bool:
        """Detect if the quote is email-style / conversational (so we avoid parsing sentences as line items)."""
        if not text or len(text) < 50:
            return False
        text_lower = text.lower()
        markers = [
            "good talking", "hey there", "let me know", "if we lock", "thanks,", "best,",
            "per your request", "following up", "ballpark", "rough numbers", "like i said",
            "call or email", "walk you through", "get you going", "we can do", "we'd probably",
            "re: ", "subject:", "from:", "to:", "sent from my", "cheers,", "regards,",
        ]
        return sum(1 for m in markers if m in text_lower) >= 2
    
    async def _extract_email_style_and_build_result(self, text: str, vendor_name: str) -> Dict[str, Any] | None:
        """For email-style quotes: extract products via LLM or regex, then build full result dict. Returns None if nothing extracted."""
        products = await self._extract_email_style_products(text, "USD")
        if not products:
            return None
        return self._build_result_from_email_products(products, text, vendor_name)
    
    async def _extract_email_style_products(self, text: str, currency: str) -> List[Dict[str, Any]]:
        """Extract product line items from email-style quote: try LLM first, then generic regex fallback."""
        import sys
        try:
            raw_items = await self._extract_email_style_via_llm(text, currency)
            if raw_items:
                print("[Price Agent] Email-style quote: using LLM extraction path.", file=sys.stderr, flush=True)
                return self._email_raw_items_to_products(raw_items, currency)
        except Exception as e:
            print(f"[Price Agent] Email-style LLM extraction failed: {e}", file=sys.stderr, flush=True)
        print("[Price Agent] Email-style quote: using regex fallback (LLM unavailable or returned no items).", file=sys.stderr, flush=True)
        return self._extract_email_style_regex_fallback(text, currency)
    
    async def _extract_email_style_via_llm(self, text: str, currency: str) -> List[Dict[str, Any]]:
        """Send email text to LLM with prompt to extract only product line items; return list of {product_name, unit_price, quantity, total_price}."""
        prompt = (
            "This is an informal email quote. Extract only actual product line items with prices. "
            "Ignore conversational text, greetings, timing comments, and payment discussion. "
            "Return a JSON object with a single key 'items' whose value is an array of objects, "
            "each with: product_name, unit_price (number), quantity (number), total_price (number). "
            "Only include items that are clearly products being sold with a price attached.\n\n"
            "Quote text:\n" + text[:12000]
        )
        out: List[Dict[str, Any]] = []
        try:
            if self.use_local_llm:
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.1, "num_predict": 2000},
                    },
                    timeout=90,
                )
                if response.status_code != 200:
                    return []
                response_text = response.json().get("response", "")
            elif self.use_ai and getattr(self, "client", None):
                response = self.client.chat.completions.create(
                    model="llama-3.1-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                )
                response_text = response.choices[0].message.content or ""
            else:
                import sys
                print("[Price Agent] Email-style LLM skipped: neither Ollama nor Groq available.", file=sys.stderr, flush=True)
                return []
            # Parse JSON: expect {"items": [...]} or bare array [...]
            json_str = self._extract_json_from_response(response_text)
            if not json_str.strip():
                # Try bare array
                start = response_text.find("[")
                if start >= 0:
                    end = response_text.rfind("]") + 1
                    if end > start:
                        json_str = response_text[start:end]
            if not json_str.strip():
                return []
            data = json.loads(json_str)
            items = data.get("items", data) if isinstance(data, dict) else (data if isinstance(data, list) else None)
            if isinstance(items, list) and items:
                for o in items:
                    if isinstance(o, dict) and o.get("product_name") and (o.get("unit_price") is not None or o.get("total_price") is not None):
                        out.append({
                            "product_name": str(o.get("product_name", "")).strip(),
                            "unit_price": float(o.get("unit_price") or 0),
                            "quantity": int(float(o.get("quantity") or 1)),
                            "total_price": float(o.get("total_price") or 0),
                        })
            return out
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            import sys
            print(f"[Price Agent] Email-style LLM parse error: {e}", file=sys.stderr, flush=True)
            return []
    
    def _email_raw_items_to_products(self, raw_items: List[Dict[str, Any]], currency: str) -> List[Dict[str, Any]]:
        """Convert LLM raw items (product_name, unit_price, quantity, total_price) to internal product format."""
        products = []
        for i, r in enumerate(raw_items):
            name = self._clean_email_product_name((r.get("product_name") or "").strip())
            if not name or len(name) > 200:
                continue
            unit_price = float(r.get("unit_price") or 0)
            quantity = int(float(r.get("quantity") or 1))
            total_price = float(r.get("total_price") or 0)
            if total_price <= 0 and unit_price > 0:
                total_price = round(unit_price * quantity, 2)
            if unit_price <= 0 and total_price > 0 and quantity > 0:
                unit_price = round(total_price / quantity, 2)
            if unit_price <= 0 and total_price <= 0:
                continue
            curr = (currency or "USD").upper()
            products.append({
                "product_id": f"product_{i + 1}",
                "name": name,
                "description": "Extracted from email-style quote",
                "category": "Not specified",
                "pricing_matrix": [{
                    "quantity_min": quantity,
                    "quantity_max": quantity,
                    "quantity_unit": "unit",
                    "payment_terms": "Not specified",
                    "unit_price": unit_price,
                    "total_price": total_price,
                    "currency": curr,
                    "notes": "Email quote",
                }],
                "default_payment_term": "Not specified",
                "warranty": "Not specified",
                "delivery_time": "Not specified",
            })
        return products
    
    def _clean_email_product_name(self, name: str) -> str:
        """Strip pricing/quantity text from product name (e.g. 'per unit x 20 Monitor stands' -> 'Monitor stands')."""
        import re
        if not name or not name.strip():
            return name
        s = name.strip()
        # Remove leading fragments: "per unit x 20 ", "each x 40 ", "$45 ", "around ", "about "
        s = re.sub(r'^(?:per\s+unit|each)\s*x\s*~?\s*\d+\s*', '', s, flags=re.IGNORECASE)
        s = re.sub(r'^\$?\s*\d+(?:\.\d{2})?\s*(?:each|/unit|per\s*unit)?\s*x\s*~?\s*\d+\s*', '', s, flags=re.IGNORECASE)
        s = re.sub(r'^(?:around|about|~|approx\.?)\s*\$?\s*\d+(?:\.\d{2})?\s*', '', s, flags=re.IGNORECASE)
        # Remove trailing fragments: " per unit x 20", " $45 each", " x 40"
        s = re.sub(r'\s*(?:per\s+unit|each)\s*x\s*~?\s*\d+\s*$', '', s, flags=re.IGNORECASE)
        s = re.sub(r'\s*\$?\s*\d+(?:\.\d{2})?\s*(?:each|/unit|per\s*unit)?\s*x\s*~?\s*\d+\s*$', '', s, flags=re.IGNORECASE)
        s = re.sub(r'\s*x\s*~?\s*\d+\s*$', '', s, flags=re.IGNORECASE)
        s = re.sub(r'\s+\d+(?:\.\d{2})?\s*(?:each|/unit|per\s*unit)\s*$', '', s, flags=re.IGNORECASE)
        return re.sub(r'\s+', ' ', s).strip()

    def _extract_email_style_regex_fallback(self, text: str, currency: str) -> List[Dict[str, Any]]:
        """Generic regex fallback: find [product description] + [price]. Extract ALL matching lines. Works for any product type."""
        import re
        products = []
        curr = (currency or "USD").upper()
        default_qty = 1
        qty_match = re.search(r'(?:for your |x\s*~?|quantity\s*:?\s*)(\d{2,6})\s*(?:folks?|units?|person|each|pieces?)?', text.lower())
        if qty_match:
            default_qty = int(qty_match.group(1))
        # One unified pattern: optional leading bullet, product name (no newlines), : or -, optional around/about, price, optional each/per unit, optional x N
        # Use [^\n]+? so we only match within one line (avoids capturing "per unit x 20\nMonitor stands" as name)
        pattern = re.compile(
            r'(?:^|[\n\r])'
            r'(?:[-*•]\s*)?'
            r'([^\n\r:]+?)'
            r'[:\-]\s*'
            r'(?:around|about|~|approx\.?)?\s*'
            r'\$?\s*(\d+(?:\.\d{2})?)'
            r'\s*(?:each|/unit|per\s*unit)?'
            r'(?:\s*x\s*~?\s*(\d{2,6}))?',
            re.IGNORECASE | re.MULTILINE
        )
        for m in pattern.finditer(text):
            name = self._clean_email_product_name(m.group(1).strip())
            name = re.sub(r'\s+', ' ', name).strip()
            if len(name) < 2 or len(name) > 150:
                continue
            if any(x in name.lower() for x in ["thanks", "best,", "let me", "if we", "good talking", "call or", "hey there"]):
                continue
            unit_price = float(m.group(2))
            qty = int(m.group(3)) if m.group(3) else default_qty
            total = round(unit_price * qty, 2)
            if any(p.get("name", "").lower() == name.lower() for p in products):
                continue
            products.append({
                "product_id": f"product_{len(products) + 1}",
                "name": name,
                "description": "Extracted from email-style quote",
                "category": "Not specified",
                "pricing_matrix": [{
                    "quantity_min": qty,
                    "quantity_max": qty,
                    "quantity_unit": "unit",
                    "payment_terms": "Not specified",
                    "unit_price": unit_price,
                    "total_price": total,
                    "currency": curr,
                    "notes": "Extracted from email quote",
                }],
                "default_payment_term": "Not specified",
                "warranty": "Not specified",
                "delivery_time": "Not specified",
            })
        return products
    
    def _build_result_from_email_products(self, products: List[Dict[str, Any]], text: str, vendor_name: str) -> Dict[str, Any]:
        """Build the same result structure as _process_ai_response from email-style product list."""
        import sys
        items = []
        total_price = 0.0
        currency = "USD"
        for product in products:
            name = product.get("name", "Unknown Product")
            pricing_matrix = product.get("pricing_matrix", [])
            if not pricing_matrix:
                items.append({"name": name, "price": 0.0, "quantity": 1.0, "unit_price": 0.0, "unit": "unit", "product_id": product.get("product_id"), "description": product.get("description", ""), "payment_terms": "Not specified"})
                continue
            entry = pricing_matrix[0]
            qty = int(entry.get("quantity_min") or entry.get("quantity_max") or 1)
            unit_price = float(entry.get("unit_price") or 0)
            total_item = float(entry.get("total_price") or unit_price * qty)
            total_price += total_item
            if entry.get("currency"):
                currency = entry["currency"]
            items.append({
                "name": name,
                "price": total_item,
                "quantity": float(qty),
                "unit_price": unit_price,
                "unit": entry.get("quantity_unit", "unit"),
                "product_id": product.get("product_id"),
                "description": product.get("description", ""),
                "payment_terms": entry.get("payment_terms", "Not specified"),
            })
        for p in products:
            if "warranty" not in p or not p.get("warranty"):
                p["warranty"] = "Not specified"
            if "pricing_matrix" not in p:
                p["pricing_matrix"] = []
        summary = {"currency": currency, "total_products": len(products)}
        return {
            "vendor_name": vendor_name,
            "items": items,
            "products": products,
            "total_price": float(total_price),
            "currency": currency,
            "extracted_text": text[:500],
            "item_count": len(products),
            "parsing_method": "AI (email-style)",
            "notes": "Not specified",
            "warranties": ["Not specified"],
            "summary": summary,
            "payment_terms_available": ["Not specified"],
            "quantity_tiers": ["Not specified"],
            "other_info": {"delivery_terms": "Not specified", "return_policy": "Not specified", "support_services": "Not specified", "additional_notes": "Not specified"},
        }
    
    def _filter_invalid_products(self, products: List[Dict[str, Any]], text: str) -> List[Dict[str, Any]]:
        """Filter out products that are actually pricing tiers, delivery info, or other non-product entries"""
        import re
        import sys
        
        # Phrases that indicate conversational text, not a product name
        conversational_phrases = [
            "good talking", "talking earlier", "lock it in", "if we lock", "let me know", "call or email",
            "we can do", "get you", "walk you through", "like i said", "ballpark numbers", "rough numbers",
            "per your request", "following up", "hey there", "thanks,", "best,", "cheers,", "regards,",
            "this month", "next steps", "give or take", "pretty close", "sharpen the pencil",
        ]
        
        valid_products = []
        
        for product in products:
            product_name = product.get('name', '').strip()
            product_name_lower = product_name.lower()
            
            # Skip if product name is clearly conversational (phrase appears in name)
            if any(phrase in product_name_lower for phrase in conversational_phrases):
                continue
            
            # Only keep line items that have a clear price (product + price)
            pricing_matrix = product.get("pricing_matrix") or []
            has_positive_price = False
            for entry in pricing_matrix:
                up = entry.get("unit_price") or 0
                tp = entry.get("total_price") or 0
                if (isinstance(up, (int, float)) and float(up) > 0) or (isinstance(tp, (int, float)) and float(tp) > 0):
                    has_positive_price = True
                    break
            if not has_positive_price and pricing_matrix:
                continue
            
            # Skip if product name is too long (likely a paragraph or sentence)
            if len(product_name) > 100:
                print(f"[Price Agent] Filtered out long text as product: {product_name[:80]}...", file=sys.stderr, flush=True)
                continue
            
            # Skip if product name contains multiple periods (likely a sentence/paragraph)
            if product_name.count('.') >= 2:
                print(f"[Price Agent] Filtered out sentence as product: {product_name[:80]}...", file=sys.stderr, flush=True)
                continue
            
            # Skip if product name looks like a phone number or email
            if re.search(r'[0-9]{3}[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}|@|XXX-XXXX', product_name, re.IGNORECASE):
                print(f"[Price Agent] Filtered out phone/email as product: {product_name[:50]}", file=sys.stderr, flush=True)
                continue
            
            # Skip if product name starts with common sentence starters (conversational, not product names)
            sentence_starters = ['so', 'hi', 'hello', 'we', 'i', 'let', 'best', 'thanks', 'thank', 'following', 'here', 'this', 'that', 'the', 'a', 'an', 'if', 'when', 'where', 'what', 'who', 'why', 'how', 'can', 'could', 'would', 'should', 'may', 'might', 'must', 'good', 'on', 're']
            first_word = product_name.split()[0].lower() if product_name.split() else ''
            if first_word in sentence_starters:
                print(f"[Price Agent] Filtered out sentence starter as product: {product_name[:50]}", file=sys.stderr, flush=True)
                continue
            
            # Skip if product name contains too many common words (likely a sentence)
            common_words = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'what', 'which', 'who', 'whom', 'whose', 'where', 'when', 'why', 'how', 'all', 'each', 'every', 'some', 'any', 'no', 'not', 'only', 'just', 'also', 'too', 'very', 'much', 'many', 'more', 'most', 'less', 'least', 'other', 'another', 'such', 'same', 'different', 'like', 'about', 'around', 'over', 'under', 'through', 'during', 'before', 'after', 'above', 'below', 'up', 'down', 'out', 'off', 'away', 'back', 'here', 'there', 'where', 'when', 'why', 'how']
            word_count = len([w for w in product_name.lower().split() if w in common_words])
            if word_count > 5:  # Too many common words = likely a sentence
                print(f"[Price Agent] Filtered out sentence (too many common words) as product: {product_name[:80]}...", file=sys.stderr, flush=True)
                continue
            
            # Skip if product name looks like a pricing tier (e.g., "1–3 kg: USD 69,")
            if re.match(r'^\d+[–-]\d+\s*(?:kg|lb|units?|pieces?)\s*:', product_name, re.IGNORECASE):
                print(f"[Price Agent] Filtered out pricing tier as product: {product_name[:50]}", file=sys.stderr, flush=True)
                continue
            
            # Skip if product name looks like delivery time (e.g., "Delivery Time: 10–12 business days")
            if re.match(r'^(?:Delivery|delivery)\s+Time', product_name, re.IGNORECASE):
                print(f"[Price Agent] Filtered out delivery info as product: {product_name[:50]}", file=sys.stderr, flush=True)
                continue
            
            # Skip if product name looks like certification info
            if re.match(r'^(?:Certification|certification|Cert|cert)', product_name, re.IGNORECASE):
                print(f"[Price Agent] Filtered out certification info as product: {product_name[:50]}", file=sys.stderr, flush=True)
                continue
            
            # Skip if product name is just a price range or partial price
            if re.match(r'^USD\s*\d+[,\s]*$', product_name, re.IGNORECASE):
                print(f"[Price Agent] Filtered out partial price as product: {product_name[:50]}", file=sys.stderr, flush=True)
                continue
            
            # Skip if product name is too short or looks incomplete (e.g., "K (%) Minted Gold Bar")
            if len(product_name) < 5 or product_name.startswith('K (%)') or product_name.startswith('(%)'):
                print(f"[Price Agent] Filtered out incomplete product name: {product_name[:50]}", file=sys.stderr, flush=True)
                continue
            
            # Skip if product name contains incomplete calculation (e.g., "Gold Eagles: x =")
            if re.search(r':\s*x\s*=\s*$', product_name, re.IGNORECASE):
                print(f"[Price Agent] Filtered out incomplete calculation as product: {product_name[:50]}", file=sys.stderr, flush=True)
                continue
            
            # Skip if product name contains "are at" or "is at" (likely part of a sentence)
            if re.search(r'\b(are|is)\s+at\s+', product_name, re.IGNORECASE):
                print(f"[Price Agent] Filtered out sentence fragment as product: {product_name[:50]}", file=sys.stderr, flush=True)
                continue
            
            # Skip if product name ends with incomplete price (e.g., "approx $2,")
            if re.search(r'approx\s+\$?\d+[,.]?\s*$', product_name, re.IGNORECASE):
                print(f"[Price Agent] Filtered out incomplete price as product: {product_name[:50]}", file=sys.stderr, flush=True)
                continue
            
            # Skip if product name contains "give or take" or similar phrases
            if re.search(r'give\s+or\s+take|roughly|approximately|around|about', product_name, re.IGNORECASE):
                if len(product_name) > 30:  # Only filter if it's long (likely a sentence)
                    print(f"[Price Agent] Filtered out sentence with approximation phrase as product: {product_name[:50]}", file=sys.stderr, flush=True)
                    continue
            
            valid_products.append(product)
        
        return valid_products
    
    def _validate_and_split_products(self, products: List[Dict[str, Any]], text: str, currency: str) -> List[Dict[str, Any]]:
        """Validate products and split any that are incorrectly combined"""
        import re
        import sys
        
        if not products:
            return products
        
        # Check if text mentions a specific number of products
        product_count_match = re.search(r'(\d+)\s*(?:different\s*)?products?', text.lower())
        expected_count = int(product_count_match.group(1)) if product_count_match else None
        
        split_products = []
        
        for product in products:
            product_name = product.get('name', '')
            
            # ALWAYS check if this product name contains multiple products
            # Signs: contains "including", has multiple commas, mentions "different products", or is very long
            should_split = False
            
            # Check various indicators that this might be a combined product
            if 'including' in product_name.lower():
                should_split = True
            elif product_name.count(',') >= 2:  # Multiple commas suggest list
                should_split = True
            elif len(product_name) > 80:  # Very long name suggests combined
                should_split = True
            elif 'different' in product_name.lower() and 'products' in product_name.lower():
                should_split = True
            elif expected_count and len(products) < expected_count:
                # If we're missing products, be more aggressive
                if product_name.count(',') >= 1:  # Even one comma might indicate list
                    should_split = True
            
            if should_split:
                print(f"[Price Agent] Detected combined product: {product_name[:100]}", file=sys.stderr, flush=True)
                print(f"[Price Agent] Attempting to split...", file=sys.stderr, flush=True)
                
                # First, try to extract from the original text (more reliable)
                # Look for pattern: "including X, Y, Z, and W" or "X, Y, Z, and W"
                text_lower = text.lower()
                product_list_patterns = [
                    r'including\s+([^.]*?)(?:\.|Pricing|pricing|For|Delivery|$)',
                    r'(?:products?|varieties?|types?)[,\s]+(?:including\s+)?([^.]*?)(?:\.|Pricing|pricing|For|Delivery|$)',
                    r':\s*([^.]*?)(?:\.|Pricing|pricing|For|Delivery|$)'
                ]
                
                product_list_text = None
                for pattern in product_list_patterns:
                    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                    if match:
                        product_list_text = match.group(1)
                        break
                
                # If found in text, use that; otherwise use product name
                source_text = product_list_text if product_list_text else product_name
                
                # Extract individual products from comma-separated list
                # Handle "X, Y, Z, and W" pattern
                # First, replace " and " with comma for consistent splitting
                source_text = re.sub(r'\s+and\s+', ', ', source_text, flags=re.IGNORECASE)
                parts = [p.strip() for p in source_text.split(',')]
                
                # Clean up each part
                individual_products = []
                for part in parts:
                    # Remove common prefixes
                    part = re.sub(r'^(including|such as|like|products?|varieties?|types?|offers?)\s+', '', part.strip(), flags=re.IGNORECASE)
                    # Remove company names at the start
                    part = re.sub(r'^[A-Z][a-z]+\s+(?:Precious|Metals|offers?|provides?)\s+', '', part.strip(), flags=re.IGNORECASE)
                    # Remove trailing periods, commas, and common words
                    part = re.sub(r'\s*(?:\.|,|and|or)$', '', part.strip())
                    # Remove leading/trailing whitespace
                    part = part.strip()
                    # Filter out empty or very short parts, and common words
                    if len(part) > 3 and part.lower() not in ['etc', 'etc.', 'the', 'a', 'an', 'different', 'five', '5']:
                        individual_products.append(part)
                
                if len(individual_products) >= 2:
                    print(f"[Price Agent] Split into {len(individual_products)} products: {individual_products}", file=sys.stderr, flush=True)
                    # Create separate product entries
                    pricing_matrix = product.get('pricing_matrix', [])
                    warranty = product.get('warranty', 'Not specified')
                    
                    for idx, prod_name in enumerate(individual_products):
                        split_products.append({
                            "product_id": f"{product.get('product_id', 'PROD')}_{idx + 1}",
                            "name": prod_name.strip(),
                            "description": product.get('description', 'Not specified'),
                            "category": product.get('category', 'Not specified'),
                            "pricing_matrix": pricing_matrix.copy() if pricing_matrix else [],
                            "default_payment_term": product.get('default_payment_term', 'Not specified'),
                            "warranty": warranty,
                            "delivery_time": product.get('delivery_time', 'Not specified')
                        })
                    continue
            
            # If no splitting needed, keep original product
            split_products.append(product)
        
        # If we still don't have the expected count, try smart fallback
        if expected_count and len(split_products) != expected_count:
            print(f"[Price Agent] Still missing products ({len(split_products)} vs {expected_count}), trying smart fallback...", file=sys.stderr, flush=True)
            fallback = self._smart_fallback_extraction(text, currency)
            if fallback and len(fallback) == expected_count:
                return fallback
        
        return split_products
    
    def _smart_fallback_extraction(self, text: str, currency: str) -> List[Dict[str, Any]]:
        """Smart fallback extraction when AI fails - specifically handles product lists"""
        import re
        products = []
        
        text_lower = text.lower()
        
        # Look for product lists: "including X, Y, Z" or "X, Y, Z, and W"
        # Pattern: "including" followed by comma-separated list ending before "Pricing" or "."
        including_match = re.search(r'including\s+([^.]+?)(?:\.|Pricing|pricing)', text, re.IGNORECASE | re.DOTALL)
        if not including_match:
            # Try alternative: look for list after "products"
            including_match = re.search(r'(?:products?|varieties|types)[,\s]+(?:including\s+)?([^.]+?)(?:\.|Pricing|pricing)', text, re.IGNORECASE | re.DOTALL)
        
        if including_match:
            product_list_text = including_match.group(1)
            import sys
            print(f"[Price Agent] Raw product list text: {product_list_text[:200]}", file=sys.stderr, flush=True)
            
            # Clean up the text
            product_list_text = re.sub(r'\s+', ' ', product_list_text).strip()
            
            # Split by comma, handling "and" before last item
            # First replace " and " with comma for consistent splitting
            product_list_text = re.sub(r'\s+and\s+', ', ', product_list_text, flags=re.IGNORECASE)
            parts = [p.strip() for p in product_list_text.split(',')]
            
            # Filter and clean product names
            product_names = []
            for part in parts:
                cleaned = part.strip().rstrip('.')
                # Remove common prefixes/suffixes
                cleaned = re.sub(r'^(including|such as|like)\s+', '', cleaned, flags=re.IGNORECASE).strip()
                # Keep product names that are meaningful
                if len(cleaned) > 3 and cleaned.lower() not in ['etc', 'etc.', 'and', 'or', 'the', 'a', 'an']:
                    product_names.append(cleaned)
            
            print(f"[Price Agent] Extracted product names: {product_names}", file=sys.stderr, flush=True)
            
            if product_names:
                import sys
                print(f"[Price Agent] Found {len(product_names)} products: {product_names}", file=sys.stderr, flush=True)
                
                # Extract quantity tiers: "1–5 kg", "6–20 kg" or "1-5 kg", "6-20 kg"
                qty_tier_pattern = r'(\d+)[–-](\d+)\s*(kg|lb|units?|pieces?)'
                qty_tiers = re.findall(qty_tier_pattern, text, re.IGNORECASE)
                print(f"[Price Agent] Found quantity tiers: {qty_tiers}", file=sys.stderr, flush=True)
                
                # Extract payment terms and their associated prices
                # Pattern: "USD X per kg for [payment term]"
                payment_patterns = [
                    (r'full\s+advance\s+payment', 'Full Advance'),
                    (r'50%\s*advance\s+with\s+balance\s+on\s+delivery', '50% Advance, Balance on Delivery'),
                    (r'50%\s*advance', '50% Advance'),
                    (r'lc\s+at\s+sight', 'LC at Sight'),
                    (r'split\s+payment', 'Split Payment')
                ]
                
                # Extract prices in order they appear, grouped by quantity tier
                # Pattern: Extract all "USD X,XXX per kg" prices
                all_price_matches = re.findall(r'USD\s+(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s+per\s+kg', text, re.IGNORECASE)
                all_prices = [float(p.replace(',', '')) for p in all_price_matches]
                import sys
                print(f"[Price Agent] Found all prices: {all_prices}", file=sys.stderr, flush=True)
                
                price_sections = []
                
                # Based on user's text structure:
                # For 1-5 kg: 3 prices (full advance, 50% advance, LC)
                # For 6-20 kg: 3 prices (full advance, split payment, LC)
                if len(all_prices) >= 6 and len(qty_tiers) >= 2:
                    # First tier (1-5 kg): first 3 prices
                    price_sections.append({
                        'qty_min': int(qty_tiers[0][0]),
                        'qty_max': int(qty_tiers[0][1]),
                        'unit': qty_tiers[0][2].lower(),
                        'prices': all_prices[0:3]
                    })
                    # Second tier (6-20 kg): next 3 prices
                    price_sections.append({
                        'qty_min': int(qty_tiers[1][0]),
                        'qty_max': int(qty_tiers[1][1]),
                        'unit': qty_tiers[1][2].lower(),
                        'prices': all_prices[3:6]
                    })
                elif len(all_prices) >= 3 and len(qty_tiers) >= 1:
                    # If only one tier mentioned, use all prices for that tier
                    prices_per_tier = len(all_prices) // len(qty_tiers) if len(qty_tiers) > 0 else len(all_prices)
                    for idx, (qty_min, qty_max, qty_unit) in enumerate(qty_tiers):
                        start_idx = idx * prices_per_tier
                        tier_prices = all_prices[start_idx:start_idx + prices_per_tier]
                        if tier_prices:
                            price_sections.append({
                                'qty_min': int(qty_min),
                                'qty_max': int(qty_max),
                                'unit': qty_unit.lower(),
                                'prices': tier_prices
                            })
                elif all_prices:
                    # Fallback: use all prices for first tier or create default tier
                    if qty_tiers:
                        price_sections.append({
                            'qty_min': int(qty_tiers[0][0]),
                            'qty_max': int(qty_tiers[0][1]) if len(qty_tiers[0]) > 1 else None,
                            'unit': qty_tiers[0][2].lower() if len(qty_tiers[0]) > 2 else 'kg',
                            'prices': all_prices
                        })
                    else:
                        price_sections.append({
                            'qty_min': 1,
                            'qty_max': None,
                            'unit': 'kg',
                            'prices': all_prices
                        })
                
                # Determine payment terms
                payment_terms = []
                if re.search(r'full\s+advance', text_lower):
                    payment_terms.append("Full Advance")
                if re.search(r'50%\s*advance', text_lower):
                    payment_terms.append("50% Advance, Balance on Delivery")
                if re.search(r'lc\s+at\s+sight', text_lower):
                    payment_terms.append("LC at Sight")
                if not payment_terms:
                    payment_terms = ["Standard"]
                
                import sys
                print(f"[Price Agent] Payment terms: {payment_terms}", file=sys.stderr, flush=True)
                print(f"[Price Agent] Price sections: {price_sections}", file=sys.stderr, flush=True)
                
                # Create products with pricing matrix
                for idx, product_name in enumerate(product_names):
                    pricing_matrix = []
                    
                    # For each quantity tier, create pricing entries for each payment term
                    for price_section in price_sections:
                        for term_idx, payment_term in enumerate(payment_terms):
                            if term_idx < len(price_section['prices']):
                                pricing_matrix.append({
                                    "quantity_min": price_section['qty_min'],
                                    "quantity_max": price_section['qty_max'],
                                    "quantity_unit": price_section['unit'],
                                    "payment_terms": payment_term,
                                    "unit_price": price_section['prices'][term_idx],
                                    "total_price": None,
                                    "currency": currency,
                                    "notes": ""
                                })
                    
                    # If still no pricing matrix, create default
                    if not pricing_matrix:
                        all_prices = [float(p.replace(',', '')) for p in re.findall(r'USD\s+(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', text, re.IGNORECASE)]
                        if all_prices:
                            avg_price = sum(all_prices) / len(all_prices)
                            pricing_matrix.append({
                                "quantity_min": 1,
                                "quantity_max": None,
                                "quantity_unit": "kg",
                                "payment_terms": payment_terms[0] if payment_terms else "Standard",
                                "unit_price": avg_price,
                                "total_price": None,
                                "currency": currency,
                                "notes": "Extracted from quote"
                            })
                    
                    if pricing_matrix:
                        products.append({
                            "product_id": f"product_{idx + 1}",
                            "name": product_name.strip(),
                            "description": "",
                            "pricing_matrix": pricing_matrix
                        })
                    else:
                        import sys
                        print(f"[Price Agent] WARNING: No pricing matrix created for product: {product_name}", file=sys.stderr, flush=True)
                        # Still add product with default pricing
                        all_prices = [float(p.replace(',', '')) for p in re.findall(r'USD\s+(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', text, re.IGNORECASE)]
                        if all_prices:
                            avg_price = sum(all_prices) / len(all_prices)
                            products.append({
                                "product_id": f"product_{idx + 1}",
                                "name": product_name.strip(),
                                "description": "",
                                "pricing_matrix": [{
                                    "quantity_min": 1,
                                    "quantity_max": None,
                                    "quantity_unit": "kg",
                                    "payment_terms": payment_terms[0] if payment_terms else "Standard",
                                    "unit_price": avg_price,
                                    "total_price": None,
                                    "currency": currency,
                                    "notes": "Extracted from quote"
                                }]
                            })
        
        import sys
        print(f"[Price Agent] Smart fallback returning {len(products)} products", file=sys.stderr, flush=True)
        if products:
            print(f"[Price Agent] Products: {[p.get('name') for p in products]}", file=sys.stderr, flush=True)
        return products
    
    def _parse_with_regex(self, text: str, vendor_name: str) -> Dict[str, Any]:
        """Fallback regex-based parsing for when AI is not available"""
        
        items = []
        total_price = 0.0
        currency = "USD"
        
        # Enhanced regex patterns to catch more variations
        # Matches: $130, 130, $130.50, 1,234.56, approx 130, ~130, around $130
        price_pattern = r'(?:approx|approximately|around|~|about)?\s*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
        # Matches: 130/lb, 130 per unit, 130 each, 130 per piece
        per_unit_pattern = r'(\d+(?:\.\d+)?)\s*(?:/|per)\s*(\w+)'
        quantity_pattern = r'(\d+(?:\.\d+)?)\s*(?:x|X|\*|units?|pcs?|pieces?|qty|quantity)'
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for per-unit pricing (e.g., "130/lvbb", "130 per unit")
            per_unit_match = re.search(per_unit_pattern, line, re.IGNORECASE)
            if per_unit_match:
                price_value = float(per_unit_match.group(1))
                unit = per_unit_match.group(2).lower()
                
                # Extract item name (text before the price)
                item_name = re.sub(per_unit_pattern, '', line).strip()
                if not item_name:
                    item_name = f"Item {len(items) + 1}"
                
                items.append({
                    "name": item_name,
                    "price": price_value,
                    "quantity": 1.0,
                    "unit_price": price_value,
                    "unit": unit,
                    "notes": "per unit pricing"
                })
                total_price += price_value
                continue
            
            # Standard price patterns
            prices = re.findall(price_pattern, line, re.IGNORECASE)
            quantities = re.findall(quantity_pattern, line, re.IGNORECASE)
            
            if prices:
                price_value = float(prices[0].replace(',', ''))
                
                # Extract item name
                item_name = re.sub(price_pattern, '', line, flags=re.IGNORECASE).strip()
                item_name = re.sub(quantity_pattern, '', item_name, flags=re.IGNORECASE).strip()
                if not item_name:
                    item_name = f"Item {len(items) + 1}"
                
                quantity = float(quantities[0]) if quantities else 1.0
                
                # Check for approximate indicators
                notes = ""
                if any(word in line.lower() for word in ["approx", "approximately", "around", "~", "about", "varies"]):
                    notes = "approximate pricing"
                
                items.append({
                    "name": item_name,
                    "price": price_value,
                    "quantity": quantity,
                    "unit_price": price_value / quantity if quantity > 0 else price_value,
                    "unit": "unit",
                    "notes": notes
                })
                
                total_price += price_value
        
        # If no items found, try to find total price
        if not items:
            total_match = re.search(r'(?:total|sum|amount|grand\s*total).*?' + price_pattern, text, re.IGNORECASE)
            if total_match:
                total_price = float(total_match.group(1).replace(',', ''))
                items.append({
                    "name": "Total Quote",
                    "price": total_price,
                    "quantity": 1,
                    "unit_price": total_price,
                    "unit": "total"
                })
        
        return {
            "vendor_name": vendor_name,
            "items": items,
            "total_price": total_price,
            "currency": currency,
            "extracted_text": text[:500],
            "item_count": len(items),
            "parsing_method": "regex"
        }
    
    def _extract_json_from_response(self, response_text: str) -> str:
        """Extract JSON from AI response (handles markdown code blocks)"""
        # Try to find JSON in markdown code blocks
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            return response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            return response_text[json_start:json_end].strip()
        else:
            # Try to find JSON object
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                return response_text[json_start:json_end]
        return response_text
    
    def compare_quotes(self, quotes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare multiple vendor quotes"""
        if not quotes:
            return {"error": "No quotes to compare"}
        
        comparison = {
            "vendors": [],
            "cheapest_vendor": None,
            "most_items": None,
            "best_value": None
        }
        
        min_price = float('inf')
        max_items = 0
        
        for quote in quotes:
            vendor_name = quote.get("vendor_name", "Unknown")
            total_price = quote.get("total_price", 0)
            item_count = quote.get("item_count", 0)
            
            comparison["vendors"].append({
                "name": vendor_name,
                "total_price": total_price,
                "item_count": item_count,
                "average_item_price": total_price / item_count if item_count > 0 else 0
            })
            
            if total_price < min_price:
                min_price = total_price
                comparison["cheapest_vendor"] = vendor_name
            
            if item_count > max_items:
                max_items = item_count
                comparison["most_items"] = vendor_name
        
        return comparison

