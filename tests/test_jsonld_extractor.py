"""Unit tests for JSON-LD extractor."""
import pytest
import json
from jsonld_extractor import JSONLDExtractor


class TestJSONLDExtractor:
    """Test JSON-LD extraction functionality."""
    
    def test_is_product(self):
        """Test product type detection."""
        assert JSONLDExtractor._is_product({'@type': 'Product'}) is True
        assert JSONLDExtractor._is_product({'@type': ['Product', 'Thing']}) is True
        assert JSONLDExtractor._is_product({'@type': 'WebPage'}) is False
    
    def test_extract_price(self):
        """Test price extraction from offer."""
        offer = {'price': '129000', 'priceCurrency': 'IRR'}
        assert JSONLDExtractor._extract_price(offer) == 129000.0
        
        offer2 = {'price': 129000}
        assert JSONLDExtractor._extract_price(offer2) == 129000.0
    
    def test_extract_product_data_simple(self):
        """Test product data extraction."""
        schema = {
            '@type': 'Product',
            'name': 'Test Product',
            'offers': {
                'price': 129000,
                'priceCurrency': 'IRR',
                'availability': 'InStock'
            },
            'brand': {'name': 'TestBrand'},
            'sku': 'SKU123'
        }
        
        result = JSONLDExtractor.extract_product_data(schema)
        assert result['name'] == 'Test Product'
        assert result['price'] == 129000
        assert result['currency'] == 'IRR'
        assert result['brand'] == 'TestBrand'
        assert result['sku'] == 'SKU123'
    
    def test_extract_product_data_array_offers(self):
        """Test with array of offers."""
        schema = {
            '@type': 'Product',
            'name': 'Test Product',
            'offers': [
                {'price': 100000, 'priceCurrency': 'IRR'},
                {'price': 120000, 'priceCurrency': 'IRR'}
            ]
        }
        
        result = JSONLDExtractor.extract_product_data(schema)
        assert result['price'] == 100000  # Takes first offer
    
    def test_find_product_schema_direct(self):
        """Test finding product in direct object."""
        objects = [
            {'@type': 'WebPage'},
            {'@type': 'Product', 'name': 'Test'}
        ]
        
        result = JSONLDExtractor.find_product_schema(objects)
        assert result is not None
        assert result['name'] == 'Test'
    
    def test_find_product_schema_graph(self):
        """Test finding product in @graph."""
        objects = [{
            '@graph': [
                {'@type': 'WebPage'},
                {'@type': 'Product', 'name': 'Test'}
            ]
        }]
        
        result = JSONLDExtractor.find_product_schema(objects)
        assert result is not None
        assert result['name'] == 'Test'
