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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sentence label constants
# ---------------------------------------------------------------------------

LABEL_COMPLAINT = "COMPLAINT"
LABEL_RECOMMENDATION = "RECOMMENDATION"
LABEL_PRAISE = "PRAISE"
LABEL_NOISE = "NOISE"
LABEL_PRAISE_NOISE = "PRAISE/NOISE"  # Backward-compatibility alias


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
    r"love|favorite|favourite|holy grail|best (?:product|cream|serum|moisturizer|cleanser|purchase|ever|app|feature|\w+)|"
    r"amazing|amazed|incredibly hydrating|so smooth|smooth|soft|glowing|glow|cleared my skin|"
    r"gentle|works wonders|fantastic|blazingly fast|super intuitive|perfect|absorbs (?:instantly|quickly|well)|"
    r"10/10|five stars|5 stars|outstanding|flawless|super soft|worth every penny|highly recommend|"
    r"excellent|wonderful|superb|brilliant|awesome|obsessed|staple|so good|really good|game changer|"
    r"hydrating|refreshing|soothing|leaves skin|feels great|smells amazing|smells great"
    r")\b",
    re.IGNORECASE,
)

# NEGATION & SYMPTOM MITIGATION guards: e.g. "isn't drying", "never irritated", "no breakouts", "removes redness", "without feeling stripped"
#
# The previous version allowed a 9-token look-ahead between the negation and the
# symptom, so ANY negation anywhere in a sentence suppressed the WHOLE sentence.
# Three unambiguous complaints were routed to PRAISE/NOISE and dropped from the
# complaint pool that drives the entire complaint dashboard:
#     "I have no breakouts but my skin is raw and burning badly."
#     "No redness at all, but the pump is jammed solid."
#     "Not worth it, the serum did not stop my irritation."
#
# Two changes fix this:
#   1. The window is 2 tokens, so the negation must actually MODIFY the symptom
#      rather than merely sharing a sentence with it.
#   2. The guard is evaluated PER CLAUSE (see _CLAUSE_SPLITTER) rather than per
#      sentence, so a negated first clause no longer cancels the defect stated in
#      the clause after "but".
# Trade-off: a genuinely negated clause whose symptom sits further than 2 tokens
# away ("I did not, after two weeks, see any reduction in redness") can still
# leak into the complaint pool. The 2-token window plus clause scoping is the
# compromise that keeps precision on "no breakouts" without eating real
# complaints; widening the window again reintroduces the bug above.
_NEGATION_TOKENS = (
    r"never|didn't|did not|not|no|wasn't|was not|isn't|is not|doesn't|does not|"
    r"without|zero|barely|hardly|scarcely"
)
_MITIGATION_TOKENS = (
    r"stop(?:ped|s)?|decrease in|decreased|prevented|prevents|removes?|reduces?|"
    r"soothes?|clears?|cures?|calms?|won't|wont|relieves?"
)
_SYMPTOM_TERMS = (
    r"irritat\w*|burn\w*|breakout\w*|acne|rash\w*|peel\w*|sting\w*|pill\w*|"
    r"problem\w*|issue\w*|defect\w*|clog\w*|leak\w*|dry\w*|crash\w*|shrink\w*|"
    r"strip\w*|redness|tightness|puffiness|wrinkle\w*"
)
_NEGATION_FILTER = re.compile(
    # "<negation> ... <symptom>"  (≤2 tokens apart)
    r"\b(?:" + _NEGATION_TOKENS + r")\b(?:\s+\w+){0,2}\s+(?:" + _SYMPTOM_TERMS + r")"
    r"|"
    # "<symptom> ... <negation>"  (≤2 tokens apart)
    r"\b(?:" + _SYMPTOM_TERMS + r")\b(?:\s+\w+){0,2}\s+(?:" + _NEGATION_TOKENS + r")\b"
    r"|"
    # "<mitigation verb> ... <symptom>"  (≤2 tokens apart)
    r"\b(?:" + _MITIGATION_TOKENS + r")\b(?:\s+\w+){0,2}\s+(?:" + _SYMPTOM_TERMS + r")",
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

# Sentence splitter — splits on '.', '!', '?' followed by whitespace or end-of-string,
# but not on common abbreviations like 'vs.', 'etc.', 'Mr.', decimal numbers.
_SENT_SPLITTER = re.compile(
    r"""(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|!)\s+""",
    re.VERBOSE,
)


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
        min_word_count: Sentences shorter than this (in words) are skipped.

    Returns:
        List of (sentence_text, start_offset, end_offset) tuples where
        offsets are relative to *redacted_text*.
        Invariant: redacted_text[start:end] == sentence_text  (for every tuple).
    """
    if not isinstance(redacted_text, str) or not redacted_text.strip():
        return []

    # Use regex splitter; fall back to simple newline split if needed
    raw_parts = _SENT_SPLITTER.split(redacted_text.strip())
    if not raw_parts:
        raw_parts = [redacted_text.strip()]

    sentences: List[Tuple[str, int, int]] = []
    search_start = 0

    for part in raw_parts:
        part_stripped = part.strip()
        if not part_stripped:
            continue
        if len(part_stripped.split()) < min_word_count:
            # Advance search cursor past this short fragment
            idx = redacted_text.find(part_stripped, search_start)
            if idx != -1:
                search_start = idx + len(part_stripped)
            continue

        # Find position of this sentence in the original redacted text
        idx = redacted_text.find(part_stripped, search_start)
        if idx == -1:
            # Fallback: linear scan with tolerance for whitespace trimming
            idx = redacted_text.find(part, search_start)
            if idx == -1:
                continue
            part_stripped = part  # use original spacing

        start = idx
        end = start + len(part_stripped)

        # Invariant check. This is a DATA invariant, not a code invariant, so it
        # must not be an `assert`: asserts are stripped under `python -O`
        # (routine in containers) and, when present, one pathological review
        # aborted the entire 10,000-row run with AssertionError. Log and skip
        # the fragment so a single bad row cannot kill the pipeline.
        if redacted_text[start:end] != part_stripped:
            logger.error(
                "Offset invariant failed for review %s (source_row_index=%s): "
                "text[%s:%s] != sentence. text_slice=%r, sentence=%r — fragment skipped.",
                review_id, source_row_index, start, end,
                redacted_text[start:end][:60], part_stripped[:60],
            )
            search_start = max(end, idx + 1)
            continue

        sentences.append((part_stripped, start, end))
        search_start = end

    return sentences


# ---------------------------------------------------------------------------
# Stage 2: Provisional Sentence Classifier
# ---------------------------------------------------------------------------

def _classify_sentence(sentence_text: str) -> Tuple[str, float]:
    """Assign a sentence to COMPLAINT | RECOMMENDATION | PRAISE/NOISE.

    PROVISIONAL: heuristic rule-based with clause-scoped negation and praise
    guards. Can be upgraded by DeBERTa-v3 model weights.

    Returns:
        (label, confidence) where confidence is an UNCALIBRATED
        evidence-strength score in [0.0, 1.0] - see the confidence-model notes
        above. It is monotonic in the amount of evidence and is intended for
        ranking, not for interpretation as a probability.
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

    # 2. Clause-scoped evidence gathering.
    #    The negation guard, the praise guard and the complaint evidence are all
    #    evaluated per clause, so "No redness at all, but the pump is jammed
    #    solid." keeps its complaint clause while the negated clause is dropped.
    real_complaint_tokens: List[str] = []
    praise_evidence = False
    mitigated = False
    clauses = [c for c in _CLAUSE_SPLITTER.split(text) if c and c.strip()]

    for clause in clauses:
        if _PRAISE_PATTERN.search(clause):
            praise_evidence = True
        if _FAILED_MITIGATION.search(clause):
            # "did not stop my irritation": the negation attaches to a mitigation
            # verb, so the symptom is still an unresolved complaint.
            mitigated = False
        elif _NEGATION_FILTER.search(clause):
            mitigated = True
            continue  # negated/mitigated clause: its symptoms are not complaints

        tokens = [m.lower() for m in _COMPLAINT_PATTERN.findall(clause)]
        # Filter out pure contrastive discourse markers if no actual defect is stated
        tokens = [m for m in tokens if m not in _PURE_MARKERS]
        if (
            _WEAK_TRIGGER_PATTERN.search(clause)
            and _WEAK_TRIGGER_CONTEXT.search(clause)
            and not _RESOLVED_SERVICE.search(clause)
        ):
            # Secondary tier: a generic commerce/tech noun only counts as
            # evidence when the clause reads as a complaint.
            tokens.extend(_WEAK_TRIGGER_PATTERN.findall(clause))
        real_complaint_tokens.extend(tokens)

    # 3. Genuine complaint: at least one real failure verb or defect descriptor
    #    in a clause that is not negated.
    if real_complaint_tokens:
        conf = _evidence_confidence(real_complaint_tokens, _COMPLAINT_CONFIDENCE_FLOOR)
        return LABEL_COMPLAINT, round(conf, 3)

    # 4. Praise guard: praise words and no defect evidence at all
    if praise_evidence:
        return LABEL_PRAISE, _PRAISE_CONFIDENCE

    # 5. Every complaint-bearing clause was negated ("no breakouts, no redness")
    if mitigated:
        return LABEL_PRAISE, _MITIGATED_CONFIDENCE

    # 6. Catch-all: no defect, no praise, no negation. Pure discourse markers
    #    (but/however) without defects are not complaints; categorized as neutral noise.
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


__all__ = [
    "LABEL_COMPLAINT",
    "LABEL_RECOMMENDATION",
    "LABEL_PRAISE",
    "LABEL_NOISE",
    "LABEL_PRAISE_NOISE",
    "SentenceRecord",
    "RoutedPools",
    "DebertaSentenceClassifier",
    "deconstruct_sentences",
    "classify_and_route_review",
    "classify_and_route_corpus",
]
