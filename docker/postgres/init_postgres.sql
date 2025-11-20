-- ═══════════════════════════════════════════════════════════════════
-- PostgreSQL Initialization Script
-- Creates tables for structured product data and scraping metadata
-- ═══════════════════════════════════════════════════════════════════

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ═══════════════════════════════════════════════════════════════════
-- PRODUCTS TABLE - Structured product data
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    url TEXT NOT NULL,
    product_title TEXT,
    price DECIMAL(12, 2),
    currency VARCHAR(10),
    original_price DECIMAL(12, 2),
    discount_percentage DECIMAL(5, 2),
    savings DECIMAL(12, 2),
    availability VARCHAR(50),
    product_id VARCHAR(255),
    brand VARCHAR(255),
    description TEXT,
    confidence_score DECIMAL(3, 2),
    extraction_strategy VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for performance
    CONSTRAINT products_url_unique UNIQUE (url)
);

CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand);
CREATE INDEX IF NOT EXISTS idx_products_created_at ON products(created_at);
CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);

-- ═══════════════════════════════════════════════════════════════════
-- PRODUCT IMAGES - Related images for products
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS product_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    image_type VARCHAR(50) DEFAULT 'primary',
    display_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_product_images_product_id ON product_images(product_id);

-- ═══════════════════════════════════════════════════════════════════
-- PRODUCT VARIANTS - Color, size, etc.
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS product_variants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    variant_type VARCHAR(50),  -- 'color', 'size', 'style', etc.
    variant_value VARCHAR(255),
    additional_price DECIMAL(10, 2) DEFAULT 0,
    availability VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_product_variants_product_id ON product_variants(product_id);

-- ═══════════════════════════════════════════════════════════════════
-- SCRAPING TASKS - Task queue and tracking
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS scraping_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    url TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'running', 'completed', 'failed'
    priority INT DEFAULT 0,
    attempts INT DEFAULT 0,
    max_attempts INT DEFAULT 3,
    last_error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    CONSTRAINT scraping_tasks_url_unique UNIQUE (url)
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON scraping_tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON scraping_tasks(priority DESC);

-- ═══════════════════════════════════════════════════════════════════
-- EXTRACTION METADATA - Confidence scores and strategy performance
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS extraction_metadata (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id UUID REFERENCES products(id) ON DELETE CASCADE,
    strategy_used VARCHAR(50),  -- 'jsonld', 'llm', 'ocr', 'dom'
    confidence_score DECIMAL(3, 2),
    extraction_time_ms INT,
    fallback_count INT DEFAULT 0,
    metadata JSONB,  -- Additional flexible metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_extraction_strategy ON extraction_metadata(strategy_used);
CREATE INDEX IF NOT EXISTS idx_extraction_confidence ON extraction_metadata(confidence_score);

-- ═══════════════════════════════════════════════════════════════════
-- SCRAPING SESSIONS - Browser session tracking
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS scraping_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_hash VARCHAR(64),  -- Unique session identifier
    domain VARCHAR(255),
    cookies JSONB,
    local_storage JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    use_count INT DEFAULT 0,
    
    CONSTRAINT sessions_hash_unique UNIQUE (session_hash)
);

CREATE INDEX IF NOT EXISTS idx_sessions_domain ON scraping_sessions(domain);
CREATE INDEX IF NOT EXISTS idx_sessions_last_used ON scraping_sessions(last_used);

-- ═══════════════════════════════════════════════════════════════════
-- ERROR LOGS - Structured error tracking
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS error_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    url TEXT,
    error_type VARCHAR(100),
    error_message TEXT,
    stack_trace TEXT,
    screenshot_path TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_errors_type ON error_logs(error_type);
CREATE INDEX IF NOT EXISTS idx_errors_created ON error_logs(created_at);

-- ═══════════════════════════════════════════════════════════════════
-- PERFORMANCE METRICS - Response time analytics
-- ═══════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS performance_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain VARCHAR(255),
    response_time_ms INT,
    status_code INT,
    success BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_perf_domain ON performance_metrics(domain);
CREATE INDEX IF NOT EXISTS idx_perf_created ON performance_metrics(created_at);

-- ═══════════════════════════════════════════════════════════════════
-- TRIGGER: Auto-update updated_at timestamp
-- ═══════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ═══════════════════════════════════════════════════════════════════
-- INITIAL DATA - Insert example task (commented out by default)
-- ═══════════════════════════════════════════════════════════════════
-- INSERT INTO scraping_tasks (url, priority) VALUES 
--     ('https://example.com/product/12345', 10);
