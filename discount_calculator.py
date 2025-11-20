"""
Discount Calculation Engine

Automatically detects and calculates discount percentages and savings.
Handles multiple price scenarios (original, sale, strikethrough).
"""

import logging
import re
from typing import Optional, Dict, Any
from playwright.async_api import Page

logger = logging.getLogger("DiscountCalculator")


class DiscountCalculator:
    """Calculate discounts from price data."""
    
    @staticmethod
    def calculate(original_price: int, sale_price: int) -> Dict[str, Any]:
        """
        Calculate discount information.
        
        Args:
            original_price: Original/regular price
            sale_price: Current/sale price
            
        Returns:
            Dict with discount_percent, savings, is_on_sale
        """
        if original_price <= 0 or sale_price <= 0:
            return {
                'discount_percent': 0.0,
                'savings': 0,
                'is_on_sale': False
            }
        
        if sale_price >= original_price:
            return {
                'discount_percent': 0.0,
                'savings': 0,
                'is_on_sale': False
            }
        
        savings = original_price - sale_price
        discount_percent = (savings / original_price) * 100
        
        return {
            'discount_percent': round(discount_percent, 2),
            'savings': savings,
            'is_on_sale': True
        }
    
    @staticmethod
    async def extract_from_page(page: Page) -> Optional[Dict[str, Any]]:
        """
        Extract discount information from page DOM.
        
        Looks for:
        - Strikethrough prices (original)
        - Sale/final prices
        - Discount badges/labels
        """
        try:
            # Find elements with line-through (original price)
            elements = await page.locator('div, span, p').all()
            
            original_price = None
            sale_price = None
            
            for el in elements[:200]:
                try:
                    text = await el.inner_text()
                    
                    # Check if strikethrough (original price)
                    try:
                        styles = await el.evaluate('el => window.getComputedStyle(el).textDecoration')
                        if 'line-through' in styles:
                            # This is likely the original price
                            from extraction_strategies import Utils
                            price = Utils.clean_price_data(text)
                            if price > 1000 and (original_price is None or price > original_price):
                                original_price = price
                                logger.debug(f"Found original price (strikethrough): {price}")
                    except:
                        pass
                    
                    # Look for "discount" or "off" text
                    if '%' in text and ('discount' in text.lower() or 'تخفیف' in text or 'off' in text.lower()):
                        # Extract percentage
                        match = re.search(r'(\d+)\s*%', text)
                        if match:
                            discount_pct = int(match.group(1))
                            logger.info(f"Found discount badge: {discount_pct}%")
                except:
                    continue
            
            if original_price:
                logger.info(f"Detected discount: original={original_price}")
                return {'original_price': original_price}
            
            return None
            
        except Exception as e:
            logger.error(f"Discount extraction failed: {e}")
            return None
    
    @staticmethod
    def validate_discount(original: int, sale: int, claimed_percent: float) -> bool:
        """
        Validate if claimed discount matches actual prices.
        
        Returns:
            True if valid, False if misleading
        """
        actual = DiscountCalculator.calculate(original, sale)
        actual_percent = actual['discount_percent']
        
        # Allow 1% tolerance
        return abs(actual_percent - claimed_percent) <= 1.0
