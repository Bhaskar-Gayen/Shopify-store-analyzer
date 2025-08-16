import requests
import re
import logging
from typing import List, Dict, Optional, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote_plus
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import time

from app.models.schemas import BrandInsights, CompetitorInfo, CompetitorAnalysis
from app.services.data_extractor import DataExtractor
from app.utils.helpers import extract_domain, clean_text

logger = logging.getLogger(__name__)


class CompetitorAnalyzer:
    def __init__(self):
        self.data_extractor = DataExtractor()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def analyze_competitors(self, main_brand: BrandInsights, max_competitors: int = 3) -> CompetitorAnalysis:
        """
        Analyze competitors for a given brand

        Args:
            main_brand: The main brand insights
            max_competitors: Maximum number of competitors to analyze

        Returns:
            CompetitorAnalysis with main brand and competitor data
        """
        logger.info(f"Starting competitor analysis for {main_brand.brand_name}")

        try:
            # Step 1: Find competitor URLs using multiple strategies
            competitor_urls = self._find_competitors(main_brand, max_competitors)

            # Step 2: Analyze each competitor
            competitors = []
            for url in competitor_urls:
                try:
                    logger.info(f"Analyzing competitor: {url}")
                    competitor_insights = self.data_extractor.extract_complete_insights(url)

                    if competitor_insights.extraction_success:
                        similarity_score = self._calculate_similarity(main_brand, competitor_insights)

                        competitor_info = CompetitorInfo(
                            brand_name=competitor_insights.brand_name,
                            website_url=url,
                            similarity_score=similarity_score,
                            insights=competitor_insights
                        )
                        competitors.append(competitor_info)

                        # Be nice to servers
                        time.sleep(2)
                    else:
                        logger.warning(f"Failed to extract insights from competitor: {url}")

                except Exception as e:
                    logger.error(f"Error analyzing competitor {url}: {e}")
                    continue

            return CompetitorAnalysis(
                main_brand=main_brand,
                competitors=competitors
            )

        except Exception as e:
            logger.error(f"Error in competitor analysis: {e}")
            return CompetitorAnalysis(
                main_brand=main_brand,
                competitors=[]
            )

    def _find_competitors(self, main_brand: BrandInsights, max_competitors: int) -> List[str]:
        """Find competitor URLs using multiple strategies"""
        competitor_urls = set()

        # Strategy 1: Google search-based discovery
        google_competitors = self._find_competitors_via_google(main_brand)
        competitor_urls.update(google_competitors[:max_competitors])

        # Strategy 2: Similar domain discovery
        if len(competitor_urls) < max_competitors:
            domain_competitors = self._find_similar_domains(main_brand)
            competitor_urls.update(domain_competitors)

        # Strategy 3: Industry keyword search
        if len(competitor_urls) < max_competitors:
            keyword_competitors = self._find_competitors_by_keywords(main_brand)
            competitor_urls.update(keyword_competitors)

        # Remove main brand URL and limit results
        main_domain = extract_domain(main_brand.website_url)
        competitor_urls = [url for url in competitor_urls
                           if extract_domain(url) != main_domain]

        return list(competitor_urls)[:max_competitors]

    def _find_competitors_via_google(self, main_brand: BrandInsights) -> List[str]:
        """Find competitors using Google search"""
        competitors = []

        try:
            # Create search queries
            search_queries = self._generate_search_queries(main_brand)

            for query in search_queries[:2]:  # Limit to 2 searches
                logger.info(f"Searching Google for: {query}")
                urls = self._google_search(query)
                competitors.extend(urls)
                time.sleep(1)  # Rate limiting

        except Exception as e:
            logger.error(f"Error in Google search: {e}")

        return competitors

    def _generate_search_queries(self, main_brand: BrandInsights) -> List[str]:
        """Generate search queries based on brand information"""
        queries = []

        # Extract product types/categories
        product_types = set()
        for product in main_brand.product_catalog[:10]:  # Sample first 10 products
            if product.product_type:
                product_types.add(product.product_type.lower())

        # Query 1: "similar to [brand]"
        queries.append(f"similar to {main_brand.brand_name} online store")

        # Query 2: "[product_type] brands like [brand]"
        if product_types:
            main_type = list(product_types)[0]
            queries.append(f"{main_type} brands like {main_brand.brand_name}")

        # Query 3: "competitors of [brand]"
        queries.append(f"competitors of {main_brand.brand_name}")

        # Query 4: "[industry] ecommerce stores"
        if product_types:
            queries.append(f"{list(product_types)[0]} ecommerce stores")

        return queries

    def _google_search(self, query: str, num_results: int = 5) -> List[str]:
        """Perform Google search and extract Shopify store URLs"""
        urls = []

        try:
            # Simple Google search (in production, use Google Custom Search API)
            search_url = f"https://www.google.com/search?q={quote_plus(query)}&num={num_results}"

            response = self.session.get(search_url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract URLs from search results
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if href and '/url?q=' in href:
                    # Extract actual URL from Google's redirect
                    actual_url = href.split('/url?q=')[1].split('&')[0]

                    # Filter for potential ecommerce sites
                    if self._is_potential_ecommerce_site(actual_url):
                        urls.append(actual_url)

        except Exception as e:
            logger.error(f"Error in Google search for '{query}': {e}")

        return urls[:num_results]

    def _find_similar_domains(self, main_brand: BrandInsights) -> List[str]:
        """Find similar domains using domain analysis"""
        similar_urls = []

        try:
            main_domain = extract_domain(main_brand.website_url)

            # Strategy: Look for common ecommerce patterns
            domain_variations = [
                f"shop{main_brand.brand_name.lower()}.com",
                f"{main_brand.brand_name.lower()}store.com",
                f"buy{main_brand.brand_name.lower()}.com"
            ]

            # Test if variations exist and are Shopify stores
            for domain in domain_variations:
                try:
                    test_url = f"https://{domain}"
                    response = self.session.head(test_url, timeout=5)
                    if response.status_code == 200:
                        # Quick check if it might be a Shopify store
                        if self.data_extractor.scraper.is_shopify_store(test_url):
                            similar_urls.append(test_url)
                except:
                    continue

        except Exception as e:
            logger.error(f"Error finding similar domains: {e}")

        return similar_urls

    def _find_competitors_by_keywords(self, main_brand: BrandInsights) -> List[str]:
        """Find competitors using product keywords and categories"""
        competitors = []

        try:
            # Extract keywords from products
            keywords = set()
            for product in main_brand.product_catalog[:20]:
                if product.tags:
                    keywords.update([tag.lower() for tag in product.tags])
                if product.product_type:
                    keywords.add(product.product_type.lower())

            # Search for stores with similar keywords
            for keyword in list(keywords)[:3]:  # Limit to top 3 keywords
                query = f"{keyword} shopify store"
                keyword_competitors = self._google_search(query, 3)
                competitors.extend(keyword_competitors)
                time.sleep(1)

        except Exception as e:
            logger.error(f"Error finding competitors by keywords: {e}")

        return competitors

    def _is_potential_ecommerce_site(self, url: str) -> bool:
        """Check if URL is likely an ecommerce site"""
        if not url.startswith(('http://', 'https://')):
            return False

        # Filter out non-ecommerce domains
        exclude_domains = [
            'google.com', 'facebook.com', 'instagram.com', 'twitter.com',
            'youtube.com', 'linkedin.com', 'pinterest.com', 'amazon.com',
            'ebay.com', 'wikipedia.org', 'reddit.com'
        ]

        domain = extract_domain(url)
        if any(excluded in domain for excluded in exclude_domains):
            return False

        # Look for ecommerce indicators in URL
        ecommerce_indicators = [
            'shop', 'store', 'buy', 'ecommerce', 'retail', 'fashion',
            'beauty', 'cosmetics', 'clothing', 'apparel'
        ]

        return any(indicator in url.lower() for indicator in ecommerce_indicators)

    def _calculate_similarity(self, main_brand: BrandInsights, competitor: BrandInsights) -> float:
        """Calculate similarity score between main brand and competitor"""
        try:
            similarity_score = 0.0

            # Product category similarity (40% weight)
            main_categories = set()
            competitor_categories = set()

            for product in main_brand.product_catalog[:50]:
                if product.product_type:
                    main_categories.add(product.product_type.lower())
                main_categories.update([tag.lower() for tag in product.tags])

            for product in competitor.product_catalog[:50]:
                if product.product_type:
                    competitor_categories.add(product.product_type.lower())
                competitor_categories.update([tag.lower() for tag in product.tags])

            if main_categories and competitor_categories:
                category_overlap = len(main_categories.intersection(competitor_categories))
                category_union = len(main_categories.union(competitor_categories))
                category_similarity = category_overlap / category_union if category_union > 0 else 0
                similarity_score += category_similarity * 0.4

            # Price range similarity (30% weight)
            main_prices = [p.price for p in main_brand.product_catalog if p.price]
            competitor_prices = [p.price for p in competitor.product_catalog if p.price]

            if main_prices and competitor_prices:
                main_avg = sum(main_prices) / len(main_prices)
                competitor_avg = sum(competitor_prices) / len(competitor_prices)
                price_diff = abs(main_avg - competitor_avg) / max(main_avg, competitor_avg)
                price_similarity = max(0, 1 - price_diff)
                similarity_score += price_similarity * 0.3

            # Product count similarity (20% weight)
            main_count = len(main_brand.product_catalog)
            competitor_count = len(competitor.product_catalog)

            if main_count > 0 and competitor_count > 0:
                count_ratio = min(main_count, competitor_count) / max(main_count, competitor_count)
                similarity_score += count_ratio * 0.2

            # Social presence similarity (10% weight)
            main_social = len([v for v in main_brand.social_handles.dict().values() if v])
            competitor_social = len([v for v in competitor.social_handles.dict().values() if v])

            if main_social > 0 or competitor_social > 0:
                social_similarity = min(main_social, competitor_social) / max(main_social, competitor_social, 1)
                similarity_score += social_similarity * 0.1

            return round(similarity_score, 3)

        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0

    def get_competitor_summary(self, analysis: CompetitorAnalysis) -> Dict:
        """Generate a summary of competitor analysis"""
        try:
            summary = {
                "main_brand": {
                    "name": analysis.main_brand.brand_name,
                    "total_products": analysis.main_brand.total_products,
                    "website": analysis.main_brand.website_url
                },
                "competitors_found": len(analysis.competitors),
                "competitors": []
            }

            for competitor in analysis.competitors:
                if competitor.insights:
                    comp_summary = {
                        "name": competitor.brand_name,
                        "website": competitor.website_url,
                        "similarity_score": competitor.similarity_score,
                        "total_products": competitor.insights.total_products,
                        "price_range": self._get_price_range(competitor.insights),
                        "main_categories": self._get_main_categories(competitor.insights)
                    }
                    summary["competitors"].append(comp_summary)

            return summary

        except Exception as e:
            logger.error(f"Error generating competitor summary: {e}")
            return {"error": str(e)}

    def _get_price_range(self, insights: BrandInsights) -> Dict:
        """Get price range for a brand"""
        prices = [p.price for p in insights.product_catalog if p.price and p.price > 0]
        if prices:
            return {
                "min": round(min(prices), 2),
                "max": round(max(prices), 2),
                "avg": round(sum(prices) / len(prices), 2)
            }
        return {"min": 0, "max": 0, "avg": 0}

    def _get_main_categories(self, insights: BrandInsights) -> List[str]:
        """Get main product categories for a brand"""
        categories = {}
        for product in insights.product_catalog:
            if product.product_type:
                categories[product.product_type] = categories.get(product.product_type, 0) + 1

        # Return top 3 categories
        sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        return [cat[0] for cat in sorted_categories[:3]]