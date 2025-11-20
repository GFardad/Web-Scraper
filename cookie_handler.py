"""
Cookie Consent Auto-Handler

Automatically detects and handles cookie consent banners.
Supports GDPR popups and common cookie notification patterns.
"""

import logging
from typing import Optional
from playwright.async_api import Page

logger = logging.getLogger("CookieHandler")


class CookieConsentHandler:
    """Handles cookie consent popups automatically."""
    
    # Common "Accept" button selectors
    ACCEPT_SELECTORS = [
        'button:has-text("Accept")',
        'button:has-text("قبول")',
        'button:has-text("پذیرفتن")',
        'button:has-text("موافقم")',
        'button:has-text("I agree")',
        'button:has-text("Accept all")',
        'button[id*="accept"]',
        'button[class*="accept"]',
        'a:has-text("Accept")',
        '.cookie-accept',
        '#cookie-accept',
        '[aria-label*="accept" i]',
    ]
    
    # Common "Reject" button selectors
    REJECT_SELECTORS = [
        'button:has-text("Reject")',
        'button:has-text("رد")',
        'button:has-text("Decline")',
        'button[id*="reject"]',
        'button[class*="reject"]',
    ]
    
    @staticmethod
    async def handle(page: Page, action: str = "accept") -> bool:
        """
        Detect and handle cookie consent popup.
        
        Args:
            page: Playwright page object
            action: "accept" or "reject"
            
        Returns:
            True if popup was handled, False if no popup found
        """
        try:
            selectors = CookieConsentHandler.ACCEPT_SELECTORS if action == "accept" else CookieConsentHandler.REJECT_SELECTORS
            
            for selector in selectors:
                try:
                    button = page.locator(selector).first
                    if await button.count() > 0:
                        # Check if visible
                        if await button.is_visible():
                            await button.click(timeout=2000)
                            logger.info(f"Clicked cookie {action} button: {selector}")
                            await page.wait_for_timeout(500)
                            return True
                except:
                    continue
            
            logger.debug("No cookie consent popup found")
            return False
            
        except Exception as e:
            logger.debug(f"Cookie consent handler error: {e}")
            return False
    
    @staticmethod
    async def detect(page: Page) -> bool:
        """
        Detect if cookie consent popup is present.
        
        Returns:
            True if popup detected
        """
        try:
            keywords = ['cookie', 'privacy', 'consent', 'gdpr', 'کوکی', 'حریم خصوصی']
            
            # Check page text
            page_text = await page.inner_text('body')
            page_text_lower = page_text.lower()
            
            # Look for cookie-related text in visible popups/modals
            for keyword in keywords:
                if keyword in page_text_lower:
                    # Check if there's a modal/dialog
                    modals = await page.locator('[role="dialog"], .modal, .popup, [class*="cookie"]').all()
                    if modals:
                        return True
            
            return False
        except:
            return False
