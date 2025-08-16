"""
Data models and schemas for the Shopify insights application
"""

from .schemas import (
    ProductModel,
    ContactDetails,
    SocialHandles,
    PolicyInfo,
    FAQ,
    ImportantLinks,
    BrandInsights,
    AnalyzeStoreRequest,
    ErrorResponse,
    SuccessResponse,
    CompetitorInfo,
    CompetitorAnalysis
)

__all__ = [
    "ProductModel",
    "ContactDetails",
    "SocialHandles",
    "PolicyInfo",
    "FAQ",
    "ImportantLinks",
    "BrandInsights",
    "AnalyzeStoreRequest",
    "ErrorResponse",
    "SuccessResponse",
    "CompetitorInfo",
    "CompetitorAnalysis"
]