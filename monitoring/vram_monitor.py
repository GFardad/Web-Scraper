"""
GPU VRAM Monitoring Module

Tracks NVIDIA GPU memory usage to ensure AI models (Ollama + PaddleOCR)
stay within the 3GB VRAM budget.

Features:
- Real-time VRAM usage tracking
- Capacity checking before GPU-heavy operations
- Automatic usage reporting to Prometheus
- VRAM threshold alerts
"""

import logging
from typing import Dict, Optional
import pynvml
from config_manager import get_config

logger = logging.getLogger(__name__)


class VRAMMonitor:
    """
    Monitors NVIDIA GPU VRAM usage.
    
    Ensures that AI operations (OCR, LLM) don't exceed the 3GB budget
    by checking available VRAM before loading models.
    """
    
    def __init__(self):
        """Initialize VRAM monitor."""
        self.config = get_config()
        self.max_vram_gb = self.config.get('ai.gpu.max_vram_gb', default=3.0)
        self.gpu_enabled = self.config.get('ai.gpu.enabled', default=True)
        
        if not self.gpu_enabled:
            logger.info("GPU disabled in config, VRAM monitoring inactive")
            self.initialized = False
            return
        
        try:
            # Initialize NVIDIA Management Library
            pynvml.nvmlInit()
            
            # Get handle for first GPU (index 0)
            self.handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            
            # Get GPU name
            self.gpu_name = pynvml.nvmlDeviceGetName(self.handle)
            
            # Get total VRAM
            info = pynvml.nvmlDeviceGetMemoryInfo(self.handle)
            self.total_vram_gb = info.total / (1024**3)
            
            self.initialized = True
            
            logger.info(f"✅ VRAM Monitor initialized: {self.gpu_name}")
            logger.info(f"   Total VRAM: {self.total_vram_gb:.2f} GB")
            logger.info(f"   Budget: {self.max_vram_gb:.2f} GB")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize VRAM monitor: {e}")
            self.initialized = False
    
    def get_usage(self) -> Dict[str, float]:
        """
        Get current VRAM usage.
        
        Returns:
            Dictionary with 'used_gb', 'free_gb', 'total_gb', 'percent'
        """
        if not self.initialized:
            return {
                'used_gb': 0.0,
                'free_gb': 0.0,
                'total_gb': 0.0,
                'percent': 0.0
            }
        
        try:
            info = pynvml.nvmlDeviceGetMemoryInfo(self.handle)
            
            used_gb = info.used / (1024**3)
            free_gb = info.free / (1024**3)
            total_gb = info.total / (1024**3)
            percent = (info.used / info.total) * 100
            
            return {
                'used_gb': used_gb,
                'free_gb': free_gb,
                'total_gb': total_gb,
                'percent': percent
            }
            
        except Exception as e:
            logger.error(f"Failed to get VRAM usage: {e}")
            return {'used_gb': 0.0, 'free_gb': 0.0, 'total_gb': 0.0, 'percent': 0.0}
    
    def has_capacity(self, task_type: str) -> bool:
        """
        Check if there's enough VRAM for a specific task.
        
        Args:
            task_type: 'ocr' or 'llm'
            
        Returns:
            True if enough VRAM available, False otherwise
        """
        if not self.initialized:
            # If monitoring disabled, allow all operations
            return True
        
        # VRAM requirements (from config)
        requirements = {
            'ocr': self.config.get('ai.paddleocr.vram_gb', default=0.7),
            'llm': self.config.get('ai.ollama.vram_gb', default=2.3)
        }
        
        required_gb = requirements.get(task_type, 0.5)
        
        usage = self.get_usage()
        current_used = usage['used_gb']
        
        # Check if adding this task would exceed budget
        projected_usage = current_used + required_gb
        
        if projected_usage > self.max_vram_gb:
            logger.warning(
                f"⚠️  Insufficient VRAM for {task_type}: "
                f"Current={current_used:.2f}GB + Required={required_gb:.2f}GB "
                f"= {projected_usage:.2f}GB > Budget={self.max_vram_gb:.2f}GB"
            )
            return False
        
        return True
    
    def get_gpu_utilization(self) -> float:
        """
        Get GPU compute utilization percentage.
        
        Returns:
            GPU utilization (0-100)
        """
        if not self.initialized:
            return 0.0
        
        try:
            util = pynvml.nvmlDeviceGetUtilizationRates(self.handle)
            return util.gpu  # Returns 0-100
            
        except Exception as e:
            logger.error(f"Failed to get GPU utilization: {e}")
            return 0.0
    
    def get_temperature(self) -> int:
        """
        Get GPU temperature in Celsius.
        
        Returns:
            Temperature in °C
        """
        if not self.initialized:
            return 0
        
        try:
            temp = pynvml.nvmlDeviceGetTemperature(self.handle, pynvml.NVML_TEMPERATURE_GPU)
            return temp
            
        except Exception as e:
            logger.error(f"Failed to get GPU temperature: {e}")
            return 0
    
    def get_power_usage(self) -> float:
        """
        Get current GPU power draw in Watts.
        
        Returns:
            Power usage in W
        """
        if not self.initialized:
            return 0.0
        
        try:
            power_mw = pynvml.nvmlDeviceGetPowerUsage(self.handle)
            power_w = power_mw / 1000.0
            return power_w
            
        except Exception as e:
            logger.error(f"Failed to get power usage: {e}")
            return 0.0
    
    def get_full_stats(self) -> Dict[str, any]:
        """
        Get comprehensive GPU statistics.
        
        Returns:
            Dictionary with all available GPU metrics
        """
        usage = self.get_usage()
        
        return {
            'gpu_name': self.gpu_name if self.initialized else 'N/A',
            'vram_used_gb': usage['used_gb'],
            'vram_free_gb': usage['free_gb'],
            'vram_total_gb': usage['total_gb'],
            'vram_percent': usage['percent'],
            'vram_budget_gb': self.max_vram_gb,
            'within_budget': usage['used_gb'] <= self.max_vram_gb,
            'gpu_utilization_percent': self.get_gpu_utilization(),
            'temperature_celsius': self.get_temperature(),
            'power_watts': self.get_power_usage()
        }
    
    def log_stats(self):
        """Log current GPU statistics."""
        stats = self.get_full_stats()
        
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"🎮 GPU: {stats['gpu_name']}")
        logger.info(f"📊 VRAM: {stats['vram_used_gb']:.2f}/{stats['vram_total_gb']:.2f} GB ({stats['vram_percent']:.1f}%)")
        logger.info(f"💰 Budget: {stats['vram_budget_gb']:.2f} GB ({'✅ OK' if stats['within_budget'] else '⚠️  EXCEEDED'})")
        logger.info(f"⚡ Utilization: {stats['gpu_utilization_percent']:.1f}%")
        logger.info(f"🌡️  Temperature: {stats['temperature_celsius']}°C")
        logger.info(f"🔌 Power: {stats['power_watts']:.1f}W")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    def cleanup(self):
        """Shutdown NVML."""
        if self.initialized:
            try:
                pynvml.nvmlShutdown()
                logger.info("VRAM monitor shutdown")
            except:
                pass


# Singleton instance
_vram_monitor = None

def get_vram_monitor() -> VRAMMonitor:
    """Get singleton VRAM monitor instance."""
    global _vram_monitor
    if _vram_monitor is None:
        _vram_monitor = VRAMMonitor()
    return _vram_monitor
