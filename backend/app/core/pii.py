import hashlib
import hmac
import logging
import os
import re
from typing import Callable, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Entity types in canonical (deterministic) reporting order.
ENTITY_ORDER = (
    "ORDER_ID",
    "PAYMENT_CARD",
    "EMAIL",
    "PHONE",
    "POSTAL_CODE",
    "PERSON_NAME",
)

# Surface words that are frequently capitalised in review prose and are
# therefore *not* evidence of a personal name. Used to suppress false positives
# from the contextual name patterns.
_NON_NAME_TOKENS = frozenset({
    "A", "About", "Abs", "After", "Again", "All", "Almost", "Although", "Also",
    "Always", "Amazing", "An", "And", "Another", "Any", "Anyway", "Are", "As",
    "At", "Ate", "Awesome", "Bad", "Bath", "Because", "Been", "Being", "Bottle",
    "Box", "Brand", "Breakout", "Broken", "Bought", "Brilliant", "But", "Buy",
    "By", "Can", "Cannot", "Cap", "Care", "Cash", "Cream", "Cracked", "Day",
    "Definitely", "Delivery", "Depot", "Disappointed", "Do", "Does", "Doesn",
    "Doing", "Don", "Dosage", "Dry", "During", "Each", "Easy", "Either",
    "Even", "Every", "Excellent", "Except", "Expect", "Experience", "Fairly",
    "Far", "Fast", "Feel", "Feels", "Few", "Finally", "Fine", "Finishes",
    "Formula", "For", "From", "Full", "Gel", "Get", "Getting", "Give", "Glass",
    "Glow", "Go", "Going", "Good", "Got", "Great", "Had", "Hair", "Has", "Have",
    "Having", "He", "Help", "Her", "Here", "Highly", "His", "Holy", "Honestly",
    "How", "However", "I", "If", "In", "Is", "It", "Its", "Just", "Keep",
    "Kept", "Kind", "Landed", "Large", "Last", "Later", "Leaked", "Least",
    "Left", "Less", "Let", "Life", "Like", "Lip", "Little", "Love", "Loved",
    "Low", "Made", "Make", "Many", "Maybe", "Me", "Mild", "Money", "Month",
    "Moisturizer", "Most", "Much", "Must", "My", "Name", "Nearly", "Needed",
    "Never", "Nice", "Night", "Not", "Note", "Now", "Of", "Off", "On", "Once",
    "One", "Only", "Or", "Order", "Other", "Out", "Over", "Package", "Packaging",
    "Pain", "Paste", "Perfect", "Perhaps", "Person", "Please", "Poor", "Price",
    "Product", "Purchase", "Quality", "Quite", "Real", "Really", "Reason",
    "Received", "Refund", "Regret", "Replace", "Return", "Right", "Rinses",
    "Scent", "Score", "Scratch", "Serum", "She", "Should", "Skin", "Smell",
    "So", "Soap", "Some", "Sorry", "Spent", "Spill", "Still", "Strong",
    "Such", "Sure", "Texture", "Than", "Thanks", "That", "The", "Their",
    "Them", "Then", "There", "These", "They", "Thick", "Thin", "This",
    "Those", "Though", "Three", "Through", "Time", "To", "Today", "Too",
    "Twice", "Unfortunately", "Under", "Until", "Up", "Us", "Use", "Used",
    "Using", "Usually", "Very", "Was", "Way", "We", "Wear", "Well", "Were",
    "What", "When", "Where", "Whether", "Which", "While", "Whole", "Why",
    "Will", "With", "Within", "Without", "Work", "Works", "Would", "Wow",
    "Yes", "Yet", "You", "Your",
})

# Explicit name-introducing frames only. Bare "i am", "this is" and "thanks,"
# are deliberately excluded: they match ordinary review prose ("This is great",
# "I am in love") and corrupted 23% of the real corpus.
_NAME_FRAME_PATTERN = re.compile(
    # Case-insensitive frame only; the captured name stays case-sensitive so
    # ordinary capitalised prose is never mistaken for a name.
    r"(?i:my\s+name\s+is|name\s+is|full\s+name|customer\s+name|"
    r"customer|buyer|account\s+holder|signed|regards|sincerely|"
    r"best\s+regards|yours\s+(?:sincerely|truly|faithfully))"
    r"\s*[,:]?\s*"
    r"([A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20})?)"
)


def _luhn_valid(digits: str) -> bool:
    """Standard Luhn (mod-10) checksum over the digits of ``digits``."""
    total = 0
    parity = len(digits) % 2
    for index, char in enumerate(digits):
        value = int(char)
        if index % 2 == parity:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def _sub_spans(text: str, spans: List[Tuple[int, int]], replacement: str) -> str:
    """Replace each ``[start, end)`` span with ``replacement``, right to left."""
    if not spans:
        return text
    pieces = []
    cursor = 0
    for start, end in sorted(set(spans)):
        if start < cursor:
            continue
        pieces.append(text[cursor:start])
        pieces.append(replacement)
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces)


class PIIRedactor:
    """
    Enterprise-grade PII detection and redaction engine.

    Detects and masks customer names, email addresses, phone numbers,
    order/tracking IDs, payment cards (Luhn-validated) and postal codes.

    Design rules:
      * Patterns are digit-anchored with lookarounds so a phone pattern can
        never carve a slice out of a longer numeric run.
      * Card candidates are only redacted when they pass the Luhn checksum, so
        invoice numbers and SKUs survive.
      * Substitutions rewrite only the matched span, never the whole document.
      * ``pii_detected`` is returned in a fixed canonical order so exports are
        byte-reproducible.
    """

    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

    # Loose candidate scan; each hit is validated in _redact_order_ids so that
    # ordinary words starting with a prefix ("refreshed", "positive", "order")
    # are not mistaken for identifiers.
    ORDER_ID_CANDIDATE_PATTERN = re.compile(
        r"(?i:\b#?(?:ORD|ORDER|TRK|TRACK|REF|INVOICE|PO|AWB|RMA)[-_:#]?\s*)"
        r"[A-Z0-9][A-Z0-9\-]{3,18}\b"
        r"|(?<![\w])OD\d{8,16}\b"
    )

    # 13-19 digits, optionally grouped by single spaces or hyphens.
    CARD_CANDIDATE_PATTERN = re.compile(r"(?<![\d])(?:\d[ \-]?){12,18}\d(?![\d])")

    # E.164 with explicit international prefix.
    PHONE_E164_PATTERN = re.compile(r"(?<![\d.])\+\d{9,14}(?![\d.])")

    # NANP-style 10 digit run, must not sit inside a longer digit run.
    PHONE_NANP_PATTERN = re.compile(r"(?<![\d.\-])\(?\d{3}\)?[ \-.]?\d{3}[ \-.]?\d{4}(?![\d.\-])")

    # Context-anchored phone (captures the label, rewrites only the number).
    PHONE_LABELLED_PATTERN = re.compile(
        r"(?i)\b(?:phone|tel|telephone|mobile|cell|contact|whatsapp|call|"
        r"reach\s+me\s+at|reach\s+us\s+at|contact\s+me\s+at|"
        r"call\s+me\s+(?:at|on)|call\s+us\s+(?:at|on)|talk\s+to|"
        r"message\s+me\s+at|text\s+me\s+at|write\s+to|email\s+me\s+at)\b"
        r"\s*(?:(?:number|no\.?|#)?\s*[:#-]?\s*)"
        r"(\+?\d[\d\s\-().]{6,17}\d)"
    )

    # Keyword is MANDATORY. Only the digit group is rewritten.
    PINCODE_PATTERN = re.compile(
        r"(?i)\b(?:pin(?:code)?|zip(?:code)?|postal(?:\s+code)?)\s*[:#-]?\s*(\d{5,6})\b"
    )

    NAME_FRAME_PATTERN = _NAME_FRAME_PATTERN
    NAME_PATTERNS = [_NAME_FRAME_PATTERN]

    def __init__(self, vault_secret: Optional[str] = None):
        """
        ``vault_secret`` enables deterministic HMAC surrogate tags
        (``[REDACTED_EMAIL_e8f2a1]``). When absent, a non-reversible placeholder
        is emitted instead - the redacted text is never reversible either way.
        """
        self._vault_secret = vault_secret or os.getenv("INSIGHT_PII_VAULT_SECRET") or None

    # -- surrogate tagging -------------------------------------------------
    def _surrogate(self, raw: str, prefix: str, redaction: str) -> str:
        """Return a deterministic, non-reversible surrogate tag when a vault key is configured."""
        if not self._vault_secret:
            return redaction
        digest = hmac.new(
            self._vault_secret.encode("utf-8"),
            raw.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"[REDACTED_{prefix}_{digest[:8]}]"

    def _sub_with_surrogate(self, pattern: re.Pattern, text: str, prefix: str, redaction: str) -> Tuple[str, List[Tuple[int, int]]]:
        spans: List[Tuple[int, int]] = []
        out = []
        cursor = 0
        for match in pattern.finditer(text):
            if match.start() < cursor:
                continue
            out.append(text[cursor:match.start()])
            out.append(self._surrogate(match.group(0), prefix, redaction))
            cursor = match.end()
            spans.append((match.start(), match.end()))
        out.append(text[cursor:])
        return "".join(out), spans

    # -- individual passes ------------------------------------------------
    def _redact_order_ids(self, text: str) -> Tuple[str, bool]:
        """
        Redact order/tracking identifiers. A candidate is only accepted when the
        token following the prefix actually contains a digit, which prevents
        "refreshed" / "positive" / "order the larger size" from being masked.
        """
        spans: List[Tuple[int, int]] = []
        for match in self.ORDER_ID_CANDIDATE_PATTERN.finditer(text):
            token = match.group(0)
            # The token minus its alphabetic prefix must contain a digit.
            digits = re.sub(r"(?i)\b#?(?:ORD|ORDER|TRK|TRACK|REF|INVOICE|PO|AWB|RMA)[-_:#]?\s*", "", token)
            digits = re.sub(r"^OD", "", digits, flags=re.IGNORECASE)
            if not any(char.isdigit() for char in digits):
                continue
            spans.append((match.start(), match.end()))
        return _sub_spans(text, spans, "[REDACTED_ORDER_ID]"), bool(spans)

    def _redact_cards(self, text: str) -> Tuple[str, bool]:
        """Redact only Luhn-valid 13/15/16/19-digit candidates."""
        spans: List[Tuple[int, int]] = []
        for match in self.CARD_CANDIDATE_PATTERN.finditer(text):
            digits = re.sub(r"\D", "", match.group(0))
            if len(digits) in (13, 15, 16, 19) and _luhn_valid(digits):
                spans.append((match.start(), match.end()))
        return _sub_spans(text, spans, "[REDACTED_PAYMENT_CARD]"), bool(spans)

    def _redact_phones(self, text: str) -> Tuple[str, bool]:
        spans: List[Tuple[int, int]] = []

        # Labelled numbers first: rewrite only the captured number group.
        for match in self.PHONE_LABELLED_PATTERN.finditer(text):
            spans.append((match.start(1), match.end(1)))

        for pattern in (self.PHONE_E164_PATTERN, self.PHONE_NANP_PATTERN):
            for match in pattern.finditer(text):
                # Skip anything overlapping an already-targeted span.
                if any(match.start() < end and start < match.end() for start, end in spans):
                    continue
                spans.append((match.start(), match.end()))

        return _sub_spans(text, spans, "[REDACTED_PHONE]"), bool(spans)

    def _redact_pincodes(self, text: str) -> str:
        # Rewrite only the digit group so surrounding whitespace/words survive.
        return self.PINCODE_PATTERN.sub(lambda m: m.group(0)[: m.start(1) - m.start(0)] + "[REDACTED_PINCODE]", text)

    def _redact_names(self, text: str) -> Tuple[str, bool]:
        spans: List[Tuple[int, int]] = []
        for match in self.NAME_FRAME_PATTERN.finditer(text):
            candidate = match.group(1)
            tokens = candidate.split()
            if any(token in _NON_NAME_TOKENS for token in tokens):
                continue
            spans.append((match.start(1), match.end(1)))
        return _sub_spans(text, spans, "[REDACTED_NAME]"), bool(spans)

    # -- public API -------------------------------------------------------
    def redact(self, text: str) -> Tuple[str, List[str]]:
        """
        Redacts sensitive PII from raw customer review text.

        Returns:
            (sanitized_text, list_of_detected_entity_types)
        """
        if not text or not isinstance(text, str):
            return text, []

        detected = set()
        sanitized = text

        sanitized, hit = self._redact_order_ids(sanitized)
        if hit:
            detected.add("ORDER_ID")

        sanitized, hit = self._redact_cards(sanitized)
        if hit:
            detected.add("PAYMENT_CARD")

        sanitized, hit = self._redact_phones(sanitized)
        if hit:
            detected.add("PHONE")

        if self.EMAIL_PATTERN.search(sanitized):
            sanitized, _ = self._sub_with_surrogate(self.EMAIL_PATTERN, sanitized, "EMAIL", "[REDACTED_EMAIL]")
            detected.add("EMAIL")

        sanitized = self._redact_pincodes(sanitized)
        if self.PINCODE_PATTERN.search(text):
            detected.add("POSTAL_CODE")

        sanitized, hit = self._redact_names(sanitized)
        if hit:
            detected.add("PERSON_NAME")

        return sanitized, [entity for entity in ENTITY_ORDER if entity in detected]


pii_redactor = PIIRedactor()
