from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DECIMAL, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
import json

from ..config import settings

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()


class StoreAnalysis(Base):
    """Main store analysis table"""
    __tablename__ = "store_analyses"

    id = Column(Integer, primary_key=True, index=True)
    brand_name = Column(String(255), nullable=False, index=True)
    website_url = Column(String(500), nullable=False, index=True)
    total_products = Column(Integer, default=0)
    extraction_success = Column(Boolean, default=False)
    extracted_at = Column(DateTime, default=datetime.utcnow)
    analysis_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    products = relationship("Product", back_populates="analysis", cascade="all, delete-orphan")
    contact_details = relationship("ContactDetail", back_populates="analysis", cascade="all, delete-orphan")
    social_handles = relationship("SocialHandle", back_populates="analysis", cascade="all, delete-orphan")
    policies = relationship("Policy", back_populates="analysis", cascade="all, delete-orphan")
    faqs = relationship("FAQ", back_populates="analysis", cascade="all, delete-orphan")
    important_links = relationship("ImportantLink", back_populates="analysis", cascade="all, delete-orphan")

    # Competitor relationships
    main_competitor_analyses = relationship("CompetitorAnalysis", foreign_keys="CompetitorAnalysis.main_analysis_id",
                                            back_populates="main_analysis", cascade="all, delete-orphan")
    competitor_analyses = relationship("CompetitorAnalysis", foreign_keys="CompetitorAnalysis.competitor_analysis_id",
                                       back_populates="competitor_analysis")

    def __repr__(self):
        return f"<StoreAnalysis(id={self.id}, brand_name='{self.brand_name}', website_url='{self.website_url}')>"


class Product(Base):
    """Products table"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("store_analyses.id"), nullable=False)
    product_id = Column(String(100))
    title = Column(String(500), nullable=False)
    handle = Column(String(255))
    description = Column(Text)
    price = Column(DECIMAL(10, 2))
    compare_at_price = Column(DECIMAL(10, 2))
    vendor = Column(String(255), index=True)
    product_type = Column(String(255), index=True)
    tags = Column(JSON)
    images = Column(JSON)
    url = Column(String(500))
    available = Column(Boolean, default=True)
    variants = Column(JSON)
    is_hero_product = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    analysis = relationship("StoreAnalysis", back_populates="products")

    def __repr__(self):
        return f"<Product(id={self.id}, title='{self.title}', price={self.price})>"


class ContactDetail(Base):
    """Contact details table"""
    __tablename__ = "contact_details"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("store_analyses.id"), nullable=False)
    emails = Column(JSON)
    phone_numbers = Column(JSON)
    address = Column(Text)
    contact_page_url = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    analysis = relationship("StoreAnalysis", back_populates="contact_details")

    def __repr__(self):
        return f"<ContactDetail(id={self.id}, analysis_id={self.analysis_id})>"


class SocialHandle(Base):
    """Social media handles table"""
    __tablename__ = "social_handles"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("store_analyses.id"), nullable=False)
    platform = Column(String(50), nullable=False, index=True)
    url = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    analysis = relationship("StoreAnalysis", back_populates="social_handles")

    def __repr__(self):
        return f"<SocialHandle(id={self.id}, platform='{self.platform}', url='{self.url}')>"


class Policy(Base):
    """Policies table"""
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("store_analyses.id"), nullable=False)
    policy_type = Column(String(100), nullable=False, index=True)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    analysis = relationship("StoreAnalysis", back_populates="policies")

    def __repr__(self):
        return f"<Policy(id={self.id}, policy_type='{self.policy_type}')>"


class FAQ(Base):
    """FAQs table"""
    __tablename__ = "faqs"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("store_analyses.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text)
    category = Column(String(100), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    analysis = relationship("StoreAnalysis", back_populates="faqs")

    def __repr__(self):
        return f"<FAQ(id={self.id}, question='{self.question[:50]}...')>"


class ImportantLink(Base):
    """Important links table"""
    __tablename__ = "important_links"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("store_analyses.id"), nullable=False)
    link_type = Column(String(100), nullable=False, index=True)
    url = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    analysis = relationship("StoreAnalysis", back_populates="important_links")

    def __repr__(self):
        return f"<ImportantLink(id={self.id}, link_type='{self.link_type}', url='{self.url}')>"


class CompetitorAnalysis(Base):
    """Competitor analysis linking table"""
    __tablename__ = "competitor_analyses"

    id = Column(Integer, primary_key=True, index=True)
    main_analysis_id = Column(Integer, ForeignKey("store_analyses.id"), nullable=False)
    competitor_brand_name = Column(String(255))
    competitor_website_url = Column(String(500))
    similarity_score = Column(DECIMAL(5, 3), index=True)
    competitor_analysis_id = Column(Integer, ForeignKey("store_analyses.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    main_analysis = relationship("StoreAnalysis", foreign_keys=[main_analysis_id],
                                 back_populates="main_competitor_analyses")
    competitor_analysis = relationship("StoreAnalysis", foreign_keys=[competitor_analysis_id],
                                       back_populates="competitor_analyses")

    def __repr__(self):
        return f"<CompetitorAnalysis(id={self.id}, main_id={self.main_analysis_id}, competitor='{self.competitor_brand_name}', score={self.similarity_score})>"


# Database utility functions
def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all database tables (use with caution)"""
    Base.metadata.drop_all(bind=engine)