# Quick Start (Already Installed)

## After PC Restart - Just Run This:

```bash
cd /home/gfardad/Documents/Scraper
docker-compose up -d
```

**That's it!**

---

## Then Go To:
**http://localhost:8501**

Add product URLs and start scraping.

---

## To Stop:
```bash
cd /home/gfardad/Documents/Scraper
docker-compose down
```

---

## Check if Running:
```bash
docker-compose ps
```

Should show:
- `scraper_engine` - Running
- `scraper_dashboard` - Running
