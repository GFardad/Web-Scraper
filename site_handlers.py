"""Site-specific scraping handlers using multi-strategy intelligent extraction."""
import logging
from typing import Dict, Any
from playwright.async_api import Page
from extraction_strategies import IntelligentExtractor, Utils

logger = logging.getLogger("SiteHandlers")


class DigikalaHandler:
    """Handler for Digikala.com using intelligent extraction."""
    
    @staticmethod
    async def can_handle(url: str) -> bool:
        return 'digikala.com' in url.lower()
    
    @staticmethod
    async def extract_price(page: Page, url: str) -> Dict[str, Any]:
        logger.info("Using Digikala handler with multi-strategy extraction")
        
        # Handle popup
        try:
            popup_button = page.locator('button:has-text("فعلا نه")')
            await popup_button.wait_for(state="visible", timeout=3000)
            await popup_button.click()
            logger.info("Dismissed Digikala popup")
            await page.wait_for_timeout(1000)
        except:
            logger.debug("No popup to dismiss")
        
        # Use intelligent multi-strategy extraction
        result = await IntelligentExtractor.extract_price(page, url)
        result['source'] = 'digikala'
        return result


class KhanoumiHandler:
    """Handler for Khanoumi.com using intelligent extraction."""
    
    @staticmethod
    async def can_handle(url: str) -> bool:
        return 'khanoumi.com' in url.lower()
    
    @staticmethod
    async def extract_price(page: Page, url: str) -> Dict[str, Any]:
        logger.info("Using Khanoumi handler with multi-strategy extraction")
        
        # Use intelligent multi-strategy extraction
        result = await IntelligentExtractor.extract_price(page, url)
        result['source'] = 'khanoumi'
        return result


class LicenseMarketHandler:
    """Handler for license-market.ir"""
    
    @staticmethod
    async def can_handle(url: str) -> bool:
        return 'license-market.ir' in url.lower()
    
    @staticmethod
    async def extract_price(page: Page, url: str) -> Dict[str, Any]:
        logger.info("Using LicenseMarket handler with multi-strategy extraction")
        
        result = await IntelligentExtractor.extract_price(page, url)
        result['source'] = 'license-market'
        return result


class AccsellHandler:
    """Handler for accsell.ir"""
    
    @staticmethod
    async def can_handle(url: str) -> bool:
        return 'accsell.ir' in url.lower()
    
    @staticmethod
    async def extract_price(page: Page, url: str) -> Dict[str, Any]:
        logger.info("Using Accsell handler with multi-strategy extraction")
        
        result = await IntelligentExtractor.extract_price(page, url)
        result['source'] = 'accsell'
        return result


class IranianCardHandler:
    """Handler for iranicard.ir"""
    
    @staticmethod
    async def can_handle(url: str) -> bool:
        return 'iranicard.ir' in url.lower()
    
    @staticmethod
    async def extract_price(page: Page, url: str) -> Dict[str, Any]:
        logger.info("Using IranianCard handler with multi-strategy extraction")
        
        result = await IntelligentExtractor.extract_price(page, url)
        result['source'] = 'iranicard'
        return result


class ParsPremiumHandler:
    """Handler for parspremium.ir"""
    
    @staticmethod
    async def can_handle(url: str) -> bool:
        return 'parspremium.ir' in url.lower()
    
    @staticmethod
    async def extract_price(page: Page, url: str) -> Dict[str, Any]:
        logger.info("Using ParsPremium handler with multi-strategy extraction")
        
        result = await IntelligentExtractor.extract_price(page, url)
        result['source'] = 'parspremium'
        return result


class TorobHandler:
    """Handler for torob.com"""
    
    @staticmethod
    async def can_handle(url: str) -> bool:
        return 'torob.com' in url.lower()
    
    @staticmethod
    async def extract_price(page: Page, url: str) -> Dict[str, Any]:
        logger.info("Using Torob handler with multi-strategy extraction")
        
        result = await IntelligentExtractor.extract_price(page, url)
        result['source'] = 'torob'
        return result


class IranGetHandler:
    """Handler for iranget.com"""
    
    @staticmethod
    async def can_handle(url: str) -> bool:
        return 'iranget.com' in url.lower()
    
    @staticmethod
    async def extract_price(page: Page, url: str) -> Dict[str, Any]:
        logger.info("Using IranGet handler with multi-strategy extraction")
        
        result = await IntelligentExtractor.extract_price(page, url)
        result['source'] = 'iranget'
        return result


class SpotifyAccHandler:
    """Handler for spotify-acc.ir"""
    
    @staticmethod
    async def can_handle(url: str) -> bool:
        return 'spotify-acc.ir' in url.lower()
    
    @staticmethod
    async def extract_price(page: Page, url: str) -> Dict[str, Any]:
        logger.info("Using SpotifyAcc handler with multi-strategy extraction")
        
        result = await IntelligentExtractor.extract_price(page, url)
        result['source'] = 'spotify-acc'
        return result


class NetUserAccHandler:
    """Handler for netuseracc.com"""
    
    @staticmethod
    async def can_handle(url: str) -> bool:
        return 'netuseracc.com' in url.lower()
    
    @staticmethod
    async def extract_price(page: Page, url: str) -> Dict[str, Any]:
        logger.info("Using NetUserAcc handler with multi-strategy extraction")
        
        result = await IntelligentExtractor.extract_price(page, url)
        result['source'] = 'netuseracc'
        return result


class NumberLandHandler:
    """Handler for numberland.ir"""
    
    @staticmethod
    async def can_handle(url: str) -> bool:
        return 'numberland.ir' in url.lower()
    
    @staticmethod
    async def extract_price(page: Page, url: str) -> Dict[str, Any]:
        logger.info("Using NumberLand handler with multi-strategy extraction")
        
        result = await IntelligentExtractor.extract_price(page, url)
        result['source'] = 'numberland'
        return result


class GenericHandler:
    """Fallback handler for unknown sites using intelligent extraction."""
    
    @staticmethod
    async def can_handle(url: str) -> bool:
        return True
    
    @staticmethod
    async def extract_price(page: Page, url: str) -> Dict[str, Any]:
        logger.info("Using Generic handler with multi-strategy extraction")
        
        result = await IntelligentExtractor.extract_price(page, url)
        result['source'] = 'generic'
        return result


# Handler registry (order matters - first match wins)
HANDLERS = [
    DigikalaHandler,
    KhanoumiHandler,
    LicenseMarketHandler,
    AccsellHandler,
    IranianCardHandler,
    ParsPremiumHandler,
    TorobHandler,
    IranGetHandler,
    SpotifyAccHandler,
    NetUserAccHandler,
    NumberLandHandler,
    GenericHandler,  # Always last
]


async def get_handler_for_url(url: str):
    """Get the appropriate handler for a URL."""
    for handler_class in HANDLERS:
        if await handler_class.can_handle(url):
            return handler_class
    return GenericHandler
