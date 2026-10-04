"""scripts/generate_complaint_dataset.py
Curates a ~2,000-sample sentence intent dataset across 4 classes:
  - COMPLAINT: ~700 samples (largest class)
  - RECOMMENDATION: ~450 samples
  - PRAISE: ~450 samples
  - NEUTRAL_NOISE: ~400 samples

Two sources are combined:
  1. `d2c_cosmetics`  — real sentences harvested from Sephora cosmetics reviews,
     labelled with rating priors (1-2 star → complaint pool, 5 star → praise,
     3-4 star → neutral, keyword scan over all rows → recommendation pool).
  2. `tech_saas`      — SYNTHETIC templated SaaS support statements.

  ############################################################
  THIS DATASET IS SYNTHETIC-PARTIAL AND HEURISTICALLY LABELLED.
  The `tech_saas` half is machine-generated template expansion, not real
  customer text. The `d2c_cosmetics` half is real text but its labels come from
  keyword rules, not human annotation. Metrics trained on it measure agreement
  with those rules and MUST NOT be reported as real-world accuracy.
  ############################################################

Anti-leakage design (this file previously leaked badly):
  - Every sample is generated with a DISTINCT base text. No `[Trace #N]` style
    identifier suffix is appended: such markers were perfectly correlated with
    `domain` (100% of tech_saas rows had one, 0% of d2c rows), which made them a
    trivial shortcut feature.
  - The train/val split is performed ON BASE TEXT, not per sample. All samples
    sharing a base text land in the same partition, so base-text overlap
    between train and val is structurally 0. (Previously 50% of val samples were
    verbatim copies of training text.)
  - The COMPLAINT label uses the PRODUCTION classifier's pattern, imported from
    `app.ml.sentence_pipeline` — there is no second, drifting keyword list here.
"""

from __future__ import annotations

import itertools
import json
import random
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
for _p in (str(PROJECT_ROOT), str(PROJECT_ROOT / "backend")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from app.ml.sentence_pipeline import deconstruct_sentences

OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "complaint_sentences_2k.json"

SEED = 42
VAL_FRACTION = 0.20

# ---------------------------------------------------------------------------
# Complaint terms — SINGLE SOURCE OF TRUTH (production classifier)
# ---------------------------------------------------------------------------
# The label a sample receives here must be derivable from the SAME signal the
# production classifier uses, otherwise the trained model can at best reproduce a
# stale local keyword subset. Import the production pattern instead of
# redeclaring it (three divergent definitions previously existed).
try:
    from app.ml.sentence_pipeline import _COMPLAINT_PATTERN  # production, single source of truth
    DEFECT_PATTERN: re.Pattern = _COMPLAINT_PATTERN
    DEFECT_PATTERN_SOURCE = "app.ml.sentence_pipeline._COMPLAINT_PATTERN"
except Exception as _exc:  # pragma: no cover - bare-script fallback
    # FALLBACK ONLY. Used when the backend package is not importable (e.g. the
    # file is copied into a Kaggle notebook on its own). This copy WILL drift
    # from production; keep it in sync or delete it.
    DEFECT_PATTERN = re.compile(
        r"\b(?:"
        r"but|however|although|though|except|unfortunately|sadly|regrettably|"
        r"despite|nevertheless|"
        r"cracked|broken|shattered|leaked|leaking|spilled|exploded|"
        r"jammed|stuck|clogged|blocked|stripped|peeled|"
        r"burning|burns|burned|stinging|stings|stung|itching|itchy|"
        r"rash|hives|dermatitis|allergic|allergy|breakout|cystic|"
        r"irritation|irritated|inflamed|redness|swelling|blisters|"
        r"terrible|horrible|awful|worst|useless|waste|disappointed|"
        r"doesn't work|didn't work|not work|stopped working|"
        r"fake|counterfeit|expired|smells off|changed formula|"
        r"no effect|no results|zero effect|"
        r"crash|crashes|crashed|freeze|freezes|frozen|"
        r"failed|fails|failure|error|bug|glitch|"
        r"limbo|pending|not loading|times out|timed out|timeout|redirect loop|login loop|"
        r"unresponsive|memory leak|deadlock|"
        r"never arrived|damaged|defective|recalled|refund|return"
        r")\b",
        re.IGNORECASE,
    )
    DEFECT_PATTERN_SOURCE = f"FALLBACK local copy (import failed: {_exc!r})"

# Backwards-compatible alias for call sites that used the old name.
DEFECT_KEYWORDS = DEFECT_PATTERN


def _top_level_alternatives(pattern: re.Pattern) -> List[str]:
    """Best-effort extraction of the pattern's alternation terms (audit only)."""
    src = pattern.pattern
    m = re.search(r"\\b\(\?:(.*?)\)\\b", src, re.DOTALL)
    body = m.group(1) if m else src
    return [t.strip() for t in body.split("|") if t.strip()]


# Recorded at import so any change to the production pattern is visible in logs
# and in training_metrics.json rather than silently changing the label set.
DEFECT_TERMS = _top_level_alternatives(DEFECT_PATTERN)
DEFECT_TERM_COUNT = len(DEFECT_TERMS)
logger_note = (
    f"COMPLAINT signal: {DEFECT_TERM_COUNT} terms from {DEFECT_PATTERN_SOURCE}"
)

# Negation guards: if any of these precede symptom words, it's NOT a complaint.
# Cosmetics-specific (this dataset's negative class is mostly skincare text).
NEGATION_FILTER = re.compile(
    r"\b(never|didn't|did not|not|no|wasn't|was not|isn't|is not|without|zero|barely|stopped|decrease in|prevented)\s+"
    r"(\w+\s+)?(irritat|burn|breakout|rash|peel|sting|pilling|problem|issue|defect|clog|leak)",
    re.IGNORECASE
)

REC_KEYWORDS = re.compile(
    r"\b(wish|would love|would like|would prefer|please add|should include|should offer|"
    r"hope they|hope you|it would be great|it would be nice|feature request|could improve|"
    r"needs to be|needs a pump|needs a better|suggestion)\b",
    re.IGNORECASE
)

PRAISE_KEYWORDS = re.compile(
    r"\b(holy grail|absolute favorite|love how|in love|so hydrating|glowing|best product|"
    r"gentle on skin|absorbs fast|worth every penny|10/10|exceeded my expectations|"
    r"cleared my skin|so smooth|plump and radiant|amazing results)\b",
    re.IGNORECASE
)

NEUTRAL_KEYWORDS = re.compile(
    r"\b(ordered|arrived|received|bought|purchased|using|routine|apply|morning|night|"
    r"texture|consistency|color|unscented|package|bottle|box|store|sale|tested|gift|"
    r"been using for|testing for|standard packaging|retail price|came in a box|"
    r"tried this product|first time purchasing)\b",
    re.IGNORECASE
)


# ---------------------------------------------------------------------------
# Cosmetics harvesting (real text)
# ---------------------------------------------------------------------------

def _harvest(
    df: pd.DataFrame,
    label: str,
    pattern: re.Pattern,
    targets: List[re.Pattern],
    max_samples: int,
    id_prefix: str,
    seen: set,
    skip_negation: bool = False,
) -> List[Dict[str, Any]]:
    """Generic sentence harvester: keep sentences matching `pattern` and
    matching none of `targets`."""
    out: List[Dict[str, Any]] = []
    # `seen` is shared ACROSS all four harvests (passed in by the caller) so a
    # sentence cannot be emitted under two different labels.
    for row_idx, row in df.iterrows():
        rev_id = f"{id_prefix}_{row_idx:05d}"
        text = str(row["review_text"])
        for sent, start, end in deconstruct_sentences(rev_id, row_idx, text):
            norm = sent.strip().lower()
            if norm in seen or len(sent.split()) < 4 or len(sent) < 16:
                continue
            if not pattern.search(sent):
                continue
            if skip_negation and NEGATION_FILTER.search(sent):
                continue
            if any(t.search(sent) for t in targets):
                continue
            seen.add(norm)
            out.append({
                "text": sent,
                "label": label,
                "domain": "d2c_cosmetics",
                "source_review_id": rev_id,
                "char_start": start,
                "char_end": end,
            })
            if len(out) >= max_samples:
                return out
    return out


def extract_cosmetics_samples(df: pd.DataFrame) -> Dict[str, List[Dict[str, Any]]]:
    """Harvests clean sentence samples from real cosmetics reviews using rating priors."""
    df_low = df[df["rating"] <= 2].copy()
    df_high = df[df["rating"] == 5].copy()
    df_mid = df[df["rating"].isin([3, 4])].copy()

    # One shared dedup set across all four classes.
    seen: set = set()

    return {
        "COMPLAINT": _harvest(
            df_low, "COMPLAINT", DEFECT_PATTERN, [], 350, "D2C_LOW", seen, skip_negation=True
        ),
        "RECOMMENDATION": _harvest(
            df, "RECOMMENDATION", REC_KEYWORDS, [], 225, "D2C_REC", seen
        ),
        "PRAISE": _harvest(
            df_high, "PRAISE", PRAISE_KEYWORDS, [DEFECT_PATTERN], 225, "D2C_HIGH", seen
        ),
        "NEUTRAL_NOISE": _harvest(
            df_mid, "NEUTRAL_NOISE", NEUTRAL_KEYWORDS, [DEFECT_PATTERN, PRAISE_KEYWORDS],
            200, "D2C_MID", seen,
        ),
    }


# ---------------------------------------------------------------------------
# SaaS synthesis — combinatorial expansion, no repeated base text
# ---------------------------------------------------------------------------

_SAAS_COMPONENTS = [
    "The SAML SSO integration", "The CSV export worker", "The automated billing module",
    "The webhook dispatcher", "The iOS mobile client", "The document editor",
    "The Android push service", "The search indexer", "The audit log downloader",
    "The attachment upload service", "The permissions service", "The nightly backup job",
    "The reporting dashboard", "The calendar sync connector", "The invoice PDF renderer",
    "The bulk user importer", "The real-time notification streamer",
    "The seat provisioning API", "The comment resolution engine",
    "The data retention scheduler",
]

_SAAS_SYMPTOMS = [
    "crashes with an uncaught runtime error whenever a workspace exceeds 10,000 records",
    "times out on Safari and traps enterprise users in an infinite login redirect loop",
    "leaks memory in the background worker and consumes over 4GB of RAM after two hours",
    "charged our credit card twice this billing cycle and issued no itemized invoice",
    "returns HTTP 500 during peak hours and drops queued events without any retry",
    "freezes on the splash screen and never loads the offline dashboard cards",
    "fails on attachments larger than 15MB with a cryptic timeout and no resume option",
    "broke table pagination and silently discarded every saved filtering preset",
    "delivers on-call alerts more than forty minutes after the triggering event",
    "deadlocks whenever two editors change document permissions in the same second",
    "truncates non-latin characters and corrupts Japanese and German customer records",
    "returns zero results for exact SKU matches whenever a hyphen is present",
    "silently truncates exports at the one millionth row with no error message",
    "duplicates every inbound webhook delivery and ignores the idempotency key",
    "rejects valid OAuth PKCE callbacks and forces users back to the login screen",
    "loses unsaved edits when the tab is backgrounded for more than five minutes",
    "recalculates usage counters incorrectly and overbills by several thousand units",
    "stops delivering scheduled reports whenever the timezone crosses a DST boundary",
    "corrupts UTF-8 filenames during drag-and-drop upload in the desktop app",
    "blocks keyboard input for several seconds after opening the filter drawer",
    "fails to render charts when a workspace has more than fifty pinned dashboards",
    "erases API keys on save without warning whenever a token expires mid-session",
    "reverts permission changes made through the SCIM provisioning endpoint",
    "renders white on white for dark-mode themes after the 2.14 release",
    "times out on any export larger than two gigabytes and leaves a partial file behind",
]

_SAAS_AREAS = [
    "the enterprise admin console", "the analytics dashboard", "the mobile client",
    "the REST API", "the Slack integration", "the Microsoft Teams integration",
    "the Snowflake connector", "the BigQuery connector", "the audit log viewer",
    "the CSV export screen", "the bulk user importer", "the calendar view",
    "the notification preferences page", "the seat management page",
    "the saved filter drawer",
]

_SAAS_ASKS = [
    "native OAuth 2.0 PKCE single sign-on", "custom HMAC webhook request headers",
    "a granular role-based access control matrix", "SCIM provisioning endpoints",
    "a true dark mode theme", "SAML metadata export", "per-field audit annotations",
    "scheduled report delivery", "a public webhook playground",
    "incremental table pagination", "an incident timeline view",
    "team-level API key rotation", "row-level retention policies",
    "an offline-first mobile cache", "column-level masking rules", "CSV import with undo",
]

_SAAS_PRAISE_SUBJECTS = [
    "The PostgreSQL and pgvector integration", "The developer sandbox",
    "The onboarding checklist", "The support response time",
    "The migration tooling", "The query explainer", "The audit export",
    "The documentation search", "The SSO setup wizard",
    "The incident runbook template", "The workspace switching flow",
    "The keyboard shortcut set", "The changelog format", "The status page",
    "The invoice preview",
]

_SAAS_PRAISE_PREDICATES = [
    "is blazingly fast and required zero unplanned downtime",
    "is genuinely thoughtful and unusually well documented",
    "is incredibly responsive and the team is always helpful",
    "saved our operations team roughly ten hours every single week",
    "is clear, complete, and far more accurate than the previous vendor",
    "is surprisingly robust under sustained production load",
    "is effortless for a new engineer to configure from scratch",
    "is exactly what our security reviewers asked us to find",
    "is well designed and trivial for auditors to verify",
    "has been reliable across every environment we have tried",
    "is a pleasure to work with and our team adopted it immediately",
    "is far better than the tool we migrated away from last year",
    "is quick to learn and remarkably hard to break",
    "was seamless from the very first login onward",
    "stayed perfectly stable through our busiest trading week",
    "is worth every seat we bought without any hesitation",
]

_SAAS_NEUTRAL_ROUTINES = [
    "is currently evaluating", "has finished evaluating", "is planning to migrate to",
    "scheduled a formal review of", "has budget approval for",
    "is running a proof of concept on", "signed a two year agreement covering",
    "renews the annual subscription for", "is documenting the configuration of",
    "completed the security questionnaire for", "is standardising on",
    "imported historical data into", "maintains an internal runbook for",
    "booked training sessions covering", "is consolidating spend on",
]

_N_TARGETS = {"COMPLAINT": 350, "RECOMMENDATION": 225, "PRAISE": 225, "NEUTRAL_NOISE": 200}


def _expand(components: List[str], second: List[str], template: str, limit: int) -> List[str]:
    """Deterministic, collision-checked combinatorial expansion."""
    out: List[str] = []
    seen: set = set()
    # symptoms outer / components inner so coverage is spread, not blocked
    # symptoms outer / components inner so coverage is spread, not blocked
    for a, b in itertools.product(second, components):
        # a = the varying slot (symptom/ask/...), b = the stable slot (component).
        s = template.format(a, b)
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= limit:
            break
    if len(out) < limit:
        raise RuntimeError(
            f"Slot vocabularies exhausted: only {len(out)} distinct base texts "
            f"for a target of {limit}. Add vocabulary."
        )
    return out


def generate_saas_propositions() -> List[Dict[str, str]]:
    """Generates SYNTHETIC SaaS statements with all-distinct base texts.

    Deterministic: every sample's text is unique, so no identifier suffix is
    needed and no base text can leak across the train/val boundary.
    """
    saas_data: List[Dict[str, str]] = []

    def add(texts: List[str], label: str) -> None:
        seen_local = {s["text"] for s in saas_data}
        for t in texts:
            if t in seen_local:
                continue
            seen_local.add(t)
            saas_data.append({"text": t, "label": label, "domain": "tech_saas"})

    add(_expand(_SAAS_COMPONENTS, _SAAS_SYMPTOMS, "{0} {1}.", _N_TARGETS["COMPLAINT"]),
        "COMPLAINT")
    add([f"Please add {ask} to {area}." for area, ask in
         itertools.product(_SAAS_AREAS, _SAAS_ASKS)][:_N_TARGETS["RECOMMENDATION"]],
        "RECOMMENDATION")
    add([f"{subj} {pred}." for subj, pred in
         itertools.product(_SAAS_PRAISE_SUBJECTS, _SAAS_PRAISE_PREDICATES)][:_N_TARGETS["PRAISE"]],
        "PRAISE")
    add([f"Our team {routine} {area}." for routine, area in
         itertools.product(_SAAS_NEUTRAL_ROUTINES, _SAAS_AREAS)][:_N_TARGETS["NEUTRAL_NOISE"]],
        "NEUTRAL_NOISE")

    return saas_data


# ---------------------------------------------------------------------------
# Split — BY BASE TEXT
# ---------------------------------------------------------------------------

def assign_splits(samples: List[Dict[str, Any]], seed: int = SEED) -> None:
    """Assign `split` in place, partitioning by BASE TEXT (not by sample).

    All samples sharing a base text go to the same partition, so base-text
    overlap between train and val is structurally zero. Splitting is done per
    (label, domain) group so class balance is preserved.
    """
    # Deterministic shuffle purely to make sentence_id assignment stable and
    # independent of dict/groupby ordering.
    rng = random.Random(seed)
    rng.shuffle(samples)

    for i, s in enumerate(samples):
        s["sentence_id"] = f"SENT_{i:05d}"
        s["base_text"] = s["text"].strip()

    val_base: set = set()
    frame = pd.DataFrame(
        [{"label": s["label"], "domain": s["domain"], "base_text": s["base_text"]} for s in samples]
    )
    for (label, domain), group in frame.groupby(["label", "domain"]):
        unique_bases = sorted(group["base_text"].unique().tolist())
        n_val = max(1, int(len(unique_bases) * VAL_FRACTION))
        rng2 = random.Random(seed)
        rng2.shuffle(unique_bases)
        val_base.update(unique_bases[:n_val])

    for s in samples:
        s["split"] = "val" if s["base_text"] in val_base else "train"


def main():
    print("=" * 70)
    print("Curating Sentence Intent Dataset (rating priors + production complaint pattern)")
    print(logger_note)
    print("=" * 70)

    cosmetics_csv = PROJECT_ROOT / "data" / "processed" / "cosmetics" / "cosmetics_10k.csv"
    df = pd.read_csv(cosmetics_csv)
    print(f"Loaded {len(df)} real Sephora reviews.")

    cos_data = extract_cosmetics_samples(df)
    cos_samples: List[Dict[str, Any]] = []
    for k, v in cos_data.items():
        print(f"  D2C {k}: {len(v)} samples")
        cos_samples.extend(v)

    saas_samples = generate_saas_propositions()
    print(f"  SaaS total: {len(saas_samples)} samples (synthetic, all-distinct base texts)")

    all_samples = cos_samples + saas_samples
    assign_splits(all_samples, seed=SEED)

    # ---- Leakage assertions -------------------------------------------------
    base_by_split: Dict[str, set] = {"train": set(), "val": set()}
    for s in all_samples:
        base_by_split[s["split"]].add(s["base_text"])
    overlap = base_by_split["train"] & base_by_split["val"]
    unique_bases = len({s["base_text"] for s in all_samples})
    marker_rows = sum(
        1 for s in all_samples if re.search(r"\[(?:trace|feature req|feedback|log)\s*#", s["text"], re.I)
    )
    if overlap:
        raise RuntimeError(f"train/val base-text overlap is {len(overlap)}, expected 0")
    if marker_rows:
        raise RuntimeError(f"{marker_rows} samples still carry a domain-correlated ID marker")

    df_all = pd.DataFrame(all_samples)

    payload = {
        "metadata": {
            "total_samples": len(all_samples),
            "train_samples": int((df_all["split"] == "train").sum()),
            "val_samples": int((df_all["split"] == "val").sum()),
            "class_distribution": df_all["label"].value_counts().to_dict(),
            "domain_distribution": df_all["domain"].value_counts().to_dict(),
            "classes": ["COMPLAINT", "RECOMMENDATION", "PRAISE", "NEUTRAL_NOISE"],
            "unique_base_texts": unique_bases,
            "train_val_base_text_overlap": len(overlap),
            "complaint_term_count": DEFECT_TERM_COUNT,
            "complaint_term_source": DEFECT_PATTERN_SOURCE,
            "is_synthetic_partial": True,
            "labels_are_keyword_heuristic": True,
            "metrics_are_not_real_world_accuracy": True,
        },
        "samples": all_samples,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False, allow_nan=False)

    CSV_OUTPUT_PATH = OUTPUT_PATH.with_suffix(".csv")
    df_all.to_csv(CSV_OUTPUT_PATH, index=False, encoding="utf-8")

    print("=" * 70)
    print(f"SUCCESS: Generated {len(all_samples)} samples")
    print(f"  UNIQUE base texts: {unique_bases} / {len(all_samples)} samples")
    print(f"  train/val base-text overlap: {len(overlap)} (must be 0)")
    print(f"  Samples with domain-correlated ID markers: {marker_rows} (must be 0)")
    print(f"  JSON Artifact: {OUTPUT_PATH}")
    print(f"  CSV Artifact:  {CSV_OUTPUT_PATH}")
    print(f"  Class Distribution: {df_all['label'].value_counts().to_dict()}")
    print(f"  Domain Distribution: {df_all['domain'].value_counts().to_dict()}")
    print("  REMINDER: labels are keyword-heuristic and tech_saas is synthetic.")
    print("           Metrics on this data are NOT a real-world accuracy claim.")
    print("=" * 70)


if __name__ == "__main__":
    main()
