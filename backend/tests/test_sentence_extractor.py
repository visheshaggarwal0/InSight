"""test_sentence_extractor.py
Comprehensive test suite for SentenceClauseExtractor.

Tests:
  1. Exact character offset guarantee: text[start:end] == span.text
  2. Contrastive discourse parsing ("...but the pump broke and leaked")
  3. Operational severity mapping (P0 harm/crash, P1 blocker, P2 degradation, P3 minor)
  4. Sentence boundary disambiguation (protects Dr., e.g., v2.4.0, decimals)
  5. Recommendation proposition isolation
  6. Mixed-polarity review routing (Praise vs Complaint vs Suggestion)
  7. Pure complaint proposition extraction for vector embeddings
  8. Pure positive review handling (detected == False)
"""

import pytest
from app.data.sentence_extractor import (
    SentenceClauseExtractor,
    sentence_clause_extractor,
    CLASS_COMPLAINT,
    CLASS_RECOMMENDATION,
    CLASS_PRAISE_NOISE,
    SEVERITY_P0,
    SEVERITY_P1,
    SEVERITY_P2,
    SEVERITY_P3,
)


def test_exact_character_offset_guarantee():
    text = "The lavender fragrance is divine, but the glass dropper cracked and shattered during delivery."
    span = sentence_clause_extractor.extract_complaint_span(text)
    assert span.detected is True
    assert span.start is not None
    assert span.end is not None
    # Crucial enterprise guarantee: exact character slice match
    assert text[span.start:span.end] == span.text
    assert span.text.startswith("but the glass dropper cracked")
    assert span.severity_hint == SEVERITY_P1


def test_operational_severity_p0_physical_harm():
    text = "Applied the cream before bed, but woke up with severe chemical burning, hives, and swollen eyelids."
    telemetry = sentence_clause_extractor.extract_telemetry("REV-TEST-01", text)
    assert telemetry.highlight_span.detected is True
    assert telemetry.overall_severity == SEVERITY_P0
    assert telemetry.highlight_span.severity_hint == SEVERITY_P0
    assert text[telemetry.highlight_span.start:telemetry.highlight_span.end] == telemetry.highlight_span.text


def test_operational_severity_p0_app_crash():
    text = "Smooth onboarding flow, however biometric auth crashes the app on startup every time."
    telemetry = sentence_clause_extractor.extract_telemetry("REV-TEST-02", text)
    assert telemetry.highlight_span.detected is True
    assert telemetry.overall_severity == SEVERITY_P0
    assert telemetry.highlight_span.severity_hint == SEVERITY_P0


def test_operational_severity_p1_functional_blocker():
    text = "Scent is subtle and nice, unfortunately the pump dispenser jammed and won't dispense any serum."
    telemetry = sentence_clause_extractor.extract_telemetry("REV-TEST-03", text)
    assert telemetry.highlight_span.detected is True
    assert telemetry.overall_severity == SEVERITY_P1
    assert telemetry.highlight_span.severity_hint == SEVERITY_P1


def test_operational_severity_p2_degradation():
    text = "The new formula feels very greasy and smells off compared to the original batch."
    telemetry = sentence_clause_extractor.extract_telemetry("REV-TEST-04", text)
    assert telemetry.overall_severity == SEVERITY_P2


def test_sentence_boundary_disambiguation_guards_abbreviations():
    text = "Consulted Dr. Smith regarding v2.4.0 update. The transaction fee of $3.50 failed to clear."
    sentences = sentence_clause_extractor._split_into_sentences(text)
    assert len(sentences) == 2
    assert "Dr. Smith" in sentences[0][0]
    assert "v2.4.0" in sentences[0][0]
    assert "$3.50 failed" in sentences[1][0]


def test_recommendation_proposition_isolation():
    text = "The dashboard is informative. It would be great if you could add a dark mode toggle in the settings."
    telemetry = sentence_clause_extractor.extract_telemetry("REV-TEST-05", text)
    assert len(telemetry.recommendation_propositions) == 1
    assert "dark mode" in telemetry.recommendation_propositions[0].text
    assert telemetry.recommendation_propositions[0].classification == CLASS_RECOMMENDATION


def test_mixed_polarity_multi_sentence_routing():
    text = (
        "I absolutely love the packaging and morning scent! "
        "However the bottle leaked all over my suitcase. "
        "Please consider offering a screw-on travel cap."
    )
    telemetry = sentence_clause_extractor.extract_telemetry("REV-TEST-06", text)
    assert len(telemetry.propositions) == 3
    assert telemetry.propositions[0].classification == CLASS_PRAISE_NOISE
    assert telemetry.propositions[1].classification == CLASS_COMPLAINT
    assert telemetry.propositions[2].classification == CLASS_RECOMMENDATION

    # Verify pure complaint extraction for embeddings
    assert "leaked all over my suitcase" in telemetry.primary_complaint_text
    # Surrounding praise should NOT be in the complaint text
    assert "love the packaging" not in telemetry.primary_complaint_text


def test_pure_positive_review():
    text = "Best customer service and fastest shipping I have experienced all year!"
    telemetry = sentence_clause_extractor.extract_telemetry("REV-TEST-07", text)
    assert telemetry.highlight_span.detected is False
    assert telemetry.highlight_span.start is None
    assert telemetry.highlight_span.end is None
    assert telemetry.overall_severity == SEVERITY_P3
    assert len(telemetry.complaint_propositions) == 0
    assert telemetry.primary_complaint_text == text
