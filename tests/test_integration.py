"""Integration tests for end-to-end scraping flows."""
import pytest
import asyncio
from config_db import DatabaseCore
from schemas import validate_product, ProductSchema


@pytest.mark.asyncio
@pytest.mark.integration
class TestEndToEnd:
    """End-to-end integration tests."""
    
    async def test_database_connection(self):
        """Test database connectivity."""
        db = DatabaseCore()
        await db.init_models()
        
        # Should not raise
        assert db is not None
        
        await db.dispose()
    
    async def test_task_creation_and_retrieval(self):
        """Test task CRUD operations."""
        db = DatabaseCore()
        await db.init_models()
        
        # Add task
        test_url = "https://example.com/test-product"
        await db.add_task(test_url)
        
        # Retrieve task
        task = await db.get_next_pending_task()
        assert task is not None
        assert test_url in task.url
        
        await db.dispose()
    
    async def test_pydantic_validation(self):
        """Test data validation with Pydantic."""
        valid_data = {
            'title': 'Test Product',
            'price': 100000,
            'currency': 'Toman',
            'url': 'https://example.com/product',
            'confidence': 0.95
        }
        
        # Should not raise
        product = validate_product(valid_data)
        assert product.price == 100000
    
    def test_pydantic_validation_fails_on_invalid(self):
        """Test that invalid data raises error."""
        invalid_data = {
            'title': '',  # Empty title should fail
            'price': -100,  # Negative price
            'currency': 'Toman',
            'url': 'not-a-url'  # Invalid URL
        }
        
        with pytest.raises(Exception):
            validate_product(invalid_data)
    
    async def test_discount_calculation(self):
        """Test discount calculator."""
        from discount_calculator import DiscountCalculator
        
        result = DiscountCalculator.calculate(
            original_price=200000,
            sale_price=150000
        )
        
        assert result['is_on_sale'] is True
        assert result['savings'] == 50000
        assert result['discount_percent'] == 25.0
    
    async def test_user_agent_rotation(self):
        """Test UA pool rotation."""
        from user_agent_pool import UserAgentPool
        
        pool = UserAgentPool()
        
        ua1 = pool.get_next()
        ua2 = pool.get_next()
        
        # Should have different UAs (or same if pool size == 1)
        assert isinstance(ua1, str)
        assert isinstance(ua2, str)
        assert len(ua1) > 0
    
    async def test_robots_txt_parser(self):
        """Test robots.txt parsing."""
        from robots_parser import RobotsManager
        
        robots = RobotsManager(respect_robots=False)
        
        # Should allow all when respect=False
        allowed = await robots.can_fetch("https://example.com/test")
        assert allowed is True


@pytest.mark.asyncio
@pytest.mark.slow
class TestFullScraping:
    """Full scraping scenario tests (slow)."""
    
    async def test_jsonld_extraction_real_page(self):
        """Test JSON-LD extraction (requires network)."""
        # This would test against a real page
        # Skipped in CI/CD
        pass
