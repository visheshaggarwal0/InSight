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
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sentence label constants
# ---------------------------------------------------------------------------

LABEL_COMPLAINT = "COMPLAINT"
LABEL_RECOMMENDATION = "RECOMMENDATION"
LABEL_PRAISE_NOISE = "PRAISE/NOISE"


# ---------------------------------------------------------------------------
# Heuristic signal patterns  (PROVISIONAL)
# ---------------------------------------------------------------------------

# COMPLAINT signals: defect keywords, discourse markers of contrast, negative
# experience descriptors.  These overlap intentionally with complaint_extraction.py
# but are extended for sentence-level precision.
_COMPLAINT_PATTERN = re.compile(
    r"\b(?:"
    # Discourse markers of contrast / concession
    r"but|however|although|though|except|unfortunately|sadly|regrettably|"
    r"despite|nevertheless|yet\b[^,]|"
    # Physical defect / safety
    r"cracked|broken|shattered|leaked|leaking|spilled|exploded|"
    r"jammed|stuck|clogged|blocked|stripped|peeled|"
    # Skin / health reactions
    r"burning|burns|burned|stinging|stings|stung|itching|itchy|"
    r"rash|hives|dermatitis|allergic|allergy|breakout|cystic|"
    r"irritation|irritated|inflamed|redness|swelling|blisters|"
    # Product failure / quality
    r"terrible|horrible|awful|worst|useless|waste|disappointed|"
    r"doesn't work|didn't work|not work|stopped working|"
    r"fake|counterfeit|expired|smells off|changed formula|"
    r"no effect|no results|zero effect|"
    # App / tech
    r"crash|crashes|crashed|freeze|freezes|frozen|frozen|"
    r"failed|fails|failure|error|bug|glitch|"
    r"limbo|pending|stuck|not loading|"
    # Delivery / service
    r"never arrived|damaged|defective|recalled|refund|return"
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

# Sentence splitter — splits on '.', '!', '?' followed by whitespace or end-of-string,
# but not on common abbreviations like 'vs.', 'etc.', 'Mr.', decimal numbers.
_SENT_SPLITTER = re.compile(
    r"""(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|!)\s+""",
    re.VERBOSE,
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
    confidence: float         # Heuristic confidence proxy [0.0, 1.0]
    is_provisional: bool = True
    classifier_note: str = (
        "PROVISIONAL: heuristic rule-based classification. "
        "No supervised training data available yet. "
        "Replace _classify_sentence() with a DeBERTa-v3 or MiniLM fine-tuned model."
    )

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
    praise_noise: List[SentenceRecord] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.complaint) + len(self.recommendation) + len(self.praise_noise)

    def summary(self) -> Dict[str, int]:
        return {
            "complaint": len(self.complaint),
            "recommendation": len(self.recommendation),
            "praise_noise": len(self.praise_noise),
            "total": self.total,
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

        # Invariant check
        assert redacted_text[start:end] == part_stripped, (
            f"Offset invariant failed for review {review_id}: "
            f"text[{start}:{end}] != sentence. "
            f"text_slice={repr(redacted_text[start:end])[:60]}, "
            f"sentence={repr(part_stripped)[:60]}"
        )

        sentences.append((part_stripped, start, end))
        search_start = end

    return sentences


# ---------------------------------------------------------------------------
# Stage 2: Provisional Sentence Classifier
# ---------------------------------------------------------------------------

def _classify_sentence(sentence_text: str) -> Tuple[str, float]:
    """Assign a sentence to COMPLAINT | RECOMMENDATION | PRAISE/NOISE.

    PROVISIONAL: Heuristic rule-based. Replace with a fine-tuned model.

    Returns:
        (label, confidence) where confidence is a proxy score [0.0, 1.0].
        Confidence is the number of pattern matches normalized by text length —
        it is an ENGINEERING proxy, not a calibrated probability.
    """
    text = sentence_text.strip()
    if not text:
        return LABEL_PRAISE_NOISE, 0.0

    complaint_matches = _COMPLAINT_PATTERN.findall(text)
    recommendation_matches = _RECOMMENDATION_PATTERN.findall(text)

    n_words = max(len(text.split()), 1)

    if complaint_matches and (not recommendation_matches or len(complaint_matches) >= len(recommendation_matches)):
        # Confidence proxy: capped ratio of matching tokens to sentence length
        conf = min(1.0, len(complaint_matches) / max(n_words * 0.15, 1))
        return LABEL_COMPLAINT, round(conf, 3)

    if recommendation_matches:
        conf = min(1.0, len(recommendation_matches) / max(n_words * 0.15, 1))
        return LABEL_RECOMMENDATION, round(conf, 3)

    return LABEL_PRAISE_NOISE, 0.8   # high confidence for the "catch-all" bucket


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

    for sent_idx, (sent_text, start, end) in enumerate(raw_sentences):
        label, confidence = _classify_sentence(sent_text)
        rec = SentenceRecord(
            sentence_id=f"{review_id}::S{sent_idx:03d}",
            review_id=review_id,
            source_row_index=source_row_index,
            sentence_text=sent_text,
            start=start,
            end=end,
            label=label,
            confidence=confidence,
        )
        all_records.append(rec)
        if label == LABEL_COMPLAINT:
            pools.complaint.append(rec)
        elif label == LABEL_RECOMMENDATION:
            pools.recommendation.append(rec)
        else:
            pools.praise_noise.append(rec)

    return all_records, pools


def classify_and_route_corpus(
    review_ids: List[str],
    source_row_indices: List[int],
    redacted_texts: List[str],
) -> Tuple[List[SentenceRecord], RoutedPools]:
    """Process all reviews in the corpus through the sentence pipeline.

    Args:
        review_ids: Stable review IDs.
        source_row_indices: Original CSV row indices.
        redacted_texts: PII-redacted review texts.

    Returns:
        (all_sentence_records, corpus_pools)
    """
    if not (len(review_ids) == len(source_row_indices) == len(redacted_texts)):
        raise ValueError("review_ids, source_row_indices, and redacted_texts must have equal length.")

    all_sentences: List[SentenceRecord] = []
    corpus_pools = RoutedPools()

    for rev_id, src_idx, text in zip(review_ids, source_row_indices, redacted_texts):
        recs, pools = classify_and_route_review(rev_id, src_idx, text)
        all_sentences.extend(recs)
        corpus_pools.complaint.extend(pools.complaint)
        corpus_pools.recommendation.extend(pools.recommendation)
        corpus_pools.praise_noise.extend(pools.praise_noise)

    logger.info(
        "Sentence pipeline: %d reviews → %d sentences | "
        "COMPLAINT=%d, RECOMMENDATION=%d, PRAISE/NOISE=%d [PROVISIONAL]",
        len(review_ids),
        len(all_sentences),
        len(corpus_pools.complaint),
        len(corpus_pools.recommendation),
        len(corpus_pools.praise_noise),
    )
    return all_sentences, corpus_pools


__all__ = [
    "LABEL_COMPLAINT",
    "LABEL_RECOMMENDATION",
    "LABEL_PRAISE_NOISE",
    "SentenceRecord",
    "RoutedPools",
    "deconstruct_sentences",
    "classify_and_route_review",
    "classify_and_route_corpus",
]
