# Production Scraper

A production-ready web scraper for e-commerce product data extraction with proxy support and admin dashboard.

## Features

- Async web scraping using Playwright
- Proxy rotation for IP protection
- SQLite database for task queuing and results
- Streamlit admin dashboard
- Docker deployment ready
- Windows/Linux compatible

## Quick Start

### Local Development

```bash
# Setup
chmod +x setup.sh
./setup.sh

# Activate environment
source venv/bin/activate

# Run scraper
python main_engine.py

# Run dashboard (in another terminal)
streamlit run dashboard.py
```

### Docker Deployment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
nano .env

# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Configuration

All configuration is managed through environment variables. See `.env.example` for available options.

Key settings:
- `DATABASE_URL`: Database connection string
- `ENABLE_PROXIES`: Enable/disable proxy rotation
- `HEADLESS_MODE`: Run browser in headless mode
- `LOG_LEVEL`: Logging verbosity (DEBUG, INFO, WARNING, ERROR)
- `DASHBOARD_PORT`: Admin dashboard port

## Architecture

```
├── main_engine.py      # Main scraper engine
├── config_db.py        # Database models and operations
├── proxy_guard.py      # Proxy management
├── dashboard.py        # Admin web interface
├── config.py           # Configuration constants
├── Dockerfile          # Container image definition
├── docker-compose.yml  # Multi-container orchestration
└── requirements.txt    # Python dependencies
```

## Usage

### Adding Tasks via Dashboard

1. Access dashboard at `http://localhost:8501`
2. Enter product URL in sidebar
3. Click "Inject Task"
4. Monitor progress in real-time

### Adding Tasks via Code

```python
from config_db import DatabaseCore

db = DatabaseCore()
await db.init_models()
await db.add_task("https://example.com/product/123", priority=1)
```

## Production Deployment

### Prerequisites

- Docker & Docker Compose
- 2GB RAM minimum
- Network access for proxy fetching

### Deployment Steps

1. Clone repository
2. Configure `.env` file
3. Run `docker-compose up -d`
4. Access dashboard at configured port
5. Add tasks via UI

### Monitoring

- Dashboard provides real-time metrics
- Logs available via `docker-compose logs`
- Database can be queried directly with SQLite tools

## Database Schema

### scrape_tasks
- `id`: Primary key
- `url`: Target URL (unique)
- `status`: pending/processing/done/failed
- `priority`: Task priority (higher = sooner)
- `attempts`: Retry counter
- `last_error`: Last error message
- `created_at`: Timestamp

### scrape_results
- `id`: Primary key
- `task_id`: Foreign key to scrape_tasks
- `title`: Product title
- `price`: Extracted price (integer)
- `currency`: Toman or Rial
- `confidence_score`: Extraction confidence
- `meta_data`: Additional metadata (JSON)
- `extracted_at`: Timestamp

## Troubleshooting

### Browser Not Found
```bash
playwright install chromium
```

### Permission Denied
```bash
chmod +x setup.sh
```

### Database Locked
Ensure only one scraper instance is running or use a different database backend (PostgreSQL recommended for production).

## License

MIT License - See LICENSE file for details
