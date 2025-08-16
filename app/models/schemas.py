from pydantic import BaseModel, HttpUrl, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class SocialPlatform(str, Enum):
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    LINKEDIN = "linkedin"
    PINTEREST = "pinterest"


class ProductModel(BaseModel):
    id: Optional[str] = None
    title: str
    handle: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    compare_at_price: Optional[float] = None
    vendor: Optional[str] = None
    product_type: Optional[str] = None
    tags: List[str] = []
    images: List[str] = []
    url: Optional[str] = None
    available: Optional[bool] = None
    variants: List[Dict[str, Any]] = []


class ContactDetails(BaseModel):
    emails: List[str] = []
    phone_numbers: List[str] = []
    address: Optional[str] = None
    contact_page_url: Optional[str] = None


class SocialHandles(BaseModel):
    instagram: Optional[str] = None
    facebook: Optional[str] = None
    twitter: Optional[str] = None
    tiktok: Optional[str] = None
    youtube: Optional[str] = None
    linkedin: Optional[str] = None
    pinterest: Optional[str] = None


class PolicyInfo(BaseModel):
    privacy_policy: Optional[str] = None
    return_policy: Optional[str] = None
    refund_policy: Optional[str] = None
    terms_of_service: Optional[str] = None
    shipping_policy: Optional[str] = None


class FAQ(BaseModel):
    question: str
    answer: str
    category: Optional[str] = None


class ImportantLinks(BaseModel):
    order_tracking: Optional[str] = None
    contact_us: Optional[str] = None
    blog: Optional[str] = None
    size_guide: Optional[str] = None
    careers: Optional[str] = None
    about_us: Optional[str] = None


class BrandInsights(BaseModel):
    brand_name: str
    website_url: str
    product_catalog: List[ProductModel] = []
    hero_products: List[ProductModel] = []
    contact_details: ContactDetails
    social_handles: SocialHandles
    policies: PolicyInfo
    faqs: List[FAQ] = []
    brand_context: Optional[str] = None
    important_links: ImportantLinks
    total_products: int = 0
    extracted_at: datetime = Field(default_factory=datetime.now)
    extraction_success: bool = True
    errors: List[str] = []


class AnalyzeStoreRequest(BaseModel):
    website_url: HttpUrl

    @validator('website_url')
    def validate_url(cls, v):
        url_str = str(v)
        if not any(shopify_indicator in url_str.lower() for shopify_indicator in ['.myshopify.com', 'shopify']):
            # Allow any URL, we'll detect Shopify in the scraper
            pass
        return v


class ErrorResponse(BaseModel):
    error: str
    message: str
    status_code: int
    timestamp: datetime = Field(default_factory=datetime.now)


class SuccessResponse(BaseModel):
    success: bool = True
    data: BrandInsights
    message: str = "Store insights extracted successfully"


# Bonus: Competitor Analysis Models
class CompetitorInfo(BaseModel):
    brand_name: str
    website_url: str
    similarity_score: Optional[float] = None
    insights: Optional[BrandInsights] = None


class CompetitorAnalysis(BaseModel):
    main_brand: BrandInsights
    competitors: List[CompetitorInfo] = []
    analysis_date: datetime = Field(default_factory=datetime.now)