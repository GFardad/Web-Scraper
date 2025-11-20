"""Unit tests for extraction strategies."""
import pytest
from extraction_strategies import Utils, PriceCandidate


class TestUtils:
    """Test utility functions."""
    
    def test_clean_price_data_persian(self):
        """Test Persian digit normalization."""
        assert Utils.clean_price_data("۱۲۹,۰۰۰ تومان") == 129000
        assert Utils.clean_price_data("۱,۲۹۰,۰۰۰ ریال") == 1290000
    
    def test_clean_price_data_arabic(self):
        """Test Arabic digit normalization."""
        assert Utils.clean_price_data("٥٠٠ تومان") == 500
    
    def test_clean_price_data_mixed(self):
        """Test mixed formats."""
        assert Utils.clean_price_data("Price: 129,000") == 129000
        assert Utils.clean_price_data("$1,234.56") == 123456
    
    def test_clean_price_data_empty(self):
        """Test empty input."""
        assert Utils.clean_price_data("") == 0
        assert Utils.clean_price_data(None) == 0
    
    def test_is_installment_text(self):
        """Test installment detection."""
        assert Utils.is_installment_text("4 قسط ماهانه") is True
        assert Utils.is_installment_text("با اسنپ‌پی") is True
        assert Utils.is_installment_text("129,000 تومان") is False
    
    def test_is_product_id(self):
        """Test product ID detection."""
        url = "https://site.com/product/12345"
        assert Utils.is_product_id("12345", url) is True
        assert Utils.is_product_id("129000", url) is False
        assert Utils.is_product_id("99999999999", url) is True  # Very large


class TestPriceCandidate:
    """Test PriceCandidate class."""
    
    def test_creation(self):
        """Test candidate creation."""
        cand = PriceCandidate(129000, "Toman", "۱۲۹,۰۰۰ تومان", 0.95, "Strategy1")
        assert cand.price == 129000
        assert cand.currency == "Toman"
        assert cand.confidence == 0.95
    
    def test_repr(self):
        """Test string representation."""
        cand = PriceCandidate(129000, "Toman", "raw", 0.95, "Strategy1")
        repr_str = repr(cand)
        assert "129,000" in repr_str
        assert "0.95" in repr_str


@pytest.mark.asyncio
class TestStrategiesIntegration:
    """Integration tests for strategies (require browser)."""
    
    async def test_jsonld_extraction(self):
        """Test JSON-LD extraction with fixture."""
        # This would use a local HTML fixture
        # For now, placeholder
        assert True  # Placeholder
