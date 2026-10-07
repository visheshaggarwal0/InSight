"""sentence_pipeline.py
Sentence-level processing pipeline for InSight ML.

Implements:
  1. Sentence Deconstructor — splits a redacted review into individual
     sentences, preserving character offsets back to the original redacted text.
  2. Provisional Sentence Classifier — assigns each sentence to one of:
       COMPLAINT | RECOMMENDATION | PRAISE/NOISE
     using heuristic rule/regex signals as a provisional baseline.
     This is explicitly NOT the existing review-level sentiment classifier.
  3. Router — partitions sentences into three pools:
       complaint_pool, recommendation_pool, noise_pool
  4. Traceability — every sentence record carries stable IDs, source review ID,
     sentence offsets relative to the redacted review text, and the classification.

IMPORTANT DESIGN NOTES:
  - The existing review-level sentiment model (TF-IDF + LR trained on weak
    rating labels) is a SEPARATE capability and must not be confused with
    sentence intent classification.
  - This classifier is PROVISIONAL. It uses heuristic rules because no
    manually labelled COMPLAINT/RECOMMENDATION/PRAISE/NOISE corpus exists.
  - Outputs are clearly marked provisional.
  - The architecture is designed so a supervised DeBERTa-v3 or MiniLM
    classifier can drop in to replace _classify_sentence() in the future.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sentence & Proposition label constants
# ---------------------------------------------------------------------------

LABEL_COMPLAINT = "COMPLAINT"
LABEL_RECOMMENDATION = "RECOMMENDATION"
LABEL_PRAISE = "PRAISE"
LABEL_NOISE = "NOISE"
LABEL_PRAISE_NOISE = "PRAISE/NOISE"  # Backward-compatibility alias

# Proposition Class Constants (guarantees backward compatibility with sentence_extractor)
CLASS_COMPLAINT = "COMPLAINT"
CLASS_RECOMMENDATION = "RECOMMENDATION"
CLASS_PRAISE_NOISE = "PRAISE_NOISE"

# Operational Severity Constants (P0 to P3)
SEVERITY_P0 = "P0"  # Critical: Physical injury/harm, app crash, financial lockout
SEVERITY_P1 = "P1"  # High: Functional blocker, broken pump/dispenser, module failure
SEVERITY_P2 = "P2"  # Medium: Performance degradation, texture/scent dislike, friction
SEVERITY_P3 = "P3"  # Low: Cosmetic nuance, suggestion, minor preference


# ---------------------------------------------------------------------------
# Heuristic signal patterns  (PROVISIONAL)
# ---------------------------------------------------------------------------

# COMPLAINT signals: defect keywords, discourse markers of contrast, negative
# experience descriptors.  These overlap intentionally with complaint_extraction.py
# but are extended for sentence-level precision.
#
# NOTE on the `yet` branch: the trailing context is a LOOKAHEAD, not part of the
# alternation.  It used to sit inside the group (`yet\b[^,]`), so findall()
# returned the string "yet " with a trailing space, which then failed the
# `pure_markers` membership test and made EVERY sentence containing "yet" a
# COMPLAINT ("I love this cream, yet the pump broke." -> COMPLAINT 0.833).
_COMPLAINT_PATTERN = re.compile(
    r"\b(?:"
    # Discourse markers of contrast / concession
    r"but|however|although|though|except|unfortunately|sadly|regrettably|"
    r"despite|nevertheless|yet(?=\s+[^,.])|"
    # Physical defect / safety
    r"cracked|broke|broken|shattered|leaked|leaking|spilled|exploded|"
    r"jammed|stuck|clogged|blocked|stripped|peeled|"
    # Skin / health reactions
    r"burning|burns|burned|stinging|stings|stung|itching|itchy|"
    r"rash|hives|dermatitis|allergic|allergy|breakout|cystic|"
    r"irritation|irritated|inflamed|redness|swelling|blisters|"
    # Product failure / quality
    r"terrible|horrible|awful|worst|useless|waste|disappointed|"
    r"doesn't work|didn't work|not work|stopped working|"
    r"expired|smells off|changed formula|"
    r"no effect|no results|zero effect|"
    r"(?:will not|won't|would not|wouldn't|never|not)\s+(?:repurchase|buy again)|"
    r"waste of (?:money|time)|not worth (?:the money|it|the price)|regret (?:buying|purchasing)|"
    # App / tech
    r"crash|crashes|crashed|freeze|freezes|frozen|"
    r"failed|fails|failure|glitch|"
    r"limbo|pending|not loading|times out|timed out|timeout|redirect loop|login loop|unresponsive|memory leak|deadlock|"
    # Delivery / service
    r"never arrived|defective"
    r")\b",
    re.IGNORECASE,
)

# Generic service/commerce/tech nouns that indicate a complaint ONLY when the
# surrounding clause is itself complaint-ish.  On their own they are neutral:
# "The return policy on their site is unclear and hard to find." is a usability
# observation, not a product failure, yet it used to score COMPLAINT 0.556.
# These are a SECONDARY TIER: they never trigger COMPLAINT by themselves.
_WEAK_TRIGGER_PATTERN = re.compile(
    r"\b(?:"
    r"return|returns|returned|returning|refund|refunded|replacement|exchange|"
    r"money back|"
    r"fake|fakes|counterfeit|knockoff|"
    r"error|errors|bug|bugs|"
    r"damaged|recalled|recall"
    r")\b",
    re.IGNORECASE,
)

# Context required to promote a weak trigger to a real complaint signal.
_WEAK_TRIGGER_CONTEXT = re.compile(
    r"\b(?:"
    r"can't|cannot|couldn't|could not|won't|will not|still|never|"
    r"waiting|waited|refuse|refused|refusing|denied|deny|"
    r"twice|second time|again|another|every time|constantly|always|"
    r"broken|damaged|defective|cracked|leaked|jammed|"
    r"arrived|arrival|received|delivery|delivered|package|parcel|shipment|box|"
    r"order|ordered|purchase|purchased|bought|"
    r"terrible|horrible|awful|worst|useless|disappointed|angry|furious|"
    r"unusable|immediately"
    r")\b",
    re.IGNORECASE,
)

# RECOMMENDATION signals: linguistic patterns of suggesting, requesting, wishing
_RECOMMENDATION_PATTERN = re.compile(
    r"\b(?:"
    r"would (?:love|like|want|prefer|suggest|recommend)|"
    r"wish (?:it|they|you)|"
    r"hope (?:they|you|it)|"
    r"should (?:add|include|have|make|create|offer|provide)|"
    r"please (?:add|make|consider|include|fix|release|offer)|"
    r"it would be (?:great|nice|better|amazing|helpful|perfect) if|"
    r"(?:add|include|offer|create|release|make)\s+(?:a|an|more|some|the)\s+\w+|"
    r"feature request|improvement|suggestion|could (?:add|include|improve|offer)|"
    r"next version|future (?:update|version|release)|needs? (?:to be|a|an|more)\s+"
    r")\b",
    re.IGNORECASE,
)

# PRAISE signals: positive enthusiasm, efficacy, sensory delight, loyalty
_PRAISE_PATTERN = re.compile(
    r"\b(?:"
    r"love|loved|loving|favorite|favourite|holy grail|best (?:product|cream|serum|moisturizer|cleanser|purchase|ever|app|feature|\w+)|"
    r"life\s*saver|lifesaver|godsend|game\s*changer|miracle\s*(?:worker)?|savior|must\s*have|"
    r"amazing|amazed|incredibly hydrating|so smooth|smooth|soft|glowing|glow|cleared my skin|"
    r"gentle|works wonders|works well|fantastic|blazingly fast|super intuitive|perfect|absorbs (?:instantly|quickly|well)|"
    r"10/10|five stars|5 stars|outstanding|flawless|super soft|worth every penny|worth the hype|highly recommend|definitely recommend|"
    r"excellent|wonderful|superb|brilliant|awesome|obsessed|staple|so good|really good|"
    r"hydrating|hydrates|hydrated|moisturizing|moisturizes|moisture|plump|brightens?|bright|nourish\w*|softens?|"
    r"refreshing|soothing|leaves skin|feels great|feels good|smells amazing|smells great|smells good|"
    r"great|good|pleased|satisfied|enjoy|enjoyed|(?<!not\s)(?<!won't\s)(?<!never\s)(?<!wouldn't\s)\brepurchase|improved|helps? with|visible difference"
    r")\b",
    re.IGNORECASE,
)

# FTC / promotional boilerplate disclosure pattern (routes pure disclaimers to NOISE)
_FTC_DISCLOSURE_PATTERN = re.compile(
    r"\b(?:"
    r"received (?:this )?(?:product )?(?:complimentary|free|as a gift)|"
    r"gifted by|"
    r"in exchange for (?:an? )?honest (?:review|opinion)|"
    r"incentivized review|"
    r"promotional post"
    r")\b",
    re.IGNORECASE,
)

# Antecedent user condition / past product comparison guards
_ANTECEDENT_CONDITION_PATTERN = re.compile(
    r"\b(?:"
    r"(?:when|if|whenever)\s+(?:my|your)?\s*skin\s+(?:has|is|gets|feels|experiences)\s+(?:\w+\s+){0,3}(?:irritat\w*|breakout\w*|acne|red\w*|rash\w*|flak\w*|dry\w*|sensit\w*)|"
    r"(?:as someone with|having|for my|with my)\s+(?:\w+\s+){0,2}(?:acne|sensitive|irritat\w*|dry|oily|redness|rosacea|eczema)|"
    r"(?:easily irritated|acne-prone|sensitive)\s+(?:skin|face)|"
    r"tired of (?:using|other)\s+\w+\s+that\s+\w+|"
    r"unlike (?:other|most)\s+\w+\s+that\s+\w+"
    r")\b",
    re.IGNORECASE,
)

# Therapeutic relief & efficacy praise patterns
_THERAPEUTIC_PRAISE_PATTERN = re.compile(
    r"\b(?:"
    r"life\s*saver|lifesaver|godsend|game\s*changer|holy\s*grail|miracle\s*(?:worker)?|savior|must\s*have|"
    r"(?:great|good|best|amazing|wonderful|excellent|works?\s+wonders?|helps?|clears?|calms?|soothes?|relief|relieves?)\s+(?:for|with|on)\s+(?:my\s+)?(?:acne|breakout\w*|irritat\w*|redness|dryness|rash\w*|blemish\w*|sensitive\s+skin|irritated\s+skin)"
    r")\b",
    re.IGNORECASE,
)

# NEGATION & SYMPTOM MITIGATION guards: e.g. "isn't drying", "never irritated", "no breakouts", "removes redness", "without feeling stripped"
_NEGATION_TOKENS = (
    r"never|didn't|didnt|did not|not|no|wasn't|wasnt|was not|isn't|isnt|is not|"
    r"doesn't|doesnt|does not|don't|dont|do not|won't|wont|will not|wouldn't|wouldnt|would not|"
    r"couldn't|couldnt|could not|haven't|havent|have not|hasn't|hasnt|has not|"
    r"can't|cant|cannot|without|zero|barely|hardly|scarcely"
)
_MITIGATION_TOKENS = (
    r"stop(?:ped|s)?|decrease in|decreased|prevented|prevents|removes?|reduces?|"
    r"soothes?|clears?|cures?|calms?|won't|wont|relieves?"
)
_SYMPTOM_TERMS = (
    r"irritat\w*|burn\w*|breakout\w*|acne|rash\w*|peel\w*|sting\w*|pill\w*|"
    r"problem\w*|issue\w*|defect\w*|clog\w*|leak\w*|dry\w*|crash\w*|shrink\w*|"
    r"strip\w*|redness|tightness|puffiness|wrinkle\w*|greas\w*|stick\w*|residue"
)
_NEGATION_FILTER = re.compile(
    # "<negation> ... <symptom>"  (≤7 tokens apart within clause)
    r"\b(?:" + _NEGATION_TOKENS + r")\b(?:\s+\w+){0,7}\s+(?:" + _SYMPTOM_TERMS + r")"
    r"|"
    # "<symptom> ... <negation>"  (≤7 tokens apart within clause)
    r"\b(?:" + _SYMPTOM_TERMS + r")\b(?:\s+\w+){0,7}\s+(?:" + _NEGATION_TOKENS + r")\b"
    r"|"
    # "<mitigation verb> ... <symptom>"  (≤7 tokens apart within clause)
    r"\b(?:" + _MITIGATION_TOKENS + r")\b(?:\s+\w+){0,7}\s+(?:" + _SYMPTOM_TERMS + r")",
    re.IGNORECASE,
)

# A negation applied to a MITIGATION VERB is a failure of the product, not
# evidence of relief: "did not stop my irritation" means the irritation
# persisted. Checked before _NEGATION_FILTER so such a clause is NOT suppressed.
_FAILED_MITIGATION = re.compile(
    r"\b(?:" + _NEGATION_TOKENS + r")\b(?:\s+\w+){0,2}\s+(?:" + _MITIGATION_TOKENS + r")",
    re.IGNORECASE,
)

# Resolved-service phrases: a service noun ("return", "refund") inside a clause
# that reports the matter as settled is not a complaint. Checked only when a weak
# trigger fires, so it costs nothing on the common path.
_RESOLVED_SERVICE = re.compile(
    r"\b(?:"
    r"works? (?:fine|great|well|perfectly)|"
    r"no (?:issues?|problems?)|"
    r"all (?:good|set|sorted|resolved|fixed)|"
    r"(?:already )?(?:sorted|resolved|fixed|processed|handled|replaced|refunded)|"
    r"happy with"
    r")\b",
    re.IGNORECASE,
)

# Clause boundaries. The negation guard, the praise guard and the complaint
# evidence are all evaluated per clause, so a mitigation statement in one clause
# cannot cancel a defect statement in another.
_CLAUSE_SPLITTER = re.compile(
    r"\s*(?:[,;:.!?]|[—–]|\bbut\b|\bhowever\b|\balthough\b|\bthough\b|\bexcept\b|"
    r"\byet\b|\bwhereas\b|\bwhile\b|\bdespite\b|\bthen\b)\s*",
    re.IGNORECASE,
)

# Contrastive discourse markers that pivot from praise to defect
_CONTRASTIVE_MARKERS = re.compile(
    r"\b(?P<marker>but|however|except\s+that|except|although|though|unfortunately|"
    r"sadly|regrettably|despite|nevertheless|yet|until)\b",
    re.IGNORECASE,
)

# P0 Signals: Severe reactions / App crashes / Financial failure
_P0_SIGNALS = re.compile(
    r"\b(?:"
    r"burning|burns|burned|stinging|stings|stung|itching|itchy|rash|hives|"
    r"dermatitis|allergic|allergy|blisters?|swollen|swelling|chemical\s+burn|"
    r"crash|crashes|crashed|freeze|freezes|frozen|black\s+screen|login\s+loop|"
    r"biometric\s+loop|money\s+stuck|double\s+charged|unauthorized\s+charge|fatal\s+error"
    r")\b",
    re.IGNORECASE,
)

# P1 Signals: Functional blockers / Physical component breakages
_P1_SIGNALS = re.compile(
    r"\b(?:"
    r"cracked|broken|shattered|leaked|leaking|spilled|exploded|jammed|stuck|"
    r"clogged|blocked|stripped|peeled|pump\s+broke|dispenser\s+broke|dropper\s+cracked|"
    r"spray\s+nozzle|seal\s+broken|half\s+empty|"
    r"failed|fails|failure|error|bug|bugs|glitch|limbo|pending|timeout|not\s+loading|"
    r"cannot\s+open|won't\s+open|white\s+screen|data\s+loss|sync\s+failed"
    r")\b",
    re.IGNORECASE,
)

# P2 Signals: Degradation / Disappointment / Sensory friction
_P2_SIGNALS = re.compile(
    r"\b(?:"
    r"terrible|horrible|awful|worst|useless|waste|disappointed|disappointing|"
    r"doesn't\s+work|didn't\s+work|stopped\s+working|smells\s+off|changed\s+formula|"
    r"(?:will not|won't|would not|wouldn't|never|not)\s+(?:repurchase|buy again)|"
    r"not worth (?:the money|it|the price)|waste of (?:money|time)|regret (?:buying|purchasing)|"
    r"greasy|sticky|chalky|dryness|drying|flaking|slow|laggy|sluggish|battery\s+drain|"
    r"overheats|heating\s+up|poor\s+quality"
    r")\b",
    re.IGNORECASE,
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
    re.IGNORECASE,
)

# Sentence splitter — splits on '.', '!', '?' followed by whitespace, unspaced capital letter,
# or hard line breaks, protecting abbreviations (Dr., Mr., Ms., Mrs., vs., e.g., i.e., v1.0, decimals)
_SENT_SPLITTER = re.compile(
    r"""(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<!\bv\d)(?<!\bDr)(?<!\bMr)(?<!\bMs)(?<!\bMrs)(?<!\bvs)(?<!\be\.g)(?<!\bi\.e)(?<!\bNo)(?<=\.|\?|!)(?:\s+|(?=[A-Z]))|[\r\n]+""",
    re.VERBOSE,
)


def evaluate_severity(text: str) -> str:
    """Evaluates operational defect severity tier (P0 > P1 > P2 > P3) with negation guards."""
    clauses = [c for c in _CLAUSE_SPLITTER.split(text) if c and c.strip()]
    has_unmitigated_p0 = False
    has_unmitigated_p1 = False
    has_unmitigated_p2 = False

    for cl in clauses:
        is_mitigated = bool(_NEGATION_FILTER.search(cl) and not _FAILED_MITIGATION.search(cl))
        if _P0_SIGNALS.search(cl):
            if not is_mitigated:
                has_unmitigated_p0 = True
        if _P1_SIGNALS.search(cl):
            if not is_mitigated:
                has_unmitigated_p1 = True
        if _P2_SIGNALS.search(cl):
            if not is_mitigated:
                has_unmitigated_p2 = True

    if has_unmitigated_p0:
        return SEVERITY_P0
    if has_unmitigated_p1:
        return SEVERITY_P1
    if has_unmitigated_p2:
        return SEVERITY_P2
    return SEVERITY_P3


# ---------------------------------------------------------------------------
# Confidence model (HEURISTIC — NOT a calibrated probability)
# ---------------------------------------------------------------------------
# The dashboard surfaces these numbers verbatim as `confidence`, so the field
# name over-promises: nothing here has been fitted, validated against labelled
# data, or compared with a ROC curve. They are monotone evidence-strength
# scores, useful for RANKING, and must not be read as probabilities.
#
# The previous formula was
#     min(1.0, n_matched / max(n_words * 0.15, 1))
# which is inversely proportional to evidence in the regime that matters: a
# 2-word sentence with one defect token scored 1.0 ("It cracked." -> 1.0) while a
# 16-word sentence carrying a real defect scored 0.42. Confidence now saturates
# on the NUMBER OF DISTINCT complaint terms instead, and never reaches 1.0 from
# a single token.
_EVIDENCE_SATURATION_TOKENS = 3      # distinct terms for a strong score
_CONFIDENCE_CEILING = 0.95            # heuristic output never claims certainty
_COMPLAINT_CONFIDENCE_FLOOR = 0.50
_RECOMMENDATION_CONFIDENCE_FLOOR = 0.40
# A sentence with no complaint/praise/recommendation evidence is routed to
# PRAISE/NOISE at a fixed score. This is also the floor for blank input: a blank
# sentence carries no evidence either way, and reporting 0.0 (as the empty-string
# branch used to) ranked it as the WEAKEST signal in the corpus, below the 0.8
# catch-all for text that was at least examined.
_NO_EVIDENCE_CONFIDENCE = 0.80
_MITIGATED_CONFIDENCE = 0.85         # negation/mitigation guard fired
_PRAISE_CONFIDENCE = 0.90

# Contrastive discourse markers carry no defect information on their own.
_PURE_MARKERS = frozenset({
    "but", "however", "although", "though", "except", "until",
    "despite", "nevertheless", "yet", "then", "while", "whereas",
})


def _evidence_confidence(tokens: List[str], floor: float) -> float:
    """Map distinct matched terms to a bounded evidence-strength score.

    Monotonically increasing in the number of DISTINCT matched terms and
    saturating at ``_CONFIDENCE_CEILING``. Sentence length deliberately does not
    appear: dividing by word count is what let a two-word fragment outrank a
    detailed complaint.
    """
    distinct = len({t.lower() for t in tokens if t})
    if distinct <= 0:
        return float(floor)
    # Saturating curve: 1 term -> ~0.49, 2 -> ~0.74, 3 -> ~0.86, 5 -> ~0.96 of
    # the floor..ceiling range.
    ratio = 1.0 - pow(2.718281828, -distinct / 1.5)
    return min(_CONFIDENCE_CEILING, floor + (_CONFIDENCE_CEILING - floor) * ratio)


# Default note for heuristic-classified sentences. Held as a module constant
# rather than read off `SentenceRecord.classifier_note`: that field is a
# dataclass default today, and the day it becomes
# `field(default_factory=...)` the class-attribute read silently returns the
# factory function instead of the note text.
HEURISTIC_CLASSIFIER_NOTE = (
    "PROVISIONAL: heuristic rule-based classification. "
    "No supervised training data available yet. "
    "Replace _classify_sentence() with a DeBERTa-v3 or MiniLM fine-tuned model. "
    "'confidence' is an uncalibrated evidence-strength score, not a probability."
)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class SentenceRecord:
    """A single sentence extracted from a review with full traceability."""

    sentence_id: str          # Stable: "{review_id}::S{n:03d}"
    review_id: str            # Source review ID (e.g. "REV-SEP-00042")
    source_row_index: int     # Original CSV row index for traceability

    # Text
    sentence_text: str        # Sentence text (from redacted review)
    start: int                # Char offset in the redacted review text
    end: int                  # Char offset in the redacted review text

    # Classification (PROVISIONAL)
    label: str                # COMPLAINT | RECOMMENDATION | PRAISE/NOISE
    confidence: float         # Heuristic evidence score in [0.0, 1.0]. NOT a
                               # calibrated probability.
    is_provisional: bool = True
    classifier_note: str = HEURISTIC_CLASSIFIER_NOTE
    operational_severity: str = SEVERITY_P3

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sentence_id": self.sentence_id,
            "review_id": self.review_id,
            "source_row_index": self.source_row_index,
            "sentence_text": self.sentence_text,
            "start": self.start,
            "end": self.end,
            "label": self.label,
            "confidence": self.confidence,
            "is_provisional": self.is_provisional,
            "classifier_note": self.classifier_note,
            "operational_severity": self.operational_severity,
        }


@dataclass
class RoutedPools:
    """Output of the router stage."""
    complaint: List[SentenceRecord] = field(default_factory=list)
    recommendation: List[SentenceRecord] = field(default_factory=list)
    praise: List[SentenceRecord] = field(default_factory=list)
    noise: List[SentenceRecord] = field(default_factory=list)

    @property
    def praise_noise(self) -> List[SentenceRecord]:
        """Backward-compatibility alias."""
        return self.praise + self.noise

    @property
    def total(self) -> int:
        return len(self.complaint) + len(self.recommendation) + len(self.praise) + len(self.noise)

    @property
    def actionable_count(self) -> int:
        """Count of complaints, praise, and recommendations (actionable feedback)."""
        return len(self.complaint) + len(self.recommendation) + len(self.praise)

    @property
    def actionable_rate_pct(self) -> float:
        """Percentage of ingested sentences carrying actionable product signal."""
        return round(100.0 * self.actionable_count / max(self.total, 1), 1)

    def summary(self) -> Dict[str, Any]:
        return {
            "complaint": len(self.complaint),
            "recommendation": len(self.recommendation),
            "praise": len(self.praise),
            "noise": len(self.noise),
            "praise_noise": len(self.praise_noise),
            "total": self.total,
            "actionable_count": self.actionable_count,
            "actionable_rate_pct": self.actionable_rate_pct,
        }


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

    @property
    def severity(self) -> str:
        return self.severity_hint

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity_hint
        return d


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


# ---------------------------------------------------------------------------
# Stage 1: Sentence Deconstructor
# ---------------------------------------------------------------------------

def deconstruct_sentences(
    review_id: str,
    source_row_index: int,
    redacted_text: str,
    min_word_count: int = 3,
) -> List[Tuple[str, int, int]]:
    """Split a redacted review into sentences with character offsets.

    Args:
        review_id: The review's stable ID.
        source_row_index: Original CSV row index for traceability.
        redacted_text: PII-redacted text to split.
        min_word_count: Sentences shorter than this (in words) are merged.

    Returns:
        List of (sentence_text, start_offset, end_offset) tuples where
        offsets are relative to *redacted_text*.
        Invariant: redacted_text[start:end] == sentence_text (for every tuple).
    """
    if not isinstance(redacted_text, str) or not redacted_text.strip():
        return []

    # Find raw boundaries using _SENT_SPLITTER finditer
    raw_spans: List[Tuple[str, int, int]] = []
    last_idx = 0
    for m in _SENT_SPLITTER.finditer(redacted_text):
        chunk = redacted_text[last_idx:m.start()]
        s_chunk = chunk.strip()
        if s_chunk:
            start = last_idx + chunk.find(s_chunk)
            end = start + len(s_chunk)
            raw_spans.append((redacted_text[start:end], start, end))
        last_idx = m.end()

    if last_idx < len(redacted_text):
        chunk = redacted_text[last_idx:]
        s_chunk = chunk.strip()
        if s_chunk:
            start = last_idx + chunk.find(s_chunk)
            end = start + len(s_chunk)
            raw_spans.append((redacted_text[start:end], start, end))

    if not raw_spans:
        s_text = redacted_text.strip()
        start = redacted_text.find(s_text)
        end = start + len(s_text)
        return [(s_text, start, end)]

    # Merge short fragments (< min_word_count words)
    merged_spans: List[Tuple[str, int, int]] = []
    for s_text, start, end in raw_spans:
        words = s_text.split()
        if len(words) < min_word_count and merged_spans:
            # Merge tail fragment into previous sentence
            prev_text, prev_start, _ = merged_spans[-1]
            new_end = end
            merged_spans[-1] = (redacted_text[prev_start:new_end], prev_start, new_end)
        else:
            merged_spans.append((s_text, start, end))

    # If the first sentence ended up < min_word_count and there are subsequent sentences, merge forward
    if len(merged_spans) > 1:
        first_words = merged_spans[0][0].split()
        if len(first_words) < min_word_count:
            first_text, first_start, _ = merged_spans[0]
            next_text, _, next_end = merged_spans[1]
            merged_spans[1] = (redacted_text[first_start:next_end], first_start, next_end)
            merged_spans = merged_spans[1:]

    # Final verification of invariant
    final_sentences: List[Tuple[str, int, int]] = []
    for s_text, start, end in merged_spans:
        if redacted_text[start:end] != s_text:
            logger.error(
                "Offset invariant failed for review %s (source_row_index=%s): "
                "text[%s:%s] != sentence. text_slice=%r, sentence=%r",
                review_id, source_row_index, start, end,
                redacted_text[start:end][:60], s_text[:60],
            )
            continue
        final_sentences.append((s_text, start, end))

    return final_sentences


# ---------------------------------------------------------------------------
# Stage 2: Provisional Sentence Classifier
# ---------------------------------------------------------------------------

def _classify_sentence(sentence_text: str) -> Tuple[str, float]:
    """Assign a sentence to COMPLAINT | RECOMMENDATION | PRAISE/NOISE.

    PROVISIONAL: heuristic rule-based with clause-scoped negation, therapeutic
    guards, and FTC disclosure filtering. Can be upgraded by DeBERTa-v3 model weights.

    Returns:
        (label, confidence) where confidence is an UNCALIBRATED
        evidence-strength score in [0.0, 1.0].
    """
    text = sentence_text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').strip()
    if not text:
        # Blank input carries no evidence in either direction.
        return LABEL_NOISE, _NO_EVIDENCE_CONFIDENCE

    # 1. Recommendation: suggestions, requests, wishes take precedence
    recommendation_matches = _RECOMMENDATION_PATTERN.findall(text)
    if recommendation_matches:
        conf = _evidence_confidence(recommendation_matches, _RECOMMENDATION_CONFIDENCE_FLOOR)
        return LABEL_RECOMMENDATION, round(conf, 3)

    # 2. Promotional / FTC disclaimer without defect: route to NOISE
    if _FTC_DISCLOSURE_PATTERN.search(text) and not _COMPLAINT_PATTERN.search(text):
        return LABEL_NOISE, _NO_EVIDENCE_CONFIDENCE

    # 3. Clause-scoped evidence gathering
    real_complaint_tokens: List[str] = []
    praise_evidence = bool(_PRAISE_PATTERN.search(text) or _THERAPEUTIC_PRAISE_PATTERN.search(text))
    mitigated = False
    clauses = [c for c in _CLAUSE_SPLITTER.split(text) if c and c.strip()]

    for clause in clauses:
        # User condition / profile / past comparison: not a defect about this product
        if _ANTECEDENT_CONDITION_PATTERN.search(clause):
            continue

        if _THERAPEUTIC_PRAISE_PATTERN.search(clause):
            praise_evidence = True
            continue

        if _FAILED_MITIGATION.search(clause):
            mitigated = False
        elif _NEGATION_FILTER.search(clause):
            mitigated = True
            continue  # negated/mitigated clause: its symptoms are not complaints

        tokens = [m.lower() for m in _COMPLAINT_PATTERN.findall(clause)]
        tokens = [m for m in tokens if m not in _PURE_MARKERS]
        if (
            _WEAK_TRIGGER_PATTERN.search(clause)
            and _WEAK_TRIGGER_CONTEXT.search(clause)
            and not _RESOLVED_SERVICE.search(clause)
        ):
            tokens.extend(_WEAK_TRIGGER_PATTERN.findall(clause))
        real_complaint_tokens.extend(tokens)

    # 4. Genuine complaint: at least one real failure verb or defect descriptor
    if real_complaint_tokens:
        # Therapeutic relief override: if reviewer is raving ("life saver", "holy grail")
        # and no catastrophic physical failure occurred, route to PRAISE
        severe_blockers = {"broke", "broken", "shattered", "leaked", "leaking", "exploded", "jammed", "crashed", "terrible", "horrible", "waste"}
        if _THERAPEUTIC_PRAISE_PATTERN.search(text) and not any(k in real_complaint_tokens for k in severe_blockers):
            return LABEL_PRAISE, _PRAISE_CONFIDENCE
        conf = _evidence_confidence(real_complaint_tokens, _COMPLAINT_CONFIDENCE_FLOOR)
        return LABEL_COMPLAINT, round(conf, 3)

    # 5. Praise guard: praise words and no defect evidence at all
    if praise_evidence:
        return LABEL_PRAISE, _PRAISE_CONFIDENCE

    # 6. Every complaint-bearing clause was negated ("no breakouts, no redness")
    if mitigated:
        return LABEL_PRAISE, _MITIGATED_CONFIDENCE

    # 7. Catch-all: no defect, no praise, no negation
    return LABEL_NOISE, _NO_EVIDENCE_CONFIDENCE


# ---------------------------------------------------------------------------
# Stage 2b: DeBERTa Sentence Intent Classifier (Supervised / INT8 quantized)
# ---------------------------------------------------------------------------

class DebertaSentenceClassifier:
    """Fast INT8 CPU / FP32 inference engine for DeBERTa-v3 complaint extraction.
    
    Provides batched inference over customer sentences. Falls back gracefully
    to rule-based classification if model weights are not present.
    """
    _INSTANCE: Optional["DebertaSentenceClassifier"] = None

    @classmethod
    def get_instance(cls, model_dir: Optional[Union[str, Path]] = None) -> Optional["DebertaSentenceClassifier"]:
        if cls._INSTANCE is None:
            inst = cls(model_dir=model_dir)
            if inst.is_available:
                cls._INSTANCE = inst
            else:
                return None
        return cls._INSTANCE

    def __init__(self, model_dir: Optional[Union[str, Path]] = None):
        self.is_available = False
        self.model = None
        self.tokenizer = None
        self.id2label = {
            0: LABEL_COMPLAINT,
            1: LABEL_RECOMMENDATION,
            2: LABEL_PRAISE_NOISE,
            3: LABEL_PRAISE_NOISE,
        }

        # Resolve candidate weight directories
        from app.ml.pipeline_config import ARTIFACTS_ROOT, PROJECT_ROOT
        candidates = [
            Path(model_dir) if model_dir else None,
            ARTIFACTS_ROOT / "deberta_extractor" / "deberta_int8",
            ARTIFACTS_ROOT / "deberta_extractor" / "deberta_fp32",
            ARTIFACTS_ROOT / "deberta_extractor",
        ]
        chosen_dir = None
        for cand in candidates:
            if cand and cand.exists() and (cand / "tokenizer_config.json").exists():
                chosen_dir = cand
                break

        if not chosen_dir:
            return

        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification

            logger.info("Initializing DeBERTa complaint extractor from %s...", chosen_dir)
            self.tokenizer = AutoTokenizer.from_pretrained(str(chosen_dir))

            int8_weights = chosen_dir / "pytorch_model_int8.bin"
            if int8_weights.exists():
                base_model = AutoModelForSequenceClassification.from_pretrained(str(chosen_dir))
                quantized = torch.ao.quantization.quantize_dynamic(
                    base_model.cpu(), {torch.nn.Linear}, dtype=torch.qint8
                )
                quantized.load_state_dict(torch.load(int8_weights, map_location="cpu"))
                quantized.eval()
                self.model = quantized
                logger.info("Loaded INT8 quantized DeBERTa-v3 extractor successfully.")
            else:
                fp32_model = AutoModelForSequenceClassification.from_pretrained(str(chosen_dir))
                fp32_model.eval()
                self.model = fp32_model
                logger.info("Loaded FP32 DeBERTa-v3 extractor successfully.")

            self.is_available = True
        except Exception as e:
            logger.warning("Could not initialize DeBERTa model from %s: %s (falling back to rule-based)", chosen_dir, e)
            self.is_available = False

    def predict_batch(self, texts: List[str], batch_size: int = 128) -> List[Tuple[str, float]]:
        if not self.is_available or not texts:
            return [_classify_sentence(t) for t in texts]

        import torch
        import torch.nn.functional as F

        results: List[Tuple[str, float]] = []
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            enc = self.tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=128,
                return_tensors="pt"
            )
            with torch.no_grad():
                logits = self.model(**enc).logits
                probs = F.softmax(logits, dim=-1)
                confs, preds = torch.max(probs, dim=-1)

            for pred_id, conf in zip(preds.cpu().tolist(), confs.cpu().tolist()):
                label = self.id2label.get(pred_id, LABEL_PRAISE_NOISE)
                results.append((label, round(float(conf), 3)))

        return results


# ---------------------------------------------------------------------------
# Stage 3: Router — build SentenceRecords and partition into pools
# ---------------------------------------------------------------------------

def classify_and_route_review(
    review_id: str,
    source_row_index: int,
    redacted_text: str,
) -> Tuple[List[SentenceRecord], RoutedPools]:
    """Deconstruct, classify, and route sentences from one review.

    Returns:
        (all_sentences, routed_pools)
    """
    raw_sentences = deconstruct_sentences(review_id, source_row_index, redacted_text)

    all_records: List[SentenceRecord] = []
    pools = RoutedPools()

    classifier = DebertaSentenceClassifier.get_instance()
    if classifier and classifier.is_available and raw_sentences:
        texts = [s[0] for s in raw_sentences]
        preds = classifier.predict_batch(texts)
        is_provisional = False
        note = "Fine-tuned DeBERTa-v3 sentence intent model."
    else:
        preds = [_classify_sentence(s[0]) for s in raw_sentences]
        is_provisional = True
        note = SentenceRecord.classifier_note

    for sent_idx, ((sent_text, start, end), (label, confidence)) in enumerate(zip(raw_sentences, preds)):
        rec = SentenceRecord(
            sentence_id=f"{review_id}::S{sent_idx:03d}",
            review_id=review_id,
            source_row_index=source_row_index,
            sentence_text=sent_text,
            start=start,
            end=end,
            label=label,
            confidence=confidence,
            is_provisional=is_provisional,
            classifier_note=note,
            operational_severity=evaluate_severity(sent_text),
        )
        all_records.append(rec)
        if label == LABEL_COMPLAINT:
            pools.complaint.append(rec)
        elif label == LABEL_RECOMMENDATION:
            pools.recommendation.append(rec)
        elif label == LABEL_PRAISE:
            pools.praise.append(rec)
        else:
            pools.noise.append(rec)

    return all_records, pools


def classify_and_route_corpus(
    review_ids: List[str],
    source_row_indices: List[int],
    redacted_texts: List[str],
) -> Tuple[List[SentenceRecord], RoutedPools]:
    """Process all reviews in the corpus through the sentence pipeline.
    
    Uses batched DeBERTa inference when weights are available, otherwise
    falls back to rule-based classification per review.
    """
    if not (len(review_ids) == len(source_row_indices) == len(redacted_texts)):
        raise ValueError("review_ids, source_row_indices, and redacted_texts must have equal length.")

    classifier = DebertaSentenceClassifier.get_instance()
    all_sentences: List[SentenceRecord] = []
    corpus_pools = RoutedPools()

    if classifier and classifier.is_available:
        flattened: List[Tuple[str, int, int, str, int, int]] = []
        for rev_id, src_idx, text in zip(review_ids, source_row_indices, redacted_texts):
            raw_sents = deconstruct_sentences(rev_id, src_idx, text)
            for sent_idx, (sent_text, start, end) in enumerate(raw_sents):
                flattened.append((rev_id, src_idx, sent_idx, sent_text, start, end))

        if flattened:
            all_texts = [f[3] for f in flattened]
            preds = classifier.predict_batch(all_texts, batch_size=128)
            note = "Fine-tuned DeBERTa-v3 sentence intent model."

            for (rev_id, src_idx, sent_idx, sent_text, start, end), (label, confidence) in zip(flattened, preds):
                rec = SentenceRecord(
                    sentence_id=f"{rev_id}::S{sent_idx:03d}",
                    review_id=rev_id,
                    source_row_index=src_idx,
                    sentence_text=sent_text,
                    start=start,
                    end=end,
                    label=label,
                    confidence=confidence,
                    is_provisional=False,
                    classifier_note=note,
                    operational_severity=evaluate_severity(sent_text),
                )
                all_sentences.append(rec)
                if label == LABEL_COMPLAINT:
                    corpus_pools.complaint.append(rec)
                elif label == LABEL_RECOMMENDATION:
                    corpus_pools.recommendation.append(rec)
                elif label == LABEL_PRAISE:
                    corpus_pools.praise.append(rec)
                else:
                    corpus_pools.noise.append(rec)
    else:
        for rev_id, src_idx, text in zip(review_ids, source_row_indices, redacted_texts):
            recs, pools = classify_and_route_review(rev_id, src_idx, text)
            all_sentences.extend(recs)
            corpus_pools.complaint.extend(pools.complaint)
            corpus_pools.recommendation.extend(pools.recommendation)
            corpus_pools.praise.extend(pools.praise)
            corpus_pools.noise.extend(pools.noise)

    logger.info(
        "Sentence pipeline: %d reviews → %d sentences | "
        "COMPLAINT=%d, PRAISE=%d, RECOMMENDATION=%d, NOISE=%d (Actionable=%.1f%%) [%s]",
        len(review_ids),
        len(all_sentences),
        len(corpus_pools.complaint),
        len(corpus_pools.praise),
        len(corpus_pools.recommendation),
        len(corpus_pools.noise),
        corpus_pools.actionable_rate_pct,
        "DeBERTa" if (classifier and classifier.is_available) else "PROVISIONAL rule-based",
    )
    return all_sentences, corpus_pools


class SentenceClauseExtractor:
    """
    Unified surgical sentence and clause deconstructor.
    Parses reviews, isolates defect spans, classifies propositions, and prepares
    isolated text spans for dense vector embeddings.
    """

    @staticmethod
    def _split_into_sentences(text: str, min_word_count: int = 3) -> List[Tuple[str, int, int]]:
        """Splits text into sentences while calculating exact start and end offsets.
        Guarantees: text[start:end] == sent_text.
        Fragments with fewer than min_word_count words are merged into the preceding sentence.
        """
        return deconstruct_sentences("ANON", 0, text, min_word_count=min_word_count)

    @staticmethod
    def _evaluate_severity(text: str) -> str:
        return evaluate_severity(text)

    def _classify_sentence(self, sentence_text: str) -> Tuple[str, str, Optional[str]]:
        severity = evaluate_severity(sentence_text)
        contrast_match = _CONTRASTIVE_MARKERS.search(sentence_text)
        detected_marker = contrast_match.group("marker") if contrast_match else None

        if _RECOMMENDATION_SIGNALS.search(sentence_text) or _RECOMMENDATION_PATTERN.search(sentence_text):
            return CLASS_RECOMMENDATION, severity, detected_marker

        is_mitigated = bool(_NEGATION_FILTER.search(sentence_text) and not _FAILED_MITIGATION.search(sentence_text))
        if (severity in {SEVERITY_P0, SEVERITY_P1, SEVERITY_P2} or contrast_match or _COMPLAINT_PATTERN.search(sentence_text)) and not is_mitigated:
            return CLASS_COMPLAINT, severity, detected_marker

        return CLASS_PRAISE_NOISE, SEVERITY_P3, None

    def extract_complaint_span(self, text: str) -> HighlightSpan:
        """Extracts the bounded defect clause span for UI highlighting.
        Guarantees: text[start:end] == span.text (exact character slice match).
        """
        if not text or not isinstance(text, str) or not text.strip():
            return HighlightSpan(detected=False, text="", start=None, end=None, trigger=None, severity_hint=SEVERITY_P3)

        def _find_bounded_end(start_pos: int) -> Tuple[int, str]:
            sub = text[start_pos:]
            bound_m = re.search(
                r"""(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<!\bv\d)(?<!\bDr)(?<!\bMr)(?<=\.|\?|!)(?:\s+|$)|[\r\n]+""",
                sub,
            )
            if bound_m:
                raw_slice = sub[:bound_m.start()]
            else:
                raw_slice = sub
            trimmed = raw_slice.rstrip()
            end_pos = start_pos + len(trimmed)
            return end_pos, text[start_pos:end_pos]

        # 1. Search for contrastive marker (e.g. "..., but the glass dropper cracked...")
        c_match = _CONTRASTIVE_MARKERS.search(text)
        if c_match:
            start_idx = c_match.start()
            end_idx, span_text = _find_bounded_end(start_idx)
            is_mitigated = bool(_NEGATION_FILTER.search(span_text) and not _FAILED_MITIGATION.search(span_text))
            sev = evaluate_severity(span_text)
            if not is_mitigated or sev in {SEVERITY_P0, SEVERITY_P1}:
                return HighlightSpan(
                    detected=True,
                    text=span_text,
                    start=start_idx,
                    end=end_idx,
                    trigger=f"contrastive:{c_match.group('marker').lower()}",
                    severity_hint=sev,
                )

        # 2. Check direct defect signals (P0, P1, P2)
        for pattern, tier, trigger_name in [
            (_P0_SIGNALS, SEVERITY_P0, "direct_defect:P0"),
            (_P1_SIGNALS, SEVERITY_P1, "direct_defect:P1"),
            (_P2_SIGNALS, SEVERITY_P2, "direct_defect:P2"),
        ]:
            match = pattern.search(text)
            if match:
                start_idx = match.start()
                end_idx, span_text = _find_bounded_end(start_idx)
                clause_start = max(
                    0,
                    text.rfind(".", 0, start_idx),
                    text.rfind("!", 0, start_idx),
                    text.rfind("?", 0, start_idx),
                    text.rfind(",", 0, start_idx),
                    text.rfind(";", 0, start_idx),
                )
                if clause_start > 0:
                    clause_start += 1
                clause_context = text[clause_start:end_idx]
                is_mitigated = bool(
                    (_NEGATION_FILTER.search(clause_context) or _NEGATION_FILTER.search(span_text))
                    and not _FAILED_MITIGATION.search(clause_context)
                )
                if not is_mitigated:
                    return HighlightSpan(
                        detected=True,
                        text=span_text,
                        start=start_idx,
                        end=end_idx,
                        trigger=trigger_name,
                        severity_hint=tier,
                    )

        return HighlightSpan(
            detected=False,
            text="",
            start=None,
            end=None,
            trigger=None,
            severity_hint=SEVERITY_P3,
        )

    def extract_telemetry(self, review_id: str, sanitized_text: str) -> ExtractedReviewTelemetry:
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
                detected_marker=marker,
            )
            propositions.append(prop)

            if classification == CLASS_COMPLAINT:
                complaints.append(prop)
                if severity_rank.get(severity, 1) > severity_rank.get(highest_severity, 1):
                    highest_severity = severity
            elif classification == CLASS_RECOMMENDATION:
                recommendations.append(prop)

        highlight_span = self.extract_complaint_span(sanitized_text)
        if highlight_span.detected:
            hl_sev = highlight_span.severity_hint
            if severity_rank.get(hl_sev, 1) > severity_rank.get(highest_severity, 1):
                highest_severity = hl_sev

        if complaints:
            primary_complaint = " ".join([c.text for c in complaints])
        elif highlight_span.detected:
            primary_complaint = highlight_span.text
        else:
            primary_complaint = sanitized_text

        return ExtractedReviewTelemetry(
            review_id=review_id,
            sanitized_text=sanitized_text,
            propositions=propositions,
            complaint_propositions=complaints,
            recommendation_propositions=recommendations,
            primary_complaint_text=primary_complaint,
            highlight_span=highlight_span,
            overall_severity=highest_severity,
        )


sentence_clause_extractor = SentenceClauseExtractor()


__all__ = [
    "LABEL_COMPLAINT",
    "LABEL_RECOMMENDATION",
    "LABEL_PRAISE",
    "LABEL_NOISE",
    "LABEL_PRAISE_NOISE",
    "CLASS_COMPLAINT",
    "CLASS_RECOMMENDATION",
    "CLASS_PRAISE_NOISE",
    "SEVERITY_P0",
    "SEVERITY_P1",
    "SEVERITY_P2",
    "SEVERITY_P3",
    "SentenceRecord",
    "RoutedPools",
    "SentenceProposition",
    "HighlightSpan",
    "ExtractedReviewTelemetry",
    "DebertaSentenceClassifier",
    "SentenceClauseExtractor",
    "sentence_clause_extractor",
    "deconstruct_sentences",
    "classify_and_route_review",
    "classify_and_route_corpus",
    "evaluate_severity",
]
