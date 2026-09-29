from datetime import datetime
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
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    themes = relationship("ThemeModel", back_populates="domain", cascade="all, delete-orphan")
    reviews = relationship("ReviewModel", back_populates="domain", cascade="all, delete-orphan")
    tickets = relationship("TicketModel", back_populates="domain", cascade="all, delete-orphan")

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
    created_at = Column(DateTime, default=datetime.utcnow)

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
    created_at = Column(DateTime, default=datetime.utcnow)

    domain = relationship("DomainModel", back_populates="reviews")

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
    created_at = Column(DateTime, default=datetime.utcnow)

    domain = relationship("DomainModel", back_populates="tickets")

class GovernanceModel(Base):
    __tablename__ = "model_governance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain_id = Column(String(64), index=True, nullable=False)
    model_architecture = Column(String(255), nullable=False)
    evaluation = Column(JSON, nullable=True)
    drift_results = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
