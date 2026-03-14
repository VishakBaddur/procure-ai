"""
Email Integration Agent
Extracts quotes from emails (IMAP/POP3) and processes them automatically
"""
import email
import imaplib
import poplib
from email.header import decode_header
from email.parser import Parser
from typing import Dict, Any, List, Optional
import os
import re
from datetime import datetime
import asyncio


class EmailAgent:
    """Agent for extracting quotes from emails"""
    
    def __init__(self):
        self.imap_server = os.getenv("EMAIL_IMAP_SERVER", "")
        self.imap_port = int(os.getenv("EMAIL_IMAP_PORT", "993"))
        self.pop_server = os.getenv("EMAIL_POP_SERVER", "")
        self.pop_port = int(os.getenv("EMAIL_POP_PORT", "995"))
        self.email_address = os.getenv("EMAIL_ADDRESS", "")
        self.email_password = os.getenv("EMAIL_PASSWORD", "")
        self.email_protocol = os.getenv("EMAIL_PROTOCOL", "imap").lower()  # "imap" or "pop3"
        
        self.use_email = bool(
            self.email_address and 
            self.email_password and 
            (self.imap_server or self.pop_server)
        )
    
    async def fetch_emails(
        self, 
        folder: str = "INBOX",
        limit: int = 10,
        unread_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Fetch emails from mailbox"""
        if not self.use_email:
            return []
        
        if self.email_protocol == "imap":
            return await self._fetch_imap(folder, limit, unread_only)
        else:
            return await self._fetch_pop3(limit, unread_only)
    
    async def _fetch_imap(
        self, 
        folder: str, 
        limit: int, 
        unread_only: bool
    ) -> List[Dict[str, Any]]:
        """Fetch emails using IMAP"""
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.email_password)
            mail.select(folder)
            
            # Search for emails
            if unread_only:
                status, messages = mail.search(None, "UNSEEN")
            else:
                status, messages = mail.search(None, "ALL")
            
            email_ids = messages[0].split()[:limit]
            emails = []
            
            for email_id in email_ids:
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                email_body = msg_data[0][1]
                email_message = email.message_from_bytes(email_body)
                
                parsed_email = self._parse_email(email_message)
                emails.append(parsed_email)
            
            mail.close()
            mail.logout()
            return emails
            
        except Exception as e:
            print(f"IMAP fetch error: {e}")
            return []
    
    async def _fetch_pop3(
        self, 
        limit: int, 
        unread_only: bool
    ) -> List[Dict[str, Any]]:
        """Fetch emails using POP3"""
        try:
            mail = poplib.POP3_SSL(self.pop_server, self.pop_port)
            mail.user(self.email_address)
            mail.pass_(self.email_password)
            
            num_messages = len(mail.list()[1])
            emails = []
            
            # POP3 doesn't have unread flag, so we fetch recent ones
            start_idx = max(1, num_messages - limit + 1)
            
            for i in range(start_idx, num_messages + 1):
                raw_email = b"\n".join(mail.retr(i)[1])
                email_message = email.message_from_bytes(raw_email)
                
                parsed_email = self._parse_email(email_message)
                emails.append(parsed_email)
            
            mail.quit()
            return emails
            
        except Exception as e:
            print(f"POP3 fetch error: {e}")
            return []
    
    def _parse_email(self, email_message) -> Dict[str, Any]:
        """Parse email message into structured format"""
        # Decode subject
        subject, encoding = decode_header(email_message["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding or "utf-8")
        
        # Decode sender
        sender, encoding = decode_header(email_message["From"])[0]
        if isinstance(sender, bytes):
            sender = sender.decode(encoding or "utf-8")
        
        # Extract email address from sender
        sender_email = self._extract_email_address(sender)
        
        # Get date
        date = email_message["Date"]
        
        # Get body
        body = self._get_email_body(email_message)
        
        # Extract attachments
        attachments = self._extract_attachments(email_message)
        
        return {
            "subject": subject or "",
            "sender": sender or "",
            "sender_email": sender_email,
            "date": date or "",
            "body": body,
            "attachments": attachments,
            "raw_message": email_message
        }
    
    def _extract_email_address(self, sender_string: str) -> str:
        """Extract email address from sender string"""
        match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', sender_string)
        return match.group(0) if match else ""
    
    def _get_email_body(self, email_message) -> str:
        """Extract text body from email"""
        body = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                # Skip attachments
                if "attachment" in content_disposition:
                    continue
                
                # Get text content
                if content_type == "text/plain":
                    try:
                        body_bytes = part.get_payload(decode=True)
                        charset = part.get_content_charset() or "utf-8"
                        body = body_bytes.decode(charset, errors="ignore")
                        break
                    except Exception:
                        continue
                elif content_type == "text/html":
                    # Fallback to HTML if no plain text
                    if not body:
                        try:
                            body_bytes = part.get_payload(decode=True)
                            charset = part.get_content_charset() or "utf-8"
                            html_body = body_bytes.decode(charset, errors="ignore")
                            # Simple HTML to text conversion
                            body = re.sub(r'<[^>]+>', '', html_body)
                        except Exception:
                            continue
        else:
            # Single part message
            try:
                body_bytes = email_message.get_payload(decode=True)
                charset = email_message.get_content_charset() or "utf-8"
                body = body_bytes.decode(charset, errors="ignore")
            except Exception:
                body = str(email_message.get_payload())
        
        return body
    
    def _extract_attachments(self, email_message) -> List[Dict[str, Any]]:
        """Extract attachments from email"""
        attachments = []
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_disposition = str(part.get("Content-Disposition"))
                
                if "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        # Decode filename
                        filename, encoding = decode_header(filename)[0]
                        if isinstance(filename, bytes):
                            filename = filename.decode(encoding or "utf-8")
                        
                        attachments.append({
                            "filename": filename,
                            "content_type": part.get_content_type(),
                            "size": len(part.get_payload(decode=True) or b""),
                            "data": part.get_payload(decode=True)
                        })
        
        return attachments
    
    def is_quote_email(self, email_data: Dict[str, Any]) -> bool:
        """Determine if email contains a quote"""
        subject = email_data.get("subject", "").lower()
        body = email_data.get("body", "").lower()
        sender = email_data.get("sender", "").lower()
        
        # Keywords that indicate a quote
        quote_keywords = [
            "quote", "quotation", "pricing", "proposal", "estimate",
            "rfq", "rfp", "bid", "tender", "cost", "price list"
        ]
        
        # Check subject
        if any(keyword in subject for keyword in quote_keywords):
            return True
        
        # Check body (first 500 chars)
        body_preview = body[:500]
        if any(keyword in body_preview for keyword in quote_keywords):
            return True
        
        # Check for price patterns
        price_patterns = [
            r'\$\d+',  # $100
            r'\d+\s*(usd|eur|gbp)',  # 100 USD
            r'price.*\d+',  # price: 100
            r'total.*\d+',  # total: 1000
        ]
        
        for pattern in price_patterns:
            if re.search(pattern, body_preview, re.IGNORECASE):
                return True
        
        return False
    
    def extract_vendor_name(self, email_data: Dict[str, Any]) -> Optional[str]:
        """Extract vendor name from email"""
        sender = email_data.get("sender", "")
        sender_email = email_data.get("sender_email", "")
        subject = email_data.get("subject", "")
        
        # Try to extract from sender name
        if sender and "<" in sender:
            # Format: "Company Name <email@domain.com>"
            name_part = sender.split("<")[0].strip()
            if name_part:
                return name_part
        
        # Try to extract from email domain
        if sender_email:
            domain = sender_email.split("@")[1].split(".")[0]
            # Capitalize first letter
            return domain.capitalize()
        
        # Try to extract from subject
        # Look for patterns like "Quote from Company Name"
        match = re.search(r'(?:from|by)\s+([A-Z][a-zA-Z\s]+)', subject, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        return None
    
    async def process_email_quote(
        self, 
        email_data: Dict[str, Any],
        project_id: str
    ) -> Dict[str, Any]:
        """Process email and extract quote, return vendor_id and quote data"""
        vendor_name = self.extract_vendor_name(email_data)
        if not vendor_name:
            vendor_name = email_data.get("sender_email", "Unknown Vendor")
        
        # Get or create vendor
        from database import add_vendor_to_project, get_vendor_id
        
        vendor_id = get_vendor_id(project_id, vendor_name)
        if not vendor_id:
            vendor_id = add_vendor_to_project(project_id, vendor_name)
        
        # Extract quote text from body
        quote_text = email_data.get("body", "")
        
        # Check attachments for PDFs/Word docs
        attachments = email_data.get("attachments", [])
        attachment_text = ""
        
        for attachment in attachments:
            filename = attachment.get("filename", "").lower()
            if filename.endswith((".pdf", ".doc", ".docx")):
                # Save attachment temporarily and process
                # For now, just note that attachment exists
                attachment_text += f"\n[Attachment: {attachment['filename']}]\n"
        
        # Combine body and attachment info
        full_text = quote_text + attachment_text
        
        return {
            "vendor_id": vendor_id,
            "vendor_name": vendor_name,
            "email_subject": email_data.get("subject", ""),
            "email_sender": email_data.get("sender_email", ""),
            "email_date": email_data.get("date", ""),
            "quote_text": full_text,
            "has_attachments": len(attachments) > 0,
            "attachments": [
                {
                    "filename": att.get("filename", ""),
                    "content_type": att.get("content_type", ""),
                    "size": att.get("size", 0)
                }
                for att in attachments
            ]
        }

