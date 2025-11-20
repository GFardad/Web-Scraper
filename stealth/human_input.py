"""
Human-like Input Simulation Module

Generates realistic mouse movements and keyboard input patterns that
mimic actual human behavior, evading bot detection systems.

Features:
- B-spline curve mouse movement
- Variable typing delays (keystroke dynamics)
- Random scroll patterns
- Click hesitation and overshoot
"""

import logging
import random
import asyncio
from typing import Tuple, List, Optional
import numpy as np
from scipy.interpolate import splprep, splev
from playwright.async_api import Page
from config_manager import get_config

logger = logging.getLogger(__name__)


class HumanMouseSimulator:
    """
    Simulates human-like mouse movements using B-spline curves.
    
    Real humans don't move the mouse in straight lines. Instead, they
    follow smooth, slightly curved paths with variable speeds.
    """
    
    def __init__(self):
        """Initialize mouse simulator."""
        self.config = get_config()
        self.enabled = self.config.get('stealth.human_input.enabled', default=True)
        self.speed_px_per_sec = self.config.get('stealth.human_input.mouse_speed_px_per_sec', default=800)
        
        logger.info(f"Human Mouse Simulator: {'Enabled' if self.enabled else 'Disabled'} ({self.speed_px_per_sec} px/s)")
    
    def generate_human_path(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        num_points: int = 50
    ) -> List[Tuple[float, float]]:
        """
        Generate smooth B-spline curve from start to end.
        
        Args:
            start: Starting (x, y) coordinates
            end: Ending (x, y) coordinates
            num_points: Number of points in the path
            
        Returns:
            List of (x, y) coordinate tuples forming smooth curve
        """
        if not self.enabled:
            # Straight line fallback
            return [start, end]
        
        # Calculate distance
        distance = np.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)
        
        # Add control points with randomness
        num_control_points = max(3, int(distance / 200))  # More points for longer distances
        
        control_x = np.linspace(start[0], end[0], num_control_points)
        control_y = np.linspace(start[1], end[1], num_control_points)
        
        # Add random offsets to middle control points (not start/end)
        offset_magnitude = min(50, distance * 0.1)  # 10% of distance, max 50px
        for i in range(1, num_control_points - 1):
            control_x[i] += np.random.randn() * offset_magnitude
            control_y[i] += np.random.randn() * offset_magnitude
        
        try:
            # Fit B-spline curve
            tck, u = splprep([control_x, control_y], s=0, k=min(3, num_control_points - 1))
            
            # Evaluate spline at evenly spaced points
            u_new = np.linspace(0, 1, num_points)
            x_new, y_new = splev(u_new, tck)
            
            # Convert to list of tuples
            path = list(zip(x_new, y_new))
            
            return path
            
        except Exception as e:
            logger.warning(f"B-spline generation failed: {e}. Using straight line.")
            return [start, end]
    
    async def move_to(
        self,
        page: Page,
        x: float,
        y: float,
        start_x: Optional[float] = None,
        start_y: Optional[float] = None
    ):
        """
        Move mouse to target coordinates following a human-like path.
        
        Args:
            page: Playwright Page object
            x: Target X coordinate
            y: Target Y coordinate
            start_x: Starting X (None = current position)
            start_y: Starting Y (None = current position)
        """
        if not self.enabled:
            # Instant movement
            await page.mouse.move(x, y)
            return
        
        # Get current mouse position (approximate as viewport center if unknown)
        if start_x is None or start_y is None:
            viewport = page.viewport_size
            start_x = viewport['width'] / 2
            start_y = viewport['height'] / 2
        
        # Generate smooth path
        path = self.generate_human_path((start_x, start_y), (x, y))
        
        # Calculate total distance
        total_distance = sum(
            np.sqrt((path[i+1][0] - path[i][0])**2 + (path[i+1][1] - path[i][1])**2)
            for i in range(len(path) - 1)
        )
        
        # Calculate total time based on speed
        total_time = total_distance / self.speed_px_per_sec
        
        # Move along path
        for i, (px, py) in enumerate(path):
            await page.mouse.move(px, py)
            
            # Variable delay between points
            if i < len(path) - 1:
                delay = (total_time / len(path)) * random.uniform(0.8, 1.2)
                await asyncio.sleep(delay)
    
    async def click_with_hesitation(
        self,
        page: Page,
        x: float,
        y: float,
        button: str = 'left'
    ):
        """
        Click with slight overshoot and correction (human behavior).
        
        Humans often slightly overshoot their target and then correct.
        
        Args:
            page: Playwright Page object
            x: Target X coordinate
            y: Target Y coordinate
            button: Mouse button ('left', 'right', 'middle')
        """
        if not self.enabled:
            await page.mouse.click(x, y, button=button)
            return
        
        # Move close to target with slight overshoot
        overshoot_x = x + random.uniform(-5, 5)
        overshoot_y = y + random.uniform(-5, 5)
        
        await self.move_to(page, overshoot_x, overshoot_y)
        
        # Small delay (hesitation)
        await asyncio.sleep(random.uniform(0.05, 0.15))
        
        # Correct to exact position
        await page.mouse.move(x, y)
        
        # Click
        await page.mouse.click(x, y, button=button, delay=random.randint(50, 150))
        
        logger.debug(f"Human-like click at ({x}, {y})")


class HumanTypingSimulator:
    """
    Simulates human-like typing with variable delays.
    
    Keystroke dynamics (typing rhythm) can be used for fingerprinting.
    We add realistic variations in typing speed.
    """
    
    def __init__(self):
        """Initialize typing simulator."""
        self.config = get_config()
        self.enabled = self.config.get('stealth.human_input.enabled', default=True)
        self.delay_min = self.config.get('stealth.human_input.typing_delay_ms_min', default=50)
        self.delay_max = self.config.get('stealth.human_input.typing_delay_ms_max', default=150)
        
        logger.info(f"Human Typing Simulator: {'Enabled' if self.enabled else 'Disabled'} ({self.delay_min}-{self.delay_max}ms)")
    
    async def type_text(
        self,
        page: Page,
        selector: str,
        text: str,
        clear_first: bool = True
    ):
        """
        Type text into an element with human-like delays.
        
        Args:
            page: Playwright Page object
            selector: CSS selector for input element
            text: Text to type
            clear_first: Whether to clear existing text first
        """
        if not self.enabled:
            # Instant typing
            await page.fill(selector, text)
            return
        
        # Locate element
        element = page.locator(selector)
        
        # Clear if needed
        if clear_first:
            await element.clear()
        
        # Focus element
        await element.focus()
        
        # Type each character with variable delay
        for char in text:
            await element.type(char, delay=random.randint(self.delay_min, self.delay_max))
            
            # Extra delay after punctuation (human behavior)
            if char in '.,!?;:':
                await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # Occasional longer pause (thinking)
            if random.random() < 0.05:  # 5% chance
                await asyncio.sleep(random.uniform(0.5, 1.5))
        
        logger.debug(f"Human-like typed: '{text[:20]}...' into {selector}")
    
    async def type_with_mistakes(
        self,
        page: Page,
        selector: str,
        text: str,
        mistake_rate: float = 0.05
    ):
        """
        Type with occasional typos and corrections (very human!).
        
        Args:
            page: Playwright Page object
            selector: CSS selector for input element
            text: Text to type
            mistake_rate: Probability of typo per character (0.0-1.0)
        """
        element = page.locator(selector)
        await element.focus()
        
        for i, char in enumerate(text):
            # Randomly make a typo
            if random.random() < mistake_rate and i > 0:
                # Type wrong key (adjacent on keyboard)
                wrong_char = self._get_adjacent_key(char)
                await element.type(wrong_char, delay=random.randint(self.delay_min, self.delay_max))
                
                # Realize mistake (short pause)
                await asyncio.sleep(random.uniform(0.2, 0.5))
                
                # Backspace
                await element.press('Backspace', delay=random.randint(50, 100))
            
            # Type correct character
            await element.type(char, delay=random.randint(self.delay_min, self.delay_max))
        
        logger.debug(f"Typed with realistic mistakes: '{text[:20]}...'")
    
    def _get_adjacent_key(self, char: str) -> str:
        """Get an adjacent key on QWERTY keyboard."""
        keyboard_layout = {
            'a': 'sq', 'b': 'vgn', 'c': 'xvd', 'd': 'sfc', 'e': 'wr',
            'f': 'dgv', 'g': 'fht', 'h': 'gjy', 'i': 'uo', 'j': 'hku',
            'k': 'jli', 'l': 'kp', 'm': 'nj', 'n': 'bmh', 'o': 'ip',
            'p': 'ol', 'q': 'wa', 'r': 'et', 's': 'adw', 't': 'ry',
            'u': 'yи', 'v': 'cfb', 'w': 'qse', 'x': 'zcd', 'y': 'tu',
            'z': 'xs'
        }
        
        adjacent = keyboard_layout.get(char.lower(), char)
        return random.choice(adjacent) if adjacent else char


class HumanScrollSimulator:
    """
    Simulates human-like scrolling patterns.
    
    Bot scrolling is often perfectly smooth or in fixed increments.
    Humans scroll erratically with variable speeds and directions.
    """
    
    def __init__(self):
        """Initialize scroll simulator."""
        self.config = get_config()
        self.enabled = self.config.get('stealth.human_input.enabled', default=True)
        
        logger.info(f"Human Scroll Simulator: {'Enabled' if self.enabled else 'Disabled'}")
    
    async def scroll_to_element(
        self,
        page: Page,
        selector: str,
        smooth: bool = True
    ):
        """
        Scroll to element with human-like behavior.
        
        Args:
            page: Playwright Page object
            selector: CSS selector for target element
            smooth: Whether to use smooth scrolling
        """
        if not self.enabled:
            await page.locator(selector).scroll_into_view_if_needed()
            return
        
        # Get element position
        element = page.locator(selector)
        box = await element.bounding_box()
        
        if not box:
            logger.warning(f"Element not found: {selector}")
            return
        
        # Get current scroll position
        current_y = await page.evaluate("window.pageYOffset")
        target_y = box['y'] - 100  # Leave some space above element
        
        # Calculate scroll distance
        distance = abs(target_y - current_y)
        
        # Number of scroll steps (more for longer distances)
        num_steps = max(5, int(distance / 100))
        
        # Scroll in increments with variable delays
        for i in range(num_steps):
            progress = (i + 1) / num_steps
            
            # Ease-in-out curve for smooth motion
            eased_progress = 0.5 - 0.5 * np.cos(progress * np.pi)
            
            scroll_y = current_y + (target_y - current_y) * eased_progress
            
            # Add small random offset
            scroll_y += random.uniform(-10, 10)
            
            await page.evaluate(f"window.scrollTo(0, {scroll_y})")
            
            # Variable delay
            await asyncio.sleep(random.uniform(0.05, 0.15))
        
        logger.debug(f"Human-like scrolled to {selector}")


# Singleton instances
_mouse_simulator = None
_typing_simulator = None
_scroll_simulator = None

def get_human_mouse() -> HumanMouseSimulator:
    """Get singleton mouse simulator."""
    global _mouse_simulator
    if _mouse_simulator is None:
        _mouse_simulator = HumanMouseSimulator()
    return _mouse_simulator

def get_human_typing() -> HumanTypingSimulator:
    """Get singleton typing simulator."""
    global _typing_simulator
    if _typing_simulator is None:
        _typing_simulator = HumanTypingSimulator()
    return _typing_simulator

def get_human_scroll() -> HumanScrollSimulator:
    """Get singleton scroll simulator."""
    global _scroll_simulator
    if _scroll_simulator is None:
        _scroll_simulator = HumanScrollSimulator()
    return _scroll_simulator
