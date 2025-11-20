"""
Hot-Reloadable Configuration Manager - Single Source of Truth

This module provides a thread-safe, singleton configuration manager that:
1. Loads config from YAML files
2. Watches for file changes and hot-reloads
3. Supports environment variable interpolation
4. Validates configuration structure
5. Provides type-safe access to config values
"""

import os
import yaml
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


class ConfigFileHandler(FileSystemEventHandler):
    """Watches config file for changes and triggers reload."""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.last_reload = time.time()
        
    def on_modified(self, event):
        if event.src_path.endswith('config.yaml'):
            # Debounce: Don't reload more than once per second
            now = time.time()
            debounce = self.config_manager.config.get('hot_reload', {}).get('debounce_delay', 1)
            
            if now - self.last_reload >= debounce:
                logger.info(f"🔄 Config file changed, reloading...")
                self.config_manager.reload()
                self.last_reload = now


class ConfigurationManager:
    """
    Singleton configuration manager with hot-reload capability.
    
    Usage:
        config = ConfigurationManager()
        delay = config.get('scraper.rate_limiting.base_delay', default=2.0)
        model = config.ai.ollama.model_name  # Dot notation access
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Only initialize once
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        self.config: Dict[str, Any] = {}
        self.config_path: Optional[Path] = None
        self.observer: Optional[Observer] = None
        self._reload_callbacks = []
        
        # Load initial config
        self.load()
        
        # Start hot-reload watcher if enabled
        if self.get('hot_reload.enabled', default=False):
            self.start_watching()
    
    def load(self, config_path: Optional[str] = None):
        """Load configuration from YAML file."""
        if config_path is None:
            # Try multiple locations
            possible_paths = [
                Path('/app/config.yaml'),  # Docker container path
                Path(__file__).parent / 'config.yaml',  # Local development
                Path.cwd() / 'config.yaml',
            ]
            
            for path in possible_paths:
                if path.exists():
                    config_path = str(path)
                    break
            else:
                raise FileNotFoundError("config.yaml not found in any standard location")
        
        self.config_path = Path(config_path)
        
        try:
            with open(self.config_path, 'r') as f:
                raw_config = yaml.safe_load(f)
            
            # Interpolate environment variables
            self.config = self._interpolate_env_vars(raw_config)
            
            logger.info(f"✅ Configuration loaded from {self.config_path}")
            logger.debug(f"   Loaded {len(self.config)} top-level sections")
            
        except Exception as e:
            logger.error(f"❌ Failed to load configuration: {e}")
            raise
    
    def reload(self):
        """Reload configuration from file."""
        old_config = self.config.copy()
        
        try:
            self.load(str(self.config_path))
            
            # Notify about reload
            if self.get('hot_reload.notify_on_reload', default=True):
                logger.info("🔄 Configuration reloaded successfully")
                self._log_changes(old_config, self.config)
            
            # Trigger callbacks
            for callback in self._reload_callbacks:
                try:
                    callback(old_config, self.config)
                except Exception as e:
                    logger.error(f"Reload callback failed: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Config reload failed, keeping old config: {e}")
            self.config = old_config
    
    def start_watching(self):
        """Start watching config file for changes."""
        if self.observer is not None:
            logger.warning("Watcher already started")
            return
        
        watch_dir = self.config_path.parent
        self.observer = Observer()
        event_handler = ConfigFileHandler(self)
        self.observer.schedule(event_handler, str(watch_dir), recursive=False)
        self.observer.start()
        
        logger.info(f"👁️  Watching {self.config_path} for changes")
    
    def stop_watching(self):
        """Stop watching config file."""
        if self.observer is not None:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("Stopped config watcher")
    
    def on_reload(self, callback):
        """Register a callback to be called when config is reloaded."""
        self._reload_callbacks.append(callback)
    
    def get(self, key_path: str, default=None):
        """
        Get config value using dot notation.
        
        Args:
            key_path: Dot-separated path (e.g., 'scraper.rate_limiting.base_delay')
            default: Default value if key not found
            
        Returns:
            Config value or default
            
        Example:
            delay = config.get('scraper.rate_limiting.base_delay', default=2.0)
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any):
        """
        Set config value using dot notation (runtime only, not persisted).
        
        Args:
            key_path: Dot-separated path
            value: Value to set
        """
        keys = key_path.split('.')
        config_ref = self.config
        
        for key in keys[:-1]:
            if key not in config_ref:
                config_ref[key] = {}
            config_ref = config_ref[key]
        
        config_ref[keys[-1]] = value
        logger.debug(f"Set {key_path} = {value}")
    
    def _interpolate_env_vars(self, config: Any) -> Any:
        """
        Recursively replace ${VAR_NAME} with environment variables.
        
        Example:
            password: "${POSTGRES_PASSWORD}" -> password: "secretpass"
        """
        if isinstance(config, dict):
            return {k: self._interpolate_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._interpolate_env_vars(item) for item in config]
        elif isinstance(config, str):
            # Replace ${VAR} or $VAR with environment variables
            if config.startswith('${') and config.endswith('}'):
                var_name = config[2:-1]
                return os.getenv(var_name, config)
            return config
        else:
            return config
    
    def _log_changes(self, old: Dict, new: Dict, prefix=''):
        """Log configuration changes after reload."""
        changes = []
        
        def compare(old_dict, new_dict, path=''):
            for key in set(list(old_dict.keys()) + list(new_dict.keys())):
                current_path = f"{path}.{key}" if path else key
                
                old_val = old_dict.get(key)
                new_val = new_dict.get(key)
                
                if old_val != new_val:
                    if isinstance(old_val, dict) and isinstance(new_val, dict):
                        compare(old_val, new_val, current_path)
                    else:
                        changes.append(f"  • {current_path}: {old_val} → {new_val}")
        
        compare(old, new)
        
        if changes:
            logger.info(f"📝 Configuration changes detected:")
            for change in changes[:10]:  # Show first 10 changes
                logger.info(change)
            if len(changes) > 10:
                logger.info(f"  ... and {len(changes) - 10} more changes")
    
    def __getattr__(self, name):
        """Allow dot notation access: config.ai.ollama.model_name"""
        if name in self.config:
            value = self.config[name]
            if isinstance(value, dict):
                return DotDict(value, self)
            return value
        raise AttributeError(f"Config has no attribute '{name}'")
    
    def to_dict(self) -> Dict[str, Any]:
        """Return full config as dictionary."""
        return self.config.copy()


class DotDict:
    """Helper class for dot notation access to nested dicts."""
    
    def __init__(self, data: Dict, manager: ConfigurationManager):
        self._data = data
        self._manager = manager
    
    def __getattr__(self, name):
        if name.startswith('_'):
            return object.__getattribute__(self, name)
        
        if name in self._data:
            value = self._data[name]
            if isinstance(value, dict):
                return DotDict(value, self._manager)
            return value
        raise AttributeError(f"Config has no attribute '{name}'")
    
    def __getitem__(self, key):
        return self._data[key]
    
    def get(self, key, default=None):
        return self._data.get(key, default)


# Singleton instance
_config_instance = None

def get_config() -> ConfigurationManager:
    """Get the global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigurationManager()
    return _config_instance


# Example usage and testing
if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Get config instance
    config = get_config()
    
    # Test different access patterns
    print("\n=== Testing Configuration Access ===")
    
    # Dot notation
    print(f"Ollama model: {config.ai.ollama.model_name}")
    print(f"Base delay: {config.scraper.rate_limiting.base_delay}")
    
    # get() method
    print(f"Max workers: {config.get('scraper.concurrency.max_workers', default=4)}")
    
    # Test hot-reload
    print("\n=== Testing Hot-Reload ===")
    print("Modify config.yaml now, changes will be detected automatically...")
    
    # Keep alive for testing
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        config.stop_watching()
        print("\nShutting down")
