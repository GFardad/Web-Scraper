#!/usr/bin/env python3
"""
Pre-Flight Verification Script
================================

Checks all prerequisites before starting the scraper application.
Run this before `docker-compose up` to catch issues early.

Usage:
    python3 verify_installation.py

Exit Codes:
    0 = All checks passed, ready to deploy
    1 = Critical checks failed, cannot proceed
    2 = Warnings detected, may proceed with caution
"""

import sys
import os
import subprocess
import socket
import shutil
from pathlib import Path
from typing import Tuple, List

# ANSI color codes
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'

class PreFlightChecker:
    def __init__(self):
        self.critical_failures = []
        self.warnings = []
        self.passed = []
    
    def check(self, name: str, func) -> bool:
        """Run a check and record result."""
        print(f"\n{BLUE}[CHECK]{RESET} {name}...", end=' ')
        try:
            success, message = func()
            if success:
                print(f"{GREEN}✓{RESET}")
                self.passed.append(name)
                return True
            else:
                print(f"{YELLOW}⚠{RESET}")
                self.warnings.append((name, message))
                return False
        except Exception as e:
            print(f"{RED}✗{RESET}")
            self.critical_failures.append((name, str(e)))
            return False
    
    def check_critical(self, name: str, func) -> bool:
        """Run a critical check (failure blocks deployment)."""
        result = self.check(name, func)
        if not result and (name, self.warnings[-1][1]) in [(w[0], w[1]) for w in self.warnings]:
            # Move from warnings to critical
            self.warnings = [w for w in self.warnings if w[0] != name]
            self.critical_failures.append((name, func()[1]))
        return result
    
    def print_summary(self):
        """Print final summary."""
        print("\n" + "="*70)
        print(f"{BOLD}PRE-FLIGHT CHECK SUMMARY{RESET}")
        print("="*70)
        
        if self.passed:
            print(f"\n{GREEN}✓ PASSED ({len(self.passed)}){RESET}")
            for item in self.passed:
                print(f"  • {item}")
        
        if self.warnings:
            print(f"\n{YELLOW}⚠ WARNINGS ({len(self.warnings)}){RESET}")
            for name, msg in self.warnings:
                print(f"  • {name}: {msg}")
        
        if self.critical_failures:
            print(f"\n{RED}✗ CRITICAL FAILURES ({len(self.critical_failures)}){RESET}")
            for name, msg in self.critical_failures:
                print(f"  • {name}: {msg}")
        
        print("\n" + "="*70)
        
        # Final verdict
        if self.critical_failures:
            print(f"{RED}{BOLD}❌ CANNOT PROCEED - Fix critical issues first{RESET}")
            return 1
        elif self.warnings:
            print(f"{YELLOW}{BOLD}⚠ CAN PROCEED - Review warnings{RESET}")
            return 2
        else:
            print(f"{GREEN}{BOLD}✅ ALL CHECKS PASSED - Ready to deploy!{RESET}")
            return 0


def check_docker_installed() -> Tuple[bool, str]:
    """Check if Docker is installed."""
    docker_path = shutil.which('docker')
    if not docker_path:
        return False, "Docker not found in PATH"
    return True, "Docker found"


def check_docker_running() -> Tuple[bool, str]:
    """Check if Docker daemon is running."""
    try:
        result = subprocess.run(
            ['docker', 'info'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return True, "Docker daemon running"
        return False, "Docker daemon not responding"
    except subprocess.TimeoutExpired:
        return False, "Docker daemon timeout"
    except Exception as e:
        return False, f"Cannot connect to Docker: {e}"


def check_docker_version() -> Tuple[bool, str]:
    """Check Docker version >= 20.0."""
    try:
        result = subprocess.run(
            ['docker', '--version'],
            capture_output=True,
            text=True
        )
        version_str = result.stdout.strip()
        # Extract version number (e.g., "Docker version 24.0.7" -> 24.0.7)
        version_part = version_str.split()[2].replace(',', '')
        major_version = int(version_part.split('.')[0])
        
        if major_version >= 20:
            return True, f"Version {version_part} OK"
        return False, f"Version {version_part} too old (need >= 20.0)"
    except Exception as e:
        return False, f"Cannot parse version: {e}"


def check_docker_compose_installed() -> Tuple[bool, str]:
    """Check if Docker Compose is installed."""
    # Try new "docker compose" command (v2)
    try:
        result = subprocess.run(
            ['docker', 'compose', 'version'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return True, f"Docker Compose v2 found: {version}"
    except:
        pass
    
    # Try old "docker-compose" command (v1)
    try:
        result = subprocess.run(
            ['docker-compose', '--version'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return True, f"Docker Compose v1 found: {version} (v2 recommended)"
    except:
        pass
    
    return False, "Docker Compose not found (neither 'docker compose' nor 'docker-compose')"


def check_ports_available() -> Tuple[bool, str]:
    """Check if required ports are available."""
    required_ports = [
        (8501, "Control Center UI"),
        (8080, "Scraper Health Check"),
        (5434, "PostgreSQL"),
        (27017, "MongoDB"),
        (6379, "Redis"),
        (11435, "Ollama"),
        (8000, "PaddleOCR"),
        (9093, "Prometheus")
    ]
    
    occupied = []
    for port, service in required_ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        
        if result == 0:
            occupied.append(f"{port} ({service})")
    
    if occupied:
        return False, f"Ports in use: {', '.join(occupied)}"
    return True, "All required ports available"


def check_disk_space() -> Tuple[bool, str]:
    """Check available disk space (need >= 10GB)."""
    try:
        stat = shutil.disk_usage('/')
        available_gb = stat.free / (1024**3)
        
        if available_gb >= 10:
            return True, f"{available_gb:.1f} GB available"
        return False, f"Only {available_gb:.1f} GB available (need >= 10 GB)"
    except Exception as e:
        return False, f"Cannot check disk space: {e}"


def check_env_file_exists() -> Tuple[bool, str]:
    """Check if .env file exists."""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        return True, f".env found at {env_path}"
    return False, ".env file missing (copy from .env.example)"


def check_env_variables() -> Tuple[bool, str]:
    """Check if required .env variables are set."""
    env_path = Path(__file__).parent / '.env'
    if not env_path.exists():
        return False, ".env file not found"
    
    required_vars = [
        'POSTGRES_PASSWORD',
        'MONGO_ROOT_PASSWORD',
        'REDIS_PASSWORD'
    ]
    
    with open(env_path, 'r') as f:
        env_content = f.read()
    
    missing = []
    for var in required_vars:
        if f"{var}=" not in env_content:
            missing.append(var)
    
    if missing:
        return False, f"Missing variables: {', '.join(missing)}"
    return True, "All required variables set"


def check_docker_compose_file() -> Tuple[bool, str]:
    """Check if docker-compose.yml exists and is valid."""
    compose_path = Path(__file__).parent / 'docker-compose.yml'
    
    if not compose_path.exists():
        return False, "docker-compose.yml not found"
    
    # Try to validate it
    try:
        result = subprocess.run(
            ['docker', 'compose', '-f', str(compose_path), 'config'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return True, "docker-compose.yml is valid"
        return False, f"Invalid YAML: {result.stderr[:100]}"
    except Exception as e:
        return False, f"Cannot validate: {e}"


def check_python_version() -> Tuple[bool, str]:
    """Check Python version >= 3.11."""
    major, minor = sys.version_info[:2]
    version_str = f"{major}.{minor}"
    
    if major == 3 and minor >= 11:
        return True, f"Python {version_str} OK"
    return False, f"Python {version_str} detected (need >= 3.11 for containers)"


def check_internet_connectivity() -> Tuple[bool, str]:
    """Check internet connectivity for Docker image pulls."""
    test_hosts = [
        ('8.8.8.8', 53, 'Google DNS'),
        ('1.1.1.1', 53, 'Cloudflare DNS'),
    ]
    
    for host, port, name in test_hosts:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                return True, f"Internet accessible via {name}"
        except:
            continue
    
    return False, "Cannot reach internet (check firewall/proxy)"


def main():
    """Run all pre-flight checks."""
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}🚀 PRE-FLIGHT VERIFICATION - Production-Ready Scraper{RESET}")
    print(f"{BOLD}{'='*70}{RESET}")
    
    checker = PreFlightChecker()
    
    # Critical checks (must pass)
    print(f"\n{BOLD}📋 CRITICAL CHECKS{RESET}")
    checker.check_critical("Docker installed", check_docker_installed)
    checker.check_critical("Docker daemon running", check_docker_running)
    checker.check_critical("Docker version >= 20.0", check_docker_version)
    checker.check_critical("Docker Compose available", check_docker_compose_installed)
    checker.check_critical(".env file exists", check_env_file_exists)
    checker.check_critical(".env variables set", check_env_variables)
    checker.check_critical("docker-compose.yml valid", check_docker_compose_file)
    
    # Important checks (warnings only)
    print(f"\n{BOLD}⚙️  RECOMMENDED CHECKS{RESET}")
    checker.check("Required ports available", check_ports_available)
    checker.check("Disk space >= 10GB", check_disk_space)
    checker.check("Internet connectivity", check_internet_connectivity)
    checker.check("Python version >= 3.11", check_python_version)
    
    # Print summary and exit
    exit_code = checker.print_summary()
    
    if exit_code == 0:
        print(f"\n{GREEN}📝 Next steps:{RESET}")
        print(f"  1. docker-compose down -v           # Clean old containers")
        print(f"  2. docker-compose build --no-cache  # Build images")
        print(f"  3. docker-compose up -d             # Start services")
        print(f"  4. docker-compose ps                # Verify all running")
        print(f"  5. Open http://localhost:8501       # Access UI\n")
    elif exit_code == 2:
        print(f"\n{YELLOW}📝 Review warnings above, then proceed if acceptable{RESET}\n")
    else:
        print(f"\n{RED}📝 Fix critical issues before proceeding{RESET}\n")
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
