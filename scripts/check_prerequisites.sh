#!/bin/bash
set -e

echo "🔍 Checking System Prerequisites for Scraper Deployment"
echo "=========================================================="

ERRORS=0

# Check Docker
echo -n "✓ Docker Engine: "
if command -v docker &> /dev/null; then
    docker --version
else
    echo "❌ NOT INSTALLED"
    ERRORS=$((ERRORS + 1))
fi

# Check Docker Compose (both new and legacy)
echo -n "✓ Docker Compose: "
if docker compose version &> /dev/null; then
    docker compose version
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    docker-compose --version
    COMPOSE_CMD="docker-compose"
else
    echo "❌ NOT INSTALLED"
    ERRORS=$((ERRORS + 1))
fi

# Check NVIDIA GPU
echo -n "✓ NVIDIA GPU: "
if command -v nvidia-smi &> /dev/null; then
    GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader)
    echo "$GPU_INFO"
else
    echo "❌ nvidia-smi NOT FOUND"
    ERRORS=$((ERRORS + 1))
fi

# Check NVIDIA Container Toolkit
echo -n "✓ NVIDIA Container Toolkit: "
if command -v nvidia-container-toolkit &> /dev/null; then
    nvidia-container-toolkit --version | head -1
elif docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 echo "OK" &> /dev/null; then
    echo "✓ WORKING (detected via test)"
else
    echo "❌ NOT INSTALLED or NOT CONFIGURED"
    echo "  Run: ./scripts/install_nvidia_toolkit.sh"
    ERRORS=$((ERRORS + 1))
fi

# Check disk space
echo -n "✓ Disk Space: "
AVAILABLE=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
if [ "$AVAILABLE" -gt 100 ]; then
    echo "${AVAILABLE}GB available ✓"
else
    echo "⚠️  Only ${AVAILABLE}GB available (recommend 100GB+)"
fi

# Check available VRAM
if command -v nvidia-smi &> /dev/null; then
    echo -n "✓ GPU VRAM: "
    VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits)
    VRAM_GB=$((VRAM / 1024))
    echo "${VRAM_GB}GB"
    if [ "$VRAM_GB" -lt 3 ]; then
        echo "  ⚠️  Less than 3GB VRAM may limit AI capabilities"
    fi
fi

# Check RAM
echo -n "✓ System RAM: "
TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
echo "${TOTAL_RAM}GB"
if [ "$TOTAL_RAM" -lt 16 ]; then
    echo "  ⚠️  Less than 16GB RAM may impact performance"
fi

echo "=========================================================="

if [ $ERRORS -eq 0 ]; then
    echo "✅ All prerequisites met! Ready to deploy."
    echo ""
    echo "To deploy the stack, run:"
    echo "  make deploy"
    exit 0
else
    echo "❌ $ERRORS error(s) found. Please fix before deploying."
    exit 1
fi
