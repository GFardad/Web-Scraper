"""
Pagination Handler

Automatically detects and traverses pagination

 across different sites.
Supports next-page links, page numbers, and load-more buttons.
"""

import logging
import re
from typing import List, Optional
from playwright.async_api import Page
from urllib.parse import urljoin, urlparse, parse_qs, urlencode

logger = logging.getLogger("PaginationHandler")


class PaginationDetector:
    """Detects pagination patterns on web pages."""
    
    # Common pagination selectors
    NEXT_SELECTORS = [
        'a[rel="next"]',
        '.next',
        '.pagination-next',
        'a:has-text("بعدی")',
        'a:has-text("Next")',
        'a:has-text(">")',
        '[aria-label*="next" i]',
    ]
    
    @staticmethod
    async def find_next_page(page: Page, current_url: str) -> Optional[str]:
        """
        Find next page URL.
        
        Args:
            page: Playwright page object
            current_url: Current page URL
            
        Returns:
            Next page URL or None
        """
        # Try CSS selectors
        for selector in PaginationDetector.NEXT_SELECTORS:
            try:
                element = page.locator(selector).first
                if await element.count() > 0:
                    # Check if not disabled
                    classes = await element.get_attribute('class') or ''
                    if 'disabled' not in classes.lower():
                        href = await element.get_attribute('href')
                        if href:
                            next_url = urljoin(current_url, href)
                            logger.info(f"Found next page via selector {selector}: {next_url}")
                            return next_url
            except:
                continue
        
        # Try URL pattern analysis
        next_url = PaginationDetector._analyze_url_pattern(current_url)
        if next_url:
            return next_url
        
        return None
    
    @staticmethod
    def _analyze_url_pattern(url: str) -> Optional[str]:
        """
        Analyze URL for pagination patterns and generate next URL.
        
        Supports:
        - ?page=2
        - ?p=2
        - /page/2/
        - /p2/
        """
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Check for page parameter
        for param in ['page', 'p', 'pg']:
            if param in query_params:
                try:
                    current_page = int(query_params[param][0])
                    next_page = current_page + 1
                    query_params[param] = [str(next_page)]
                    
                    new_query = urlencode(query_params, doseq=True)
                    next_url = parsed._replace(query=new_query).geturl()
                    logger.info(f"Generated next page from URL pattern: {next_url}")
                    return next_url
                except ValueError:
                    continue
        
        # Check path-based pagination
        path = parsed.path
        # Match /page/2/, /p/2/, etc.
        match = re.search(r'/(page|p)/(\d+)/?$', path)
        if match:
            prefix, current_page = match.groups()
            next_page = int(current_page) + 1
            new_path = re.sub(r'/(page|p)/\d+/?$', f'/{prefix}/{next_page}/', path)
            next_url = parsed._replace(path=new_path).geturl()
            logger.info(f"Generated next page from path: {next_url}")
            return next_url
        
        return None


class PaginationHandler:
    """Handles pagination traversal."""
    
    def __init__(self, max_pages: int = 10):
        """
        Initialize pagination handler.
        
        Args:
            max_pages: Maximum pages to traverse
        """
        self.max_pages = max_pages
        self.visited_urls: set = set()
    
    async def get_all_pages(self, page: Page, start_url: str) -> List[str]:
        """
        Get all paginated URLs starting from a URL.
        
        Args:
            page: Playwright page object
            start_url: Starting URL
            
        Returns:
            List of all page URLs (including start_url)
        """
        urls = [start_url]
        self.visited_urls = {start_url}
        current_url = start_url
        
        for i in range(self.max_pages - 1):
            next_url = await PaginationDetector.find_next_page(page, current_url)
            
            if not next_url:
                logger.info(f"No more pages found after {len(urls)} pages")
                break
            
            if next_url in self.visited_urls:
                logger.warning(f"Circular pagination detected at page {i+2}")
                break
            
            urls.append(next_url)
            self.visited_urls.add(next_url)
            current_url = next_url
            
            # Navigate to next page to get subsequent links
            try:
                await page.goto(next_url, timeout=30000, wait_until="domcontentloaded")
                await page.wait_for_timeout(1000)
            except Exception as e:
                logger.error(f"Failed to navigate to page {i+2}: {e}")
                break
        
        logger.info(f"Total pages discovered: {len(urls)}")
        return urls
