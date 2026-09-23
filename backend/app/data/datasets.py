import random
from typing import List, Dict, Any, Tuple
import pandas as pd
from app.core.pii import pii_redactor

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

        names = ["Aarav Sharma", "Pooja Mehta", "Rohan Verma", "Sneha Patel", "Ananya Iyer", "Vikram Singh"]
        cities = ["Mumbai 400001", "Bengaluru 560034", "Delhi 110001", "Pune 411007"]

        reviews = []
        ground_truth_sample = []

        for i in range(1, n + 1):
            batch_choice = batches[min(i // (n // 4), 3)]
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
                "ground_truth_label": label
            }

            reviews.append(review_obj)

            # Hold out 1,000 for strict gold-standard evaluation
            if len(ground_truth_sample) < 1000 and (i % 10 == 0):
                ground_truth_sample.append(review_obj)

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

        reviews = []
        ground_truth_sample = []

        for i in range(1, n + 1):
            ver = versions[min(i // (n // 4), 3)]
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
                "ground_truth_label": label
            }

            reviews.append(review_obj)
            if len(ground_truth_sample) < 1000 and (i % 10 == 0):
                ground_truth_sample.append(review_obj)

        return reviews, ground_truth_sample

    @staticmethod
    def parse_custom_csv(df: pd.DataFrame) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Parses custom user-uploaded CSV dataframe into unified InSight telemetry schema.
        """
        text_col = next((c for c in df.columns if any(k in c.lower() for k in ["text", "review", "comment", "feedback"])), None)
        if not text_col:
            raise ValueError("CSV must contain a column for review text (e.g. 'review', 'text', 'comment').")

        rating_col = next((c for c in df.columns if any(k in c.lower() for k in ["rating", "score", "star"])), None)
        version_col = next((c for c in df.columns if any(k in c.lower() for k in ["batch", "version", "release", "date"])), None)
        prod_col = next((c for c in df.columns if any(k in c.lower() for k in ["product", "sku", "item", "name"])), None)

        reviews = []
        ground_truth = []

        for idx, row in df.iterrows():
            raw_text = str(row[text_col])
            rating = int(row[rating_col]) if rating_col and pd.notnull(row[rating_col]) else 3
            ver = str(row[version_col]) if version_col and pd.notnull(row[version_col]) else "Batch-Custom"
            prod = str(row[prod_col]) if prod_col and pd.notnull(row[prod_col]) else "Custom Item"

            # Derive proxy ground truth from star rating if present
            if rating <= 2:
                gt_label = "NEGATIVE"
            elif rating == 3:
                gt_label = "NEUTRAL"
            else:
                gt_label = "POSITIVE"

            sanitized, pii_tags = pii_redactor.redact(raw_text)

            obj = {
                "id": f"REV-USER-{idx+1:05d}",
                "domain": "custom",
                "product_name": prod,
                "sku_or_module": "General",
                "batch_or_version": ver,
                "channel": "Upload CSV",
                "rating": rating,
                "raw_text": raw_text,
                "redacted_text": sanitized,
                "pii_detected": pii_tags,
                "ground_truth_label": gt_label
            }
            reviews.append(obj)
            if len(ground_truth) < 1000 and (idx % 5 == 0):
                ground_truth.append(obj)

        return reviews, ground_truth

dataset_manager = TelemetryDatasetManager()
