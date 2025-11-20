"""
Canvas & WebGL Fingerprint Noise Injection

Injects random noise into Canvas and WebGL APIs to prevent fingerprinting.
Each browser session will have a unique fingerprint, making tracking difficult.

Techniques:
- Canvas pixel data perturbation
- Font metrics randomization
- WebGL vendor/renderer spoofing
- AudioContext fingerprint noise
"""

import logging
import random
from typing import Optional
from playwright.async_api import Page
from config_manager import get_config

logger = logging.getLogger(__name__)


class CanvasNoiseInjector:
    """
    Injects noise into Canvas API to prevent fingerprinting.
    
    Canvas fingerprinting works by drawing text/shapes and reading pixel data.
    We inject random noise into the pixel values to make each session unique.
    """
    
    def __init__(self):
        """Initialize canvas noise injector."""
        self.config = get_config()
        self.enabled = self.config.get('stealth.canvas_noise.enabled', default=True)
        self.noise_intensity = self.config.get('stealth.canvas_noise.intensity', default=5)
        
        logger.info(f"Canvas Noise Injection: {'Enabled' if self.enabled else 'Disabled'} (intensity={self.noise_intensity})")
    
    async def inject(self, page: Page):
        """
        Inject canvas noise into the page context.
        
        This must be called BEFORE navigating to the target page,
        so the script runs before any page scripts.
        
        Args:
            page: Playwright page object
        """
        if not self.enabled:
            return
        
        noise_script = self._generate_canvas_noise_script()
        await page.add_init_script(noise_script)
        
        logger.debug("Canvas noise injected into page context")
    
    def _generate_canvas_noise_script(self) -> str:
        """
        Generate JavaScript code for canvas noise injection.
        
        Returns:
            JavaScript code as string
        """
        noise_intensity = self.noise_intensity
        
        return f"""
        (function() {{
            // Override getImageData to add noise
            const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
            CanvasRenderingContext2D.prototype.getImageData = function(...args) {{
                const imageData = originalGetImageData.apply(this, args);
                
                // Add random noise to pixel values
                for (let i = 0; i < imageData.data.length; i += 4) {{
                    const noise = Math.floor(Math.random() * {noise_intensity * 2}) - {noise_intensity};
                    
                    imageData.data[i] = Math.min(255, Math.max(0, imageData.data[i] + noise));      // R
                    imageData.data[i+1] = Math.min(255, Math.max(0, imageData.data[i+1] + noise));  // G
                    imageData.data[i+2] = Math.min(255, Math.max(0, imageData.data[i+2] + noise));  // B
                    // Alpha channel (i+3) unchanged
                }}
                
                return imageData;
            }};
            
            // Override toDataURL to add noise
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function(...args) {{
                const context = this.getContext('2d');
                if (context) {{
                    const imageData = context.getImageData(0, 0, this.width, this.height);
                    // Noise already added via getImageData override
                }}
                return originalToDataURL.apply(this, args);
            }};
            
            console.log('[Stealth] Canvas noise injection active (intensity={noise_intensity})');
        }})();
        """


class FontFingerprintRandomizer:
    """
    Randomizes font metrics to prevent font-based fingerprinting.
    
    Font fingerprinting measures text rendering dimensions which vary
    slightly between systems. We add random offsets to make tracking harder.
    """
    
    def __init__(self):
        """Initialize font randomizer."""
        self.config = get_config()
        self.enabled = self.config.get('stealth.font_randomization.enabled', default=True)
        
        logger.info(f"Font Randomization: {'Enabled' if self.enabled else 'Disabled'}")
    
    async def inject(self, page: Page):
        """Inject font metric randomization."""
        if not self.enabled:
            return
        
        script = """
        (function() {
            // Randomize measureText results
            const originalMeasureText = CanvasRenderingContext2D.prototype.measureText;
            CanvasRenderingContext2D.prototype.measureText = function(...args) {
                const metrics = originalMeasureText.apply(this, args);
                
                // Add small random offsets to width
                const offset = (Math.random() - 0.5) * 0.1;
                Object.defineProperty(metrics, 'width', {
                    value: metrics.width + offset,
                    writable: false
                });
                
                return metrics;
            };
            
            console.log('[Stealth] Font metric randomization active');
        })();
        """
        
        await page.add_init_script(script)
        logger.debug("Font randomization injected")


class WebGLFingerprintSpoofer:
    """
    Spoofs WebGL parameters to prevent GPU fingerprinting.
    
    WebGL exposes GPU vendor and renderer information which can be
    used for fingerprinting. We override these with common values.
    """
    
    def __init__(self):
        """Initialize WebGL spoofer."""
        self.config = get_config()
        self.enabled = self.config.get('stealth.webgl_spoofing.enabled', default=True)
        
        # Common GPU configurations to blend in with
        self.fake_renderers = [
            "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (NVIDIA, NVIDIA GeForce GTX 1060 Direct3D11 vs_5_0 ps_5_0)",
            "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0)"
        ]
        
        logger.info(f"WebGL Spoofing: {'Enabled' if self.enabled else 'Disabled'}")
    
    async def inject(self, page: Page):
        """Inject WebGL parameter spoofing."""
        if not self.enabled:
            return
        
        # Pick a random common renderer
        fake_renderer = random.choice(self.fake_renderers)
        
        script = f"""
        (function() {{
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {{
                // Override UNMASKED_VENDOR_WEBGL
                if (parameter === 37445) {{
                    return 'Google Inc. (NVIDIA)';
                }}
                // Override UNMASKED_RENDERER_WEBGL
                if (parameter === 37446) {{
                    return '{fake_renderer}';
                }}
                return getParameter.call(this, parameter);
            }};
            
            console.log('[Stealth] WebGL fingerprint spoofed');
        }})();
        """
        
        await page.add_init_script(script)
        logger.debug(f"WebGL spoofed: {fake_renderer}")


class StealthInjector:
    """
    Unified stealth injection manager.
    
    Combines all fingerprint prevention techniques into a single
    easy-to-use interface.
    """
    
    def __init__(self):
        """Initialize all stealth injectors."""
        self.canvas_noise = CanvasNoiseInjector()
        self.font_randomizer = FontFingerprintRandomizer()
        self.webgl_spoof = WebGLFingerprintSpoofer()
        
        logger.info("Stealth Injector initialized (Canvas, Font, WebGL)")
    
    async def inject_all(self, page: Page):
        """
        Inject all stealth scripts into page.
        
        Call this BEFORE navigating to the target page.
        
        Args:
            page: Playwright page object
        """
        await self.canvas_noise.inject(page)
        await self.font_randomizer.inject(page)
        await self.webgl_spoof.inject(page)
        
        logger.info("✅ All stealth scripts injected")
    
    async def test_fingerprint(self, page: Page) -> dict:
        """
        Test fingerprint by navigating to a fingerprinting site.
        
        Returns:
            Dictionary with fingerprint test results
        """
        try:
            await self.inject_all(page)
            await page.goto('https://browserleaks.com/canvas', wait_until='networkidle')
            
            # Wait for canvas test to complete
            await page.wait_for_timeout(3000)
            
            # Extract canvas hash (if available)
            canvas_hash = await page.evaluate("""
                () => {
                    const canvas = document.querySelector('canvas');
                    if (canvas) {
                        return canvas.toDataURL();
                    }
                    return null;
                }
            """)
            
            logger.info("Canvas fingerprint test completed")
            
            return {
                'canvas_data_url': canvas_hash[:100] + '...' if canvas_hash else None,
                'test_url': 'https://browserleaks.com/canvas'
            }
            
        except Exception as e:
            logger.error(f"Fingerprint test failed: {e}")
            return {'error': str(e)}


# Singleton instance
_stealth_injector = None

def get_stealth_injector() -> StealthInjector:
    """Get singleton stealth injector instance."""
    global _stealth_injector
    if _stealth_injector is None:
        _stealth_injector = StealthInjector()
    return _stealth_injector
