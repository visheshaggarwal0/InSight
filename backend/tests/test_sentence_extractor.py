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
    SentenceProposition,
    SentenceRecord,
    RoutedPools,
    CLASS_COMPLAINT,
    CLASS_RECOMMENDATION,
    CLASS_PRAISE,
    CLASS_NOISE,
    CLASS_PRAISE_NOISE,
    INTENT_COMPLAINT,
    INTENT_RECOMMENDATION,
    INTENT_PRAISE,
    INTENT_NOISE,
    ALL_INTENTS,
    ACTIONABLE_INTENTS,
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


def test_unspaced_punctuation_sentence_separation():
    text = "when my skin has irritation this is a life saver.I love this product so much."
    sentences = sentence_clause_extractor._split_into_sentences(text)
    assert len(sentences) == 2
    assert sentences[0][0] == "when my skin has irritation this is a life saver."
    assert sentences[1][0] == "I love this product so much."
    # Enterprise invariant: exact slice match
    for sent_text, start, end in sentences:
        assert text[start:end] == sent_text


def test_negation_mitigation_and_therapeutic_praise_suppresses_false_positives():
    from app.ml.sentence_pipeline import _classify_sentence, LABEL_PRAISE, LABEL_NOISE, LABEL_COMPLAINT

    # 1. Negated symptom with wide token window and apostrophe-less contraction
    lbl, _ = _classify_sentence("it doesnt leave my skin feeling dry or stripped")
    assert lbl in (LABEL_PRAISE, LABEL_NOISE)

    # 2. Therapeutic antecedent with rescue praise
    lbl2, _ = _classify_sentence("when my skin has irritation this is a life saver.")
    assert lbl2 == LABEL_PRAISE

    # 3. FTC disclosure
    lbl3, _ = _classify_sentence("I received this complimentary from Estee Lauder in exchange for my honest opinion.")
    assert lbl3 in (LABEL_NOISE, LABEL_PRAISE)

    # 4. Real physical defect MUST still trigger COMPLAINT
    lbl4, _ = _classify_sentence("I broke out under my skin and it dried my skin out horribly.")
    assert lbl4 == LABEL_COMPLAINT


def test_canonical_proposition_contract_attributes():
    """Verify ONE canonical proposition model carrying all required enterprise attributes."""
    text = (
        "The moisturizer feels wonderful and smells amazing. "
        "However, the pump jammed and cracked on day 2. "
        "Could you please offer a pump replacement kit? "
        "Shipped from warehouse facility."
    )
    telemetry = sentence_clause_extractor.extract_telemetry("REV-PROPO-01", text, domain_id="cosmetics_qa")

    # 1. Total propositions count and list presence
    assert len(telemetry.propositions) == 4
    assert len(telemetry.complaint_propositions) == 1
    assert len(telemetry.recommendation_propositions) == 1
    assert len(telemetry.praise_propositions) == 1
    assert len(telemetry.noise_propositions) == 1

    # 2. Traceability and deterministic proposition IDs
    for idx, prop in enumerate(telemetry.propositions):
        assert prop.proposition_id == f"REV-PROPO-01::P{idx:03d}"
        assert prop.review_id == "REV-PROPO-01"
        assert prop.sentence_idx == idx
        assert prop.domain_id == "cosmetics_qa"
        assert prop.confidence > 0.0
        # Invariant check: exact text slice match
        assert text[prop.char_start:prop.char_end] == prop.text

    # 3. Model conversion methods
    first_prop = telemetry.propositions[0]
    rec = first_prop.to_sentence_record(source_row_index=12)
    assert isinstance(rec, SentenceRecord)
    assert rec.sentence_id == first_prop.proposition_id
    assert rec.source_row_index == 12

    roundtrip_prop = rec.to_proposition(domain_id="cosmetics_qa")
    assert isinstance(roundtrip_prop, SentenceProposition)
    assert roundtrip_prop.proposition_id == first_prop.proposition_id
    assert roundtrip_prop.intent == CLASS_PRAISE

    # 4. Dictionary serialization includes all canonical keys
    d = first_prop.to_dict()
    for key in (
        "proposition_id", "review_id", "sentence_idx", "text",
        "char_start", "char_end", "intent", "classification",
        "severity_hint", "severity", "confidence", "domain_id", "is_actionable"
    ):
        assert key in d, f"Missing key {key} in proposition dict"


def test_4_way_independent_intent_routing():
    """Verify COMPLAINT, RECOMMENDATION, PRAISE, and NOISE are routed independently."""
    text = (
        "I love this rich moisturizer so much! "
        "The pump broke after only three pumps. "
        "Please add a travel-sized bottle option. "
        "Order delivered via standard ground shipping."
    )
    telemetry = sentence_clause_extractor.extract_telemetry("REV-4WAY-01", text)

    # Validate independent proposition pools
    assert len(telemetry.praise_propositions) == 1
    assert telemetry.praise_propositions[0].intent == CLASS_PRAISE
    assert telemetry.praise_propositions[0].is_actionable is True

    assert len(telemetry.complaint_propositions) == 1
    assert telemetry.complaint_propositions[0].intent == CLASS_COMPLAINT
    assert telemetry.complaint_propositions[0].severity_hint == SEVERITY_P1
    assert telemetry.complaint_propositions[0].is_actionable is True

    assert len(telemetry.recommendation_propositions) == 1
    assert telemetry.recommendation_propositions[0].intent == CLASS_RECOMMENDATION
    assert telemetry.recommendation_propositions[0].is_actionable is True

    assert len(telemetry.noise_propositions) == 1
    assert telemetry.noise_propositions[0].intent == CLASS_NOISE
    assert telemetry.noise_propositions[0].is_actionable is False

    # Check telemetry payload dictionary serialization
    telem_dict = telemetry.to_dict()
    assert len(telem_dict["praise_propositions"]) == 1
    assert len(telem_dict["noise_propositions"]) == 1
    assert len(telem_dict["complaint_propositions"]) == 1
    assert len(telem_dict["recommendation_propositions"]) == 1


def test_exact_source_span_traceability_across_all_propositions():
    """Verify character offset invariance: text[start:end] == prop.text across all propositions."""
    text = "Absolutely divine morning serum. The glass dropper cracked on arrival. Would love a pump dispenser instead. Batch shipped in March."
    telemetry = sentence_clause_extractor.extract_telemetry("REV-SPAN-01", text)

    assert len(telemetry.propositions) == 4
    for prop in telemetry.propositions:
        # Crucial guarantee: exact substring slice
        assert text[prop.char_start:prop.char_end] == prop.text


def test_praise_noise_backward_compatibility():
    """Verify _PraiseNoiseCompatibility symmetric equality with legacy CLASS_PRAISE_NOISE."""
    assert CLASS_PRAISE == "PRAISE"
    assert CLASS_PRAISE == CLASS_PRAISE_NOISE
    assert CLASS_PRAISE_NOISE == CLASS_PRAISE

    assert CLASS_NOISE == "NOISE"
    assert CLASS_NOISE == CLASS_PRAISE_NOISE
    assert CLASS_PRAISE_NOISE == CLASS_NOISE

    assert CLASS_PRAISE != CLASS_COMPLAINT
    assert CLASS_COMPLAINT != CLASS_PRAISE
    assert CLASS_PRAISE != CLASS_RECOMMENDATION
    assert CLASS_PRAISE_NOISE != CLASS_COMPLAINT
    assert CLASS_PRAISE_NOISE != CLASS_RECOMMENDATION

    # Test proposition property equality
    prop_praise = SentenceProposition(
        sentence_idx=0,
        text="I love this cream",
        char_start=0,
        char_end=17,
        intent=CLASS_PRAISE,
    )
    # Legacy code testing classification against CLASS_PRAISE_NOISE still passes:
    assert prop_praise.classification == CLASS_PRAISE_NOISE
    assert CLASS_PRAISE_NOISE == prop_praise.classification
    # And modern code testing against CLASS_PRAISE also passes:
    assert prop_praise.intent == CLASS_PRAISE
    assert prop_praise.classification == CLASS_PRAISE

