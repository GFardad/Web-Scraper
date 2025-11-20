"""
User-Agent Pool & Rotation System

Maintains a pool of realistic User-Agents and rotates them automatically
to avoid browser fingerprinting detection.
"""

import random
import logging
from typing import Dict, List

logger = logging.getLogger("UserAgentPool")

# Curated list of real User-Agents (Chrome, Firefox, Safari, Edge)
USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    
    # Chrome on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    
    # Firefox on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    
    # Safari on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    
    # Chrome on Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    
    # Mobile Chrome
    "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    
    # Mobile Safari
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
]

# Browser-appropriate headers
BROWSER_HEADERS = {
    "chrome": {
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
    },
    "firefox": {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "accept-encoding": "gzip, deflate, br",
        "upgrade-insecure-requests": "1",
    },
    "safari": {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept-encoding": "gzip, deflate, br",
    }
}


class UserAgentPool:
    """Manages User-Agent rotation with appropriate headers."""
    
    def __init__(self, user_agents: List[str] = None):
        """
        Initialize UA pool.
        
        Args:
            user_agents: Optional custom UA list
        """
        self.user_agents = user_agents or USER_AGENTS
        self.current_index = 0
        logger.info(f"Initialized UA pool with {len(self.user_agents)} agents")
    
    def get_random(self) -> str:
        """Get a random User-Agent."""
        return random.choice(self.user_agents)
    
    def get_next(self) -> str:
        """Get next User-Agent in rotation."""
        ua = self.user_agents[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.user_agents)
        return ua
    
    def get_with_headers(self) -> Dict[str, str]:
        """
        Get User-Agent with appropriate browser headers.
        
        Returns:
            Dict with 'user-agent' and browser-specific headers
        """
        ua = self.get_random()
        
        # Detect browser type
        if "Firefox" in ua:
            browser_type = "firefox"
        elif "Safari" in ua and "Chrome" not in ua:
            browser_type = "safari"
        else:
            browser_type = "chrome"
        
        headers = {
            "user-agent": ua,
            "accept-language": "en-US,en;q=0.9,fa;q=0.8",
        }
        
        # Add browser-specific headers
        headers.update(BROWSER_HEADERS.get(browser_type, {}))
        
        logger.debug(f"Generated headers for {browser_type}")
        return headers
    
    @staticmethod
    def is_mobile(ua: str) -> bool:
        """Check if User-Agent is mobile."""
        mobile_indicators = ["Mobile", "Android", "iPhone", "iPad"]
        return any(indicator in ua for indicator in mobile_indicators)
