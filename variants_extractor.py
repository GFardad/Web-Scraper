"""
Product Variants Extraction

Extracts all product variants (colors, sizes, SKUs) from e-commerce pages.
Uses both JSON-LD and interactive DOM manipulation.
"""

import logging
from typing import List, Dict, Any, Optional
from playwright.async_api import Page

logger = logging.getLogger("VariantsExtractor")


class ProductVariant:
    """Represents a single product variant."""
    
    def __init__(
        self,
        variant_type: str,  # "color", "size", "material"
        variant_value: str,  # "Red", "XL", "Cotton"
        price: Optional[int] = None,
        availability: str = "Unknown",
        sku: Optional[str] = None,
        url: Optional[str] = None
    ):
        self.variant_type = variant_type
        self.variant_value = variant_value
        self.price = price
        self.availability = availability
        self.sku = sku
        self.url = url
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'type': self.variant_type,
            'value': self.variant_value,
            'price': self.price,
            'availability': self.availability,
            'sku': self.sku,
            'url': self.url
        }


class VariantsExtractor:
    """Extract product variants from pages."""
    
    @staticmethod
    async def extract_from_jsonld(jsonld_data: Dict[str, Any]) -> List[ProductVariant]:
        """
        Extract variants from JSON-LD Product schema.
        
        JSON-LD may include hasVariant property with variant info.
        """
        variants = []
        
        if 'hasVariant' in jsonld_data:
            variant_list = jsonld_data['hasVariant']
            if not isinstance(variant_list, list):
                variant_list = [variant_list]
            
            for var in variant_list:
                # Extract variant properties
                variant_name = var.get('name', '')
                offers = var.get('offers', {})
                
                price = None
                if isinstance(offers, dict):
                    price_str = offers.get('price', 0)
                    try:
                        price = int(float(price_str))
                    except:
                        pass
                
                availability = offers.get('availability', '') if isinstance(offers, dict) else ''
                sku = var.get('sku', '')
                
                # Determine variant type and value
                # This is heuristic-based
                variant_type = "variant"
                variant_value = variant_name
                
                variant = ProductVariant(
                    variant_type=variant_type,
                    variant_value=variant_value,
                    price=price,
                    availability=availability,
                    sku=sku
                )
                variants.append(variant)
        
        return variants
    
    @staticmethod
    async def extract_from_dom(page: Page) -> List[ProductVariant]:
        """
        Extract variants by interacting with DOM elements.
        
        Looks for:
        - Color swatches
        - Size buttons/dropdowns
        - Variant selectors
        """
        variants = []
        
        # Common variant selectors
        variant_selectors = [
            'button[data-variant]',
            '.product-variant',
            '.color-swatch',
            '.size-option',
            'select[data-variant-selector]',
            '[class*="variant"]',
        ]
        
        for selector in variant_selectors:
            try:
                elements = await page.locator(selector).all()
                
                for el in elements:
                    try:
                        # Get variant info from element
                        text = await el.inner_text()
                        data_variant = await el.get_attribute('data-variant')
                        data_value = await el.get_attribute('data-value')
                        
                        variant_value = data_value or text.strip()
                        
                        if variant_value:
                            # Determine type based on selector
                            variant_type = "color" if "color" in selector else "size" if "size" in selector else "variant"
                            
                            variant = ProductVariant(
                                variant_type=variant_type,
                                variant_value=variant_value
                            )
                            variants.append(variant)
                    except:
                        continue
            except:
                continue
        
        return variants
    
    @staticmethod
    async def extract_all(page: Page, jsonld_data: Optional[Dict[str, Any]] = None) -> List[ProductVariant]:
        """
        Extract all variants using all available methods.
        
        Args:
            page: Playwright page
            jsonld_data: Optional JSON-LD data if already extracted
            
        Returns:
            List of ProductVariant objects
        """
        all_variants = []
        
        # Try JSON-LD first
        if jsonld_data:
            try:
                jsonld_variants = await VariantsExtractor.extract_from_jsonld(jsonld_data)
                all_variants.extend(jsonld_variants)
                logger.info(f"Extracted {len(jsonld_variants)} variants from JSON-LD")
            except Exception as e:
                logger.debug(f"JSON-LD variant extraction failed: {e}")
        
        # Try DOM extraction
        try:
            dom_variants = await VariantsExtractor.extract_from_dom(page)
            all_variants.extend(dom_variants)
            logger.info(f"Extracted {len(dom_variants)} variants from DOM")
        except Exception as e:
            logger.debug(f"DOM variant extraction failed: {e}")
        
        # Deduplicate
        unique_variants = []
        seen = set()
        for var in all_variants:
            key = (var.variant_type, var.variant_value)
            if key not in seen:
                seen.add(key)
                unique_variants.append(var)
        
        logger.info(f"Total unique variants: {len(unique_variants)}")
        return unique_variants
