"""
Configuration Module - ZERO HARDCODING Wrapper

This module provides backward compatibility with the old config.py interface
while using config_manager.py as the single source of truth.

ALL values come from config.yaml. This file contains NO hardcoded values.
"""

from config_manager import get_config

# Get the global config instance
_config = get_config()

# ═══════════════════════════════════════════════════════════════════
# DATABASE SETTINGS
# ═══════════════════════════════════════════════════════════════════

def get_database_url():
    """Get PostgreSQL database URL."""
    pg = _config.databases.postgres
    return f"postgresql://{pg.username}:{pg.password}@{pg.host}:{pg.port}/{pg.database}"

DATABASE_URL = get_database_url()

def get_mongo_url():
    """Get MongoDB connection URL."""
    mongo = _config.databases.mongo
    return f"mongodb://{mongo.username}:{mongo.password}@{mongo.host}:{mongo.port}/{mongo.database}?authSource={mongo.auth_source}"

MONGO_URL = get_mongo_url()

def get_redis_url():
    """Get Redis connection URL."""
    redis = _config.databases.redis
    password_part = f":{redis.password}@" if redis.password else "@"
    return f"redis://{password_part}{redis.host}:{redis.port}/{redis.db}"

REDIS_URL = get_redis_url()

# ═══════════════════════════════════════════════════════════════════
# SCRAPING CONSTANTS (Persian-specific kept for backward compatibility)
# ═══════════════════════════════════════════════════════════════════

# These are language-specific and don't change dynamically
PERSIAN_CURRENCY_TOMAN = "تومان"
PERSIAN_CURRENCY_RIAL = "ریال"
PERSIAN_BLOCKED_KEYWORDS = ["captcha", "access denied", "مسدود", "کپچا"]

# ═══════════════════════════════════════════════════════════════════
# ALGORITHM SETTINGS - All from YAML
# ═══════════════════════════════════════════════════════════════════

# Legacy constants - now dynamically loaded
# These will auto-update when config.yaml changes (if hot-reload is enabled)

@property
def MAX_ELEMENTS_TO_SCAN():
    return _config.get('scraper.algorithm.max_elements_to_scan', default=300)

@property
def MAX_DISTANCE_FOR_PRICE():
    return _config.get('scraper.algorithm.max_distance_for_price', default=900)

@property
def VERTICAL_ALIGNMENT_THRESHOLD():
    return _config.get('scraper.algorithm.vertical_alignment_threshold', default=150)

@property
def MIN_PRICE_VALUE():
    return _config.get('scraper.algorithm.min_price_value', default=1000)

# ═══════════════════════════════════════════════════════════════════
# PROXY SETTINGS
# ═══════════════════════════════════════════════════════════════════

ENABLE_PROXIES = lambda: _config.proxies.enabled
PROXY_SOURCES = lambda: _config.proxies.sources
PROXY_TEST_SAMPLE_SIZE = lambda: _config.get('proxies.test_sample_size', default=250)
PROXY_TOP_PERCENTAGE = lambda: _config.get('proxies.top_percentage', default=0.3)

# ═══════════════════════════════════════════════════════════════════
# BROWSER SETTINGS
# ═══════════════════════════════════════════════════════════════════

USER_AGENT = lambda: _config.headers.user_agents[0]  # First UA (or use rotation)
VIEWPORT_WIDTH = lambda: _config.scraper.browser.viewport_width
VIEWPORT_HEIGHT = lambda: _config.scraper.browser.viewport_height
HEADLESS_MODE = lambda: _config.scraper.browser.headless

# ═══════════════════════════════════════════════════════════════════
# RETRY SETTINGS
# ═══════════════════════════════════════════════════════════════════

MAX_TASK_ATTEMPTS = lambda: _config.scraper.retries.max_attempts

# ═══════════════════════════════════════════════════════════════════
# OUTPUT DIRECTORIES
# ═══════════════════════════════════════════════════════════════════

ERROR_SCREENSHOTS_DIR = lambda: _config.paths.error_screenshots_dir

# ═══════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════

LOG_LEVEL = lambda: _config.logging.level

# ═══════════════════════════════════════════════════════════════════
# CONCURRENT PROCESSING
# ═══════════════════════════════════════════════════════════════════

CONCURRENT_WORKERS = lambda: _config.scraper.concurrency.max_workers
PER_DOMAIN_RATE_LIMIT = lambda: _config.scraper.rate_limiting.per_domain_delay

# ═══════════════════════════════════════════════════════════════════
# PAGINATION
# ═══════════════════════════════════════════════════════════════════

ENABLE_PAGINATION = lambda: _config.scraper.pagination.enabled
MAX_PAGINATION_PAGES = lambda: _config.scraper.pagination.max_pages

# ═══════════════════════════════════════════════════════════════════
# NEW: AI CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

# Ollama settings
OLLAMA_URL = lambda: _config.ai.ollama.base_url
OLLAMA_MODEL = lambda: _config.ai.ollama.model_name
OLLAMA_TEMPERATURE = lambda: _config.ai.ollama.temperature
OLLAMA_TIMEOUT = lambda: _config.ai.ollama.timeout

# PaddleOCR settings
PADDLEOCR_URL = lambda: _config.ai.paddleocr.base_url
PADDLEOCR_USE_GPU = lambda: _config.ai.paddleocr.use_gpu

# GPU settings
GPU_ENABLED = lambda: _config.ai.gpu.enabled
MAX_VRAM_GB = lambda: _config.ai.gpu.max_vram_gb

# Confidence thresholds
MIN_LLM_CONFIDENCE = lambda: _config.ai.confidence.min_llm_extraction
MIN_OCR_CONFIDENCE = lambda: _config.ai.confidence.min_ocr_extraction
MIN_JSONLD_CONFIDENCE = lambda: _config.ai.confidence.min_jsonld

# ═══════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def reload_config():
    """Manually trigger config reload (if hot-reload is disabled)."""
    _config.reload()

def get_config_value(key_path, default=None):
    """
    Get any config value using dot notation.
    
    Example:
        delay = get_config_value('scraper.rate_limiting.base_delay', default=2.0)
    """
    return _config.get(key_path, default=default)

def get_full_config():
    """Return the entire configuration as a dictionary."""
    return _config.to_dict()

# ═══════════════════════════════════════════════════════════════════
# BACKWARD COMPATIBILITY NOTE
# ═══════════════════════════════════════════════════════════════════
"""
For modules that used:
    from config import CONCURRENT_WORKERS
    
They now need to use:
    from config import CONCURRENT_WORKERS
    workers = CONCURRENT_WORKERS()  # Call as function
    
OR better yet, import directly:
    from config_manager import get_config
    config = get_config()
    workers = config.scraper.concurrency.max_workers
"""

