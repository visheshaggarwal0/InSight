from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
    JSON,
    ForeignKey,
    Index
)
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.core.database import Base
from app.core.config import settings

class DomainModel(Base):
    __tablename__ = "domains"

    id = Column(String(64), primary_key=True)  # e.g., "d2c_cosmetics", "tech_saas", "custom"
    name = Column(String(255), nullable=False)
    category = Column(String(128), nullable=False)
    focus = Column(Text, nullable=True)
    review_count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    themes = relationship("ThemeModel", back_populates="domain", cascade="all, delete-orphan")
    reviews = relationship("ReviewModel", back_populates="domain", cascade="all, delete-orphan")
    tickets = relationship("TicketModel", back_populates="domain", cascade="all, delete-orphan")
    propositions = relationship("PropositionModel", back_populates="domain", cascade="all, delete-orphan")

class ThemeModel(Base):
    __tablename__ = "themes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain_id = Column(String(64), ForeignKey("domains.id", ondelete="CASCADE"), index=True, nullable=False)
    cluster_id = Column(Integer, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    severity = Column(String(32), nullable=False)  # CRITICAL, HIGH, MEDIUM, LOW
    review_count = Column(Integer, default=0)
    negative_rate = Column(Float, default=0.0)
    positive_rate = Column(Float, default=0.0)
    neutral_rate = Column(Float, default=0.0)
    keywords = Column(JSON, nullable=True)  # list of top keywords (c-TF-IDF)
    sample_verbatims = Column(JSON, nullable=True)  # list of representative review dicts
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    domain = relationship("DomainModel", back_populates="themes")

class ReviewModel(Base):
    __tablename__ = "reviews"

    id = Column(String(64), primary_key=True)  # e.g. "REV-00001"
    domain_id = Column(String(64), ForeignKey("domains.id", ondelete="CASCADE"), index=True, nullable=False)
    product_name = Column(String(255), nullable=True)
    sku_or_module = Column(String(128), nullable=True)
    batch_or_version = Column(String(64), index=True, nullable=True)
    channel = Column(String(64), nullable=True)
    rating = Column(Integer, default=3)
    raw_text = Column(Text, nullable=False)
    redacted_text = Column(Text, nullable=False)
    pii_detected = Column(JSON, default=list)
    ground_truth_label = Column(String(32), nullable=True)
    highlight_span = Column(JSON, nullable=True)
    sentiment_pred = Column(String(32), index=True, nullable=True)
    sentiment_confidence = Column(Float, default=0.0)
    cluster_id = Column(Integer, index=True, nullable=True)
    theme_title = Column(String(255), nullable=True)
    
    # 384-dimensional dense vector from all-MiniLM-L6-v2
    embedding = Column(Vector(settings.EMBEDDING_DIM), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    domain = relationship("DomainModel", back_populates="reviews")
    propositions = relationship("PropositionModel", back_populates="review", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_review_domain_cluster", "domain_id", "cluster_id"),
        Index("idx_review_domain_sentiment", "domain_id", "sentiment_pred"),
        Index("idx_review_domain_batch", "domain_id", "batch_or_version"),
    )

class TicketModel(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain_id = Column(String(64), ForeignKey("domains.id", ondelete="CASCADE"), index=True, nullable=False)
    cluster_id = Column(Integer, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    severity = Column(String(32), nullable=False)
    ticket_type = Column(String(128), nullable=True)
    affected_field = Column(String(128), nullable=True)
    affected_values = Column(JSON, default=list)
    incident_volume = Column(Integer, default=0)
    ticket_markdown = Column(Text, nullable=False)
    status = Column(String(32), default="OPEN")  # OPEN, IN_PROGRESS, RESOLVED
    jira_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    domain = relationship("DomainModel", back_populates="tickets")

class GovernanceModel(Base):
    __tablename__ = "model_governance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain_id = Column(String(64), index=True, nullable=False)
    model_architecture = Column(String(255), nullable=False)
    evaluation = Column(JSON, nullable=True)
    drift_results = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PropositionModel(Base):
    """First-class SQL persistence for atomic 4-way propositions with 384D pgvector embeddings."""
    __tablename__ = "propositions"

    id = Column(String(128), primary_key=True)  # Deterministic: "{review_id}::P{sentence_idx:03d}"
    review_id = Column(String(64), ForeignKey("reviews.id", ondelete="CASCADE"), index=True, nullable=False)
    domain_id = Column(String(64), ForeignKey("domains.id", ondelete="CASCADE"), index=True, nullable=False)
    sentence_idx = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    char_start = Column(Integer, nullable=False)
    char_end = Column(Integer, nullable=False)
    intent = Column(String(32), index=True, nullable=False)  # COMPLAINT | RECOMMENDATION | PRAISE | NOISE
    severity = Column(String(16), default="P3", index=True, nullable=False)  # P0 | P1 | P2 | P3
    confidence = Column(Float, default=0.80)
    is_actionable = Column(Integer, default=1, index=True)
    embedding = Column(Vector(settings.EMBEDDING_DIM), nullable=True)
    detected_marker = Column(String(64), nullable=True)
    extra_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    review = relationship("ReviewModel", back_populates="propositions")
    domain = relationship("DomainModel", back_populates="propositions")

    __table_args__ = (
        Index("idx_proposition_domain_intent", "domain_id", "intent"),
        Index("idx_proposition_intent_severity", "intent", "severity"),
        Index("idx_proposition_review", "review_id"),
    )

    def to_dict(self, include_embedding: bool = False) -> dict:
        d = {
            "id": self.id,
            "proposition_id": self.id,
            "review_id": self.review_id,
            "domain_id": self.domain_id,
            "sentence_idx": self.sentence_idx,
            "text": self.text,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "intent": self.intent,
            "classification": self.intent,  # backward compatibility alias
            "severity": self.severity,
            "severity_hint": self.severity,
            "confidence": self.confidence,
            "is_actionable": bool(self.is_actionable),
            "detected_marker": self.detected_marker,
            "extra_metadata": self.extra_metadata or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_embedding and self.embedding is not None:
            if hasattr(self.embedding, "tolist"):
                d["embedding"] = self.embedding.tolist()
            elif isinstance(self.embedding, (list, tuple)):
                d["embedding"] = list(self.embedding)
        return d
