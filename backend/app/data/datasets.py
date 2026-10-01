import random
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
from app.core.pii import pii_redactor

import re

# Compiled ONCE at module scope. Previously this regex was recompiled inside
# extract_complaint_span, i.e. once per review (21,000 times per corpus).
_COMPLAINT_SPAN_PATTERN = re.compile(
    r'\b(?:but|however|except\s+that|except|although|unfortunately|until|cracked|jammed|leaked|burning|stinging|rash|dermatitis|crash|crashes|freeze|freezes|failed|fails|limbo|terrible|horrible)\b.*',
    re.IGNORECASE
)


def extract_complaint_span(text: str) -> Dict[str, Any]:
    """
    PROVISIONAL heuristic: extracts contrastive complaint clauses or defect phrases.
    Matches discourse markers ('but', 'however', 'except that', 'although',
    'unfortunately', 'until') or defect terms ('cracked', 'leaked', 'jammed',
    'burning', 'crash', etc.).

    Returns:
        detected : bool – True if a complaint pattern was found
        text     : str  – matched span text (empty string when not detected)
        start    : int  – start character offset (None when not detected)
        end      : int  – end character offset (None when not detected)

    When detected is True: source_text[start:end] == text (guaranteed).
    When detected is False: text is "" and offsets are None.

    IMPORTANT: The previous implementation returned {text: full_text, start: 0,
    end: len(text)} on no-match, which made it impossible to distinguish
    "no complaint detected" from "complaint found at position 0". Fixed.
    """
    if not isinstance(text, str) or not text.strip():
        return {"detected": False, "text": "", "start": None, "end": None}

    pattern = _COMPLAINT_SPAN_PATTERN
    match = pattern.search(text)
    if match:
        return {
            "detected": True,
            "text": match.group(0),
            "start": match.start(),
            "end": match.end(),
        }
    return {
        "detected": False,
        "text": "",
        "start": None,
        "end": None,
    }

def _holdout_templates(templates: List[str], name: str) -> List[str]:
    """Deterministic GOLD half of a template list (never used for corpus generation)."""
    if len(templates) < 2:
        raise ValueError(
            f"Template group {name!r} has {len(templates)} entry(ies); at least 2 are required "
            "to form a disjoint train/gold partition."
        )
    half = max(1, len(templates) // 2)
    return templates[-half:]


def _train_templates(templates: List[str], name: str) -> List[str]:
    """Deterministic TRAIN half of a template list (disjoint from the gold half)."""
    half = max(1, len(templates) // 2)
    return templates[:-half]


class TelemetryDatasetManager:
    """
    Manages multi-domain datasets (D2C Beauty/Cosmetics & Tech SaaS/App),
    provides pre-labeled ground truth for validation, and handles custom CSV uploads.
    """

    @staticmethod
    def generate_d2c_cosmetics(n: int = 10000) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Generates realistic feedback telemetry for D2C Cosmetics brand 'Aura Botanicals'.
        Simulates:
        - 4 Batches: Batch-24A, Batch-24B, Batch-24C (Preservative revamp -> Skin irritation anomaly & pump defect), Batch-24D.
        - SKUs: 15% Vitamin C Glow Serum, Hydra-Barrier Ceramide Cream, Velvet Matte Lip Tint, Ultra-Light Gel Sunscreen SPF50.
        - Channels: Direct Website, Nykaa, Amazon, Blinkit.
        """
        random.seed(42)

        skus = [
            ("SKU-VITC-15", "15% Vitamin C Glow Serum"),
            ("SKU-CER-50", "Hydra-Barrier Ceramide Cream"),
            ("SKU-LIP-04", "Velvet Matte Lip Tint"),
            ("SKU-SUN-50", "Ultra-Light Gel Sunscreen SPF50")
        ]
        channels = ["Direct Website", "Nykaa", "Amazon", "Blinkit"]
        batches = ["Batch-24A", "Batch-24B", "Batch-24C", "Batch-24D"]

        # Templates for different aspects
        positive_templates = [
            "Absolutely love the {product}! My skin has never felt softer. Fast delivery from {channel}.",
            "Holy grail product! Glowing results within a week of using {product}. Will definitely repurchase.",
            "Super lightweight texture, absorbs instantly without any greasy residue. 5 stars!",
            "Matches my skin tone perfectly, very hydrating and no fragrance. Great job on this formula.",
            "Best sunscreen I've tested this year. Zero white cast under makeup. Thanks for the quick shipping."
        ]

        neutral_templates = [
            "The {product} is okay. Decent hydration but takes some time to absorb. Expected slightly more glow.",
            "Average experience. Packaging looks nice but the scent is a bit strong for my liking.",
            "It does the job, nothing extraordinary for the price. Might try something else next time.",
            "Texture is fine, but delivery through {channel} took almost 6 days. Product is acceptable."
        ]

        # Specific negative themes
        negative_leakage_templates = [
            "Terrible packaging! The dropper pipette arrived cracked and the serum leaked all over the box. Order #ORD-{order_id}. Refund immediately!",
            "Pump dispenser is jammed and completely useless! Can't get any product out of the bottle. Quality control is shocking. Phone: {phone}",
            "Bottle arrived with broken seal and spilled contents in the package. My order reference is OD{order_id}. Very disappointed."
        ]

        negative_irritation_templates = [
            "Severe burning and redness! Used this new batch and my face broke out in tiny bumps within an hour. Avoid! Contact me at {email}.",
            "Did you change the formulation? Batch-24C caused extreme stinging around my cheeks and neck. Had to wash it off immediately.",
            "Gave me horrible allergic contact dermatitis. This batch smells completely different and irritates my skin barrier. Call me: {phone}."
        ]

        negative_delivery_templates = [
            "Worst courier service ever. Package was left in the heat outside my door at {address}. Product was completely warm and spoiled.",
            "Delayed by over 10 days on {channel}. Customer support completely ghosted me regarding order #ORD-{order_id}."
        ]

        # ------------------------------------------------------------------
        # Train / gold template partition.
        #
        # A generated review's label is a deterministic function of the
        # template it came from. Drawing the "held-out" evaluation sample from
        # the SAME template lists meant an independent random seed only
        # re-rolled the slot values (order id, phone, product) inside an
        # otherwise identical sentence, so any TF-IDF model could score near
        # perfect accuracy by recognising ~10 tokens.
        #
        # Each list is therefore split, and the corpus below uses only the
        # TRAIN half. The evaluation sample below uses only the GOLD half.
        # ------------------------------------------------------------------
        gold_templates = {
            "positive": _holdout_templates(positive_templates, "positive"),
            "neutral": _holdout_templates(neutral_templates, "neutral"),
            "irritation": _holdout_templates(negative_irritation_templates, "irritation"),
            "leakage": _holdout_templates(negative_leakage_templates, "leakage"),
            "delivery": _holdout_templates(negative_delivery_templates, "delivery"),
        }
        positive_templates = _train_templates(positive_templates, "positive")
        neutral_templates = _train_templates(neutral_templates, "neutral")
        negative_irritation_templates = _train_templates(negative_irritation_templates, "irritation")
        negative_leakage_templates = _train_templates(negative_leakage_templates, "leakage")
        negative_delivery_templates = _train_templates(negative_delivery_templates, "delivery")

        names = ["Aarav Sharma", "Pooja Mehta", "Rohan Verma", "Sneha Patel", "Ananya Iyer", "Vikram Singh"]
        cities = ["Mumbai 400001", "Bengaluru 560034", "Delhi 110001", "Pune 411007"]

        reviews = []

        for i in range(1, n + 1):
            batch_choice = batches[min(i // max(n // 4, 1), len(batches) - 1)]
            sku_code, product_name = random.choice(skus)
            channel = random.choice(channels)
            order_id = random.randint(100000, 999999)
            phone = f"+91-98{random.randint(10000000, 99999999)}"
            email = f"user_{order_id}@gmail.com"
            cust_name = random.choice(names)
            address = f"Flat {random.randint(101, 804)}, Green Enclave, {random.choice(cities)}"

            # Inject batch-specific defect spike in Batch-24C
            is_anomaly_batch = (batch_choice == "Batch-24C")

            rand_val = random.random()
            if is_anomaly_batch:
                # 65% negative in Batch-24C to simulate formulation/packaging crisis
                if rand_val < 0.35:
                    label = "NEGATIVE"
                    rating = 1
                    raw_text = random.choice(negative_irritation_templates).format(
                        email=email, phone=phone, order_id=order_id
                    )
                elif rand_val < 0.65:
                    label = "NEGATIVE"
                    rating = random.choice([1, 2])
                    raw_text = random.choice(negative_leakage_templates).format(
                        order_id=order_id, phone=phone
                    )
                elif rand_val < 0.80:
                    label = "NEUTRAL"
                    rating = 3
                    raw_text = random.choice(neutral_templates).format(product=product_name, channel=channel)
                else:
                    label = "POSITIVE"
                    rating = random.choice([4, 5])
                    raw_text = random.choice(positive_templates).format(product=product_name, channel=channel)
            else:
                # Normal stable distribution (70% pos, 15% neu, 15% neg)
                if rand_val < 0.70:
                    label = "POSITIVE"
                    rating = random.choice([4, 5])
                    raw_text = random.choice(positive_templates).format(product=product_name, channel=channel)
                elif rand_val < 0.85:
                    label = "NEUTRAL"
                    rating = 3
                    raw_text = random.choice(neutral_templates).format(product=product_name, channel=channel)
                else:
                    label = "NEGATIVE"
                    rating = random.choice([1, 2])
                    raw_text = random.choice(negative_delivery_templates).format(
                        channel=channel, order_id=order_id, address=address
                    )

            # Natural PII injection on 20% of reviews
            if random.random() < 0.2:
                intro = f"Hi, my name is {cust_name}. "
                raw_text = intro + raw_text

            sanitized_text, pii_tags = pii_redactor.redact(raw_text)

            review_obj = {
                "id": f"REV-D2C-{i:05d}",
                "domain": "d2c_cosmetics",
                "product_name": product_name,
                "sku_or_module": sku_code,
                "batch_or_version": batch_choice,
                "channel": channel,
                "rating": rating,
                "raw_text": raw_text,
                "redacted_text": sanitized_text,
                "pii_detected": pii_tags,
                "ground_truth_label": label,
                "highlight_span": extract_complaint_span(sanitized_text)
            }

            reviews.append(review_obj)

        # Held-out evaluation sample (N = 1,000), drawn only from the GOLD
        # template half reserved above. The corpus above never sees these.
        gt_rng = random.Random(7777)
        ground_truth_sample = []
        for j in range(1, 1001):
            sku_code, product_name = gt_rng.choice(skus)
            channel = gt_rng.choice(channels)
            order_id = gt_rng.randint(200000, 999999)
            phone = f"+91-98{gt_rng.randint(10000000, 99999999)}"
            email = f"eval_user_{order_id}@gmail.com"
            address = f"Flat {gt_rng.randint(101, 804)}, Green Enclave, {gt_rng.choice(cities)}"

            r_val = gt_rng.random()
            if r_val < 0.35:
                label = "POSITIVE"
                rating = gt_rng.choice([4, 5])
                raw_text = gt_rng.choice(gold_templates["positive"]).format(product=product_name, channel=channel)
            elif r_val < 0.65:
                label = "NEUTRAL"
                rating = 3
                raw_text = gt_rng.choice(gold_templates["neutral"]).format(product=product_name, channel=channel)
            else:
                label = "NEGATIVE"
                rating = gt_rng.choice([1, 2])
                neg_choice = gt_rng.choice([
                    gold_templates["irritation"],
                    gold_templates["leakage"],
                    gold_templates["delivery"],
                ])
                raw_text = gt_rng.choice(neg_choice).format(
                    email=email, phone=phone, order_id=order_id, channel=channel, address=address
                )

            sanitized_text, pii_tags = pii_redactor.redact(raw_text)
            ground_truth_sample.append({
                "id": f"REV-D2C-GOLD-{j:04d}",
                "domain": "d2c_cosmetics",
                "product_name": product_name,
                "sku_or_module": sku_code,
                "batch_or_version": "Gold-Standard-Evaluation",
                "channel": channel,
                "rating": rating,
                "raw_text": raw_text,
                "redacted_text": sanitized_text,
                "pii_detected": pii_tags,
                "ground_truth_label": label,
                "highlight_span": extract_complaint_span(sanitized_text)
            })

        return reviews, ground_truth_sample

    @staticmethod
    def generate_tech_saas(n: int = 10000) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Generates realistic app-store review telemetry for mobile fintech app 'NovaPay'.
        Simulates:
        - Releases: v2.1.0, v2.2.0, v2.3.0, v2.4.0 (Regression: Biometric auth crashes on Android 14).
        - Modules: Biometric Auth, Instant P2P Transfers, Card Controls, Bill Payments.
        """
        random.seed(1337)
        modules = [
            ("MOD-AUTH", "Biometric & FaceID Auth"),
            ("MOD-P2P", "Instant UPI / P2P Transfers"),
            ("MOD-CARDS", "Virtual & Physical Cards"),
            ("MOD-BILLS", "Utility Bill Payments")
        ]
        versions = ["v2.1.0", "v2.2.0", "v2.3.0", "v2.4.0"]
        channels = ["Google Play Store", "Apple App Store"]

        pos_templates = [
            "Super fast payments! Seamless UI and love the transaction speed on {channel}.",
            "Best banking app hands down. Instant push notifications and never lags. 5 stars!",
            "Love the new card lock controls. Super clean design and reliable experience.",
            "Transfers go through in seconds without fail. Great job to the engineering team."
        ]
        neu_templates = [
            "App works fine, but the new dark mode contrast could be slightly better.",
            "Decent app, but charges for international transactions could be clearer in the statement.",
            "Does what it says. Sometimes takes 5 seconds to load past the splash screen."
        ]
        neg_biometric_spike = [
            "Crash on open! Since updating to v2.4.0, fingerprint biometric auth completely freezes the app. Device: Galaxy S24, Android 14. Contact me: {email}",
            "Cannot log in anymore! FaceID fails and typing the PIN causes the screen to go black. Fix this bug immediately! Phone: {phone}",
            "App constantly terminates upon biometric verification. Lost access to my funds when I needed to pay. Fix build v2.4.0 ASAP!"
        ]
        neg_p2p_failed = [
            "Transaction debited from my bank but transfer failed! Transaction Ref: #TRK-{order_id}. Customer support has not responded for 3 days.",
            "Stuck on 'Payment Pending' spinner. My money is in limbo. Ticket ID: OD{order_id}."
        ]

        # Train / gold template partition (see generate_d2c_cosmetics).
        # Without this the "held-out" gold sample is template-identical to the
        # corpus, so reported accuracy measures template recognition.
        gold_pos = _holdout_templates(pos_templates, "pos")
        gold_neu = _holdout_templates(neu_templates, "neu")
        gold_biometric = _holdout_templates(neg_biometric_spike, "neg_biometric_spike")
        gold_p2p = _holdout_templates(neg_p2p_failed, "neg_p2p_failed")
        pos_templates = _train_templates(pos_templates, "pos")
        neu_templates = _train_templates(neu_templates, "neu")
        neg_biometric_spike = _train_templates(neg_biometric_spike, "neg_biometric_spike")
        neg_p2p_failed = _train_templates(neg_p2p_failed, "neg_p2p_failed")

        reviews = []
        ground_truth_sample = []

        for i in range(1, n + 1):
            ver = versions[min(i // max(n // 4, 1), len(versions) - 1)]
            mod_code, mod_name = random.choice(modules)
            channel = random.choice(channels)
            order_id = random.randint(100000, 999999)
            phone = f"+1-555-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
            email = f"app_user_{order_id}@icloud.com"

            is_buggy_release = (ver == "v2.4.0")
            rand_val = random.random()

            if is_buggy_release:
                if rand_val < 0.55:
                    label = "NEGATIVE"
                    rating = 1
                    raw_text = random.choice(neg_biometric_spike).format(email=email, phone=phone)
                    mod_code, mod_name = ("MOD-AUTH", "Biometric & FaceID Auth")
                elif rand_val < 0.70:
                    label = "NEGATIVE"
                    rating = 2
                    raw_text = random.choice(neg_p2p_failed).format(order_id=order_id)
                elif rand_val < 0.85:
                    label = "NEUTRAL"
                    rating = 3
                    raw_text = random.choice(neu_templates)
                else:
                    label = "POSITIVE"
                    rating = 5
                    raw_text = random.choice(pos_templates).format(channel=channel)
            else:
                if rand_val < 0.72:
                    label = "POSITIVE"
                    rating = random.choice([4, 5])
                    raw_text = random.choice(pos_templates).format(channel=channel)
                elif rand_val < 0.86:
                    label = "NEUTRAL"
                    rating = 3
                    raw_text = random.choice(neu_templates)
                else:
                    label = "NEGATIVE"
                    rating = 1
                    raw_text = random.choice(neg_p2p_failed).format(order_id=order_id)

            sanitized_text, pii_tags = pii_redactor.redact(raw_text)

            review_obj = {
                "id": f"REV-APP-{i:05d}",
                "domain": "tech_saas",
                "product_name": "NovaPay Mobile",
                "sku_or_module": mod_name,
                "batch_or_version": ver,
                "channel": channel,
                "rating": rating,
                "raw_text": raw_text,
                "redacted_text": sanitized_text,
                "pii_detected": pii_tags,
                "ground_truth_label": label,
                "highlight_span": extract_complaint_span(sanitized_text)
            }

            reviews.append(review_obj)

        # STRICTLY DISJOINT evaluation sample (N = 1,000) for Tech SaaS.
        # Drawn only from the GOLD template half reserved above.
        gt_rng = random.Random(8888)
        ground_truth_sample = []
        for j in range(1, 1001):
            mod_code, mod_name = gt_rng.choice(modules)
            channel = gt_rng.choice(channels)
            order_id = gt_rng.randint(200000, 999999)
            phone = f"+1-555-{gt_rng.randint(100, 999)}-{gt_rng.randint(1000, 9999)}"
            email = f"eval_user_{order_id}@icloud.com"

            r_val = gt_rng.random()
            if r_val < 0.35:
                label = "POSITIVE"
                rating = gt_rng.choice([4, 5])
                raw_text = gt_rng.choice(gold_pos).format(channel=channel)
            elif r_val < 0.65:
                label = "NEUTRAL"
                rating = 3
                raw_text = gt_rng.choice(gold_neu)
            else:
                label = "NEGATIVE"
                rating = gt_rng.choice([1, 2])
                neg_choice = gt_rng.choice([gold_biometric, gold_p2p])
                raw_text = gt_rng.choice(neg_choice).format(email=email, phone=phone, order_id=order_id)

            sanitized_text, pii_tags = pii_redactor.redact(raw_text)
            ground_truth_sample.append({
                "id": f"REV-APP-GOLD-{j:04d}",
                "domain": "tech_saas",
                "product_name": "NovaPay Mobile",
                "sku_or_module": mod_name,
                "batch_or_version": "Gold-Standard-Evaluation",
                "channel": channel,
                "rating": rating,
                "raw_text": raw_text,
                "redacted_text": sanitized_text,
                "pii_detected": pii_tags,
                "ground_truth_label": label,
                "highlight_span": extract_complaint_span(sanitized_text)
            })

        return reviews, ground_truth_sample
    # Ordered by specificity. The previous first-match substring scan bound
    # this project's own Sephora schema to `total_feedback_count` because it
    # contains "feedback" and appears before `review_text` in column order.
    TEXT_COLUMN_CANDIDATES = [
        "review_text", "reviewtext", "review", "comment_text", "comment",
        "feedback_text", "feedback", "body", "content", "message", "text",
    ]
    RATING_COLUMN_CANDIDATES = ["rating", "stars", "star_rating", "score", "overall"]
    VERSION_COLUMN_CANDIDATES = ["batch_or_version", "version", "release", "build", "batch", "date"]
    PRODUCT_COLUMN_CANDIDATES = ["product_name", "product", "sku", "item_name", "item", "name"]

    @classmethod
    def _resolve_column(
        cls,
        df: pd.DataFrame,
        candidates: List[str],
        require_text: bool = False,
    ) -> Optional[str]:
        """
        Resolves a column by exact name first, then by scored substring match.

        Only object/string columns are eligible when ``require_text`` is set, so
        an integer count column can never be mistaken for review text.
        """
        lowered = {str(c).strip().lower(): c for c in df.columns}

        for candidate in candidates:
            if candidate in lowered:
                return lowered[candidate]

        best: Optional[str] = None
        best_score = 0
        for lower, original in lowered.items():
            if require_text and not (
                pd.api.types.is_object_dtype(df[original])
                or pd.api.types.is_string_dtype(df[original])
            ):
                continue
            for rank, candidate in enumerate(candidates):
                if candidate in lower:
                    # Longer, more specific candidate wins.
                    score = len(candidate) * 100 - rank
                    if score > best_score:
                        best_score = score
                        best = original
                    break
        return best

    @classmethod
    def parse_custom_csv(cls, df: pd.DataFrame) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Parses a custom user-uploaded CSV into the unified InSight telemetry schema.

        Returns:
            (all_records, evaluation_records) where the two lists are disjoint.

        Raises:
            ValueError: if no usable review-text column is present.
        """
        text_col = cls._resolve_column(df, cls.TEXT_COLUMN_CANDIDATES, require_text=True)
        if not text_col:
            raise ValueError(
                "CSV must contain a text column (e.g. 'review_text', 'review', 'comment', 'text')."
            )

        rating_col = cls._resolve_column(df, cls.RATING_COLUMN_CANDIDATES)
        version_col = cls._resolve_column(df, cls.VERSION_COLUMN_CANDIDATES)
        prod_col = cls._resolve_column(df, cls.PRODUCT_COLUMN_CANDIDATES)

        all_records: List[Dict[str, Any]] = []

        for position, (_, row) in enumerate(df.iterrows()):
            raw_text = str(row[text_col])
            if not raw_text.strip() or raw_text.lower() == "nan":
                continue

            rating = 3
            if rating_col and pd.notnull(row[rating_col]):
                try:
                    rating = int(float(row[rating_col]))
                except (TypeError, ValueError):
                    rating = 3
                # Ratings on a non-1..5 scale would otherwise be silently
                # mapped to POSITIVE by the `else` branch below.
                if not 1 <= rating <= 5:
                    rating = 3

            ver = str(row[version_col]) if version_col and pd.notnull(row[version_col]) else "Batch-Custom"
            prod = str(row[prod_col]) if prod_col and pd.notnull(row[prod_col]) else "Custom Item"

            if rating <= 2:
                gt_label = "NEGATIVE"
            elif rating == 3:
                gt_label = "NEUTRAL"
            else:
                gt_label = "POSITIVE"

            sanitized, pii_tags = pii_redactor.redact(raw_text)

            all_records.append({
                # Positional index, not the DataFrame index label: index labels
                # are non-sequential and duplicate when a CSV is re-read or
                # filtered, which collided on the primary key.
                "id": f"REV-USER-{position+1:05d}",
                "domain": "custom",
                "product_name": prod,
                "sku_or_module": "General",
                "batch_or_version": ver,
                "channel": "Upload CSV",
                "rating": rating,
                "raw_text": raw_text,
                "redacted_text": sanitized,
                "pii_detected": pii_tags,
                "ground_truth_label": gt_label,
                "highlight_span": extract_complaint_span(sanitized),
            })

        # Splitting here is redundant: the caller performs a seeded, shuffled
        # split and evaluates only on rows the model never saw. Kept for
        # backwards compatibility with callers that request two lists.
        return all_records, []

dataset_manager = TelemetryDatasetManager()
