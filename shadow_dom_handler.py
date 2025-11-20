"""
Shadow DOM Handler

Penetrates Shadow DOM to extract data from modern web components.
"""

import logging
from typing import List, Optional, Any
from playwright.async_api import Page, ElementHandle

logger = logging.getLogger("ShadowDOMHandler")


class ShadowDOMHandler:
    """Handles Shadow DOM traversal and data extraction."""
    
    @staticmethod
    async def find_shadow_roots(page: Page) -> List[ElementHandle]:
        """
        Find all Shadow DOM roots on page.
        
        Returns:
            List of shadow root element handles
        """
        try:
            # JavaScript to find all shadow roots
            shadow_roots = await page.evaluate("""
            () => {
                const roots = [];
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_ELEMENT
                );
                
                let node;
                while (node = walker.nextNode()) {
                    if (node.shadowRoot) {
                        roots.push(node);
                    }
                }
                
                return roots.length;
            }
            """)
            
            logger.info(f"Found {shadow_roots} Shadow DOM roots")
            return shadow_roots
            
        except Exception as e:
            logger.error(f"Shadow DOM detection failed: {e}")
            return []
    
    @staticmethod
    async def pierce_shadow_dom(page: Page, selector: str) -> List[Any]:
        """
        Query selector that pierces Shadow DOM boundaries.
        
        Args:
            page: Playwright page
            selector: CSS selector
            
        Returns:
            List of matching elements
        """
        try:
            # Use piercing selector (>>>) for Shadow DOM
            piercing_selector = f"* >>> {selector}"
            elements = await page.locator(piercing_selector).all()
            
            logger.debug(f"Found {len(elements)} elements via Shadow DOM pierce")
            return elements
            
        except Exception as e:
            logger.debug(f"Shadow DOM pierce failed: {e}")
            return []
    
    @staticmethod
    async def extract_from_shadow_dom(page: Page) -> dict:
        """
        Extract common data from Shadow DOM elements.
        
        Returns:
            Dict with extracted data
        """
        data = {
            'texts': [],
            'links': [],
            'images': []
        }
        
        try:
            # Pierce for common elements
            text_elements = await ShadowDOMHandler.pierce_shadow_dom(page, 'div, span, p')
            for el in text_elements[:50]:
                try:
                    text = await el.inner_text()
                    if text and len(text) > 3:
                        data['texts'].append(text)
                except:
                    pass
            
            # Pierce for links
            link_elements = await ShadowDOMHandler.pierce_shadow_dom(page, 'a')
            for el in link_elements[:20]:
                try:
                    href = await el.get_attribute('href')
                    if href:
                        data['links'].append(href)
                except:
                    pass
            
            logger.info(f"Extracted from Shadow DOM: {len(data['texts'])} texts, {len(data['links'])} links")
            return data
            
        except Exception as e:
            logger.error(f"Shadow DOM extraction failed: {e}")
            return data
