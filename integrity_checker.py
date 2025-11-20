"""
Data Integrity Checker

Validates data quality with statistical and logical checks before database insertion.
"""

import logging
from typing import Dict, Any, List, Optional
from statistics import mean, median
from datetime import datetime

logger = logging.getLogger("IntegrityChecker")


class DataIntegrityChecker:
    """Comprehensive data validation and integrity checks."""
    
    def __init__(self):
        """Initialize integrity checker."""
        self.price_history: List[int] = []
        self.quarantined_count = 0
    
    def check_product(self, product_data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Comprehensive product data validation.
        
        Args:
            product_data: Product dictionary
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Required fields check
        required = ['title', 'price', 'currency', 'url']
        for field in required:
            if field not in product_data or not product_data[field]:
                errors.append(f"Missing required field: {field}")
        
        # Title validation
        if 'title' in product_data:
            if len(product_data['title']) < 3:
                errors.append("Title too short (< 3 chars)")
            elif len(product_data['title']) > 500:
                errors.append("Title suspiciously long (> 500 chars)")
        
        # Price validation
        if 'price' in product_data:
            price = product_data['price']
            
            # Range check
            if price <= 0:
                errors.append("Price must be positive")
            elif price > 1000000000:
                errors.append("Price unreasonably high (> 1 billion)")
            
            # Statistical outlier detection
            if self.price_history:
                avg_price = mean(self.price_history)
                if price > avg_price * 100:
                    errors.append(f"Price is 100x average ({avg_price:.0f})")
        
        # Currency validation
        valid_currencies = ['Toman', 'Rial', 'USD', 'EUR', 'IRR']
       if 'currency' in product_data:
            if product_data['currency'] not in valid_currencies:
                errors.append(f"Invalid currency: {product_data['currency']}")
        
        # Discount consistency check
        if 'original_price' in product_data and 'price' in product_data:
            original = product_data['original_price']
            current = product_data['price']
            
            if original and current:
                if current > original:
                    errors.append("Sale price higher than original price")
                
                discount_pct = product_data.get('discount_percent', 0)
                if discount_pct:
                    expected_pct = ((original - current) / original) * 100
                    if abs(expected_pct - discount_pct) > 2:
                        errors.append(f"Discount mismatch: claimed {discount_pct}% but actual {expected_pct:.1f}%")
        
        # Confidence check
        if 'confidence' in product_data:
            conf = product_data['confidence']
            if conf < 0.5:
                errors.append(f"Low confidence extraction: {conf}")
        
        # URL validation
        if 'url' in product_data:
            url = str(product_data['url'])
            if 'localhost' in url or '127.0.0.1' in url:
                errors.append("Localhost URL not allowed")
        
        is_valid = len(errors) == 0
        
        if is_valid:
            # Add to history for statistical tracking
            if 'price' in product_data:
                self.price_history.append(product_data['price'])
                # Keep only last 1000
                if len(self.price_history) > 1000:
                    self.price_history = self.price_history[-1000:]
        else:
            self.quarantined_count += 1
            logger.warning(f"Data failed integrity checks: {errors}")
        
        return is_valid, errors
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get integrity checker statistics."""
        if not self.price_history:
            return {
                'total_validated': 0,
                'quarantined': self.quarantined_count
            }
        
        return {
            'total_validated': len(self.price_history),
            'quarantined': self.quarantined_count,
            'avg_price': mean(self.price_history),
            'median_price': median(self.price_history),
            'min_price': min(self.price_history),
            'max_price': max(self.price_history)
        }
    
    def quarantine(self, product_data: Dict[str, Any], errors: List[str]):
        """
        Quarantine invalid data for manual review.
        
        Args:
            product_data: Invalid product data
            errors: List of validation errors
        """
        quarantine_entry = {
            'timestamp': datetime.now().isoformat(),
            'data': product_data,
            'errors': errors
        }
        
        # Log to file for admin review
        logger.error(f"QUARANTINED: {quarantine_entry}")
