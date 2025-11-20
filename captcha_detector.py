"""
CAPTCHA Detection System

Detects the presence of CAPTCHAs on web pages using multiple detection methods.
Supports reCAPTCHA, hCaptcha, and custom implementations.
"""

import logging
from typing import Optional, Dict, Any
from playwright.async_api import Page

logger = logging.getLogger("CAPTCHADetector")


class CAPTCHADetector:
    """
    Multi-method CAPTCHA detection system.
    
    Detects:
    - Google reCAPTCHA (v2, v3)
    - hCaptcha
    - Custom CAPTCHA implementations
    """
    
    # Known CAPTCHA domains
    CAPTCHA_DOMAINS = [
        'google.com/recaptcha',
        'gstatic.com/recaptcha',
        'hcaptcha.com',
        'cloudflare.com'
    ]
    
    # CSS selectors for CAPTCHA elements
    CAPTCHA_SELECTORS = [
        '#g-recaptcha',
        '.g-recaptcha',
        '[data-sitekey]',
        '.h-captcha',
        'iframe[src*="recaptcha"]',
        'iframe[src*="hcaptcha"]',
        '.captcha-container',
        '[id*="captcha"]',
        '[class*="captcha"]',
    ]
    
    # Text indicators
    CAPTCHA_KEYWORDS = [
        'verify you are human',
        'captcha',
        'recaptcha',
        'hcaptcha',
        'prove you',
        'not a robot',
        'human verification',
    ]
    
    @staticmethod
    async def detect(page: Page) -> Optional[Dict[str, Any]]:
        """
        Detect CAPTCHA on page.
        
        Args:
            page: Playwright page object
            
        Returns:
            Dict with CAPTCHA info or None if not detected
        """
        captcha_info = {
            'detected': False,
            'type': None,
            'method': None,
            'sitekey': None
        }
        
        # Method 1: CSS Selector Detection
        for selector in CAPTCHADetector.CAPTCHA_SELECTORS:
            try:
                element = page.locator(selector).first
                if await element.count() > 0:
                    captcha_info['detected'] = True
                    captcha_info['method'] = 'css_selector'
                    captcha_info['type'] = CAPTCHADetector._identify_type(selector)
                    
                    # Try to get sitekey
                    try:
                        sitekey = await element.get_attribute('data-sitekey')
                        if sitekey:
                            captcha_info['sitekey'] = sitekey
                    except:
                        pass
                    
                    logger.warning(f"CAPTCHA detected via selector: {selector}")
                    return captcha_info
            except:
                continue
        
        # Method 2: Network Request Detection
        # Check if page made requests to CAPTCHA domains
        try:
            page_content = await page.content()
            for domain in CAPTCHADetector.CAPTCHA_DOMAINS:
                if domain in page_content:
                    captcha_info['detected'] = True
                    captcha_info['method'] = 'network_analysis'
                    captcha_info['type'] = CAPTCHADetector._identify_type(domain)
                    logger.warning(f"CAPTCHA detected via domain: {domain}")
                    return captcha_info
        except:
            pass
        
        # Method 3: Text Content Analysis
        try:
            page_text = await page.inner_text('body')
            page_text_lower = page_text.lower()
            
            for keyword in CAPTCHADetector.CAPTCHA_KEYWORDS:
                if keyword in page_text_lower:
                    captcha_info['detected'] = True
                    captcha_info['method'] = 'text_analysis'
                    captcha_info['type'] = 'unknown'
                    logger.warning(f"CAPTCHA detected via keyword: {keyword}")
                    return captcha_info
        except:
            pass
        
        return None
    
    @staticmethod
    def _identify_type(indicator: str) -> str:
        """Identify CAPTCHA type from indicator."""
        indicator_lower = indicator.lower()
        
        if 'recaptcha' in indicator_lower or 'google' in indicator_lower:
            return 'reCAPTCHA'
        elif 'hcaptcha' in indicator_lower:
            return 'hCaptcha'
        elif 'cloudflare' in indicator_lower:
            return 'Cloudflare'
        else:
            return 'Custom'
    
    @staticmethod
    async def wait_for_captcha_solution(page: Page, timeout: int = 300) -> bool:
        """
        Wait for CAPTCHA to be solved (manual or automated).
        
        Args:
            page: Playwright page object
            timeout: Max wait time in seconds
            
        Returns:
            True if solved, False if timeout
        """
        import asyncio
        
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            captcha = await CAPTCHADetector.detect(page)
            
            if not captcha or not captcha['detected']:
                logger.info("CAPTCHA solved!")
                return True
            
            await asyncio.sleep(2)  # Check every 2 seconds
        
        logger.error(f"CAPTCHA not solved after {timeout}s")
        return False
