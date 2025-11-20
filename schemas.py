"""
Pydantic Data Validation Schemas

Enforces strict data types and validation rules before database insertion.
Ensures data integrity and provides auto-documentation.
"""

from typing import Optional, List
from pydantic import BaseModel, HttpUrl, validator, Field
from datetime import datetime


class ProductSchema(BaseModel):
    """
    Validated product data schema.
    
    All fields are strictly typed and validated.
    """
    
    title: str = Field(..., min_length=1, max_length=500, description="Product title")
    price: int = Field(..., gt=0, description="Price in smallest currency unit")
    currency: str = Field(..., pattern="^(Toman|Rial|USD|EUR)$", description="Currency code")
    url: HttpUrl = Field(..., description="Product URL")
    
    # Optional fields
    raw_price: Optional[str] = Field(None, description="Raw price text")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Extraction confidence")
    method: Optional[str] = Field(None, description="Extraction method used")
    source: Optional[str] = Field(None, description="Source site")
    images: Optional[List[HttpUrl]] = Field(default_factory=list, description="Product images")
    rating: Optional[float] = Field(None, ge=0.0, le=5.0, description="Product rating")
    review_count: Optional[int] = Field(None, ge=0, description="Number of reviews")
    availability: Optional[str] = Field(None, description="Stock availability")
    sku: Optional[str] = Field(None, description="SKU/Product ID")
    brand: Optional[str] = Field(None, description="Brand name")
    
    # Discount information
    original_price: Optional[int] = Field(None, gt=0, description="Original price before discount")
    discount_percent: Optional[float] = Field(None, ge=0.0, le=100.0, description="Discount percentage")
    
    # Metadata
    scraped_at: datetime = Field(default_factory=datetime.now, description="Scrape timestamp")
    
    @validator('title')
    def title_not_empty(cls, v):
        """Ensure title is not just whitespace."""
        if not v.strip():
            raise ValueError('Title cannot be empty or whitespace')
        return v.strip()
    
    @validator('price')
    def price_reasonable(cls, v):
        """Ensure price is within reasonable range."""
        if v > 1000000000:  # 1 billion
            raise ValueError('Price seems unreasonably high')
        return v
    
    @validator('discount_percent', always=True)
    def calculate_discount(cls, v, values):
        """Auto-calculate discount if not provided."""
        if v is None and 'original_price' in values and 'price' in values:
            original = values.get('original_price')
            current = values.get('price')
            if original and current and original > current:
                v = ((original - current) / original) * 100
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Example Product",
                "price": 129000,
                "currency": "Toman",
                "url": "https://example.com/product/123",
                "confidence": 0.95,
                "method": "Strategy0_JSONLD"
            }
        }


class TaskSchema(BaseModel):
    """Validated scraping task schema."""
    
    url: HttpUrl = Field(..., description="URL to scrape")
    priority: int = Field(default=5, ge=1, le=10, description="Task priority (1=low, 10=high)")
    max_attempts: int = Field(default=3, ge=1, le=10, description="Maximum retry attempts")
    enable_pagination: bool = Field(default=False, description="Enable pagination")
    
    @validator('url')
    def url_not_localhost(cls, v):
        """Prevent scraping localhost."""
        if 'localhost' in str(v) or '127.0.0.1' in str(v):
            raise ValueError('Cannot scrape localhost URLs')
        return v


class ProxySchema(BaseModel):
    """Validated proxy configuration schema."""
    
    server: HttpUrl = Field(..., description="Proxy server URL")
    username: Optional[str] = Field(None, description="Proxy username")
    password: Optional[str] = Field(None, description="Proxy password")
    latency_ms: Optional[float] = Field(None, ge=0, description="Measured latency")
    success_rate: Optional[float] = Field(None, ge=0.0, le=1.0, description="Success rate")


# Validation helper functions
def validate_product(data: dict) -> ProductSchema:
    """
    Validate product data against schema.
    
    Args:
        data: Raw product data dict
        
    Returns:
        Validated ProductSchema instance
        
    Raises:
        ValidationError: If data doesn't match schema
    """
    return ProductSchema(**data)


def validate_task(data: dict) -> TaskSchema:
    """Validate task data against schema."""
    return TaskSchema(**data)
