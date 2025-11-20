"""
Canonical URL Detection & Deduplication

Prevents duplicate scraping by detecting canonical URLs and normalizing variants.
"""

import logging
import hashlib
from typing import Optional, Set
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from playwright.async_api import Page

logger = logging.getLogger("URLDeduplicator")


class URLDeduplicator:
    """Detects canonical URLs and prevents duplicates."""
    
    def __init__(self):
        """Initialize deduplicator."""
        self.seen_urls: Set[str] = set()
        self.url_hashes: Set[str] = set()
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Normalize URL for comparison.
        
        - Remove trailing slashes
        - Sort query parameters
        - Lowercase scheme and domain
        - Remove common tracking parameters
        """
        parsed = urlparse(url)
        
        # Normalize scheme and netloc
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        
        # Remove trailing slash from path
        path = parsed.path.rstrip('/')
        if not path:
            path = '/'
        
        # Parse and sort query params
        query_params = parse_qs(parsed.query)
        
        # Remove tracking parameters
        tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 'fbclid', 'gclid', 'ref', 'source']
        for param in tracking_params:
            query_params.pop(param, None)
        
        # Sort and rebuild query string
        sorted_query = urlencode(sorted(query_params.items()), doseq=True)
        
        # Rebuild URL
        normalized = urlunparse((
            scheme,
            netloc,
            path,
            '',  # params (rarely used)
            sorted_query,
            ''   # fragment (ignore)
        ))
        
        return normalized
    
    @staticmethod
    async def extract_canonical(page: Page) -> Optional[str]:
        """
        Extract canonical URL from page.
        
        Args:
            page: Playwright page object
            
        Returns:
            Canonical URL or None
        """
        try:
            # Method 1: <link rel="canonical">
            canonical_tag = page.locator('link[rel="canonical"]').first
            if await canonical_tag.count() > 0:
                href = await canonical_tag.get_attribute('href')
                if href:
                    logger.info(f"Found canonical URL: {href}")
                    return href
            
            # Method 2: og:url meta tag
            og_url_tag = page.locator('meta[property="og:url"]').first
            if await og_url_tag.count() > 0:
                content = await og_url_tag.get_attribute('content')
                if content:
                    logger.info(f"Found og:url: {content}")
                    return content
            
            return None
            
        except Exception as e:
            logger.debug(f"Canonical extraction failed: {e}")
            return None
    
    def is_duplicate(self, url: str) -> bool:
        """
        Check if URL is duplicate (already seen).
        
        Args:
            url: URL to check
            
        Returns:
            True if duplicate
        """
        normalized = self.normalize_url(url)
        
        if normalized in self.seen_urls:
            logger.debug(f"Duplicate URL detected: {url}")
            return True
        
        # Also check content hash (for completely different URLs with same content)
        url_hash = hashlib.md5(normalized.encode()).hexdigest()
        if url_hash in self.url_hashes:
            logger.debug(f"Duplicate content hash: {url}")
            return True
        
        return False
    
    def mark_seen(self, url: str, canonical: Optional[str] = None):
        """
        Mark URL as seen.
        
        Args:
            url: Original URL
            canonical: Canonical URL if different
        """
        # Mark normalized original URL
        normalized = self.normalize_url(url)
        self.seen_urls.add(normalized)
        
        url_hash = hashlib.md5(normalized.encode()).hexdigest()
        self.url_hashes.add(url_hash)
        
        # Also mark canonical if provided
        if canonical and canonical != url:
            canonical_normalized = self.normalize_url(canonical)
            self.seen_urls.add(canonical_normalized)
            
            canonical_hash = hashlib.md5(canonical_normalized.encode()).hexdigest()
            self.url_hashes.add(canonical_hash)
    
    def get_stats(self) -> dict:
        """Get deduplication statistics."""
        return {
            'unique_urls': len(self.seen_urls),
            'total_hashes': len(self.url_hashes)
        }
