# ═══════════════════════════════════════════════════════════════════
# SCRAPER DOCKERFILE - Multi-Stage Build (VPN-HARDENED)
# GPU-Enabled | Python 3.11 | Playwright | Zero Host Dependencies
# DNS-ENFORCED for VPN/Corporate Network Resilience
# ═══════════════════════════════════════════════════════════════════

# ───────────────────────────────────────────────────────────────────
# STAGE 1: Builder - Build Python wheels and dependencies
# ───────────────────────────────────────────────────────────────────
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04 as builder

# ╔═══════════════════════════════════════════════════════════════════╗
# ║ CRITICAL: VPN/PROXY DNS FIX - Force Google DNS During Build      ║
# ║ Without this, builds FAIL behind corporate VPN/proxy             ║
# ╚═══════════════════════════════════════════════════════════════════╝
RUN echo "nameserver 8.8.8.8" > /etc/resolv.conf && \
    echo "nameserver 1.1.1.1" >> /etc/resolv.conf && \
    echo "nameserver 8.8.4.4" >> /etc/resolv.conf && \
    cat /etc/resolv.conf

# Install Python and build tools
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3-pip \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Create virtual environment
WORKDIR /build
RUN python -m pip install --upgrade pip setuptools wheel

# Copy requirements and build wheels
COPY requirements.txt .

# ╔═══════════════════════════════════════════════════════════════════╗
# ║ HARDENED: Add PyPI mirrors + retry logic for network resilience  ║
# ╚═══════════════════════════════════════════════════════════════════╝
RUN pip wheel --no-cache-dir \
    --retries 5 \
    --timeout 30 \
    --index-url https://pypi.org/simple \
    --extra-index-url https://mirrors.aliyun.com/pypi/simple/ \
    --wheel-dir /build/wheels \
    -r requirements.txt

# ───────────────────────────────────────────────────────────────────
# STAGE 2: Runtime - Minimal runtime image with GPU support
# ───────────────────────────────────────────────────────────────────
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

# ╔═══════════════════════════════════════════════════════════════════╗
# ║ CRITICAL: VPN/PROXY DNS FIX - Enforce runtime DNS too            ║
# ╚═══════════════════════════════════════════════════════════════════╝
RUN echo "nameserver 8.8.8.8" > /etc/resolv.conf && \
    echo "nameserver 1.1.1.1" >> /etc/resolv.conf && \
    echo "nameserver 8.8.4.4" >> /etc/resolv.conf

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
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

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Create non-root user for security
RUN groupadd -r scraper && useradd -r -g scraper -s /bin/bash scraper

# Create application directory
WORKDIR /app

# Copy built wheels from builder stage
COPY --from=builder /build/wheels /wheels
COPY requirements.txt .

# Install Python dependencies from wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt && \
    rm -rf /wheels

# Install Playwright browsers
RUN python -m playwright install chromium && \
    python -m playwright install-deps chromium

# Copy application code
COPY --chown=scraper:scraper . /app/

# Create necessary directories with proper permissions
RUN mkdir -p \
    /app/data \
    /app/logs \
    /app/data/screenshots \
    /app/data/error_screenshots \
    /app/data/browser_sessions \
   /tmp/scraper && \
    chown -R scraper:scraper /app /tmp/scraper

# Switch to non-root user
USER scraper

# Expose ports
EXPOSE 8080 9090

# Health check with timeout protection
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command - start health check server and scraper
CMD ["python", "docker_entrypoint.py"]
