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
    r"crash|crashes|crashed|freeze|freezes|frozen|"
    r"failed|fails|failure|error|bug|glitch|"
    r"limbo|pending|stuck|not loading|times out|timed out|timeout|redirect loop|login loop|unresponsive|memory leak|deadlock|"
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

# PRAISE signals: prevent positive enthusiasm with contrastive words from being labeled as complaints
_PRAISE_PATTERN = re.compile(
    r"\b(?:"
    r"love|favorite|holy grail|best product|amazing|amazed|incredibly hydrating|so smooth|"
    r"glowing|cleared my skin|gentle|works wonders|fantastic|blazingly fast|super intuitive|"
    r"10/10|five stars|outstanding|flawless|super soft|worth every penny|highly recommend"
    r")\b",
    re.IGNORECASE,
)

# NEGATION & SYMPTOM MITIGATION guards: e.g. "isn't drying", "never irritated", "no breakouts", "removes redness", "without feeling stripped"
_NEGATION_FILTER = re.compile(
    r"\b(?:"
    r"never|didn't|did not|not|no|wasn't|was not|isn't|is not|doesn't|does not|without|zero|barely|"
    r"stopped|decrease in|decreased|prevented|prevents|removes?|reduces?|soothes?|clears?|cures?|calms?|won't|wont"
    r")\b(?:\s+\w+){0,9}\s+"
    r"(?:irritat\w*|burn\w*|breakout\w*|acne|rash\w*|peel\w*|sting\w*|pill\w*|problem\w*|issue\w*|defect\w*|"
    r"clog\w*|leak\w*|dry\w*|crash\w*|shrink\w*|strip\w*|redness|tightness|puffiness|wrinkle\w*)",
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

    PROVISIONAL: Heuristic rule-based with negation and praise guards.
    Can be seamlessly upgraded by DeBERTa-v3 model weights.

    Returns:
        (label, confidence) where confidence is a proxy score [0.0, 1.0].
    """
    text = sentence_text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').strip()
    if not text:
        return LABEL_PRAISE_NOISE, 0.0

    # 1. Recommendation: suggestions, requests, wishes take precedence
    recommendation_matches = _RECOMMENDATION_PATTERN.findall(text)
    if recommendation_matches:
        n_words = max(len(text.split()), 1)
        conf = min(1.0, len(recommendation_matches) / max(n_words * 0.15, 1))
        return LABEL_RECOMMENDATION, round(conf, 3)

    # 2. Negation / Symptom mitigation guard: e.g. "isn't drying", "never irritated my skin", "no breakouts"
    if _NEGATION_FILTER.search(text):
        return LABEL_PRAISE_NOISE, 0.85

    complaint_matches = _COMPLAINT_PATTERN.findall(text)
    praise_matches = _PRAISE_PATTERN.findall(text)

    # Filter out pure contrastive discourse markers if no actual defect is stated
    pure_markers = {"but", "however", "although", "though", "except", "until", "despite", "nevertheless", "yet"}
    real_complaint_tokens = [m.lower() for m in complaint_matches if m.lower() not in pure_markers]

    # 3. Praise guard: If praise words exist and no real physical defect occurred, route to PRAISE/NOISE
    if praise_matches and not real_complaint_tokens:
        return LABEL_PRAISE_NOISE, 0.90

    # 4. Genuine complaint: requires at least one real failure verb or defect descriptor
    if real_complaint_tokens:
        n_words = max(len(text.split()), 1)
        conf = min(1.0, len(real_complaint_tokens) / max(n_words * 0.15, 1))
        return LABEL_COMPLAINT, max(0.5, round(conf, 3))

    return LABEL_PRAISE_NOISE, 0.8   # Catch-all: pure discourse markers (but/however) without defects are not complaints


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
            PROJECT_ROOT / "InSight_ML" / "outputs" / "deberta_extractor" / "deberta_int8",
            PROJECT_ROOT / "InSight_ML" / "outputs" / "deberta_extractor" / "deberta_fp32",
            PROJECT_ROOT / "InSight_ML" / "outputs" / "deberta_extractor",
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
        else:
            pools.praise_noise.append(rec)

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
                else:
                    corpus_pools.praise_noise.append(rec)
    else:
        for rev_id, src_idx, text in zip(review_ids, source_row_indices, redacted_texts):
            recs, pools = classify_and_route_review(rev_id, src_idx, text)
            all_sentences.extend(recs)
            corpus_pools.complaint.extend(pools.complaint)
            corpus_pools.recommendation.extend(pools.recommendation)
            corpus_pools.praise_noise.extend(pools.praise_noise)

    logger.info(
        "Sentence pipeline: %d reviews → %d sentences | "
        "COMPLAINT=%d, RECOMMENDATION=%d, PRAISE/NOISE=%d [%s]",
        len(review_ids),
        len(all_sentences),
        len(corpus_pools.complaint),
        len(corpus_pools.recommendation),
        len(corpus_pools.praise_noise),
        "DeBERTa" if (classifier and classifier.is_available) else "PROVISIONAL rule-based",
    )
    return all_sentences, corpus_pools


__all__ = [
    "LABEL_COMPLAINT",
    "LABEL_RECOMMENDATION",
    "LABEL_PRAISE_NOISE",
    "SentenceRecord",
    "RoutedPools",
    "DebertaSentenceClassifier",
    "deconstruct_sentences",
    "classify_and_route_review",
    "classify_and_route_corpus",
]
