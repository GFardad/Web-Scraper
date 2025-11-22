# ═══════════════════════════════════════════════════════════════════
# SCRAPER DOCKERFILE - MIRROR FIXED VERSION
# Switched to US Mirrors to fix "Hash Mismatch" errors
# ═══════════════════════════════════════════════════════════════════

# ───────────────────────────────────────────────────────────────────
# STAGE 1: Builder
# ───────────────────────────────────────────────────────────────────
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04 as builder

# NOTE: DNS is handled by host daemon.json.

# --- [FIX] SWITCH MIRRORS TO US (More Stable) ---
RUN sed -i 's/archive.ubuntu.com/us.archive.ubuntu.com/g' /etc/apt/sources.list && \
    sed -i 's/security.ubuntu.com/us.archive.ubuntu.com/g' /etc/apt/sources.list

# Install Python and build tools
# Added --fix-missing to handle minor network drops
RUN apt-get update --fix-missing && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3-pip \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

WORKDIR /build
RUN python -m pip install --upgrade pip setuptools wheel

COPY requirements.txt .

# Build Wheels with Mirrors
RUN pip wheel --no-cache-dir \
    --retries 10 \
    --timeout 60 \
    --index-url https://pypi.org/simple \
    --extra-index-url https://mirrors.aliyun.com/pypi/simple/ \
    --wheel-dir /build/wheels \
    -r requirements.txt

# ───────────────────────────────────────────────────────────────────
# STAGE 2: Runtime
# ───────────────────────────────────────────────────────────────────
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

# --- [FIX] SWITCH MIRRORS TO US (Runtime Stage) ---
RUN sed -i 's/archive.ubuntu.com/us.archive.ubuntu.com/g' /etc/apt/sources.list && \
    sed -i 's/security.ubuntu.com/us.archive.ubuntu.com/g' /etc/apt/sources.list

# Install runtime dependencies
RUN apt-get update --fix-missing && apt-get install -y \
    python3.11 \
    python3-pip \
    curl \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libx11-6 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.11 default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Security Setup
RUN groupadd -r scraper && useradd -r -g scraper -s /bin/bash scraper
WORKDIR /app

# Copy artifacts
COPY --from=builder /build/wheels /wheels
COPY requirements.txt .

# Install packages
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && \
    rm -rf /wheels

# Install Playwright
RUN python -m playwright install chromium && \
    python -m playwright install-deps chromium

# App Setup
COPY --chown=scraper:scraper . /app/
RUN mkdir -p /app/data /app/logs /app/data/screenshots /app/data/error_screenshots /app/data/browser_sessions /tmp/scraper && \
    chown -R scraper:scraper /app /tmp/scraper

USER scraper
EXPOSE 8080 9090

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "docker_entrypoint.py"]s