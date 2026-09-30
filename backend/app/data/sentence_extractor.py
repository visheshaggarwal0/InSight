"""sentence_extractor.py
Surgical Sentence Deconstructor & Clause-Level Defect Span Extractor for InSight.

Solves the core NLP limitation in customer review clustering:
Reviews with mixed sentiment (e.g. 70% praise + 30% complaint) dilute embedding vectors.
This module deconstructs reviews into atomic propositions, isolates explicit
defect clauses via contrastive discourse markers, assigns operational severity hints (P0–P3),
and guarantees exact character offset provenance for UI span highlighting.

Guarantees:
  1. Bidirectional Provenance: parent_text[start:end] == span_text (100% exact character match).
  2. Sentence Boundary Disambiguation (SBD): Guards abbreviations (Dr., e.g., v1.0, decimals).
  3. Four-Tier Operational Severity Tagging: P0 (Harm/Crash), P1 (Blocker), P2 (Degradation), P3 (Minor).
  4. Sentence Pool Classification: COMPLAINT, RECOMMENDATION, or PRAISE_NOISE.
  5. Isolated Complaint Text: Extracts pure defect clauses for downstream dense vector embeddings.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Proposition Class Constants
# ---------------------------------------------------------------------------
CLASS_COMPLAINT = "COMPLAINT"
CLASS_RECOMMENDATION = "RECOMMENDATION"
CLASS_PRAISE_NOISE = "PRAISE_NOISE"

# ---------------------------------------------------------------------------
# Operational Severity Constants (P0 to P3)
# ---------------------------------------------------------------------------
SEVERITY_P0 = "P0"  # Critical: Physical injury/harm, data loss, crash on start, financial lockout
SEVERITY_P1 = "P1"  # High: Functional blocker, broken pump/dispenser, core module failure
SEVERITY_P2 = "P2"  # Medium: Performance degradation, texture/scent dislike, minor friction
SEVERITY_P3 = "P3"  # Low: Cosmetic nuance, polite suggestion, minor cosmetic preference

# ---------------------------------------------------------------------------
# Linguistic Regular Expressions
# ---------------------------------------------------------------------------

# Contrastive discourse markers that pivot from praise to complaint
_CONTRASTIVE_MARKERS = re.compile(
    r"\b(?P<marker>but|however|except\s+that|except|although|though|unfortunately|"
    r"sadly|regrettably|despite|nevertheless|yet|until)\b",
    re.IGNORECASE
)

# P0 Signals: Severe reactions / App crashes / Financial failure
_P0_SIGNALS = re.compile(
    r"\b(?:"
    # Physical/Clinical Harm
    r"burning|burns|burned|stinging|stings|stung|itching|itchy|rash|hives|"
    r"dermatitis|allergic|allergy|blisters?|swollen|swelling|chemical\s+burn|"
    # Software/Financial Critical Failures
    r"crash|crashes|crashed|freeze|freezes|frozen|black\s+screen|login\s+loop|"
    r"biometric\s+loop|money\s+stuck|double\s+charged|unauthorized\s+charge|fatal\s+error"
    r")\b",
    re.IGNORECASE
)

# P1 Signals: Functional blockers / Physical component breakages
_P1_SIGNALS = re.compile(
    r"\b(?:"
    # Physical Product Blockers
    r"cracked|broken|shattered|leaked|leaking|spilled|exploded|jammed|stuck|"
    r"clogged|blocked|stripped|peeled|pump\s+broke|dispenser\s+broke|dropper\s+cracked|"
    r"spray\s+nozzle|seal\s+broken|half\s+empty|"
    # Software Blockers
    r"failed|fails|failure|error|bug|glitch|limbo|pending|timeout|not\s+loading|"
    r"cannot\s+open|won't\s+open|white\s+screen|data\s+loss|sync\s+failed"
    r")\b",
    re.IGNORECASE
)

# P2 Signals: Degradation / Disappointment / Sensory friction
_P2_SIGNALS = re.compile(
    r"\b(?:"
    r"terrible|horrible|awful|worst|useless|waste|disappointed|disappointing|"
    r"doesn't\s+work|didn't\s+work|stopped\s+working|smells\s+off|changed\s+formula|"
    r"greasy|sticky|chalky|dryness|drying|flaking|slow|laggy|sluggish|battery\s+drain|"
    r"overheats|heating\s+up|poor\s+quality"
    r")\b",
    re.IGNORECASE
)

# Recommendation signals: suggestions & requests
_RECOMMENDATION_SIGNALS = re.compile(
    r"\b(?:"
    r"would\s+(?:love|like|want|prefer|suggest|recommend)|"
    r"wish\s+(?:it|they|you)|"
    r"hope\s+(?:they|you|it)|"
    r"should\s+(?:add|include|have|make|create|offer|provide|fix)|"
    r"please\s+(?:add|make|consider|include|fix|release|offer)|"
    r"it\s+would\s+be\s+(?:great|nice|better|amazing|helpful|perfect)\s+if|"
    r"feature\s+request|suggestion|could\s+(?:add|include|improve|offer)"
    r")\b",
    re.IGNORECASE
)

# Sentence boundary disambiguation regex protecting common abbreviations & decimals
_SENTENCE_BOUNDARY_REGEX = re.compile(
    r"""(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<!\bv\d)(?<!\bDr)(?<!\bMr)(?<!\bMs)(?<!\bNo)(?<=\.|\?|!)\s+""",
    re.VERBOSE
)


@dataclass
class SentenceProposition:
    """An individual atomic sentence proposition extracted from a review."""
    sentence_idx: int
    text: str
    char_start: int
    char_end: int
    classification: str  # COMPLAINT | RECOMMENDATION | PRAISE_NOISE
    severity_hint: str   # P0 | P1 | P2 | P3
    detected_marker: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HighlightSpan:
    """Exact character span of the primary defect clause for UI rendering and Jira tickets."""
    detected: bool
    text: str
    start: Optional[int]
    end: Optional[int]
    trigger: Optional[str]
    severity_hint: str = SEVERITY_P3

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExtractedReviewTelemetry:
    """Complete clause-level extraction payload for a single review."""
    review_id: str
    sanitized_text: str
    propositions: List[SentenceProposition]
    complaint_propositions: List[SentenceProposition]
    recommendation_propositions: List[SentenceProposition]
    primary_complaint_text: str
    highlight_span: HighlightSpan
    overall_severity: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["highlight_span"] = self.highlight_span.to_dict()
        d["propositions"] = [p.to_dict() for p in self.propositions]
        d["complaint_propositions"] = [p.to_dict() for p in self.complaint_propositions]
        d["recommendation_propositions"] = [p.to_dict() for p in self.recommendation_propositions]
        return d


class SentenceClauseExtractor:
    """
    Surgical sentence and clause deconstructor.
    Parses reviews, isolates defect spans, classifies propositions, and prepares
    isolated text spans for dense vector embeddings.
    """

    @staticmethod
    def _split_into_sentences(text: str) -> List[Tuple[str, int, int]]:
        """
        Splits text into sentences while calculating exact start and end offsets.
        Returns list of (sentence_text, start_offset, end_offset).
        """
        if not text:
            return []

        # Find boundaries
        spans: List[Tuple[str, int, int]] = []
        last_end = 0

        for match in _SENTENCE_BOUNDARY_REGEX.finditer(text):
            sent_end = match.start()
            sent_text = text[last_end:sent_end].strip()
            if sent_text:
                # Find exact start of non-whitespace
                actual_start = text.find(sent_text, last_end)
                actual_end = actual_start + len(sent_text)
                spans.append((sent_text, actual_start, actual_end))
            last_end = match.end()

        # Final trailing sentence
        if last_end < len(text):
            sent_text = text[last_end:].strip()
            if sent_text:
                actual_start = text.find(sent_text, last_end)
                actual_end = actual_start + len(sent_text)
                spans.append((sent_text, actual_start, actual_end))

        if not spans and text.strip():
            stripped = text.strip()
            s_idx = text.find(stripped)
            spans.append((stripped, s_idx, s_idx + len(stripped)))

        return spans

    @staticmethod
    def _evaluate_severity(text: str) -> str:
        """Determines operational severity tier (P0 > P1 > P2 > P3)."""
        if _P0_SIGNALS.search(text):
            return SEVERITY_P0
        if _P1_SIGNALS.search(text):
            return SEVERITY_P1
        if _P2_SIGNALS.search(text):
            return SEVERITY_P2
        return SEVERITY_P3

    def _classify_sentence(self, sentence_text: str) -> Tuple[str, str, Optional[str]]:
        """
        Evaluates an individual sentence proposition.
        Returns (classification, severity_hint, detected_marker).
        """
        severity = self._evaluate_severity(sentence_text)
        contrast_match = _CONTRASTIVE_MARKERS.search(sentence_text)
        detected_marker = contrast_match.group("marker") if contrast_match else None

        # Check for explicit recommendation first
        if _RECOMMENDATION_SIGNALS.search(sentence_text):
            return CLASS_RECOMMENDATION, severity, detected_marker

        # Check for defect/complaint
        if severity in {SEVERITY_P0, SEVERITY_P1, SEVERITY_P2} or contrast_match:
            return CLASS_COMPLAINT, severity, detected_marker

        return CLASS_PRAISE_NOISE, SEVERITY_P3, None

    def extract_complaint_span(self, text: str) -> HighlightSpan:
        """
        Extracts the primary defect clause span for UI highlighting.
        Guarantees: text[start:end] == span.text.
        """
        if not text or not isinstance(text, str):
            return HighlightSpan(detected=False, text="", start=None, end=None, trigger=None, severity_hint=SEVERITY_P3)

        # 1. Search for contrastive marker (e.g. "..., but the pump broke...")
        c_match = _CONTRASTIVE_MARKERS.search(text)
        if c_match:
            start_idx = c_match.start()
            span_text = text[start_idx:].strip()
            end_idx = start_idx + len(span_text)
            severity = self._evaluate_severity(span_text)
            return HighlightSpan(
                detected=True,
                text=span_text,
                start=start_idx,
                end=end_idx,
                trigger=f"contrastive:{c_match.group('marker').lower()}",
                severity_hint=severity
            )

        # 2. Search for direct P0/P1 defect keyword match
        p0_match = _P0_SIGNALS.search(text)
        if p0_match:
            start_idx = p0_match.start()
            span_text = text[start_idx:].strip()
            end_idx = start_idx + len(span_text)
            return HighlightSpan(
                detected=True,
                text=span_text,
                start=start_idx,
                end=end_idx,
                trigger="direct_defect:P0",
                severity_hint=SEVERITY_P0
            )

        p1_match = _P1_SIGNALS.search(text)
        if p1_match:
            start_idx = p1_match.start()
            span_text = text[start_idx:].strip()
            end_idx = start_idx + len(span_text)
            return HighlightSpan(
                detected=True,
                text=span_text,
                start=start_idx,
                end=end_idx,
                trigger="direct_defect:P1",
                severity_hint=SEVERITY_P1
            )

        p2_match = _P2_SIGNALS.search(text)
        if p2_match:
            start_idx = p2_match.start()
            span_text = text[start_idx:].strip()
            end_idx = start_idx + len(span_text)
            return HighlightSpan(
                detected=True,
                text=span_text,
                start=start_idx,
                end=end_idx,
                trigger="direct_defect:P2",
                severity_hint=SEVERITY_P2
            )

        return HighlightSpan(
            detected=False,
            text="",
            start=None,
            end=None,
            trigger=None,
            severity_hint=SEVERITY_P3
        )

    def extract_telemetry(self, review_id: str, sanitized_text: str) -> ExtractedReviewTelemetry:
        """
        Processes a single review into full clause telemetry.
        """
        raw_sentences = self._split_into_sentences(sanitized_text)
        propositions: List[SentenceProposition] = []
        complaints: List[SentenceProposition] = []
        recommendations: List[SentenceProposition] = []

        highest_severity = SEVERITY_P3
        severity_rank = {SEVERITY_P0: 4, SEVERITY_P1: 3, SEVERITY_P2: 2, SEVERITY_P3: 1}

        for idx, (sent_text, s_start, s_end) in enumerate(raw_sentences):
            classification, severity, marker = self._classify_sentence(sent_text)
            prop = SentenceProposition(
                sentence_idx=idx,
                text=sent_text,
                char_start=s_start,
                char_end=s_end,
                classification=classification,
                severity_hint=severity,
                detected_marker=marker
            )
            propositions.append(prop)

            if classification == CLASS_COMPLAINT:
                complaints.append(prop)
                if severity_rank.get(severity, 1) > severity_rank.get(highest_severity, 1):
                    highest_severity = severity
            elif classification == CLASS_RECOMMENDATION:
                recommendations.append(prop)

        # Highlight span for drawer UI
        highlight_span = self.extract_complaint_span(sanitized_text)

        # Determine primary complaint text for dense vector embeddings
        if complaints:
            # Concatenate pure complaint propositions
            primary_complaint = " ".join([c.text for c in complaints])
        elif highlight_span.detected:
            primary_complaint = highlight_span.text
        else:
            # If no explicit complaint, pass full text
            primary_complaint = sanitized_text

        return ExtractedReviewTelemetry(
            review_id=review_id,
            sanitized_text=sanitized_text,
            propositions=propositions,
            complaint_propositions=complaints,
            recommendation_propositions=recommendations,
            primary_complaint_text=primary_complaint,
            highlight_span=highlight_span,
            overall_severity=highest_severity
        )


# Singleton extractor instance
sentence_clause_extractor = SentenceClauseExtractor()

__all__ = [
    "SentenceClauseExtractor",
    "SentenceProposition",
    "HighlightSpan",
    "ExtractedReviewTelemetry",
    "sentence_clause_extractor",
    "CLASS_COMPLAINT",
    "CLASS_RECOMMENDATION",
    "CLASS_PRAISE_NOISE",
    "SEVERITY_P0",
    "SEVERITY_P1",
    "SEVERITY_P2",
    "SEVERITY_P3",
]
