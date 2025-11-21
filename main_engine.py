"""
Enterprise Scraper Orchestrator

The central nervous system of the scraper. Orchestrates:
- Task management (DB)
- Browser lifecycle (Playwright)
- Stealth systems (TLS, Canvas, Human Input)
- Resilience (Retries, Circuit Breakers, Graceful Shutdown)
- Concurrency (Semaphores, Rate Limiting)
"""

import asyncio
import sys
import os
import signal
import structlog
from pathlib import Path
from typing import Dict, Optional, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Third-party imports
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# Local imports
from config_manager import get_config
from config_db import DatabaseCore
# from proxy_guard import ProxyManager  # Temporarily disabled - requires aiohttp
from site_handlers import get_handler_for_url
from resilience.adaptive_throttle import get_adaptive_throttler
from concurrent_engine import DomainRateLimiter, CircuitBreaker
from captcha_detector import CAPTCHADetector

# Stealth imports
from stealth.tls_spoofer import TLSSpoofingManager
from stealth.canvas_noise import CanvasNoiseInjector
from stealth.human_input import get_human_mouse, get_human_typing

# Logging Setup
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger()

class GracefulKiller:
    """
    Handles SIGINT/SIGTERM to allow the scraper to finish current tasks
    and save state before exiting.
    """
    kill_now = False
    
    def __init__(self):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
    
    def exit_gracefully(self, signum, frame):
        logger.warning("shutdown_signal_received", signal=signum)
        self.kill_now = True

class RetryableException(Exception):
    """Exception that triggers a retry."""
    pass

class FatalException(Exception):
    """Exception that aborts the task without retry."""
    pass

class BrowserWorker:
    """
    Handles browser automation with full stealth integration.
    """
    
    def __init__(self, config):
        self.config = config
        self.canvas_injector = CanvasNoiseInjector()
        self.human_mouse = get_human_mouse()
        self.human_typing = get_human_typing()
        self.captcha_detector = CAPTCHADetector()
        
        # Config values
        self.headless = config.get('scraper.headless', default=True)
        self.user_agent = config.get('scraper.user_agent', default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        self.viewport = {
            "width": config.get('scraper.viewport.width', default=1920),
            "height": config.get('scraper.viewport.height', default=1080)
        }
        self.error_dir = config.get('system.paths.error_screenshots', default="data/errors")
        Path(self.error_dir).mkdir(parents=True, exist_ok=True)

    async def run(self, url: str, proxy: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Execute scraping for a given URL with stealth and resilience.
        """
        async with async_playwright() as p:
            launch_args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ]
            
            browser: Browser = await p.chromium.launch(
                headless=self.headless,
                args=launch_args,
            )

            try:
                context: BrowserContext = await browser.new_context(
                    user_agent=self.user_agent,
                    viewport=self.viewport,
                    proxy=proxy,
                    locale="en-US",
                    timezone_id="UTC"
                )

                # ---------------------------------------------------------
                # STEALTH: Inject Canvas/WebGL Noise
                # ---------------------------------------------------------
                page: Page = await context.new_page()
                await self.canvas_injector.inject(page)
                
                # Block media for performance
                await context.route(
                    "**/*",
                    lambda route: (
                        route.abort()
                        if route.request.resource_type in ["image", "media"]
                        else route.continue_()
                    ),
                )

                logger.info("loading_page", url=url)

                try:
                    # Navigation with explicit error handling
                    response = await page.goto(url, timeout=90000, wait_until="domcontentloaded")
                    
                    if not response:
                        raise RetryableException("No response received")
                        
                    status = response.status
                    
                    # -----------------------------------------------------
                    # RESILIENCE: Status Code Handling
                    # -----------------------------------------------------
                    if status == 403 or status == 429:
                        logger.warning("soft_ban_detected", url=url, status=status)
                        raise RetryableException(f"Soft Ban ({status})")
                    elif status == 404:
                        logger.error("page_not_found", url=url)
                        return {'error': '404 Not Found', 'status': 404}
                    elif status >= 500:
                        logger.error("server_error", url=url, status=status)
                        raise RetryableException(f"Server Error ({status})")

                    # Wait for network settle
                    try:
                        await page.wait_for_load_state("networkidle", timeout=20000)
                    except:
                        logger.warning("network_idle_timeout")

                    # -----------------------------------------------------
                    # CAPTCHA Handling
                    # -----------------------------------------------------
                    captcha_info = await self.captcha_detector.detect(page)
                    if captcha_info and captcha_info['detected']:
                        logger.warning("captcha_detected", type=captcha_info['type'])
                        solved = await self.captcha_detector.solve_captcha(page, captcha_info)
                        if not solved:
                            raise RetryableException("CAPTCHA detected and solve failed")

                    # -----------------------------------------------------
                    # STEALTH: Human-like Interaction
                    # -----------------------------------------------------
                    await self.human_mouse.move_to(page, 500, 500)
                    
                    # Get handler
                    handler_class = await get_handler_for_url(url)
                    logger.info("using_handler", handler=handler_class.__name__)
                    
                    # Extract
                    result = await handler_class.extract_price(page, url)
                    
                    # Add metadata
                    result['score'] = 100.0
                    result['meta'] = {'handler': handler_class.__name__}
                    
                    return result

                except RetryableException:
                    raise
                except Exception as e:
                    # Save debug screenshot
                    screenshot_path = os.path.join(self.error_dir, f"error_{int(asyncio.get_event_loop().time())}.png")
                    try:
                        await page.screenshot(path=screenshot_path, full_page=True)
                        logger.error("error_screenshot_saved", path=screenshot_path)
                    except:
                        pass
                    raise e
                    
            finally:
                await context.close()
                await browser.close()

class ScraperOrchestrator:
    """
    Main orchestration engine with concurrency.
    """
    
    def __init__(self):
        self.config = get_config()
        self.db = DatabaseCore()
        self.killer = GracefulKiller()
        self.throttler = get_adaptive_throttler()
        self.domain_limiter = DomainRateLimiter(delay_seconds=2.0)
        self.circuit_breaker = CircuitBreaker()
        
        # Concurrency Control
        self.max_concurrent = self.config.get('scraper.concurrency', default=5)
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        
        # Managers
        self.proxy_manager = None
        # Temporarily disabled - ProxyManager requires aiohttp
        # if self.config.get('proxies.enabled', default=False):
        #     self.proxy_manager = ProxyManager()
            
        self.tls_manager = TLSSpoofingManager()
        self.worker = BrowserWorker(self.config)
        
        # Resilience: Retry Policy
        self.retry_decorator = retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type(RetryableException),
            reraise=True
        )

    async def initialize(self):
        """Initialize resources."""
        logger.info("initializing_orchestrator")
        await self.db.init_models()
        
        if self.proxy_manager:
            asyncio.create_task(self.proxy_manager.refresh_pool())

    async def run(self):
        """Main execution loop."""
        await self.initialize()
        
        logger.info("system_ready_waiting_for_tasks")
        
        tasks = set()
        
        while not self.killer.kill_now:
            # Clean up finished tasks
            done, tasks = await asyncio.wait(tasks, timeout=0.1) if tasks else (set(), set())
            
            # Check if we can start more tasks
            if len(tasks) < self.max_concurrent:
                try:
                    task = await self.db.get_pending_task()
                    
                    if not task:
                        await asyncio.sleep(1)
                        continue
                    
                    # Create new task
                    t = asyncio.create_task(self.process_task_wrapper(task))
                    tasks.add(t)
                    
                except Exception as e:
                    logger.error("task_fetch_error", error=str(e))
                    await asyncio.sleep(5)
            else:
                await asyncio.sleep(0.1)
        
        # Wait for remaining tasks
        if tasks:
            logger.info("waiting_for_remaining_tasks", count=len(tasks))
            await asyncio.gather(*tasks, return_exceptions=True)
            
        await self.shutdown()

    async def process_task_wrapper(self, task):
        """Wrapper to handle concurrency logic."""
        async with self.semaphore:
            # Check Circuit Breaker
            if self.circuit_breaker.is_open(task.url):
                logger.warning("circuit_breaker_open", url=task.url)
                await self.db.log_failure(task.id, "Circuit Breaker Open")
                return

            # Domain Rate Limiting
            await self.domain_limiter.acquire(task.url)
            
            logger.info("processing_task", url=task.url, id=task.id)
            
            try:
                # Apply adaptive throttling (sleep)
                self.throttler.sleep(task.url)
                
                # Execute with retry logic
                result = await self.process_task_with_retry(task.url)
                
                if 'error' in result and result.get('status') == 404:
                     await self.db.log_failure(task.id, "404 Not Found")
                else:
                    await self.db.save_success(task.id, result)
                    self.throttler.record_success(task.url)
                    logger.info("task_success", title=result.get('title', 'Unknown'), price=result.get('price', 0))
                
            except Exception as e:
                logger.error("task_failed", error=str(e))
                await self.db.log_failure(task.id, str(e))
                self.throttler.record_failure(task.url)
                self.circuit_breaker.record_failure(task.url)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=retry_if_exception_type(RetryableException))
    async def process_task_with_retry(self, url: str) -> Dict[str, Any]:
        """
        Process a task with automatic retries.
        """
        proxy = None
        if self.proxy_manager:
            proxy_data = self.proxy_manager.get_best_proxy()
            if proxy_data:
                proxy = proxy_data
        
        return await self.worker.run(url, proxy=proxy)

    async def shutdown(self):
        """Graceful shutdown."""
        logger.info("shutting_down_orchestrator")
        await self.db.dispose()
        logger.info("goodbye")

if __name__ == "__main__":
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    orchestrator = ScraperOrchestrator()
    asyncio.run(orchestrator.run())
