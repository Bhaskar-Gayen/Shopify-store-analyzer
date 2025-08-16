from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import re
import logging
from urllib.parse import urljoin

from app.models.schemas import (
    ProductModel, ContactDetails, SocialHandles, PolicyInfo,
    FAQ, ImportantLinks, BrandInsights
)
from app.services.scraper import WebScraper

logger = logging.getLogger(__name__)


class DataExtractor:
    def __init__(self):
        self.scraper = WebScraper()

    def extract_products_from_json(self, products_data: List[Dict[Any, Any]], base_url: str) -> List[ProductModel]:
        """Extract products from Shopify products.json data"""
        products = []

        for product_data in products_data:
            try:
                # Extract images
                images = []
                if 'images' in product_data:
                    images = [img.get('src', '') for img in product_data['images'] if img.get('src')]

                # Extract tags
                tags = []
                if 'tags' in product_data and isinstance(product_data['tags'], str):
                    tags = [tag.strip() for tag in product_data['tags'].split(',')]
                elif 'tags' in product_data and isinstance(product_data['tags'], list):
                    tags = product_data['tags']

                # Extract variants
                variants = product_data.get('variants', [])

                # Get price from first available variant
                price = None
                available = False
                if variants:
                    first_variant = variants[0]
                    price = float(first_variant.get('price', 0))
                    available = first_variant.get('available', False)

                product = ProductModel(
                    id=str(product_data.get('id', '')),
                    title=product_data.get('title', ''),
                    handle=product_data.get('handle', ''),
                    description=self._clean_html(product_data.get('body_html', '')),
                    price=price,
                    compare_at_price=float(variants[0].get('compare_at_price') or 0) if variants and variants[0].get(
                        'compare_at_price') else None,
                    vendor=product_data.get('vendor', ''),
                    product_type=product_data.get('product_type', ''),
                    tags=tags,
                    images=images,
                    url=urljoin(base_url, f'/products/{product_data.get("handle", "")}'),
                    available=available,
                    variants=variants
                )
                products.append(product)

            except Exception as e:
                logger.error(f"Error processing product {product_data.get('id', 'unknown')}: {e}")
                continue

        return products

    def extract_hero_products(self, soup: BeautifulSoup, all_products: List[ProductModel], base_url: str) -> List[
        ProductModel]:
        """Extract hero/featured products from homepage"""
        hero_products = []

        # Look for product links on homepage
        product_links = []

        # Common selectors for product links on Shopify homepage
        selectors = [
            'a[href*="/products/"]',
            '.product-item a',
            '.featured-product a',
            '.hero-product a',
            '.product-card a'
        ]

        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href', '')
                if '/products/' in href:
                    if href.startswith('/'):
                        href = urljoin(base_url, href)
                    product_links.append(href)

        # Remove duplicates
        product_links = list(set(product_links))

        # Match with products from catalog
        for product in all_products[:10]:  # Limit to first 10 to avoid too many hero products
            if product.url in product_links:
                hero_products.append(product)

        return hero_products[:6]  # Return max 6 hero products

    def extract_contact_details(self, soup: BeautifulSoup, base_url: str) -> ContactDetails:
        """Extract contact details from the page"""
        contact_info = self.scraper.extract_contact_info(soup)

        # Try to find contact page
        contact_links = self.scraper.extract_important_links(soup, base_url)
        contact_page_url = contact_links.get('contact_us')

        # If we found a contact page, scrape it for more info
        if contact_page_url:
            contact_soup = self.scraper.get_page_content(contact_page_url)
            if contact_soup:
                additional_contact = self.scraper.extract_contact_info(contact_soup)
                contact_info['emails'].extend(additional_contact['emails'])
                contact_info['phones'].extend(additional_contact['phones'])

        return ContactDetails(
            emails=list(set(contact_info['emails'])),
            phone_numbers=list(set(contact_info['phones'])),
            contact_page_url=contact_page_url
        )

    def extract_social_handles(self, soup: BeautifulSoup, base_url: str) -> SocialHandles:
        """Extract social media handles"""
        social_links = self.scraper.extract_social_links(soup, base_url)

        return SocialHandles(
            instagram=social_links.get('instagram'),
            facebook=social_links.get('facebook'),
            twitter=social_links.get('twitter'),
            tiktok=social_links.get('tiktok'),
            youtube=social_links.get('youtube'),
            linkedin=social_links.get('linkedin'),
            pinterest=social_links.get('pinterest')
        )

    def extract_policies(self, soup: BeautifulSoup, base_url: str) -> PolicyInfo:
        """Extract policy information"""
        policy_links = self.scraper.extract_policy_links(soup, base_url)

        # Fetch policy content if links exist
        policies = {}
        for policy_type, url in policy_links.items():
            if url:
                policy_soup = self.scraper.get_page_content(url)
                if policy_soup:
                    # Extract main content, avoid headers/footers
                    content_selectors = ['main', '.main-content', '.policy-content', '.content', 'article']
                    content = ""

                    for selector in content_selectors:
                        content_element = policy_soup.select_one(selector)
                        if content_element:
                            content = self._clean_html(content_element.get_text())
                            break

                    if not content:
                        content = self._clean_html(policy_soup.get_text())

                    policies[policy_type] = content[:1000]  # Limit to 1000 chars

        return PolicyInfo(
            privacy_policy=policies.get('privacy_policy'),
            return_policy=policies.get('return_policy'),
            refund_policy=policies.get('refund_policy'),
            terms_of_service=policies.get('terms_of_service'),
            shipping_policy=policies.get('shipping_policy')
        )

    def extract_faqs(self, soup: BeautifulSoup, base_url: str) -> List[FAQ]:
        """Extract FAQ information from various sources"""
        faqs = []
        logger.info("Starting FAQ extraction")

        # 1. Look for FAQ sections on current page
        faq_sections = soup.find_all(['div', 'section'],
                                     class_=re.compile(r'faq|question|accordion|customerservice|help', re.I))
        logger.info(f"Found {len(faq_sections)} FAQ sections on current page")

        for section in faq_sections:
            questions = section.find_all(['h3', 'h4', 'h5', '.question', '[data-question]'], limit=10)

            for question_elem in questions:
                question_text = question_elem.get_text().strip()

                # Find associated answer
                answer_elem = None
                next_sibling = question_elem.find_next_sibling()

                if next_sibling:
                    answer_elem = next_sibling
                else:
                    # Look for answer in parent container
                    parent = question_elem.parent
                    if parent:
                        answer_candidates = parent.find_all(['p', 'div', '.answer'])
                        if answer_candidates:
                            answer_elem = answer_candidates[0]

                if answer_elem and question_text:
                    answer_text = self._clean_html(answer_elem.get_text())
                    if len(answer_text) > 10:
                        faqs.append(FAQ(
                            question=question_text,
                            answer=answer_text[:500],
                            category="General"
                        ))

        # 2. Look for FAQ links in footer, header, and navigation
        faq_urls = self._find_faq_links(soup, base_url)
        logger.info(f"Found {len(faq_urls)} FAQ page URLs")

        # 3. Extract FAQs from dedicated pages
        for faq_url in faq_urls[:3]:
            logger.info(f"Extracting FAQs from: {faq_url}")
            faq_soup = self.scraper.get_page_content(faq_url)
            if faq_soup:
                page_faqs = self._extract_faqs_from_page(faq_soup, base_url)
                faqs.extend(page_faqs)
                if len(faqs) >= 10:
                    break

        # 4. Remove duplicates and limit results
        unique_faqs = self._remove_duplicate_faqs(faqs)
        logger.info(f"Extracted {len(unique_faqs)} unique FAQs")

        return unique_faqs[:10]

    def _find_faq_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Find FAQ page links from various sections of the page"""
        faq_urls = []

        # Enhanced FAQ detection patterns
        faq_patterns = [
            'faq', 'faqs', 'frequently asked questions', 'help', 'support',
            'questions', 'customerservice', 'customer service', 'help center',
            'support center', 'knowledge base', 'ask us', 'common questions'
        ]

        # Look in multiple sections
        search_areas = [
            soup,  # Entire page
            soup.find('footer'),  # Footer specifically
            soup.find('header'),  # Header
            soup.find('nav'),  # Navigation
            soup.find(id=re.compile(r'footer|navigation|menu', re.I)),  # ID-based sections
            soup.find(class_=re.compile(r'footer|navigation|menu|nav', re.I))  # Class-based sections
        ]

        for area in search_areas:
            if area is None:
                continue

            # Find all links in this area
            links = area.find_all('a', href=True)

            for link in links:
                href = link.get('href', '')
                text = link.get_text().lower().strip()

                # Check if link matches FAQ patterns
                if any(pattern in text for pattern in faq_patterns) or \
                        any(pattern in href.lower() for pattern in faq_patterns):

                    # Convert relative URLs to absolute
                    if href.startswith('/'):
                        full_url = urljoin(base_url, href)
                    elif href.startswith('http'):
                        full_url = href
                    else:
                        continue

                    if full_url not in faq_urls:
                        faq_urls.append(full_url)

        return faq_urls

    def _extract_faqs_from_page(self, soup: BeautifulSoup, base_url: str) -> List[FAQ]:
        """Extract FAQs from a dedicated FAQ page"""
        faqs = []

        # Multiple strategies to find FAQ content
        strategies = [
            self._extract_accordion_faqs,
            self._extract_structured_faqs,
            self._extract_list_faqs,
            self._extract_toggle_faqs
        ]

        for strategy in strategies:
            strategy_faqs = strategy(soup)
            faqs.extend(strategy_faqs)
            if len(faqs) >= 5:  # Stop if we found enough from one strategy
                break

        return faqs

    def _extract_accordion_faqs(self, soup: BeautifulSoup) -> List[FAQ]:
        """Extract FAQs from accordion-style sections"""
        faqs = []

        # Look for accordion containers
        accordion_selectors = [
            '[class*="accordion"]',
            '[class*="collapse"]',
            '[class*="toggle"]',
            '[data-toggle]',
            '.faq-item',
            '.question-item'
        ]

        for selector in accordion_selectors:
            accordion_items = soup.select(selector)

            for item in accordion_items[:5]:  # Limit per selector
                # Look for question in headers or buttons
                question_elem = item.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'button', '.question'])
                if question_elem:
                    question_text = question_elem.get_text().strip()

                    # Look for answer in associated content
                    answer_elem = item.find(['.answer', '.content', '.collapse', '.accordion-content'])
                    if not answer_elem:
                        # Try finding next element
                        answer_elem = question_elem.find_next_sibling()

                    if answer_elem and question_text and '?' in question_text:
                        answer_text = self._clean_html(answer_elem.get_text())
                        if len(answer_text) > 10:
                            faqs.append(FAQ(
                                question=question_text[:200],
                                answer=answer_text[:500],
                                category="FAQ Page"
                            ))

        return faqs

    def _extract_structured_faqs(self, soup: BeautifulSoup) -> List[FAQ]:
        """Extract FAQs from structured Q&A format"""
        faqs = []

        # Look for structured FAQ patterns
        faq_containers = soup.find_all(['div', 'section'], class_=re.compile(r'faq|qa|question', re.I))

        for container in faq_containers[:3]:
            # Strategy 1: Find Q: and A: patterns
            text_content = container.get_text()
            qa_matches = re.findall(r'Q[:\s]*([^?]+\?)\s*A[:\s]*([^Q]+?)(?=Q:|$)', text_content,
                                    re.DOTALL | re.IGNORECASE)

            for question, answer in qa_matches[:3]:
                question_clean = question.strip()
                answer_clean = self._clean_html(answer.strip())

                if len(question_clean) > 5 and len(answer_clean) > 10:
                    faqs.append(FAQ(
                        question=question_clean[:200],
                        answer=answer_clean[:500],
                        category="Structured FAQ"
                    ))

        return faqs

    def _extract_list_faqs(self, soup: BeautifulSoup) -> List[FAQ]:
        """Extract FAQs from list format"""
        faqs = []

        # Look for FAQ lists
        faq_lists = soup.find_all(['ul', 'ol', 'dl'], class_=re.compile(r'faq|question|help', re.I))

        for faq_list in faq_lists[:2]:
            list_items = faq_list.find_all(['li', 'dt', 'dd'])

            for i in range(0, len(list_items) - 1, 2):  # Process in pairs
                if i + 1 < len(list_items):
                    question_item = list_items[i]
                    answer_item = list_items[i + 1]

                    question_text = question_item.get_text().strip()
                    answer_text = self._clean_html(answer_item.get_text())

                    if '?' in question_text and len(answer_text) > 10:
                        faqs.append(FAQ(
                            question=question_text[:200],
                            answer=answer_text[:500],
                            category="List FAQ"
                        ))

        return faqs

    def _extract_toggle_faqs(self, soup: BeautifulSoup) -> List[FAQ]:
        """Extract FAQs from toggle/expandable sections"""
        faqs = []

        # Look for expandable sections
        toggle_selectors = [
            '[data-toggle="collapse"]',
            '.toggle-question',
            '.expandable',
            '[onclick*="toggle"]',
            '.faq-toggle'
        ]

        for selector in toggle_selectors:
            toggles = soup.select(selector)

            for toggle in toggles[:5]:
                question_text = toggle.get_text().strip()

                # Find associated content
                target_id = toggle.get('data-target') or toggle.get('aria-controls')
                answer_elem = None

                if target_id:
                    target_id = target_id.lstrip('#')
                    answer_elem = soup.find(id=target_id)
                else:
                    answer_elem = toggle.find_next_sibling()

                if answer_elem and '?' in question_text:
                    answer_text = self._clean_html(answer_elem.get_text())
                    if len(answer_text) > 10:
                        faqs.append(FAQ(
                            question=question_text[:200],
                            answer=answer_text[:500],
                            category="Toggle FAQ"
                        ))

        return faqs

    def _remove_duplicate_faqs(self, faqs: List[FAQ]) -> List[FAQ]:
        """Remove duplicate FAQs based on question similarity"""
        unique_faqs = []
        seen_questions = set()

        for faq in faqs:
            # Normalize question for comparison
            normalized_question = re.sub(r'[^\w\s]', '', faq.question.lower()).strip()

            if normalized_question not in seen_questions and len(normalized_question) > 5:
                seen_questions.add(normalized_question)
                unique_faqs.append(faq)

        return unique_faqs

    def extract_brand_context(self, soup: BeautifulSoup, base_url: str) -> str:
        """Extract brand context/about information"""
        brand_context = ""

        # Look for about sections on homepage
        about_selectors = [
            '.about', '.brand-story', '.our-story', '.hero-text',
            '[class*="about"]', '[class*="story"]'
        ]

        for selector in about_selectors:
            about_element = soup.select_one(selector)
            if about_element:
                text = self._clean_html(about_element.get_text())
                if len(text) > 50:
                    brand_context = text[:500]
                    break

        # If not found on homepage, check about page
        if not brand_context:
            important_links = self.scraper.extract_important_links(soup, base_url)
            about_url = important_links.get('about_us')

            if about_url:
                about_soup = self.scraper.get_page_content(about_url)
                if about_soup:
                    # Look for main content
                    content_selectors = ['main', '.main-content', '.about-content', '.content']
                    for selector in content_selectors:
                        content_elem = about_soup.select_one(selector)
                        if content_elem:
                            brand_context = self._clean_html(content_elem.get_text())[:500]
                            break

        return brand_context or "Brand context not found"

    def extract_important_links(self, soup: BeautifulSoup, base_url: str) -> ImportantLinks:
        """Extract important navigation links"""
        links = self.scraper.extract_important_links(soup, base_url)

        return ImportantLinks(
            order_tracking=links.get('order_tracking'),
            contact_us=links.get('contact_us'),
            blog=links.get('blog'),
            size_guide=links.get('size_guide'),
            careers=links.get('careers'),
            about_us=links.get('about_us')
        )

    def _clean_html(self, html_content: str) -> str:
        """Clean HTML content and extract readable text"""
        if not html_content:
            return ""

        # Remove HTML tags
        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text()

        # Clean up whitespace
        text = ' '.join(text.split())

        return text.strip()

    def extract_complete_insights(self, url: str) -> BrandInsights:
        """Extract complete brand insights from Shopify store"""
        try:
            # Normalize URL
            url = self.scraper.normalize_url(url)

            # Get homepage content
            soup = self.scraper.get_page_content(url)
            if not soup:
                raise Exception("Could not fetch website content")

            # Check if it's a Shopify store
            if not self.scraper.is_shopify_store(url, str(soup)):
                logger.warning(f"Website {url} may not be a Shopify store")

            # Extract brand name
            brand_name = self.scraper.get_brand_name(soup, url)

            # Get all products
            all_products_data = self.scraper.get_all_products_paginated(url)
            product_catalog = self.extract_products_from_json(all_products_data, url)

            # Extract hero products
            hero_products = self.extract_hero_products(soup, product_catalog, url)

            # Extract all other information
            contact_details = self.extract_contact_details(soup, url)
            social_handles = self.extract_social_handles(soup, url)
            policies = self.extract_policies(soup, url)
            faqs = self.extract_faqs(soup, url)
            brand_context = self.extract_brand_context(soup, url)
            important_links = self.extract_important_links(soup, url)

            return BrandInsights(
                brand_name=brand_name,
                website_url=url,
                product_catalog=product_catalog,
                hero_products=hero_products,
                contact_details=contact_details,
                social_handles=social_handles,
                policies=policies,
                faqs=faqs,
                brand_context=brand_context,
                important_links=important_links,
                total_products=len(product_catalog),
                extraction_success=True,
                errors=[]
            )

        except Exception as e:
            logger.error(f"Error extracting insights from {url}: {e}")
            return BrandInsights(
                brand_name="Unknown",
                website_url=url,
                contact_details=ContactDetails(),
                social_handles=SocialHandles(),
                policies=PolicyInfo(),
                important_links=ImportantLinks(),
                extraction_success=False,
                errors=[str(e)]
            )