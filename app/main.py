from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from app.models.schemas import ErrorResponse
from app.api.routes import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up...")
    try:
        from app.models.database import create_tables
        create_tables()
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    yield
    logger.info("Application shutting down...")

# Create FastAPI app with explicit docs configuration
app = FastAPI(
    title="Shopify Store Insights Fetcher",
    description="""
    ## A comprehensive API to extract insights from Shopify stores
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes with prefix
app.include_router(router, prefix="/api/v1", tags=["Store Analysis"])


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Shopify Store Insights Fetcher API",
        "version": "1.0.0",
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json"
        },
        "endpoints": {
            "analyze_store": "/api/v1/analyze-store",
            "analyze_competitors": "/api/v1/analyze-competitors",
            "get_analysis": "/api/v1/analysis/{id}",
            "recent_analyses": "/api/v1/recent-analyses",
            "statistics": "/api/v1/statistics",
            "search": "/api/v1/search",
            "demo": "/api/v1/analyze-store/demo",
            "health": "/api/v1/health"
        },
        "status": "active",
        "features": [
            "Store Analysis with Database Persistence",
            "Competitor Discovery and Analysis",
            "Advanced Search and Analytics",
            "Comprehensive Data Extraction"
        ]
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "version": "1.0.0",
        "service": "Shopify Store Insights Fetcher",
        "database": "Connected",
        "features": {
            "store_analysis": " Active",
            "competitor_analysis": " Active",
            "database_persistence": " Active",
            "search_analytics": " Active"
        }
    }


# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Shopify Store Insights Fetcher",
        version="1.0.0",
        description="Extract comprehensive insights from Shopify stores with competitor analysis and database persistence",
        routes=app.routes,
    )

    # Add custom info
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Global exception handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(
            error="Not Found",
            message="The requested resource was not found",
            status_code=404
        ).model_dump()
    )


@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            message="An internal server error occurred",
            status_code=500
        ).model_dump()
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="HTTP Error",
            message=exc.detail,
            status_code=exc.status_code
        ).model_dump()
    )




if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)