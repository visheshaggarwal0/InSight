import re
from typing import Tuple, List

class PIIRedactor:
    """
    Enterprise-grade PII detection and redaction engine.
    Sanitizes customer names, email addresses, phone numbers,
    order/tracking IDs, credit cards, and addresses.
    """
    
    # Pre-compiled high-performance regular expressions
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    PHONE_PATTERN = re.compile(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
    ORDER_ID_PATTERN = re.compile(r'(?i)\b(#?(?:ORD|ORDER|TRK|TRACK|REF|INVOICE)[-_:]?\s*[A-Z0-9]{5,15}|OD[0-9]{8,16})\b')
    CARD_PATTERN = re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b')
    PINCODE_PATTERN = re.compile(r'(?i)\b(?:pin|pincode|zip|postal)?\s*(?:code\s*)?[:#-]?\s*([0-9]{5,6})\b')
    NAME_PATTERNS = [
        re.compile(r'(?i)\b(?:my name is|i am|this is|regards,?|thanks,?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'),
        re.compile(r'(?i)\b(?:customer|user|account holder)\s*[:#-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b')
    ]

    def redact(self, text: str) -> Tuple[str, List[str]]:
        """
        Redacts sensitive PII from raw customer review text.
        Returns:
            (sanitized_text, list_of_detected_entity_types)
        """
        if not text or not isinstance(text, str):
            return text, []

        detected_entities = []
        sanitized = text

        # 1. Order / Tracking IDs
        if self.ORDER_ID_PATTERN.search(sanitized):
            detected_entities.append("ORDER_ID")
            sanitized = self.ORDER_ID_PATTERN.sub("[REDACTED_ORDER_ID]", sanitized)

        # 2. Credit Cards / Payment patterns
        if self.CARD_PATTERN.search(sanitized):
            detected_entities.append("PAYMENT_CARD")
            sanitized = self.CARD_PATTERN.sub("[REDACTED_PAYMENT_CARD]", sanitized)

        # 3. Email Addresses
        if self.EMAIL_PATTERN.search(sanitized):
            detected_entities.append("EMAIL")
            sanitized = self.EMAIL_PATTERN.sub("[REDACTED_EMAIL]", sanitized)

        # 4. Phone Numbers
        if self.PHONE_PATTERN.search(sanitized):
            detected_entities.append("PHONE")
            sanitized = self.PHONE_PATTERN.sub("[REDACTED_PHONE]", sanitized)

        # 5. Pincodes / Postal
        if self.PINCODE_PATTERN.search(sanitized):
            detected_entities.append("POSTAL_CODE")
            sanitized = self.PINCODE_PATTERN.sub("[REDACTED_PINCODE]", sanitized)

        # 6. Contextual Names
        for pattern in self.NAME_PATTERNS:
            matches = list(pattern.finditer(sanitized))
            if matches:
                detected_entities.append("PERSON_NAME")
                for match in matches:
                    name_span = match.group(1)
                    if name_span:
                        sanitized = sanitized.replace(name_span, "[REDACTED_NAME]")

        return sanitized, list(set(detected_entities))

pii_redactor = PIIRedactor()
