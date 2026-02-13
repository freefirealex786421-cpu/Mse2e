"""
Advanced Logging System Module
Author: Darkstar Boii Sahiil
Version: 3.0 - Production Ready
Description: Comprehensive logging system with rotation, filtering, and multiple handlers
"""

import logging
import logging.handlers
import sys
import os
import gzip
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json
import threading
import traceback
from contextlib import contextmanager
import time

import config


@dataclass
class LogConfig:
    """Logging configuration"""
    log_dir: str = "logs"
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 30
    console_output: bool = True
    file_output: bool = True
    json_output: bool = False
    include_traceback: bool = True
    colorize_console: bool = True


class CustomRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """Custom rotating file handler with gzip compression for old logs"""
    
    def __init__(self, filename, maxBytes=10*1024*1024, backupCount=30, encoding='utf-8'):
        super().__init__(filename, maxBytes=maxBytes, backupCount=backupCount, encoding=encoding)
        self.backupCount = backupCount
    
    def doRollover(self):
        """Do a rollover with gzip compression"""
        if self.stream:
            self.stream.close()
            self.stream = None
        
        # Compress existing backups
        for i in range(self.backupCount - 1, 0, -1):
            src = f"{self.baseFilename}.{i}.gz"
            dst = f"{self.baseFilename}.{i+1}.gz"
            if os.path.exists(src):
                if os.path.exists(dst):
                    os.remove(dst)
                os.rename(src, dst)
        
        # Compress current log
        if os.path.exists(self.baseFilename):
            with open(self.baseFilename, 'rb') as f_in:
                with gzip.open(f"{self.baseFilename}.1.gz", 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        
        # Create new log file
        self.stream = open(self.baseFilename, 'a', encoding=self.encoding)


class ColoredFormatter(logging.Formatter):
    """Colored console formatter for better readability"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'
    }
    
    def __init__(self, fmt=None, datefmt=None, colorize=True):
        super().__init__(fmt, datefmt)
        self.colorize = colorize
    
    def format(self, record):
        if self.colorize:
            levelname = record.levelname
            if levelname in self.COLORS:
                record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        
        return super().format(record)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
        
        return json.dumps(log_data)


class LogFilter(logging.Filter):
    """Custom log filter for filtering log messages"""
    
    def __init__(self, min_level: str = 'DEBUG'):
        super().__init__()
        self.min_level = min_level
    
    def filter(self, record):
        return record.levelno >= getattr(logging, self.min_level)


class LoggerManager:
    """
    Advanced logger manager with multiple handlers, rotation, and filtering
    """
    
    _instance: Optional['LoggerManager'] = None
    _lock = threading.Lock()
    _loggers: Dict[str, logging.Logger] = {}
    
    def __new__(cls, config_obj: Optional[LogConfig] = None):
        """Singleton pattern implementation"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(LoggerManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_obj: Optional[LogConfig] = None):
        """Initialize logger manager"""
        if self._initialized:
            return
        
        self.config = config_obj or LogConfig()
        self._setup_directories()
        self._setup_root_logger()
        
        self._initialized = True
        self._cleanup_old_logs()
        
        logging.info("LoggerManager initialized successfully")
    
    def _setup_directories(self):
        """Setup log directory"""
        log_dir = Path(self.config.log_dir)
        if not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)
            logging.info(f"Created log directory: {self.config.log_dir}")
    
    def _setup_root_logger(self):
        """Setup root logger with handlers"""
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config.log_level))
        
        # Remove existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        if self.config.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(getattr(logging, self.config.log_level))
            
            if self.config.colorize_console:
                console_formatter = ColoredFormatter(
                    self.config.log_format,
                    self.config.date_format,
                    colorize=True
                )
            else:
                console_formatter = logging.Formatter(
                    self.config.log_format,
                    self.config.date_format
                )
            
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)
        
        # File handler
        if self.config.file_output:
            log_file = Path(self.config.log_dir) / f"app_{datetime.now().strftime('%Y%m%d')}.log"
            
            file_handler = CustomRotatingFileHandler(
                filename=str(log_file),
                maxBytes=self.config.max_file_size,
                backupCount=self.config.backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(getattr(logging, self.config.log_level))
            
            file_formatter = logging.Formatter(
                self.config.log_format,
                self.config.date_format
            )
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
        
        # JSON handler
        if self.config.json_output:
            json_file = Path(self.config.log_dir) / f"app_{datetime.now().strftime('%Y%m%d')}.json"
            
            json_handler = CustomRotatingFileHandler(
                filename=str(json_file),
                maxBytes=self.config.max_file_size,
                backupCount=self.config.backup_count,
                encoding='utf-8'
            )
            json_handler.setLevel(getattr(logging, self.config.log_level))
            json_handler.setFormatter(JSONFormatter())
            root_logger.addHandler(json_handler)
        
        # Error handler (separate file for errors)
        error_file = Path(self.config.log_dir) / "errors.log"
        error_handler = CustomRotatingFileHandler(
            filename=str(error_file),
            maxBytes=self.config.max_file_size,
            backupCount=self.config.backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        root_logger.addHandler(error_handler)
    
    def _cleanup_old_logs(self):
        """Clean up old log files"""
        try:
            log_dir = Path(self.config.log_dir)
            cutoff_date = datetime.now() - timedelta(days=self.config.backup_count)
            
            for log_file in log_dir.glob("*.log*"):
                try:
                    file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if file_time < cutoff_date:
                        log_file.unlink()
                        logging.info(f"Deleted old log file: {log_file}")
                except Exception as e:
                    logging.warning(f"Failed to delete {log_file}: {e}")
            
            for log_file in log_dir.glob("*.gz"):
                try:
                    file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                    if file_time < cutoff_date:
                        log_file.unlink()
                        logging.info(f"Deleted old compressed log: {log_file}")
                except Exception as e:
                    logging.warning(f"Failed to delete {log_file}: {e}")
        
        except Exception as e:
            logging.error(f"Log cleanup error: {e}")
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get or create a logger with the given name"""
        if name not in self._loggers:
            logger = logging.getLogger(name)
            logger.setLevel(getattr(logging, self.config.log_level))
            self._loggers[name] = logger
        
        return self._loggers[name]
    
    @contextmanager
    def log_context(self, logger: logging.Logger, context: Dict[str, Any]):
        """Context manager for adding temporary logging context"""
        class ContextFilter(logging.Filter):
            def __init__(self, context_data):
                super().__init__()
                self.context_data = context_data
            
            def filter(self, record):
                for key, value in self.context_data.items():
                    setattr(record, key, value)
                return True
        
        context_filter = ContextFilter(context)
        logger.addFilter(context_filter)
        try:
            yield
        finally:
            logger.removeFilter(context_filter)
    
    def log_exception(self, logger: logging.Logger, message: str, exc_info: bool = True):
        """Log exception with full traceback"""
        logger.error(message, exc_info=exc_info)
        if self.config.include_traceback:
            logger.error(f"Traceback:\n{traceback.format_exc()}")
    
    def get_log_stats(self) -> Dict[str, Any]:
        """Get logging statistics"""
        log_dir = Path(self.config.log_dir)
        
        stats = {
            'log_directory': str(log_dir),
            'log_files': [],
            'total_size': 0,
            'file_count': 0
        }
        
        for log_file in log_dir.glob("*.log"):
            file_size = log_file.stat().st_size
            stats['log_files'].append({
                'name': log_file.name,
                'size': file_size,
                'modified': datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
            })
            stats['total_size'] += file_size
            stats['file_count'] += 1
        
        for gz_file in log_dir.glob("*.gz"):
            file_size = gz_file.stat().st_size
            stats['log_files'].append({
                'name': gz_file.name,
                'size': file_size,
                'modified': datetime.fromtimestamp(gz_file.stat().st_mtime).isoformat(),
                'compressed': True
            })
            stats['total_size'] += file_size
            stats['file_count'] += 1
        
        return stats
    
    def search_logs(self, pattern: str, start_date: Optional[datetime] = None, 
                    end_date: Optional[datetime] = None, 
                    level: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search logs for pattern matching"""
        results = []
        log_dir = Path(self.config.log_dir)
        
        for log_file in log_dir.glob("*.log"):
            try:
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                
                if start_date and file_time < start_date:
                    continue
                if end_date and file_time > end_date:
                    continue
                
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if pattern.lower() in line.lower():
                            if level and level.upper() not in line:
                                continue
                            
                            results.append({
                                'file': log_file.name,
                                'line': line.strip(),
                                'timestamp': file_time.isoformat()
                            })
                            
                            if len(results) >= 1000:  # Limit results
                                return results
            
            except Exception as e:
                logging.warning(f"Failed to search {log_file}: {e}")
        
        return results
    
    def export_logs(self, output_file: str, start_date: Optional[datetime] = None,
                    end_date: Optional[datetime] = None) -> bool:
        """Export logs to a file"""
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as out_f:
                log_dir = Path(self.config.log_dir)
                
                for log_file in sorted(log_dir.glob("*.log")):
                    file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                    
                    if start_date and file_time < start_date:
                        continue
                    if end_date and file_time > end_date:
                        continue
                    
                    out_f.write(f"\n{'='*60}\n")
                    out_f.write(f"File: {log_file.name}\n")
                    out_f.write(f"{'='*60}\n\n")
                    
                    with open(log_file, 'r', encoding='utf-8') as in_f:
                        out_f.write(in_f.read())
            
            logging.info(f"Logs exported to: {output_file}")
            return True
        
        except Exception as e:
            logging.error(f"Failed to export logs: {e}")
            return False


# Global logger manager instance
logger_manager = LoggerManager()


def get_logger(name: str = __name__) -> logging.Logger:
    """Get a logger instance"""
    return logger_manager.get_logger(name)


if __name__ == "__main__":
    # Test logger system
    print("Testing Advanced Logging System...")
    
    logger = get_logger("test_logger")
    
    # Test different log levels
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Test with context
    with logger_manager.log_context(logger, {'user_id': '123', 'session': 'abc'}):
        logger.info("Message with context")
    
    # Test exception logging
    try:
        1 / 0
    except Exception:
        logger_manager.log_exception(logger, "Division by zero occurred")
    
    # Get log stats
    stats = logger_manager.get_log_stats()
    print(f"\nLog Statistics:")
    print(f"Total files: {stats['file_count']}")
    print(f"Total size: {stats['total_size']} bytes")