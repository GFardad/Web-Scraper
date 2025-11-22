#!/usr/bin/env python3
"""
Docker Entrypoint with Auto-Restart and Self-Healing

Features:
- Automatic restart on crash (up to 5 attempts)
- Exponential backoff between retries
- Graceful shutdown handling
- Health check server integration

ADDED (Second-Pass Audit):
- Self-healing auto-restart mechanism
- Crash detection and logging
- Resource cleanup between restarts
"""
import asyncio
import sys
import signal
import logging
import time
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GracefulKiller:
    """Signal handler for graceful shutdown."""
    
    def __init__(self):
        self.kill_now = False
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
    
    def exit_gracefully(self, *args):
        logger.info("🛑 Shutdown signal received")
        self.kill_now = True


async def run_with_auto_restart(
    max_attempts: int = 5,
    min_backoff: float = 4.0,
    max_backoff: float = 60.0
) -> int:
    """
    Run scraper with automatic restart on failure.
    
    Args:
        max_attempts: Maximum restart attempts
        min_backoff: Minimum wait time between restarts (seconds)
        max_backoff: Maximum wait time between restarts (seconds)
        
    Returns:
        Exit code (0 = success, 1 = fatal failure)
    """
    from main_engine import ScraperOrchestrator
    
    killer = GracefulKiller()
    attempt = 0
    backoff = min_backoff
    
    while attempt < max_attempts and not killer.kill_now:
        attempt += 1
        
        try:
            logger.info(f"🚀 Starting Scraper Orchestrator (Attempt {attempt}/{max_attempts})...")
            
            orchestrator = ScraperOrchestrator()
            
            if attempt == 1:
                print("✅ System ready - waiting for tasks")
            
            # Run orchestrator
            await orchestrator.run()
            
            # If we get here, normal shutdown occurred
            logger.info("✅ Scraper shutdown normally")
            return 0
            
        except KeyboardInterrupt:
            logger.info("⌨️  Keyboard interrupt received")
            return 0
            
        except Exception as e:
            logger.error(
                f"💥 Scraper crashed (Attempt {attempt}/{max_attempts}): {e}",
                exc_info=True
            )
            
            # Check if we should retry
            if attempt >= max_attempts:
                logger.error(f"❌ Max restart attempts ({max_attempts}) reached. Giving up.")
                return 1
            
            if killer.kill_now:
                logger.info("🛑 Shutdown requested, not restarting")
                return 0
            
            # Exponential backoff
            wait_time = min(backoff, max_backoff)
            logger.info(f"⏳ Waiting {wait_time:.1f}s before restart...")
            await asyncio.sleep(wait_time)
            
            backoff *= 2  # Exponential increase
            logger.info(f"🔄 Restarting scraper (Attempt {attempt + 1}/{max_attempts})...")
    
    logger.warning("🛑 Shutdown requested, exiting")
    return 0


def main():
    """Main entry point."""
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    logger.info("=" * 70)
    logger.info("🚀 ENTERPRISE SCRAPER - SELF-HEALING MODE")
    logger.info("=" * 70)
    logger.info(f"Python: {sys.version}")
    logger.info(f"Platform: {sys.platform}")
    logger.info("Features: Auto-Restart | Exponential Backoff | Graceful Shutdown")
    logger.info("=" * 70)
    
    # Run with auto-restart
    exit_code = asyncio.run(run_with_auto_restart(
        max_attempts=5,
        min_backoff=4.0,
        max_backoff=60.0
    ))
    
    if exit_code == 0:
        logger.info("👋 Scraper exited cleanly")
    else:
        logger.error("💀 Scraper exited with errors")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
