"""
Session Persistence & Cookie Management

Maintains browser sessions and cookies across requests for authenticated scraping.
"""

import logging
import json
import os
from typing import Dict, List, Optional
from pathlib import Path
from playwright.async_api import BrowserContext, Page

logger = logging.getLogger("SessionManager")


class SessionManager:
    """Manages persistent browser sessions and cookies."""
    
    def __init__(self, storage_dir: str = "sessions"):
        """
        Initialize session manager.
        
        Args:
            storage_dir: Directory to store session data
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        logger.info(f"Session storage: {self.storage_dir}")
    
    def get_session_file(self, session_name: str) -> Path:
        """Get path to session file."""
        return self.storage_dir / f"{session_name}.json"
    
    async def save_session(self, context: BrowserContext, session_name: str):
        """
        Save browser context state (cookies, localStorage, etc.).
        
       Args:
            context: Playwright BrowserContext
            session_name: Name for this session
        """
        try:
            session_file = self.get_session_file(session_name)
            
            # Save storage state
            await context.storage_state(path=str(session_file))
            
            logger.info(f"Session saved: {session_name}")
        except Exception as e:
            logger.error(f"Failed to save session {session_name}: {e}")
    
    async def load_session(self, session_name: str) -> Optional[Dict]:
        """
        Load session state.
        
        Args:
            session_name: Session name to load
            
        Returns:
            Storage state dict or None
        """
        try:
            session_file = self.get_session_file(session_name)
            
            if not session_file.exists():
                logger.debug(f"Session not found: {session_name}")
                return None
            
            # Load from file
            with open(session_file, 'r') as f:
                state = json.load(f)
            
            logger.info(f"Session loaded: {session_name}")
            return state
            
        except Exception as e:
            logger.error(f"Failed to load session {session_name}: {e}")
            return None
    
    async def get_cookies(self, context: BrowserContext) -> List[Dict]:
        """Get all cookies from context."""
        try:
            cookies = await context.cookies()
            return cookies
        except Exception as e:
            logger.error(f"Failed to get cookies: {e}")
            return []
    
    async def add_cookies(self, context: BrowserContext, cookies: List[Dict]):
        """Add cookies to context."""
       try:
            await context.add_cookies(cookies)
            logger.info(f"Added {len(cookies)} cookies to context")
        except Exception as e:
            logger.error(f"Failed to add cookies: {e}")
    
    def delete_session(self, session_name: str) -> bool:
        """
        Delete saved session.
        
        Args:
            session_name: Session to delete
            
        Returns:
            True if deleted
        """
        try:
            session_file = self.get_session_file(session_name)
            if session_file.exists():
                session_file.unlink()
                logger.info(f"Session deleted: {session_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False
    
    def list_sessions(self) -> List[str]:
        """List all saved sessions."""
        try:
            sessions = [f.stem for f in self.storage_dir.glob("*.json")]
            return sessions
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []
