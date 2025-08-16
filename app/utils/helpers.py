import requests
import logging
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, urljoin
import re
from functools import wraps
import time

logger = logging.getLogger(__name__)


def validate_shopify_url(url: str, timeout: int = 10) -> bool:
    """
    Validate if a URL is accessible and returns a valid response

    Args:
        url: The URL to validate
        timeout: Request timeout in seconds

    Returns:
        bool: True if URL is accessible, False otherwise
    """
    try:
        # Normalize URL
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        # Make a HEAD request first (faster)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.head(url, headers=headers, timeout=timeout, allow_redirects=True)

        # If HEAD fails, try GET with a small range
        if response.status_code >= 400:
            response = requests.get(url, headers=headers, timeout=timeout, stream=True)
            response.raise_for_status()

        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"URL validation failed for {url}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error validating URL {url}: {e}")
        return False


def normalize_url(url: str) -> str:
    """
    Normalize a URL by ensuring proper protocol and removing trailing slashes

    Args:
        url: The URL to normalize

    Returns:
        str: Normalized URL
    """
    if not url:
        return ""

    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    # Remove trailing slash
    return url.rstrip('/')


def clean_text(text: str, max_length: Optional[int] = None) -> str:
    """
    Clean and normalize text content

    Args:
        text: Text to clean
        max_length: Maximum length to truncate to

    Returns:
        str: Cleaned text
    """
    if not text:
        return ""

    # Remove extra whitespace and normalize
    cleaned = ' '.join(text.split())

    # Remove special characters but keep basic punctuation
    cleaned = re.sub(r'[^\w\s\.\,\!\?\-\(\)\:]', '', cleaned)

    # Truncate if needed
    if max_length and len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rsplit(' ', 1)[0] + '...'

    return cleaned.strip()


def extract_domain(url: str) -> str:
    """
    Extract domain from URL

    Args:
        url: URL to extract domain from

    Returns:
        str: Domain name
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        return domain.replace('www.', '') if domain else ""
    except Exception:
        return ""


def is_valid_email(email: str) -> bool:
    """
    Validate email format

    Args:
        email: Email to validate

    Returns:
        bool: True if valid email format
    """
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email.strip()))


def is_valid_phone(phone: str) -> bool:
    """
    Validate phone number format

    Args:
        phone: Phone number to validate

    Returns:
        bool: True if valid phone format
    """
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)

    # Check if it's a reasonable phone number length (7-15 digits)
    return 7 <= len(digits_only) <= 15


def handle_extraction_errors(errors: List[str]) -> Dict[str, Any]:
    """
    Process and categorize extraction errors

    Args:
        errors: List of error messages

    Returns:
        dict: Categorized error information
    """
    error_categories = {
        'network': ['timeout', 'connection', 'dns', 'network'],
        'parsing': ['parse', 'html', 'json', 'format'],
        'access': ['403', '404', '401', 'denied', 'blocked'],
        'content': ['empty', 'missing', 'not found']
    }

    categorized = {'network': [], 'parsing': [], 'access': [], 'content': [], 'other': []}

    for error in errors:
        error_lower = error.lower()
        categorized_flag = False

        for category, keywords in error_categories.items():
            if any(keyword in error_lower for keyword in keywords):
                categorized[category].append(error)
                categorized_flag = True
                break

        if not categorized_flag:
            categorized['other'].append(error)

    return categorized


def retry_on_failure(retries: int = 3, delay: float = 1.0):
    """
    Decorator to retry function calls on failure

    Args:
        retries: Number of retry attempts
        delay: Delay between retries in seconds
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < retries:
                        logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}")
                        time.sleep(delay * (attempt + 1))  # Exponential backoff
                    else:
                        logger.error(f"All {retries + 1} attempts failed for {func.__name__}: {e}")

            raise last_exception

        return wrapper

    return decorator


def format_price(price: Optional[float]) -> Optional[str]:
    """
    Format price for display

    Args:
        price: Price value

    Returns:
        str: Formatted price string
    """
    if price is None:
        return None

    try:
        return f"${price:.2f}"
    except (ValueError, TypeError):
        return None


def extract_numeric_value(text: str) -> Optional[float]:
    """
    Extract numeric value from text

    Args:
        text: Text containing numeric value

    Returns:
        float: Extracted numeric value or None
    """
    if not text:
        return None

    # Find first number in the text
    match = re.search(r'(\d+\.?\d*)', str(text))
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass

    return None


def get_file_extension(url: str) -> str:
    """
    Get file extension from URL

    Args:
        url: URL to extract extension from

    Returns:
        str: File extension (without dot)
    """
    try:
        parsed = urlparse(url)
        path = parsed.path.lower()
        if '.' in path:
            return path.split('.')[-1]
        return ""
    except Exception:
        return ""


def is_image_url(url: str) -> bool:
    """
    Check if URL points to an image

    Args:
        url: URL to check

    Returns:
        bool: True if URL appears to be an image
    """
    image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'ico']
    extension = get_file_extension(url)
    return extension in image_extensions


def truncate_list(items: List[Any], max_items: int = 10) -> List[Any]:
    """
    Truncate a list to maximum number of items

    Args:
        items: List to truncate
        max_items: Maximum number of items

    Returns:
        list: Truncated list
    """
    if not items or len(items) <= max_items:
        return items

    return items[:max_items]


def merge_unique_lists(*lists) -> List[Any]:
    """
    Merge multiple lists and remove duplicates while preserving order

    Args:
        *lists: Lists to merge

    Returns:
        list: Merged list with unique items
    """
    seen = set()
    result = []

    for lst in lists:
        if lst:
            for item in lst:
                if item not in seen:
                    seen.add(item)
                    result.append(item)

    return result