"""
Enhanced Configuration Management Module
Author: Darkstar Boii Sahiil
Version: 3.0 - Production Ready
Description: Advanced configuration management with environment support, validation, and auto-reload
"""

import os
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
import threading
import hashlib
import secrets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    path: str = "users.db"
    backup_path: str = "backups"
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    connection_pool_size: int = 10
    connection_timeout: int = 30
    query_timeout: int = 60
    enable_foreign_keys: bool = True
    journal_mode: str = "WAL"
    synchronous_mode: str = "NORMAL"
    cache_size: int = -2000  # 2MB
    temp_store: str = "MEMORY"


@dataclass
class BrowserConfig:
    """Browser automation configuration"""
    headless: bool = True
    window_width: int = 1920
    window_height: int = 1080
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    binary_location: Optional[str] = None
    driver_path: Optional[str] = None
    download_directory: str = "downloads"
    proxy_enabled: bool = False
    proxy_address: Optional[str] = None
    proxy_port: Optional[int] = None
    proxy_username: Optional[str] = None
    proxy_password: Optional[str] = None
    page_load_timeout: int = 60
    script_timeout: int = 30
    implicit_wait: int = 10
    pool_size: int = 3
    max_retries: int = 3
    retry_delay: int = 5


@dataclass
class AutomationConfig:
    """Automation engine configuration"""
    max_workers: int = 5
    worker_timeout: int = 300
    message_delay_min: int = 10
    message_delay_max: int = 60
    auto_restart_enabled: bool = True
    auto_restart_delay: int = 30
    max_restart_attempts: int = 10
    health_check_interval: int = 60
    log_rotation_size: int = 10  # MB
    log_retention_days: int = 30
    enable_metrics: bool = True
    metrics_retention_hours: int = 24


@dataclass
class SecurityConfig:
    """Security and encryption settings"""
    encryption_key_file: str = ".encryption_key"
    session_timeout: int = 3600  # 1 hour
    max_login_attempts: int = 5
    lockout_duration: int = 900  # 15 minutes
    password_min_length: int = 6
    require_strong_password: bool = False
    csrf_protection: bool = True
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds


@dataclass
class AlertConfig:
    """Alert and notification configuration"""
    enabled: bool = True
    email_enabled: bool = False
    email_smtp_server: Optional[str] = None
    email_smtp_port: int = 587
    email_username: Optional[str] = None
    email_password: Optional[str] = None
    email_from: Optional[str] = None
    email_to: List[str] = field(default_factory=list)
    webhook_enabled: bool = False
    webhook_url: Optional[str] = None
    alert_on_error: bool = True
    alert_on_restart: bool = True
    alert_on_threshold: int = 5  # errors


@dataclass
class AppConfig:
    """Main application configuration"""
    app_name: str = "Darkstar E2EE Automation"
    app_version: str = "3.0.0"
    debug_mode: bool = False
    log_level: str = "INFO"
    workspace_dir: str = "/workspace"
    data_dir: str = "data"
    temp_dir: str = "temp"
    logs_dir: str = "logs"
    enable_analytics: bool = True
    enable_health_checks: bool = True
    health_check_port: int = 8051
    enable_auto_update: bool = False
    
    # Sub-configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    automation: AutomationConfig = field(default_factory=AutomationConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)


class ConfigManager:
    """
    Advanced configuration manager with validation, auto-reload, and environment support
    """
    
    _instance: Optional['ConfigManager'] = None
    _lock = threading.Lock()
    
    def __new__(cls, config_file: str = "config.yaml"):
        """Singleton pattern implementation"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ConfigManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_file: str = "config.yaml"):
        """Initialize configuration manager"""
        if self._initialized:
            return
            
        self.config_file = Path(config_file)
        self.config: AppConfig = AppConfig()
        self._watch_thread: Optional[threading.Thread] = None
        self._watch_enabled = False
        self._callbacks: List[callable] = []
        
        # Load configuration from file if exists
        if self.config_file.exists():
            self.load_config()
        
        # Override with environment variables
        self._load_env_vars()
        
        # Validate configuration
        self._validate_config()
        
        # Create necessary directories
        self._create_directories()
        
        self._initialized = True
        logger.info(f"Configuration manager initialized: {self.config.app_name} v{self.config.app_version}")
    
    def _load_env_vars(self):
        """Load configuration from environment variables"""
        env_mappings = {
            'APP_DEBUG': ('debug_mode', bool),
            'APP_LOG_LEVEL': ('log_level', str),
            'DB_PATH': ('database.path', str),
            'DB_BACKUP_ENABLED': ('database.backup_enabled', bool),
            'BROWSER_HEADLESS': ('browser.headless', bool),
            'BROWSER_POOL_SIZE': ('browser.pool_size', int),
            'AUTOMATION_MAX_WORKERS': ('automation.max_workers', int),
            'AUTO_RESTART_ENABLED': ('automation.auto_restart_enabled', bool),
            'SECURITY_SESSION_TIMEOUT': ('security.session_timeout', int),
            'ALERTS_ENABLED': ('alerts.enabled', bool),
        }
        
        for env_var, (config_path, config_type) in env_mappings.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                
                if config_type == bool:
                    value = value.lower() in ('true', '1', 'yes', 'on')
                elif config_type == int:
                    value = int(value)
                
                # Navigate to nested attribute
                parts = config_path.split('.')
                obj = self.config
                for part in parts[:-1]:
                    obj = getattr(obj, part)
                setattr(obj, parts[-1], value)
                
                logger.debug(f"Loaded env var: {env_var} -> {config_path} = {value}")
    
    def _validate_config(self):
        """Validate configuration values"""
        logger.info("Validating configuration...")
        
        # Validate database settings
        assert self.config.database.connection_pool_size > 0, "Connection pool size must be positive"
        assert self.config.database.backup_interval_hours > 0, "Backup interval must be positive"
        
        # Validate browser settings
        assert 0 < self.config.browser.window_width <= 4096, "Invalid window width"
        assert 0 < self.config.browser.window_height <= 4096, "Invalid window height"
        assert 0 < self.config.browser.pool_size <= 10, "Pool size must be between 1 and 10"
        
        # Validate automation settings
        assert 0 < self.config.automation.max_workers <= 20, "Max workers must be between 1 and 20"
        assert 0 < self.config.automation.message_delay_min < self.config.automation.message_delay_max, \
            "Invalid delay range"
        
        # Validate security settings
        assert self.config.security.password_min_length >= 4, "Password min length too short"
        assert self.config.security.session_timeout > 0, "Session timeout must be positive"
        
        logger.info("Configuration validation passed")
    
    def _create_directories(self):
        """Create necessary directories"""
        dirs = [
            self.config.workspace_dir,
            self.config.data_dir,
            self.config.temp_dir,
            self.config.logs_dir,
            self.config.database.backup_path,
            self.config.browser.download_directory,
        ]
        
        for dir_path in dirs:
            path = Path(dir_path)
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {dir_path}")
    
    def load_config(self, config_file: Optional[str] = None) -> AppConfig:
        """Load configuration from file"""
        if config_file:
            self.config_file = Path(config_file)
        
        if not self.config_file.exists():
            logger.warning(f"Config file not found: {self.config_file}, using defaults")
            return self.config
        
        try:
            with open(self.config_file, 'r') as f:
                if self.config_file.suffix in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            # Update config with loaded data
            self._update_config_from_dict(self.config, data)
            
            logger.info(f"Configuration loaded from: {self.config_file}")
            return self.config
            
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return self.config
    
    def _update_config_from_dict(self, config_obj: Any, data: Dict[str, Any]):
        """Update configuration object from dictionary"""
        for key, value in data.items():
            if hasattr(config_obj, key):
                attr = getattr(config_obj, key)
                if isinstance(attr, (DatabaseConfig, BrowserConfig, AutomationConfig, 
                                    SecurityConfig, AlertConfig)):
                    # Nested configuration object
                    if isinstance(value, dict):
                        self._update_config_from_dict(attr, value)
                else:
                    # Simple attribute
                    try:
                        setattr(config_obj, key, value)
                    except Exception as e:
                        logger.warning(f"Failed to set {key}: {e}")
    
    def save_config(self, config_file: Optional[str] = None):
        """Save configuration to file"""
        if config_file:
            self.config_file = Path(config_file)
        
        try:
            config_dict = asdict(self.config)
            
            with open(self.config_file, 'w') as f:
                if self.config_file.suffix in ['.yaml', '.yml']:
                    yaml.dump(config_dict, f, default_flow_style=False)
                else:
                    json.dump(config_dict, f, indent=2)
            
            logger.info(f"Configuration saved to: {self.config_file}")
            
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value by key path (e.g., 'database.path')"""
        parts = key_path.split('.')
        obj = self.config
        
        try:
            for part in parts:
                obj = getattr(obj, part)
            return obj
        except AttributeError:
            return default
    
    def set(self, key_path: str, value: Any) -> bool:
        """Set configuration value by key path"""
        parts = key_path.split('.')
        obj = self.config
        
        try:
            for part in parts[:-1]:
                obj = getattr(obj, part)
            setattr(obj, parts[-1], value)
            logger.debug(f"Config updated: {key_path} = {value}")
            return True
        except AttributeError:
            logger.error(f"Failed to set config: {key_path}")
            return False
    
    def register_callback(self, callback: callable):
        """Register a callback to be called on config changes"""
        self._callbacks.append(callback)
    
    def start_watching(self):
        """Start watching configuration file for changes"""
        if self._watch_enabled:
            return
        
        self._watch_enabled = True
        self._watch_thread = threading.Thread(target=self._watch_config_file, daemon=True)
        self._watch_thread.start()
        logger.info("Configuration file watching enabled")
    
    def _watch_config_file(self):
        """Watch configuration file for changes"""
        last_modified = self.config_file.stat().st_mtime if self.config_file.exists() else 0
        
        while self._watch_enabled:
            try:
                if self.config_file.exists():
                    current_modified = self.config_file.stat().st_mtime
                    if current_modified != last_modified:
                        logger.info("Configuration file changed, reloading...")
                        self.load_config()
                        self._validate_config()
                        
                        # Call registered callbacks
                        for callback in self._callbacks:
                            try:
                                callback(self.config)
                            except Exception as e:
                                logger.error(f"Callback error: {e}")
                        
                        last_modified = current_modified
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Config watch error: {e}")
                time.sleep(10)
    
    def stop_watching(self):
        """Stop watching configuration file"""
        self._watch_enabled = False
        if self._watch_thread:
            self._watch_thread.join(timeout=5)
        logger.info("Configuration file watching stopped")
    
    def export_config(self) -> str:
        """Export configuration as JSON string"""
        return json.dumps(asdict(self.config), indent=2, default=str)
    
    def import_config(self, config_str: str) -> bool:
        """Import configuration from JSON string"""
        try:
            data = json.loads(config_str)
            self._update_config_from_dict(self.config, data)
            self._validate_config()
            logger.info("Configuration imported successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to import config: {e}")
            return False


# Global configuration instance
config = ConfigManager()


def get_config() -> AppConfig:
    """Get global configuration instance"""
    return config.config


def reload_config() -> AppConfig:
    """Reload configuration from file"""
    return config.load_config()


if __name__ == "__main__":
    # Test configuration manager
    print("Testing Configuration Manager...")
    print(f"App Name: {config.config.app_name}")
    print(f"App Version: {config.config.app_version}")
    print(f"Database Path: {config.config.database.path}")
    print(f"Max Workers: {config.config.automation.max_workers}")
    print(f"Debug Mode: {config.config.debug_mode}")
    
    # Test get/set
    config.set('automation.max_workers', 10)
    print(f"Updated Max Workers: {config.get('automation.max_workers')}")
    
    # Export/Import
    config_json = config.export_config()
    print(f"\nExported Config (first 500 chars):\n{config_json[:500]}...")