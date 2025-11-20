"""
JSON-LD Extraction System

Extracts structured data from application/ld+json scripts - the gold standard
for e-commerce data extraction. Provides highest accuracy with minimal parsing.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from playwright.async_api import Page

logger = logging.getLogger("JSONLDExtractor")


class JSONLDExtractor:
    """
    Extracts and parses JSON-LD structured data from web pages.
    
    JSON-LD (JavaScript Object Notation for Linked Data) is the preferred
    format for embedding structured data in HTML. Most modern e-commerce sites
    implement Schema.org Product markup via JSON-LD.
    """
    
    @staticmethod
    async def extract_all(page: Page) -> List[Dict[str, Any]]:
        """
        Extract all JSON-LD blocks from a page.
        
        Args:
            page: Playwright page object
            
        Returns:
            List of parsed JSON-LD objects
        """
        try:
            # Find all JSON-LD script tags
            scripts = await page.locator('script[type="application/ld+json"]').all()
            
            if not scripts:
                logger.debug("No JSON-LD scripts found on page")
                return []
            
            json_ld_objects = []
            
            for script in scripts:
                try:
                    content = await script.inner_text()
                    if content.strip():
                        # Parse JSON safely
                        parsed = json.loads(content)
                        json_ld_objects.append(parsed)
                        logger.debug(f"Parsed JSON-LD object: {parsed.get('@type', 'Unknown')}")
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON-LD: {e}")
                except Exception as e:
                    logger.warning(f"Error extracting JSON-LD: {e}")
            
            logger.info(f"Extracted {len(json_ld_objects)} JSON-LD objects")
            return json_ld_objects
            
        except Exception as e:
            logger.error(f"JSON-LD extraction failed: {e}")
            return []
    
    @staticmethod
    def find_product_schema(json_ld_objects: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Find Product schema from JSON-LD objects.
        
        Args:
            json_ld_objects: List of parsed JSON-LD objects
            
        Returns:
            Product schema dict or None
        """
        for obj in json_ld_objects:
            # Handle @graph arrays
            if '@graph' in obj:
                for item in obj['@graph']:
                    if JSONLDExtractor._is_product(item):
                        return item
            
            # Direct product object
            if JSONLDExtractor._is_product(obj):
                return obj
        
        return None
    
    @staticmethod
    def _is_product(obj: Dict[str, Any]) -> bool:
        """Check if object is a Product schema."""
        type_field = obj.get('@type', '')
        
        # Handle array of types
        if isinstance(type_field, list):
            return 'Product' in type_field
        
        return type_field == 'Product'
    
    @staticmethod
    def extract_product_data(product_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured product data from Product schema.
        
        Args:
            product_schema: Product JSON-LD object
            
        Returns:
            Normalized product data dict
        """
        try:
            # Extract name
            name = product_schema.get('name', '')
            
            # Extract price (offers can be single object or array)
            offers = product_schema.get('offers', {})
            price = 0
            currency = ""
            availability = ""
            
            if isinstance(offers, dict):
                price = JSONLDExtractor._extract_price(offers)
                currency = offers.get('priceCurrency', '')
                availability = offers.get('availability', '')
            elif isinstance(offers, list) and offers:
                # Take first offer
                price = JSONLDExtractor._extract_price(offers[0])
                currency = offers[0].get('priceCurrency', '')
                availability = offers[0].get('availability', '')
            
            # Extract images
            image_field = product_schema.get('image', [])
            images = []
            if isinstance(image_field, str):
                images = [image_field]
            elif isinstance(image_field, list):
                images = image_field
            
            # Extract rating
            rating_obj = product_schema.get('aggregateRating', {})
            rating_value = rating_obj.get('ratingValue', 0)
            review_count = rating_obj.get('reviewCount', 0)
            
            # Extract SKU/GTIN
            sku = product_schema.get('sku', '')
            gtin = product_schema.get('gtin', '') or product_schema.get('gtin13', '')
            
            # Extract brand
            brand_obj = product_schema.get('brand', {})
            brand = brand_obj.get('name', '') if isinstance(brand_obj, dict) else str(brand_obj)
            
            # Extract description
            description = product_schema.get('description', '')
            
            result = {
                'name': name,
                'price': price,
                'currency': currency,
                'availability': availability,
                'images': images,
                'rating': rating_value,
                'review_count': review_count,
                'sku': sku,
                'gtin': gtin,
                'brand': brand,
                'description': description,
                'source': 'jsonld'
            }
            
            logger.info(f"Extracted product from JSON-LD: {name}, Price: {price} {currency}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract product data: {e}")
            return {}
    
    @staticmethod
    def _extract_price(offer: Dict[str, Any]) -> float:
        """Extract numeric price from offer object."""
        price_str = offer.get('price', 0)
        
        # Handle string prices
        if isinstance(price_str, str):
            # Remove non-numeric characters
            import re
            price_str = re.sub(r'[^\d.]', '', price_str)
            try:
                return float(price_str)
            except ValueError:
                return 0.0
        
        return float(price_str)
    
    @staticmethod
    async def extract_from_page(page: Page) -> Optional[Dict[str, Any]]:
        """
        Main entry point: Extract product data from page via JSON-LD.
        
        Args:
            page: Playwright page object
            
        Returns:
            Product data dict or None if not found
        """
        # Extract all JSON-LD
        json_ld_objects = await JSONLDExtractor.extract_all(page)
        
        if not json_ld_objects:
            return None
        
        # Find Product schema
        product_schema = JSONLDExtractor.find_product_schema(json_ld_objects)
        
        if not product_schema:
            logger.debug("No Product schema found in JSON-LD")
            return None
        
        # Extract and normalize data
        product_data = JSONLDExtractor.extract_product_data(product_schema)
        
        if product_data and product_data.get('price', 0) > 0:
            logger.info("Successfully extracted product via JSON-LD")
            return product_data
        
        return None
