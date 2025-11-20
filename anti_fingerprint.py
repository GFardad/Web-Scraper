"""
Advanced Anti-Fingerprinting

Implements techniques to bypass browser fingerprinting and bot detection.
Includes canvas noise injection, WebGL spoofing, and timezone matching.
"""

import logging
import random

logger = logging.getLogger("AntiFingerprint")

# Canvas noise injection script
CANVAS_DEFENDER = """
() => {
    const originalGetContext = HTMLCanvasElement.prototype.getContext;
    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    const originalToBlob = HTMLCanvasElement.prototype.toBlob;
    
    const noise = () => Math.random() * 0.0001;
    
    HTMLCanvasElement.prototype.getContext = function(type, attributes) {
        const context = originalGetContext.call(this, type, attributes);
        
        if (type === '2d' && context) {
            const originalFillText = context.fillText;
            const originalStrokeText = context.strokeText;
            
            context.fillText = function(...args) {
                args[1] += noise();
                args[2] += noise();
                return originalFillText.apply(this, args);
            };
            
            context.strokeText = function(...args) {
                args[1] += noise();
                args[2] += noise();
                return originalStrokeText.apply(this, args);
            };
        }
        
        return context;
    };
}
"""

# WebGL fingerprint randomization
WEBGL_DEFENDER = """
() => {
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) {
            return 'Intel Inc.';
        }
        if (parameter === 37446) {
            return 'Intel Iris OpenGL Engine';
        }
        return getParameter.call(this, parameter);
    };
}
"""

# Randomize plugin/font lists
PLUGIN_RANDOMIZER = """
() => {
    Object.defineProperty(navigator, 'plugins', {
        get: () => [
            {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
            {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
            {name: 'Native Client', filename: 'internal-nacl-plugin'}
        ]
    });
}
"""


class AntiFingerprint:
    """Anti-fingerprinting techniques."""
    
    @staticmethod
    async def apply_stealth(page):
        """
        Apply all anti-fingerprinting techniques to a page.
        
        Args:
            page: Playwright page object
        """
        try:
            # Inject canvas defender
            await page.add_init_script(CANVAS_DEFENDER)
            logger.debug("Canvas defender injected")
            
            # Inject WebGL defender
            await page.add_init_script(WEBGL_DEFENDER)
            logger.debug("WebGL defender injected")
            
            # Inject plugin randomizer
            await page.add_init_script(PLUGIN_RANDOMIZER)
            logger.debug("Plugin randomizer injected")
            
            # Randomize screen resolution slightly
            await page.add_init_script(f"""
            () => {{
                Object.defineProperty(screen, 'width', {{
                    get: () => {1920 + random.randint(-10, 10)}
                }});
                Object.defineProperty(screen, 'height', {{
                    get: () => {1080 + random.randint(-10, 10)}
                }});
            }}
            """)
            
            logger.info("Anti-fingerprinting techniques applied")
            
        except Exception as e:
            logger.error(f"Failed to apply anti-fingerprinting: {e}")
    
    @staticmethod
    def get_random_timezone():
        """Get a random timezone for geo-matching."""
        timezones = [
            'Asia/Tehran',
            'Asia/Dubai',
            'Europe/Istanbul',
            'Europe/London',
            'America/New_York'
        ]
        return random.choice(timezones)
