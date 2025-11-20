# Quick Start Deployment Guide

## Prerequisites ✅
- Docker installed
- Docker Compose installed
- Project files downloaded

## Step-by-Step Instructions

### 1. Navigate to Project Directory
```bash
cd /path/to/Scraper
```

### 2. Create Environment Configuration
```bash
cp .env.example .env
```

Edit `.env` file:
```bash
nano .env
```

**Minimal configuration:**
```env
DATABASE_URL=sqlite+aiosqlite:///commercial_scraper.db
ENABLE_PROXIES=true
HEADLESS_MODE=true
LOG_LEVEL=INFO
DASHBOARD_PORT=8501
```

### 3. Build and Start Services
```bash
docker-compose up -d
```

This starts:
- **scraper** - Background worker processing URLs
- **dashboard** - Web UI at http://localhost:8501

### 4. Access Admin Dashboard
Open browser: **http://localhost:8501**

### 5. Add URLs to Scrape
In the dashboard sidebar:
1. Enter product URL (Digikala or Khanoumi)
2. Click "Inject Task"
3. Watch results appear in real-time

### 6. Monitor System

**View logs:**
```bash
docker-compose logs -f
```

**View specific service:**
```bash
docker-compose logs -f scraper
docker-compose logs -f dashboard
```

**Check status:**
```bash
docker-compose ps
```

### 7. Stop Services
```bash
docker-compose down
```

## Supported Sites

| Site | Status | Example URL |
|------|--------|-------------|
| Digikala | ✅ Working | `https://www.digikala.com/product/dkp-XXXXX` |
| Khanoumi | ✅ Working | `https://www.khanoumi.com/products/...` |
| Others | ⚠️ Generic handler | Any e-commerce site |

## Troubleshooting

### Container won't start
```bash
docker-compose logs scraper
```

### Dashboard not accessible
Check port 8501 is not in use:
```bash
lsof -i :8501
```

Change port in `.env`:
```env
DASHBOARD_PORT=8502
```

### Database locked
Stop all containers:
```bash
docker-compose down
rm commercial_scraper.db
docker-compose up -d
```

## Production Tips

1. **Disable proxies** if not needed (`.env`):
   ```env
   ENABLE_PROXIES=false
   ```

2. **Increase logging** for debugging:
   ```env
   LOG_LEVEL=DEBUG
   ```

3. **Backup database** regularly:
   ```bash
   docker-compose exec scraper cp /app/commercial_scraper.db /app/backup.db
   ```

## Quick Commands Reference

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Restart
docker-compose restart

# View logs
docker-compose logs -f

# Rebuild after code changes
docker-compose up -d --build
```

## Support

Dashboard shows:
- Total tasks
- Pending tasks
- Completed tasks
- Failed tasks

All data persists in `commercial_scraper.db`.
