"""
Sitemap.xml Parser

Efficiently discovers URLs from XML sitemaps with priority support.
"""

import logging
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
import aiohttp
from datetime import datetime

logger = logging.getLogger("SitemapParser")


class SitemapURL:
    """Represents a URL from sitemap."""
    
    def __init__(
        self,
        loc: str,
        lastmod: Optional[datetime] = None,
        changefreq: Optional[str] = None,
        priority: float = 0.5
    ):
        self.loc = loc
        self.lastmod = lastmod
        self.changefreq = changefreq
        self.priority = priority
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'url': self.loc,
            'last_modified': self.lastmod.isoformat() if self.lastmod else None,
            'change_frequency': self.changefreq,
            'priority': self.priority
        }


class SitemapParser:
    """Parses XML sitemaps and extracts URLs."""
    
    @staticmethod
    async def fetch_sitemap(url: str) -> Optional[str]:
        """Fetch sitemap content."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        content = await response.text()
                        logger.info(f"Fetched sitemap: {url}")
                        return content
                    else:
                        logger.warning(f"Sitemap fetch failed: {url} (status={response.status})")
                        return None
        except Exception as e:
            logger.error(f"Failed to fetch sitemap {url}: {e}")
            return None
    
    @staticmethod
    def parse_sitemap(xml_content: str) -> List[SitemapURL]:
        """
        Parse sitemap XML content.
        
        Args:
            xml_content: XML string
            
        Returns:
            List of SitemapURL objects
        """
        urls = []
        
        try:
            root = ET.fromstring(xml_content)
            
            # Define XML namespaces
            namespaces = {
                'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'
            }
            
            # Find all <url> elements
            for url_element in root.findall('sitemap:url', namespaces):
                loc_element = url_element.find('sitemap:loc', namespaces)
                if loc_element is None:
                    continue
                
                loc = loc_element.text
                if not loc:
                    continue
                
                # Extract optional fields
                lastmod_element = url_element.find('sitemap:lastmod', namespaces)
                lastmod = None
                if lastmod_element is not None and lastmod_element.text:
                    try:
                        lastmod = datetime.fromisoformat(lastmod_element.text.replace('Z', '+00:00'))
                    except:
                        pass
                
                changefreq_element = url_element.find('sitemap:changefreq', namespaces)
                changefreq = changefreq_element.text if changefreq_element is not None else None
                
                priority_element = url_element.find('sitemap:priority', namespaces)
                priority = 0.5
                if priority_element is not None and priority_element.text:
                    try:
                        priority = float(priority_element.text)
                    except:
                        pass
                
                sitemap_url = SitemapURL(
                    loc=loc,
                    lastmod=lastmod,
                    changefreq=changefreq,
                    priority=priority
                )
                urls.append(sitemap_url)
            
            logger.info(f"Parsed {len(urls)} URLs from sitemap")
            return urls
            
        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}")
            return []
        except Exception as e:
            logger.error(f"Sitemap parsing failed: {e}")
            return []
    
    @staticmethod
    def parse_sitemap_index(xml_content: str) -> List[str]:
        """
        Parse sitemap index file to get child sitemap URLs.
        
        Args:
            xml_content: Sitemap index XML
            
        Returns:
            List of child sitemap URLs
        """
        sitemap_urls = []
        
        try:
            root = ET.fromstring(xml_content)
            
            namespaces = {
                'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'
            }
            
            # Find all <sitemap> elements
            for sitemap_element in root.findall('sitemap:sitemap', namespaces):
                loc_element = sitemap_element.find('sitemap:loc', namespaces)
                if loc_element is not None and loc_element.text:
                    sitemap_urls.append(loc_element.text)
            
            logger.info(f"Found {len(sitemap_urls)} child sitemaps in index")
            return sitemap_urls
            
        except Exception as e:
            logger.error(f"Sitemap index parsing failed: {e}")
            return []
    
    @staticmethod
    async def discover_from_robots(base_url: str) -> List[str]:
        """
        Discover sitemap URLs from robots.txt.
        
        Args:
            base_url: Base URL of website
            
        Returns:
            List of sitemap URLs
        """
        from urllib.parse import urljoin
        
        robots_url = urljoin(base_url, '/robots.txt')
        sitemap_urls = []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(robots_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        content = await response.text()
                        
                        # Parse robots.txt for Sitemap directives
                        for line in content.split('\n'):
                            if line.lower().startswith('sitemap:'):
                                sitemap_url = line.split(':', 1)[1].strip()
                                sitemap_urls.append(sitemap_url)
                        
                        logger.info(f"Discovered {len(sitemap_urls)} sitemaps from robots.txt")
            
            return sitemap_urls
            
        except Exception as e:
            logger.debug(f"Failed to discover sitemaps from robots.txt: {e}")
            return []
    
    @staticmethod
    async def get_all_urls(sitemap_url: str) -> List[SitemapURL]:
        """
        Get all URLs from sitemap (handles both regular and index).
        
        Args:
            sitemap_url: Sitemap URL
            
        Returns:
            List of all URLs
        """
        all_urls = []
        
        # Fetch sitemap
        content = await SitemapParser.fetch_sitemap(sitemap_url)
        if not content:
            return all_urls
        
        # Check if it's a sitemap index
        if '<sitemapindex' in content:
            # Parse index to get child sitemaps
            child_sitemaps = SitemapParser.parse_sitemap_index(content)
            
            # Fetch and parse each child sitemap
            for child_url in child_sitemaps:
                child_content = await SitemapParser.fetch_sitemap(child_url)
                if child_content:
                    urls = SitemapParser.parse_sitemap(child_content)
                    all_urls.extend(urls)
        else:
            # Regular sitemap
            urls = SitemapParser.parse_sitemap(content)
            all_urls.extend(urls)
        
        logger.info(f"Total URLs extracted: {len(all_urls)}")
        return all_urls
