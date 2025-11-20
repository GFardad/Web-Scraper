import aiohttp
import asyncio
import random
import logging
import time
from typing import List, Optional, Dict, Set, Tuple, Any
from config import PROXY_SOURCES, PROXY_TEST_SAMPLE_SIZE, PROXY_TOP_PERCENTAGE

logger = logging.getLogger("ProxyGuard")

class ProxyManager:
    def __init__(self) -> None:
        self.valid_proxies: List[str] = []
        self.proxy_sources: List[str] = PROXY_SOURCES
        self.is_updating: bool = False

    async def fetch_raw_proxies(self) -> List[str]:
        """Download raw proxy list from internet."""
        raw_proxies: Set[str] = set()
        async with aiohttp.ClientSession() as session:
            for url in self.proxy_sources:
                try:
                    async with session.get(url, timeout=10) as response:
                        if response.status == 200:
                            text = await response.text()
                            for line in text.splitlines():
                                if ':' in line: 
                                    raw_proxies.add(line.strip())
                except Exception as e:
                    logger.warning(f"Failed to fetch proxies from {url}: {e}")
        return list(raw_proxies)

    async def validate_single_proxy(self, proxy: str, session: aiohttp.ClientSession) -> Tuple[Optional[str], Optional[float]]:
        """Test real connection to measure latency."""
        try:
            start_time = time.perf_counter()
            proxy_url = f"http://{proxy}"
            async with session.get("http://httpbin.org/ip", proxy=proxy_url, timeout=6) as resp:
                if resp.status == 200:
                    latency = time.perf_counter() - start_time
                    return proxy, latency
        except Exception:
            pass
        return None, None

    async def refresh_pool(self) -> None:
        """Refresh the pool of valid proxies."""
        if self.is_updating:
            return
        self.is_updating = True
        logger.info("Scanning and updating proxies (approximately 1 minute)...")
        
        try:
            raw_list = await self.fetch_raw_proxies()
            sample = random.sample(raw_list, min(len(raw_list), PROXY_TEST_SAMPLE_SIZE))
            
            new_valid: List[Dict[str, Any]] = []
            async with aiohttp.ClientSession() as session:
                tasks = [self.validate_single_proxy(p, session) for p in sample]
                results = await asyncio.gather(*tasks)
                
                for proxy, latency in results:
                    if proxy and latency is not None:
                        new_valid.append({'url': proxy, 'latency': latency})
            
            # Sort by latency (fastest first)
            new_valid.sort(key=lambda x: x['latency'])
            self.valid_proxies = [p['url'] for p in new_valid]
            
            logger.info(f"{len(self.valid_proxies)} high-speed proxies activated.")
        except Exception as e:
            logger.error(f"Error refreshing proxy pool: {e}")
        finally:
            self.is_updating = False

    def get_best_proxy(self) -> Optional[Dict[str, str]]:
        """Get a proxy from the top percentage of the list."""
        if not self.valid_proxies:
            return None
        # Randomly select from top percentage to distribute load
        top_n = max(1, int(len(self.valid_proxies) * PROXY_TOP_PERCENTAGE))
        proxy_url = random.choice(self.valid_proxies[:top_n])
        return {"server": f"http://{proxy_url}"}

    def remove_bad_proxy(self, proxy_url: str) -> None:
        """Remove a proxy that failed."""
        if proxy_url in self.valid_proxies:
            self.valid_proxies.remove(proxy_url)
