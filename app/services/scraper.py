import requests
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any, List
import json
import re
from urllib.parse import urljoin, urlparse
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebScraper:
    def __init__(self):
        self.session = self._create_session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def normalize_url(self, url: str) -> str:
        """Normalize URL by ensuring it has proper protocol"""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url.rstrip('/')

    def is_shopify_store(self, url: str, html_content: str = None) -> bool:
        """Check if the website is a Shopify store"""
        try:
            if not html_content:
                response = self.session.get(url, headers=self.headers, timeout=10)
                html_content = response.text

            # Multiple ways to detect Shopify
            shopify_indicators = [
                'Shopify.theme',
                'shopify_pay',
                'cdn.shopify.com',
                'myshopify.com',
                'Shopify.shop',
                'shopify-section',
                '/products.json'
            ]

            return any(indicator in html_content for indicator in shopify_indicators)
        except Exception as e:
            logger.error(f"Error checking if Shopify store: {e}")
            return False

    def get_page_content(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse page content"""
        try:
            response = self.session.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'lxml')
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def get_json_content(self, url: str) -> Optional[Dict[Any, Any]]:
        """Fetch JSON content from URL"""
        try:
            response = self.session.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            logger.error(f"Error fetching JSON from {url}: {e}")
            return None

    def get_products_json(self, base_url: str) -> Optional[Dict[Any, Any]]:
        """Fetch products.json from Shopify store"""
        products_url = urljoin(base_url, '/products.json')
        return self.get_json_content(products_url)

    def get_all_products_paginated(self, base_url: str) -> List[Dict[Any, Any]]:
        """Fetch all products with pagination support"""
        all_products = []
        page = 1
        limit = 50  # Shopify default limit

        while True:
            products_url = f"{base_url.rstrip('/')}/products.json?limit={limit}&page={page}"
            data = self.get_json_content(products_url)

            if not data or 'products' not in data or not data['products']:
                break

            all_products.extend(data['products'])

            if len(data['products']) < limit:
                break

            page += 1

        return all_products

    def extract_social_links(self, soup: BeautifulSoup, base_url: str) -> Dict[str, str]:
        """Extract social media links from the page"""
        social_handles = {}

        # Common social media patterns
        social_patterns = {
            'instagram': [r'instagram\.com/([^/\s\?&]+)', r'instagr\.am/([^/\s\?&]+)'],
            'facebook': [r'facebook\.com/([^/\s\?&]+)', r'fb\.com/([^/\s\?&]+)'],
            'twitter': [r'twitter\.com/([^/\s\?&]+)', r'x\.com/([^/\s\?&]+)'],
            'tiktok': [r'tiktok\.com/@?([^/\s\?&]+)'],
            'youtube': [r'youtube\.com/(?:c/|channel/|user/)?([^/\s\?&]+)', r'youtu\.be/([^/\s\?&]+)'],
            'linkedin': [r'linkedin\.com/(?:company/|in/)?([^/\s\?&]+)'],
            'pinterest': [r'pinterest\.com/([^/\s\?&]+)']
        }

        # Find all links
        links = soup.find_all('a', href=True)

        for link in links:
            href = link.get('href', '')

            for platform, patterns in social_patterns.items():
                for pattern in patterns:
                    match = re.search(pattern, href, re.IGNORECASE)
                    if match:
                        social_handles[platform] = href
                        break

        return social_handles

    def extract_contact_info(self, soup: BeautifulSoup) -> Dict[str, List[str]]:
        """Extract contact information from the page"""
        contact_info = {'emails': [], 'phones': [], 'addresses': []}

        text_content = soup.get_text()

        # Email patterns
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text_content)
        contact_info['emails'] = list(set(emails))

        # Phone patterns (various formats)
        phone_patterns = [
            r'\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}',  # US format
            r'\+?[0-9]{1,4}[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{3,4}[-.\s]?[0-9]{3,4}',  # International
            r'\([0-9]{3}\)\s?[0-9]{3}-?[0-9]{4}'  # (xxx) xxx-xxxx format
        ]

        phones = []
        for pattern in phone_patterns:
            phones.extend(re.findall(pattern, text_content))
        contact_info['phones'] = list(set([phone.strip() for phone in phones if len(phone.strip()) >= 10]))

        return contact_info

    def extract_policy_links(self, soup: BeautifulSoup, base_url: str) -> Dict[str, str]:
        """Extract policy page links"""
        policy_links = {}

        policy_keywords = {
            'privacy_policy': ['privacy', 'privacy policy', 'privacy-policy'],
            'return_policy': ['return', 'returns', 'return policy', 'return-policy'],
            'refund_policy': ['refund', 'refunds', 'refund policy', 'refund-policy'],
            'terms_of_service': ['terms', 'terms of service', 'terms-of-service', 'tos'],
            'shipping_policy': ['shipping', 'shipping policy', 'shipping-policy']
        }

        links = soup.find_all('a', href=True)

        for link in links:
            href = link.get('href', '')
            text = link.get_text().lower().strip()

            # Convert relative URLs to absolute
            if href.startswith('/'):
                href = urljoin(base_url, href)

            for policy_type, keywords in policy_keywords.items():
                if any(keyword in text or keyword in href.lower() for keyword in keywords):
                    policy_links[policy_type] = href
                    break

        return policy_links

    def extract_important_links(self, soup: BeautifulSoup, base_url: str) -> Dict[str, str]:
        """Extract important navigation links"""
        important_links = {}

        link_keywords = {
            'contact_us': ['contact', 'contact us', 'contact-us'],
            'about_us': ['about', 'about us', 'about-us', 'our story'],
            'blog': ['blog', 'news', 'journal'],
            'order_tracking': ['track', 'tracking', 'order tracking', 'track order'],
            'size_guide': ['size guide', 'size-guide', 'sizing'],
            'careers': ['careers', 'jobs', 'join us']
        }

        links = soup.find_all('a', href=True)

        for link in links:
            href = link.get('href', '')
            text = link.get_text().lower().strip()

            # Convert relative URLs to absolute
            if href.startswith('/'):
                href = urljoin(base_url, href)

            for link_type, keywords in link_keywords.items():
                if any(keyword in text or keyword in href.lower() for keyword in keywords):
                    important_links[link_type] = href
                    break

        return important_links

    def get_brand_name(self, soup: BeautifulSoup, url: str) -> str:
        """Extract brand name from various sources"""
        # Try title tag first
        title = soup.find('title')
        if title:
            title_text = title.get_text().strip()
            # Remove common suffixes
            brand_name = re.sub(r'\s*[-–|]\s*.*$', '', title_text)
            if brand_name:
                return brand_name

        # Try meta property="og:site_name"
        og_site_name = soup.find('meta', property='og:site_name')
        if og_site_name and og_site_name.get('content'):
            return og_site_name['content'].strip()

        # Try to extract from URL
        domain = urlparse(url).netloc
        if domain:
            brand_name = domain.replace('www.', '').split('.')[0]
            return brand_name.title()

        return "Unknown Brand"

    def close(self):
        """Close the session"""
        if self.session:
            self.session.close()