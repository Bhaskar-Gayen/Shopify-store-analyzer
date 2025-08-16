# Shopify Store Insights Fetcher

A comprehensive FastAPI application that extracts detailed insights from Shopify stores without using the official Shopify API. This tool scrapes and analyzes Shopify websites to provide structured data about products, brand information, policies, and more.

## Features

### Mandatory Features ✅
- **Product Catalog**: Complete list of all products in the store
- **Hero Products**: Featured products from the homepage
- **Contact Details**: Email addresses, phone numbers, and contact information
- **Social Media Handles**: Instagram, Facebook, Twitter, TikTok, etc.
- **Policies**: Privacy policy, return/refund policies, terms of service
- **FAQs**: Frequently asked questions and answers
- **Brand Context**: About us and brand story information
- **Important Links**: Order tracking, contact us, blog, size guide, etc.

### Technical Features
- **Robust Error Handling**: Comprehensive error responses with appropriate HTTP status codes
- **Data Validation**: Strong Pydantic models for data consistency
- **Retry Logic**: Automatic retry on network failures
- **Clean Architecture**: Modular design following SOLID principles
- **Async Support**: Efficient async operations where possible

## API Endpoints

### Main Endpoint
```
POST /api/v1/analyze-store
```

**Request Body:**
```json
{
    "website_url": "https://memy.co.in"
}
```

**Response:**
```json
{
    "success": true,
    "message": "Successfully extracted insights from Memy",
    "data": {
        "brand_name": "Memy",
        "website_url": "https://memy.co.in",
        "product_catalog": [...],
        "hero_products": [...],
        "contact_details": {...},
        "social_handles": {...},
        "policies": {...},
        "faqs": [...],
        "brand_context": "...",
        "important_links": {...},
        "total_products": 150,
        "extracted_at": "2025-01-XX...",
        "extraction_success": true,
        "errors": []
    }
}
```

### Error Responses
- **400**: Invalid URL format
- **401**: Website not found or not accessible
- **500**: Internal server error during extraction

## Quick Start

### 1. Setup Environment
```bash
# Create virtual environment
python -m venv shopify_env
source shopify_env/bin/activate  # Windows: shopify_env\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration
Create a `.env` file (optional):
```env
DEBUG=true
REQUEST_TIMEOUT=30
MAX_RETRIES=3
LOG_LEVEL=INFO
```

### 3. Run the Application
```bash
# Development
uvicorn app.main:app --reload --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 4. Access API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
shopify_insights/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── scraper.py          # Web scraping service
│   │   └── data_extractor.py   # Data extraction logic
│   ├── utils/
│   │   ├── __init__.py
│   │   └── helpers.py          # Utility functions
│   └── api/
│       ├── __init__.py
│       └── routes.py           # API endpoints
├── requirements.txt
├── config.py                   # Configuration settings
└── README.md
```

## Testing

### Test with Sample Stores
```bash
# Using curl
curl -X POST "http://localhost:8000/api/v1/analyze-store" \
     -H "Content-Type: application/json" \
     -d '{"website_url": "https://memy.co.in"}'

# Using Python requests
import requests
response = requests.post(
    "http://localhost:8000/api/v1/analyze-store",
    json={"website_url": "https://hairoriginals.com"}
)
print(response.json())
```

### Sample Shopify Stores for Testing
- https://memy.co.in
- https://hairoriginals.com
- https://colourpop.com
- https://allbirds.com
- https://bombas.com

## Key Components

### 1. Web Scraper (`app/services/scraper.py`)
- Handles HTTP requests with retry logic
- Detects Shopify stores
- Extracts various data types (JSON, HTML, links)
- Implements robust error handling

### 2. Data Extractor (`app/services/data_extractor.py`)
- Processes raw scraped data
- Implements business logic for each data type
- Handles edge cases and data validation
- Structures data according to Pydantic models

### 3. API Layer (`app/api/routes.py`)
- RESTful endpoint implementation
- Request/response validation
- Error handling and logging
- Dependencies injection

### 4. Models (`app/models/schemas.py`)
- Pydantic models for data validation
- Type safety and serialization
- Request/response schemas

## Advanced Features

### Shopify Detection
The application automatically detects Shopify stores by looking for:
- `Shopify.theme` in page source
- `cdn.shopify.com` references
- `/products.json` endpoint availability
- Shopify-specific CSS classes and IDs

### Product Extraction
- Uses `/products.json` endpoint for complete catalog
- Handles pagination automatically
- Extracts detailed product information including variants
- Matches homepage products with catalog data

### Robust Error Handling
- Network timeouts and retries
- Invalid URL handling
- Missing content graceful degradation
- Detailed error logging and reporting

## Configuration Options

Key configuration parameters in `config.py`:
- `REQUEST_TIMEOUT`: HTTP request timeout (default: 30s)
- `MAX_RETRIES`: Number of retry attempts (default: 3)
- `MAX_PRODUCTS`: Maximum products to extract (default: 1000)
- `MAX_FAQS`: Maximum FAQs to extract (default: 10)

## Deployment

### Using Docker (Recommended)
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Using uvicorn
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Monitoring and Logging

The application includes comprehensive logging:
- Request/response logging
- Error tracking and categorization
- Performance metrics
- Extraction success rates

## Bonus Features (Future Implementation)

### 1. Competitor Analysis
- Automatic competitor discovery
- Comparative analysis
- Market insights

### 2. Database Persistence
- MySQL integration
- Historical data tracking
- Analytics and reporting

### 3. LLM Enhancement
- Content summarization
- FAQ categorization
- Brand sentiment analysis

## Contributing

1. Follow the existing code structure
2. Add proper error handling
3. Include comprehensive logging
4. Write clean, documented code
5. Test with multiple Shopify stores

## License

This project is for educational and demonstration purposes. Please ensure compliance with website terms of service when scraping.

## Support

For issues and questions:
1. Check the API documentation at `/docs`
2. Review the logs for detailed error information
3. Test with known working Shopify stores
4. Ensure proper internet connectivity

## Performance Tips

1. **Caching**: Implement Redis caching for repeated requests
2. **Rate Limiting**: Add rate limiting to prevent abuse
3. **Async Processing**: Use background tasks for large stores
4. **Database**: Use database persistence for better performance
5. **CDN**: Consider CDN for static assets and responses