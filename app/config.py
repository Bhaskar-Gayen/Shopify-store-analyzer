import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    # API Configuration
    API_TITLE = "Shopify Store Insights Fetcher"
    API_VERSION = "1.0.0"
    API_DESCRIPTION = "A robust API to extract comprehensive insights from Shopify stores"

    # Server Configuration
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 8000))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    # Request Configuration
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 30))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
    RETRY_DELAY = float(os.getenv("RETRY_DELAY", 1.0))

    # Content Limits
    MAX_PRODUCTS = int(os.getenv("MAX_PRODUCTS", 1000))
    MAX_FAQS = int(os.getenv("MAX_FAQS", 10))
    MAX_HERO_PRODUCTS = int(os.getenv("MAX_HERO_PRODUCTS", 6))
    MAX_POLICY_LENGTH = int(os.getenv("MAX_POLICY_LENGTH", 1000))
    MAX_BRAND_CONTEXT_LENGTH = int(os.getenv("MAX_BRAND_CONTEXT_LENGTH", 500))

    # Database Configuration (for bonus features)
    DATABASE_URL = os.getenv("DATABASE_URL", "mysql://user:password@localhost/shopify_insights")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "shopify_insights")

    # LLM Configuration (Optional)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    USE_LLM_ENHANCEMENT = os.getenv("USE_LLM_ENHANCEMENT", "false").lower() == "true"
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "shopify_insights.log")

    # Security Configuration
    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    API_KEY = os.getenv("API_KEY", "")  # Optional API key for authentication

    # Shopify Specific
    SHOPIFY_INDICATORS = [
        "Shopify.theme",
        "shopify_pay",
        "cdn.shopify.com",
        "myshopify.com",
        "Shopify.shop",
        "shopify-section"
    ]

    # Common Shopify Paths
    SHOPIFY_PATHS = {
        "products": "/products.json",
        "collections": "/collections.json",
        "policies": ["/policies/privacy-policy", "/policies/refund-policy", "/policies/terms-of-service"]
    }

    # User Agent String
    USER_AGENT = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )


# Create settings instance
settings = Settings()


# Environment check
def get_environment():
    """Get current environment"""
    return os.getenv("ENVIRONMENT", "development")


def is_production():
    """Check if running in production"""
    return get_environment().lower() == "production"


def is_development():
    """Check if running in development"""
    return get_environment().lower() == "development"