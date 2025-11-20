// ═══════════════════════════════════════════════════════════════════
// MongoDB Initialization Script
// Creates collections, indexes, and TTL policies for raw data storage
// ═══════════════════════════════════════════════════════════════════

// Switch to scraper_raw database
db = db.getSiblingDB('scraper_raw');

// ═══════════════════════════════════════════════════════════════════
// COLLECTIONS
// ═══════════════════════════════════════════════════════════════════

// Raw HTML storage
db.createCollection('raw_html');
db.raw_html.createIndex({ "url": 1 }, { unique: true });
db.raw_html.createIndex({ "timestamp": 1 });
db.raw_html.createIndex({ "domain": 1 });
// TTL index: Delete documents older than 90 days
db.raw_html.createIndex({ "timestamp": 1 }, { expireAfterSeconds: 7776000 });

// Screenshots storage (metadata only, files on volume)
db.createCollection('screenshots');
db.screenshots.createIndex({ "url": 1 });
db.screenshots.createIndex({ "timestamp": 1 });
db.screenshots.createIndex({ "screenshot_type": 1 });  // 'success', 'error', 'debug'

// API responses (for sites with JSON APIs)
db.createCollection('api_responses');
db.api_responses.createIndex({ "url": 1 });
db.api_responses.createIndex({ "timestamp": 1 });
db.api_responses.createIndex({ "api_endpoint": 1 });

// Debug logs (verbose logs for troubleshooting)
db.createCollection('debug_logs');
db.debug_logs.createIndex({ "timestamp": 1 });
db.debug_logs.createIndex({ "log_level": 1 });
db.debug_logs.createIndex({ "component": 1 });
// TTL index: Delete logs older than 30 days
db.debug_logs.createIndex({ "timestamp": 1 }, { expireAfterSeconds: 2592000 });

// Error archive (comprehensive error details)
db.createCollection('error_archive');
db.error_archive.createIndex({ "timestamp": 1 });
db.error_archive.createIndex({ "error_type": 1 });
db.error_archive.createIndex({ "url": 1 });
// TTL index: Keep errors for 180 days
db.error_archive.createIndex({ "timestamp": 1 }, { expireAfterSeconds: 15552000 });

// URL deduplication cache
db.createCollection('url_cache');
db.url_cache.createIndex({ "url_hash": 1 }, { unique: true });
db.url_cache.createIndex({ "canonical_url": 1 });
db.url_cache.createIndex({ "last_seen": 1 });

// CAPTCHA encounters (for analysis)
db.createCollection('captcha_log');
db.captcha_log.createIndex({ "timestamp": 1 });
db.captcha_log.createIndex({ "captcha_type": 1 });
db.captcha_log.createIndex({ "domain": 1 });

// ═══════════════════════════════════════════════════════════════════
// SAMPLE DOCUMENT STRUCTURES (for reference)
// ═══════════════════════════════════════════════════════════════════

// raw_html example
db.raw_html.insertOne({
    url: "https://example.com/product/sample",
    domain: "example.com",
    html_content: "<html>...</html>",
    headers: {
        "content-type": "text/html",
        "status": 200
    },
    timestamp: new Date(),
    size_bytes: 52341,
    compression: "gzip",
    metadata: {
        user_agent: "Mozilla/5.0...",
        proxy_used: null
    }
});

// screenshots example
db.screenshots.insertOne({
    url: "https://example.com/product/sample",
    screenshot_type: "success",
    file_path: "/app/data/screenshots/sample_20240101_123456.png",
    timestamp: new Date(),
    viewport: { width: 1920, height: 1080 },
    file_size_bytes: 125000
});

// api_responses example
db.api_responses.insertOne({
    url: "https://example.com/product/sample",
    api_endpoint: "https://api.example.com/products/123",
    method: "GET",
    status_code: 200,
    response_body: { /* JSON data */ },
    headers: { /* response headers */ },
    timestamp: new Date()
});

// debug_logs example
db.debug_logs.insertOne({
    timestamp: new Date(),
    log_level: "DEBUG",
    component: "jsonld_extractor",
    message: "Found 3 JSON-LD scripts in page",
    metadata: {
        url: "https://example.com/product/sample",
        script_count: 3
    }
});

// error_archive example
db.error_archive.insertOne({
    timestamp: new Date(),
    url: "https://example.com/product/sample",
    error_type: "TimeoutException",
    error_message: "Page load timeout exceeded 30s",
    stack_trace: "...",
    screenshot_path: "/app/data/error_screenshots/error_123.png",
    metadata: {
        user_agent: "...",
        proxy: null,
        retry_attempt: 2
    }
});

// url_cache example
db.url_cache.insertOne({
    url_hash: "abc123def456",
    original_url: "https://example.com/product/sample?utm_source=google",
    canonical_url: "https://example.com/product/sample",
    normalized_url: "https://example.com/product/sample",
    first_seen: new Date(),
    last_seen: new Date(),
    visit_count: 5
});

// captcha_log example
db.captcha_log.insertOne({
    timestamp: new Date(),
    url: "https://example.com/product/sample",
    domain: "example.com",
    captcha_type: "recaptcha_v2",
    detection_method: "css_selector",
    solved: false,
    solver_used: null
});

// ═══════════════════════════════════════════════════════════════════
// STATISTICS & MONITORING
// ═══════════════════════════════════════════════════════════════════

// Enable stats collection
db.setProfilingLevel(1, { slowms: 100 });

print("✅ MongoDB initialization complete!");
print("Collections created:");
print("  - raw_html (with 90-day TTL)");
print("  - screenshots");
print("  - api_responses");
print("  - debug_logs (with 30-day TTL)");
print("  - error_archive (with 180-day TTL)");
print("  - url_cache");
print("  - captcha_log");
print("\nIndexes and TTL policies configured.");
