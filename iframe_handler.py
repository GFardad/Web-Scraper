"""
Iframe Content Extraction Handler

Switches context to extract data from iframe elements.
"""

import logging
from typing import List, Optional, Dict, Any
from playwright.async_api import Page, Frame

logger = logging.getLogger("IframeHandler")


class IframeHandler:
    """Handles iframe detection and content extraction."""
    
    @staticmethod
    async def find_iframes(page: Page) -> List[Frame]:
        """
        Find all iframes on page.
        
        Returns:
            List of Frame objects
        """
        try:
            frames = page.frames
            # Filter out main frame
            iframes = [f for f in frames if f != page.main_frame]
            
            logger.info(f"Found {len(iframes)} iframes on page")
            return iframes
            
        except Exception as e:
            logger.error(f"Iframe detection failed: {e}")
            return []
    
    @staticmethod
    async def extract_from_iframe(frame: Frame) -> Dict[str, Any]:
        """
        Extract data from single iframe.
        
        Args:
            frame: Playwright Frame object
            
        Returns:
            Dict with extracted data
        """
        data = {
            'url': None,
            'title': None,
            'text_content': None,
            'links': [],
            'forms': []
        }
        
        try:
            # Get iframe URL
            data['url'] = frame.url
            
            # Get title
            try:
                title_el = frame.locator('title').first
                if await title_el.count() > 0:
                    data['title'] = await title_el.inner_text()
            except:
                pass
            
            # Get text content
            try:
                body = frame.locator('body').first
                if await body.count() > 0:
                    text = await body.inner_text()
                    data['text_content'] = text[:500]  # First 500 chars
            except:
                pass
            
            # Get links
            try:
                links = await frame.locator('a').all()
                for link in links[:10]:  # Max 10 links
                    href = await link.get_attribute('href')
                    if href:
                        data['links'].append(href)
            except:
                pass
            
            # Detect forms (useful for payment/auth iframes)
            try:
                forms = await frame.locator('form').all()
                data['forms'] = len(forms)
            except:
                pass
            
            logger.debug(f"Extracted from iframe: {data['url']}")
            return data
            
        except Exception as e:
            logger.error(f"Iframe extraction failed: {e}")
            return data
    
    @staticmethod
    async def extract_all_iframes(page: Page) -> List[Dict[str, Any]]:
        """
        Extract data from all iframes on page.
        
        Args:
            page: Playwright Page
            
        Returns:
            List of data dicts from each iframe
        """
        results = []
        
        iframes = await IframeHandler.find_iframes(page)
        
        for iframe in iframes:
            try:
                data = await IframeHandler.extract_from_iframe(iframe)
                if data:
                    results.append(data)
            except Exception as e:
                logger.warning(f"Failed to extract from iframe: {e}")
        
        logger.info(f"Extracted data from {len(results)} iframes")
        return results
    
    @staticmethod
    async def wait_for_iframe_load(page: Page, iframe_selector: str, timeout: int = 30000):
        """
        Wait for specific iframe to load.
        
        Args:
            page: Playwright Page
            iframe_selector: CSS selector for iframe
            timeout: Max wait time in ms
        """
        try:
            iframe_element = page.locator(iframe_selector).first
            await iframe_element.wait_for(state='attached', timeout=timeout)
            logger.info(f"Iframe loaded: {iframe_selector}")
        except Exception as e:
            logger.warning(f"Iframe load timeout: {e}")
