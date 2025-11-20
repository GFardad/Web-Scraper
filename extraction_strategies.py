"""
Multi-Strategy Intelligent Price Extraction Engine

This module implements multiple extraction strategies with intelligent
fallback and confidence-based selection to maximize accuracy across
different website structures and anti-bot measures.
"""

import re
import logging
import math
from typing import Dict, Any, Optional, List, Tuple
from playwright.async_api import Page, Locator
from playwright_stealth import Stealth
from jsonld_extractor import JSONLDExtractor

logger = logging.getLogger("ExtractionStrategies")


class PriceCandidate:
    """Represents a potential price with confidence score."""
    
    def __init__(self, price: int, currency: str, raw_text: str, confidence: float, method: str):
        self.price = price
        self.currency = currency
        self.raw_text = raw_text
        self.confidence = confidence
        self.method = method
    
    def __repr__(self):
        return f"PriceCandidate({self.price:,} {self.currency}, conf={self.confidence:.2f}, method={self.method})"


class Utils:
    """Utility functions for text processing."""
    
    @staticmethod
    def clean_price_data(raw_text: str) -> int:
        """Clean and normalize price text to integer."""
        if not raw_text:
            return 0
            
        persian_map = {
            '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
            '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
        }
        
        arabic_map = {
            '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
            '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9',
        }
        
        text = raw_text
        for persian, english in {**persian_map, **arabic_map}.items():
            text = text.replace(persian, english)
        
        digits_only = re.sub(r'[^\d]', '', text)
        
        try:
            return int(digits_only) if digits_only else 0
        except ValueError:
            return 0
    
    @staticmethod
    def is_installment_text(text: str) -> bool:
        """Check if text is about installments."""
        installment_keywords = ['قسط', 'ماهانه', 'ماهیانه', 'اقساط', 'اسنپ']
        return any(kw in text for kw in installment_keywords)
    
    @staticmethod
    def is_product_id(text: str, url: str) -> bool:
        """Check if number is likely a product ID."""
        normalized = Utils.clean_price_data(text)
        digits_only = str(normalized)
        
        if digits_only and digits_only in url:
            return True
        
        if normalized > 10000000 and 'تومان' not in text and 'ریال' not in text:
            return True
            
        return False


class Strategy1_StealthCSS:
    """
    Strategy 1: Stealth Mode + CSS Selectors
    
    Uses playwright-stealth to bypass bot detection and targets
    specific CSS selectors commonly used for prices.
    
    Confidence: HIGH (when selectors match)
    """
    
    @staticmethod
    async def extract(page: Page, url: str) -> Optional[PriceCandidate]:
        """Extract price using stealth and CSS selectors."""
        try:
            # Apply stealth techniques (handled at browser context level)
            
            # Common price selectors across Iranian e-commerce
            price_selectors = [
                'span[data-testid="price-no-discount"]',  # Digikala
                'span[data-testid="price-single"]',
                '.price-final',
                '.product-price',
                '.special-price',
                '.sale-price',
                'div[class*="price"]',
                'span[class*="price"]',
                '[data-price]',
            ]
            
            for selector in price_selectors:
                try:
                    element = page.locator(selector).first
                    await element.wait_for(state="visible", timeout=2000)
                    text = await element.inner_text()
                    
                    if Utils.is_installment_text(text):
                        continue
                    
                    if 'تومان' in text or 'ریال' in text:
                        price = Utils.clean_price_data(text)
                        if 1000 < price < 100000000:
                            currency = "Toman" if 'تومان' in text else "Rial"
                            confidence = 0.95  # High confidence - targeted selector
                            logger.info(f"Strategy1 found price via selector {selector}: {text}")
                            return PriceCandidate(price, currency, text, confidence, "Strategy1_StealthCSS")
                except:
                    continue
            
            return None
        except Exception as e:
            logger.debug(f"Strategy1 failed: {e}")
            return None


class Strategy2_TextScan:
    """
    Strategy 2: Intelligent Text Scanning
    
    Scans all visible text elements, filters out installments,
    and ranks by font size and position.
    
    Confidence: MEDIUM-HIGH
    """
    
    @staticmethod
    async def extract(page: Page, url: str) -> Optional[PriceCandidate]:
        """Extract price by scanning text elements."""
        try:
            candidates = []
            elements = await page.locator('div, span, p, strong, b').all()
            
            for el in elements[:500]:  # Limit scan
                try:
                    text = await el.inner_text()
                    
                    # Filter criteria
                    if len(text) > 100 or len(text) < 3:
                        continue
                    
                    if 'تومان' not in text and 'ریال' not in text:
                        continue
                    
                    if Utils.is_installment_text(text):
                        continue
                    
                    if Utils.is_product_id(text, url):
                        continue
                    
                    # Check if crossed out (old price)
                    try:
                        styles = await el.evaluate('el => window.getComputedStyle(el).textDecoration')
                        if 'line-through' in styles:
                            continue
                    except:
                        pass
                    
                    price = Utils.clean_price_data(text)
                    if 1000 < price < 100000000:
                        # Get font size for ranking
                        try:
                            font_size = await el.evaluate('el => parseFloat(window.getComputedStyle(el).fontSize)')
                        except:
                            font_size = 12
                        
                        # Get bounding box for position
                        try:
                            box = await el.bounding_box()
                            y_pos = box['y'] if box else 9999
                        except:
                            y_pos = 9999
                        
                        currency = "Toman" if 'تومان' in text else "Rial"
                        
                        # Calculate confidence based on font size and position
                        conf = min(0.9, (font_size / 20) * 0.5 + (1 - y_pos / 10000) * 0.4)
                        
                        candidates.append(PriceCandidate(price, currency, text, conf, "Strategy2_TextScan"))
                except:
                    continue
            
            if candidates:
                # Sort by confidence
                candidates.sort(key=lambda x: x.confidence, reverse=True)
                best = candidates[0]
                logger.info(f"Strategy2 found {len(candidates)} candidates, best: {best}")
                return best
            
            return None
        except Exception as e:
            logger.debug(f"Strategy2 failed: {e}")
            return None


class Strategy3_Geometric:
    """
    Strategy 3: Geometric Analysis
    
    Finds H1 title and looks for nearby numbers with appropriate
    font size and distance.
    
    Confidence: MEDIUM
    """
    
    @staticmethod
    async def extract(page: Page, url: str) -> Optional[PriceCandidate]:
        """Extract price using geometric proximity to title."""
        try:
            # Find H1
            h1 = page.locator("h1").first
            await h1.wait_for(state="visible", timeout=5000)
            h1_box = await h1.bounding_box()
            
            if not h1_box:
                return None
            
            candidates = []
            elements = await page.locator('div, span, p').all()
            
            for el in elements[:300]:
                try:
                    text = await el.inner_text()
                    
                    if 'تومان' not in text and 'ریال' not in text:
                        continue
                    
                    if Utils.is_installment_text(text):
                        continue
                    
                    box = await el.bounding_box()
                    if not box:
                        continue
                    
                    # Calculate distance from H1
                    distance = math.sqrt(
                        (h1_box['x'] - box['x'])**2 + 
                        (h1_box['y'] - box['y'])**2
                    )
                    
                    if distance > 900:
                        continue
                    
                    price = Utils.clean_price_data(text)
                    if 1000 < price < 100000000:
                        # Get font size
                        try:
                            font_size = await el.evaluate('el => parseFloat(window.getComputedStyle(el).fontSize)')
                        except:
                            font_size = 12
                        
                        # Confidence based on distance and font
                        conf = min(0.85, (1000 / (distance + 1)) * 0.3 + (font_size / 20) * 0.4)
                        
                        currency = "Toman" if 'تومان' in text else "Rial"
                        candidates.append(PriceCandidate(price, currency, text, conf, "Strategy3_Geometric"))
                except:
                    continue
            
            if candidates:
                candidates.sort(key=lambda x: x.confidence, reverse=True)
                best = candidates[0]
                logger.info(f"Strategy3 found {len(candidates)} candidates, best: {best}")
                return best
            
            return None
        except Exception as e:
            logger.debug(f"Strategy3 failed: {e}")
            return None


class IntelligentExtractor:
    """
    Intelligent multi-strategy price extractor.
    
    Tries all strategies and selects the best result based on confidence.
    """
    
    @staticmethod
    async def extract_price(page: Page, url: str) -> Dict[str, Any]:
        """
        Execute all extraction strategies and return best result.
        
        Strategy Priority:
        0. JSON-LD (confidence: 0.98) - Gold standard
        1. Stealth+CSS (confidence: 0.95)
        2. Text Scan (confidence: 0.5-0.9)
        3. Geometric (confidence: 0.4-0.85)
        
        Returns:
            Dict with title, price, currency, confidence, method
        """
        # Extract title first
        try:
            h1 = page.locator("h1").first
            await h1.wait_for(state="visible", timeout=10000)
            title = await h1.inner_text()
        except:
            title = "Unknown Product"
        
        all_candidates: List[PriceCandidate] = []
        
        # Strategy 0: JSON-LD (Highest Priority)
        try:
            logger.info("Trying Strategy0_JSONLD...")
            jsonld_data = await JSONLDExtractor.extract_from_page(page)
            
            if jsonld_data and jsonld_data.get('price', 0) > 0:
                price_int = int(jsonld_data['price'])
                
                # Determine currency
                currency_str = jsonld_data.get('currency', '').upper()
                if 'IRR' in currency_str or 'RIAL' in currency_str:
                    currency = "Rial"
                elif 'TOMAN' in currency_str or not currency_str:
                    # Default to Toman for Iranian sites
                    currency = "Toman"
                else:
                    currency = currency_str
                
                candidate = PriceCandidate(
                    price=price_int,
                    currency=currency,
                    raw_text=f"{jsonld_data['price']} {jsonld_data.get('currency', '')}",
                    confidence=0.98,  # Highest confidence
                    method="Strategy0_JSONLD"
                )
                all_candidates.append(candidate)
                logger.info(f"JSON-LD extraction successful: {candidate}")
        except Exception as e:
            logger.debug(f"Strategy0_JSONLD error: {e}")
        
        # Try other strategies
        strategies = [
            Strategy1_StealthCSS,
            Strategy2_TextScan,
            Strategy3_Geometric,
        ]
        
        for strategy in strategies:
            try:
                logger.info(f"Trying {strategy.__name__}...")
                result = await strategy.extract(page, url)
                if result:
                    all_candidates.append(result)
            except Exception as e:
                logger.warning(f"{strategy.__name__} error: {e}")
        
        if not all_candidates:
            raise Exception("All extraction strategies failed")
        
        # Select best candidate (highest confidence)
        all_candidates.sort(key=lambda x: x.confidence, reverse=True)
        best = all_candidates[0]
        
        logger.info(f"WINNER: {best} from {len(all_candidates)} candidates")
        
        # Log alternatives for debugging
        for i, cand in enumerate(all_candidates[:5]):
            logger.debug(f"  #{i+1}: {cand}")
        
        return {
            "title": title.strip(),
            "price": best.price,
            "currency": best.currency,
            "raw": best.raw_text,
            "confidence": best.confidence,
            "method": best.method,
            "alternatives": len(all_candidates)
        }

