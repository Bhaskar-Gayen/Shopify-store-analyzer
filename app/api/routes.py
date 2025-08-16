import logging

from fastapi import APIRouter, HTTPException, status, Depends

from app.models.schemas import (
    AnalyzeStoreRequest, BrandInsights, SuccessResponse
)
from app.services.data_extractor import DataExtractor
from app.utils.helpers import validate_shopify_url

logger = logging.getLogger(__name__)
router = APIRouter()


# Dependency injection for DataExtractor
def get_data_extractor() -> DataExtractor:
    return DataExtractor()


@router.post("/analyze-store", response_model=SuccessResponse)
async def analyze_store(
        request: AnalyzeStoreRequest,
        extractor: DataExtractor = Depends(get_data_extractor)
):
    """
    Analyze a Shopify store and extract comprehensive brand insights

    **Parameters:**
    - website_url: The URL of the Shopify store to analyze

    **Returns:**
    - Complete brand insights including products, contact info, policies, etc.

    **Error Codes:**
    - 400: Invalid URL or not a valid website
    - 401: Website not found or not accessible
    - 500: Internal server error during extraction
    """
    try:
        website_url = str(request.website_url)
        logger.info(f"Starting analysis for store: {website_url}")

        # Validate URL accessibility
        if not validate_shopify_url(website_url):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Website not found or not accessible"
            )

        # Extract insights
        insights = extractor.extract_complete_insights(website_url)

        # Check if extraction was successful
        if not insights.extraction_success:
            error_message = "; ".join(insights.errors) if insights.errors else "Unknown extraction error"
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Extraction failed: {error_message}"
            )

        logger.info(f"Successfully analyzed store: {website_url}")
        logger.info(f"Extracted {insights.total_products} products, {len(insights.faqs)} FAQs")

        return SuccessResponse(
            success=True,
            data=insights,
            message=f"Successfully extracted insights from {insights.brand_name}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error analyzing store {website_url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred during store analysis"
        )


@router.get("/analyze-store/demo")
async def demo_analysis():
    """
    Demo endpoint with a sample analysis result
    """
    from app.models.schemas import ContactDetails, SocialHandles, PolicyInfo, ImportantLinks

    demo_insights = BrandInsights(
        brand_name="Demo Store",
        website_url="https://demo-store.myshopify.com",
        product_catalog=[],
        hero_products=[],
        contact_details=ContactDetails(
            emails=["support@demo-store.com"],
            phone_numbers=["+1-555-123-4567"]
        ),
        social_handles=SocialHandles(
            instagram="https://instagram.com/demostore",
            facebook="https://facebook.com/demostore"
        ),
        policies=PolicyInfo(
            privacy_policy="Demo privacy policy content...",
            return_policy="Demo return policy content..."
        ),
        faqs=[],
        brand_context="Demo brand context...",
        important_links=ImportantLinks(),
        total_products=0,
        extraction_success=True
    )

    return SuccessResponse(
        success=True,
        data=demo_insights,
        message="Demo analysis result"
    )


@router.get("/health")
async def health_check():
    """Health check for the API routes"""
    return {
        "status": "healthy",
        "service": "Shopify Store Analysis API",
        "endpoints_available": [
            "/analyze-store",
            "/analyze-store/demo",
            "/health"
        ]
    }


