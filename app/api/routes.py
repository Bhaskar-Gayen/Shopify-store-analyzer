import logging

from fastapi import APIRouter, HTTPException, status, Depends

from app.models.schemas import (
    AnalyzeStoreRequest, BrandInsights, SuccessResponse
)
from app.services.data_extractor import DataExtractor
from app.services.compititor_analysis import CompetitorAnalyzer
from app.services.database_service import DatabaseService
from app.utils.helpers import validate_shopify_url

logger = logging.getLogger(__name__)
router = APIRouter()


# Dependency injection for services
def get_data_extractor() -> DataExtractor:
    return DataExtractor()


def get_competitor_analyzer() -> CompetitorAnalyzer:
    return CompetitorAnalyzer()


def get_database_service() -> DatabaseService:
    return DatabaseService()


@router.post("/analyze-store", response_model=SuccessResponse)
async def analyze_store(
        request: AnalyzeStoreRequest,
        save_to_db: bool = True,
        extractor: DataExtractor = Depends(get_data_extractor),
        db_service: DatabaseService = Depends(get_database_service)
):
    """
    Analyze a Shopify store and extract comprehensive brand insights

    **Parameters:**
    - website_url: The URL of the Shopify store to analyze
    - save_to_db: Whether to save results to database (default: True)

    **Returns:**
    - Complete brand insights including products, contact info, policies, etc.
    - Database ID if saved to database

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

        #  Save to database if requested
        analysis_id = None
        if save_to_db:
            try:
                analysis_id = db_service.save_brand_insights(insights)
                logger.info(f"Saved analysis to database with ID: {analysis_id}")
            except Exception as e:
                logger.error(f"Failed to save to database: {e}")
                # Continue without failing the request

        # Add database ID to response
        response_message = f"Successfully extracted insights from {insights.brand_name}"
        if analysis_id:
            response_message += f" (saved to DB with ID: {analysis_id})"

        return SuccessResponse(
            success=True,
            data=insights,
            message=response_message
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error analyzing store {website_url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred during store analysis"
        )


@router.post("/analyze-competitors")
async def analyze_competitors(
        request: AnalyzeStoreRequest,
        max_competitors: int = 3,
        save_to_db: bool = True,
        extractor: DataExtractor = Depends(get_data_extractor),
        competitor_analyzer: CompetitorAnalyzer = Depends(get_competitor_analyzer),
        db_service: DatabaseService = Depends(get_database_service)
):
    """
     Find and analyze competitors for a given brand

    **Parameters:**
    - website_url: The URL of the main store to find competitors for
    - max_competitors: Maximum number of competitors to analyze (default: 3)
    - save_to_db: Whether to save results to database (default: True)

    **Returns:**
    - Main brand analysis plus competitor insights and similarity scores
    - Database ID if saved to database

    **Note:** This operation may take 2-3 minutes as it analyzes multiple stores
    """
    try:
        website_url = str(request.website_url)
        logger.info(f"Starting competitor analysis for: {website_url}")

        # Validate URL accessibility
        if not validate_shopify_url(website_url):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Website not found or not accessible"
            )

        # Step 1: Analyze the main brand
        logger.info("Analyzing main brand...")
        main_insights = extractor.extract_complete_insights(website_url)

        if not main_insights.extraction_success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to analyze main brand"
            )

        # Step 2:  Analyze competitors
        logger.info(f"Finding and analyzing up to {max_competitors} competitors...")
        competitor_analysis = competitor_analyzer.analyze_competitors(main_insights, max_competitors)

        # Step 3:  Save to database if requested
        analysis_id = None
        if save_to_db:
            try:
                analysis_id = db_service.save_competitor_analysis(competitor_analysis)
                logger.info(f"Saved competitor analysis to database with ID: {analysis_id}")
            except Exception as e:
                logger.error(f"Failed to save competitor analysis to database: {e}")

        # Step 4: Generate summary
        summary = competitor_analyzer.get_competitor_summary(competitor_analysis)

        return {
            "success": True,
            "message": f"Found {len(competitor_analysis.competitors)} competitors for {main_insights.brand_name}",
            "database_id": analysis_id,
            "summary": summary,
            "detailed_analysis": competitor_analysis.dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in competitor analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during competitor analysis"
        )


@router.get("/analysis/{analysis_id}")
async def get_analysis(
        analysis_id: int,
        db_service: DatabaseService = Depends(get_database_service)
):
    """
     Retrieve a stored analysis by ID

    **Parameters:**
    - analysis_id: The database ID of the analysis to retrieve
    """
    try:
        analysis = db_service.get_brand_analysis(analysis_id)

        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Analysis with ID {analysis_id} not found"
            )

        return {
            "success": True,
            "data": analysis,
            "message": f"Retrieved analysis for {analysis['brand_name']}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving analysis {analysis_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the analysis"
        )


@router.get("/competitor-analysis/{analysis_id}")
async def get_competitor_analysis(
        analysis_id: int,
        db_service: DatabaseService = Depends(get_database_service)
):
    """
     Retrieve a stored competitor analysis by main analysis ID
    """
    try:
        competitor_analysis = db_service.get_competitor_analysis(analysis_id)

        if not competitor_analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Competitor analysis with ID {analysis_id} not found"
            )

        return {
            "success": True,
            "data": competitor_analysis,
            "message": f"Retrieved competitor analysis for {competitor_analysis['main_brand']['brand_name']}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving competitor analysis {analysis_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the competitor analysis"
        )


@router.get("/recent-analyses")
async def get_recent_analyses(
        limit: int = 10,
        db_service: DatabaseService = Depends(get_database_service)
):
    """
     Get list of recent store analyses

    **Parameters:**
    - limit: Maximum number of analyses to return (default: 10)
    """
    try:
        analyses = db_service.get_recent_analyses(limit)

        return {
            "success": True,
            "data": analyses,
            "total": len(analyses),
            "message": f"Retrieved {len(analyses)} recent analyses"
        }

    except Exception as e:
        logger.error(f"Error getting recent analyses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving recent analyses"
        )


@router.get("/statistics")
async def get_statistics(
        db_service: DatabaseService = Depends(get_database_service)
):
    """
     Get database statistics including total analyses, products, etc.
    """
    try:
        stats = db_service.get_analysis_statistics()

        return {
            "success": True,
            "data": stats,
            "message": "Database statistics retrieved successfully"
        }

    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving statistics"
        )


@router.get("/search")
async def search_analyses(
        brand_name: str = None,
        website_url: str = None,
        db_service: DatabaseService = Depends(get_database_service)
):
    """
     Search for analyses by brand name or website URL

    **Parameters:**
    - brand_name: Brand name to search for (partial match)
    - website_url: Website URL to search for (partial match)
    """
    try:
        if not brand_name and not website_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one search parameter (brand_name or website_url) is required"
            )

        analyses = db_service.search_analyses(brand_name, website_url)

        return {
            "success": True,
            "data": analyses,
            "total": len(analyses),
            "message": f"Found {len(analyses)} matching analyses"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching analyses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while searching analyses"
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
            "/analyze-competitors",
            "/analysis/{id}",
            "/competitor-analysis/{id}",
            "/recent-analyses",
            "/statistics",
            "/search",
            "/analyze-store/demo",
            "/health"
        ]
    }