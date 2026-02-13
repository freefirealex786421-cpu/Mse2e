"""
Enhanced Database Module with Connection Pooling
Author: Darkstar Boii Sahiil
Version: 3.0 - Production Ready
Description: Advanced database layer with connection pooling, backup, and monitoring
"""

import sqlite3
import hashlib
import threading
import time
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager
from queue import Queue, Empty, Full
import json
import gzip
import shutil
import os

from cryptography.fernet import Fernet

import config
import logger_system

logger = logger_system.get_logger(__name__)


@dataclass
class ConnectionConfig:
    """Database connection configuration"""
    timeout: int = 30
    isolation_level: str = None  # None = autocommit mode
    check_same_thread: bool = False
    cached_statements: int = 100
    factory: Any = None
    enable_foreign_keys: bool = True
    journal_mode: str = "WAL"
    synchronous_mode: str = "NORMAL"
    cache_size: int = -2000  # 2MB
    temp_store: str = "MEMORY"


@dataclass
class BackupConfig:
    """Backup configuration"""
    enabled: bool = True
    backup_path: str = "backups"
    interval_hours: int = 24
    max_backups: int = 30
    compress: bool = True
    include_schema: bool = True


@dataclass
class DatabaseStats:
    """Database statistics"""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    total_queries: int = 0
    failed_queries: int = 0
    avg_query_time: float = 0.0
    last_backup: Optional[str] = None
    database_size: int = 0


class ConnectionPool:
    """
    Thread-safe SQLite connection pool
    """
    
    def __init__(self, db_path: str, pool_size: int = 10, config: Optional[ConnectionConfig] = None):
        self.db_path = db_path
        self.pool_size = pool_size
        self.config = config or ConnectionConfig()
        self._pool: Queue[sqlite3.Connection] = Queue(maxsize=pool_size)
        self._lock = threading.RLock()
        self._stats = DatabaseStats()
        
        # Initialize connections
        self._initialize_pool()
        
        logger.info(f"Connection pool initialized: {pool_size} connections for {db_path}")
    
    def _initialize_pool(self):
        """Initialize connection pool"""
        for _ in range(self.pool_size):
            conn = self._create_connection()
            self._pool.put(conn)
            self._stats.total_connections += 1
        
        self._stats.idle_connections = self.pool_size
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection"""
        conn = sqlite3.connect(
            self.db_path,
            timeout=self.config.timeout,
            isolation_level=self.config.isolation_level,
            check_same_thread=self.config.check_same_thread,
            cached_statements=self.config.cached_statements,
            factory=self.config.factory
        )
        
        # Configure connection
        cursor = conn.cursor()
        
        if self.config.enable_foreign_keys:
            cursor.execute("PRAGMA foreign_keys = ON")
        
        cursor.execute(f"PRAGMA journal_mode = {self.config.journal_mode}")
        cursor.execute(f"PRAGMA synchronous = {self.config.synchronous_mode}")
        cursor.execute(f"PRAGMA cache_size = {self.config.cache_size}")
        cursor.execute(f"PRAGMA temp_store = {self.config.temp_store}")
        
        conn.commit()
        return conn
    
    @contextmanager
    def get_connection(self, timeout: float = 30.0):
        """
        Get a connection from the pool (context manager)
        
        Args:
            timeout: Maximum time to wait for a connection
            
        Yields:
            sqlite3.Connection: Database connection
        """
        conn = None
        start_time = time.time()
        
        try:
            # Try to get connection with timeout
            conn = self._pool.get(timeout=timeout)
            
            with self._lock:
                self._stats.idle_connections -= 1
                self._stats.active_connections += 1
            
            # Verify connection is still alive
            try:
                conn.execute("SELECT 1")
            except sqlite3.Error:
                # Connection is dead, create new one
                conn.close()
                conn = self._create_connection()
            
            yield conn
            
        except Empty:
            raise TimeoutError(f"Could not get database connection within {timeout} seconds")
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                # Return connection to pool
                try:
                    self._pool.put_nowait(conn)
                    with self._lock:
                        self._stats.active_connections -= 1
                        self._stats.idle_connections += 1
                except Full:
                    # Pool is full, close the connection
                    conn.close()
                    with self._lock:
                        self._stats.active_connections -= 1
                        self._stats.total_connections -= 1
    
    def close_all(self):
        """Close all connections in the pool"""
        with self._lock:
            while not self._pool.empty():
                try:
                    conn = self._pool.get_nowait()
                    conn.close()
                except Empty:
                    break
            
            self._stats.total_connections = 0
            self._stats.active_connections = 0
            self._stats.idle_connections = 0
        
        logger.info("All database connections closed")
    
    def get_stats(self) -> DatabaseStats:
        """Get connection pool statistics"""
        with self._lock:
            self._stats.database_size = Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0
            return self._stats
    
    def execute_query(self, query: str, params: Tuple = (), fetch: bool = False, 
                     many: bool = False) -> Optional[List[Tuple]]:
        """
        Execute a database query with connection from pool
        
        Args:
            query: SQL query to execute
            params: Query parameters
            fetch: Whether to fetch results
            many: Whether to execute executemany
            
        Returns:
            Query results if fetch=True, else None
        """
        start_time = time.time()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                if many:
                    cursor.executemany(query, params)
                else:
                    cursor.execute(query, params)
                
                if fetch:
                    results = cursor.fetchall()
                else:
                    conn.commit()
                    results = None
                
                # Update stats
                query_time = time.time() - start_time
                with self._lock:
                    self._stats.total_queries += 1
                    self._stats.avg_query_time = (
                        self._stats.avg_query_time * (self._stats.total_queries - 1) + query_time
                    ) / self._stats.total_queries
                
                return results
            
            except Exception as e:
                logger.error(f"Query execution failed: {e}")
                conn.rollback()
                
                with self._lock:
                    self._stats.failed_queries += 1
                
                raise


class DatabaseManager:
    """
    Enhanced database manager with pooling, backup, and monitoring
    """
    
    def __init__(self, db_path: Optional[str] = None, pool_size: int = 10):
        self.db_path = db_path or str(Path(__file__).parent / "users.db")
        self.encryption_key_file = Path(__file__).parent / ".encryption_key"
        
        # Configuration
        self.connection_config = ConnectionConfig()
        self.backup_config = BackupConfig()
        
        # Connection pool
        self.pool = ConnectionPool(self.db_path, pool_size, self.connection_config)
        
        # Encryption
        self.encryption_key = self._get_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        # Background threads
        self._backup_thread: Optional[threading.Thread] = None
        self._backup_running = False
        
        # Initialize database
        self._initialize_database()
        
        logger.info(f"DatabaseManager initialized: {self.db_path}")
    
    def _get_encryption_key(self) -> bytes:
        """Get or create encryption key for cookie storage"""
        if self.encryption_key_file.exists():
            with open(self.encryption_key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self.encryption_key_file, 'wb') as f:
                f.write(key)
            return key
    
    def _initialize_database(self):
        """Initialize database with tables"""
        self.pool.execute_query('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                failed_login_attempts INTEGER DEFAULT 0,
                locked_until TIMESTAMP
            )
        ''')
        
        self.pool.execute_query('''
            CREATE TABLE IF NOT EXISTS user_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id TEXT,
                name_prefix TEXT,
                delay INTEGER DEFAULT 30,
                cookies_encrypted TEXT,
                messages TEXT,
                automation_running INTEGER DEFAULT 0,
                locked_group_name TEXT,
                locked_nicknames TEXT,
                lock_enabled INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        self.pool.execute_query('''
            CREATE TABLE IF NOT EXISTS automation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                process_id TEXT,
                log_level TEXT,
                message TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        self.pool.execute_query('''
            CREATE TABLE IF NOT EXISTS message_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id TEXT,
                message TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success INTEGER DEFAULT 1,
                error_message TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        self.pool.execute_query('''
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT NOT NULL,
                metric_value REAL,
                metadata TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Add columns for backward compatibility
        self._add_column_if_not_exists('user_configs', 'automation_running', 'INTEGER DEFAULT 0')
        self._add_column_if_not_exists('user_configs', 'locked_group_name', 'TEXT')
        self._add_column_if_not_exists('user_configs', 'locked_nicknames', 'TEXT')
        self._add_column_if_not_exists('user_configs', 'lock_enabled', 'INTEGER DEFAULT 0')
        
        # Create indexes
        self._create_index_if_not_exists('idx_user_configs_user_id', 'user_configs', 'user_id')
        self._create_index_if_not_exists('idx_automation_logs_user_id', 'automation_logs', 'user_id')
        self._create_index_if_not_exists('idx_automation_logs_timestamp', 'automation_logs', 'timestamp')
        self._create_index_if_not_exists('idx_message_history_user_id', 'message_history', 'user_id')
        self._create_index_if_not_exists('idx_message_history_timestamp', 'message_history', 'sent_at')
        self._create_index_if_not_exists('idx_system_metrics_timestamp', 'system_metrics', 'timestamp')
        
        logger.info("Database initialized successfully")
    
    def _add_column_if_not_exists(self, table: str, column: str, definition: str):
        """Add column to table if it doesn't exist"""
        try:
            self.pool.execute_query(f'ALTER TABLE {table} ADD COLUMN {column} {definition}')
        except sqlite3.OperationalError:
            pass  # Column already exists
    
    def _create_index_if_not_exists(self, index_name: str, table: str, column: str):
        """Create index if it doesn't exist"""
        try:
            self.pool.execute_query(f'CREATE INDEX IF NOT EXISTS {index_name} ON {table}({column})')
        except Exception as e:
            logger.warning(f"Failed to create index {index_name}: {e}")
    
    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def encrypt_cookies(self, cookies: str) -> Optional[str]:
        """Encrypt cookies for secure storage"""
        if not cookies:
            return None
        return self.cipher_suite.encrypt(cookies.encode()).decode()
    
    def decrypt_cookies(self, encrypted_cookies: str) -> str:
        """Decrypt cookies"""
        if not encrypted_cookies:
            return ""
        try:
            return self.cipher_suite.decrypt(encrypted_cookies.encode()).decode()
        except Exception:
            return ""
    
    # User Management
    def create_user(self, username: str, password: str, email: Optional[str] = None) -> Tuple[bool, str]:
        """Create new user"""
        try:
            password_hash = self.hash_password(password)
            
            result = self.pool.execute_query(
                'INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)',
                (username, password_hash, email),
                fetch=True
            )
            
            user_id = self.pool.execute_query(
                'SELECT last_insert_rowid()',
                fetch=True
            )[0][0]
            
            # Create default config
            self.pool.execute_query(
                '''INSERT INTO user_configs (user_id, chat_id, name_prefix, delay, messages)
                VALUES (?, ?, ?, ?, ?)''',
                (user_id, '', '', 30, '')
            )
            
            logger.info(f"User created: {username} (ID: {user_id})")
            return True, "Account created successfully!"
        
        except sqlite3.IntegrityError:
            return False, "Username already exists!"
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return False, f"Error: {str(e)}"
    
    def verify_user(self, username: str, password: str) -> Optional[int]:
        """Verify user credentials"""
        try:
            result = self.pool.execute_query(
                '''SELECT id, password_hash, is_active, locked_until, failed_login_attempts
                FROM users WHERE username = ?''',
                (username,),
                fetch=True
            )
            
            if not result:
                return None
            
            user_id, password_hash, is_active, locked_until, failed_attempts = result[0]
            
            # Check if account is active
            if not is_active:
                logger.warning(f"Inactive account attempted login: {username}")
                return None
            
            # Check if account is locked
            if locked_until:
                locked_time = datetime.fromisoformat(locked_until)
                if locked_time > datetime.now():
                    logger.warning(f"Locked account attempted login: {username}")
                    return None
                else:
                    # Unlock account
                    self.pool.execute_query(
                        'UPDATE users SET locked_until = NULL, failed_login_attempts = 0 WHERE id = ?',
                        (user_id,)
                    )
            
            # Verify password
            if password_hash == self.hash_password(password):
                # Reset failed attempts
                self.pool.execute_query(
                    'UPDATE users SET failed_login_attempts = 0, last_login = CURRENT_TIMESTAMP WHERE id = ?',
                    (user_id,)
                )
                return user_id
            else:
                # Increment failed attempts
                failed_attempts += 1
                if failed_attempts >= 5:
                    # Lock account for 15 minutes
                    lock_until = (datetime.now() + timedelta(minutes=15)).isoformat()
                    self.pool.execute_query(
                        'UPDATE users SET failed_login_attempts = ?, locked_until = ? WHERE id = ?',
                        (failed_attempts, lock_until, user_id)
                    )
                    logger.warning(f"Account locked due to failed attempts: {username}")
                else:
                    self.pool.execute_query(
                        'UPDATE users SET failed_login_attempts = ? WHERE id = ?',
                        (failed_attempts, user_id)
                    )
                return None
        
        except Exception as e:
            logger.error(f"User verification error: {e}")
            return None
    
    def get_username(self, user_id: int) -> Optional[str]:
        """Get username by user ID"""
        result = self.pool.execute_query(
            'SELECT username FROM users WHERE id = ?',
            (user_id,),
            fetch=True
        )
        return result[0][0] if result else None
    
    # User Config Management
    def get_user_config(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user configuration"""
        result = self.pool.execute_query(
            '''SELECT chat_id, name_prefix, delay, cookies_encrypted, messages, automation_running
            FROM user_configs WHERE user_id = ?''',
            (user_id,),
            fetch=True
        )
        
        if not result:
            return None
        
        return {
            'chat_id': result[0][0] or '',
            'name_prefix': result[0][1] or '',
            'delay': result[0][2] or 30,
            'cookies': self.decrypt_cookies(result[0][3]),
            'messages': result[0][4] or '',
            'automation_running': result[0][5] or 0
        }
    
    def update_user_config(self, user_id: int, chat_id: str, name_prefix: str, 
                          delay: int, cookies: str, messages: str) -> bool:
        """Update user configuration"""
        try:
            encrypted_cookies = self.encrypt_cookies(cookies)
            
            self.pool.execute_query(
                '''UPDATE user_configs 
                SET chat_id = ?, name_prefix = ?, delay = ?, cookies_encrypted = ?, 
                    messages = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?''',
                (chat_id, name_prefix, delay, encrypted_cookies, messages, user_id)
            )
            
            logger.info(f"User config updated: {user_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to update user config: {e}")
            return False
    
    # Automation State Management
    def set_automation_running(self, user_id: int, is_running: bool) -> bool:
        """Set automation running state for a user"""
        try:
            self.pool.execute_query(
                '''UPDATE user_configs 
                SET automation_running = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?''',
                (1 if is_running else 0, user_id)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set automation state: {e}")
            return False
    
    def get_automation_running(self, user_id: int) -> bool:
        """Get automation running state for a user"""
        result = self.pool.execute_query(
            'SELECT automation_running FROM user_configs WHERE user_id = ?',
            (user_id,),
            fetch=True
        )
        return bool(result[0][0]) if result else False
    
    # Lock Configuration
    def get_lock_config(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get lock configuration for a user"""
        result = self.pool.execute_query(
            '''SELECT chat_id, locked_group_name, locked_nicknames, lock_enabled, cookies_encrypted
            FROM user_configs WHERE user_id = ?''',
            (user_id,),
            fetch=True
        )
        
        if not result:
            return None
        
        try:
            nicknames = json.loads(result[0][2]) if result[0][2] else {}
        except:
            nicknames = {}
        
        return {
            'chat_id': result[0][0] or '',
            'locked_group_name': result[0][1] or '',
            'locked_nicknames': nicknames,
            'lock_enabled': bool(result[0][3]),
            'cookies': self.decrypt_cookies(result[0][4])
        }
    
    def update_lock_config(self, user_id: int, chat_id: str, locked_group_name: str, 
                          locked_nicknames: Dict[str, str], cookies: Optional[str] = None) -> bool:
        """Update lock configuration"""
        try:
            nicknames_json = json.dumps(locked_nicknames)
            
            if cookies is not None:
                encrypted_cookies = self.encrypt_cookies(cookies)
                self.pool.execute_query(
                    '''UPDATE user_configs 
                    SET chat_id = ?, locked_group_name = ?, locked_nicknames = ?, 
                        cookies_encrypted = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?''',
                    (chat_id, locked_group_name, nicknames_json, encrypted_cookies, user_id)
                )
            else:
                self.pool.execute_query(
                    '''UPDATE user_configs 
                    SET chat_id = ?, locked_group_name = ?, locked_nicknames = ?, 
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?''',
                    (chat_id, locked_group_name, nicknames_json, user_id)
                )
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to update lock config: {e}")
            return False
    
    def set_lock_enabled(self, user_id: int, enabled: bool) -> bool:
        """Enable or disable the lock system"""
        try:
            self.pool.execute_query(
                '''UPDATE user_configs 
                SET lock_enabled = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?''',
                (1 if enabled else 0, user_id)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to set lock enabled: {e}")
            return False
    
    def get_lock_enabled(self, user_id: int) -> bool:
        """Check if lock is enabled for a user"""
        result = self.pool.execute_query(
            'SELECT lock_enabled FROM user_configs WHERE user_id = ?',
            (user_id,),
            fetch=True
        )
        return bool(result[0][0]) if result else False
    
    # Logging
    def log_automation_event(self, user_id: Optional[int], process_id: str, 
                            level: str, message: str):
        """Log automation event"""
        try:
            self.pool.execute_query(
                '''INSERT INTO automation_logs (user_id, process_id, log_level, message)
                VALUES (?, ?, ?, ?)''',
                (user_id, process_id, level, message)
            )
        except Exception as e:
            logger.error(f"Failed to log automation event: {e}")
    
    def get_automation_logs(self, user_id: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get automation logs"""
        if user_id:
            results = self.pool.execute_query(
                '''SELECT id, user_id, process_id, log_level, message, timestamp
                FROM automation_logs 
                WHERE user_id = ? 
                ORDER BY timestamp DESC LIMIT ?''',
                (user_id, limit),
                fetch=True
            )
        else:
            results = self.pool.execute_query(
                '''SELECT id, user_id, process_id, log_level, message, timestamp
                FROM automation_logs 
                ORDER BY timestamp DESC LIMIT ?''',
                (limit,),
                fetch=True
            )
        
        return [
            {
                'id': r[0],
                'user_id': r[1],
                'process_id': r[2],
                'level': r[3],
                'message': r[4],
                'timestamp': r[5]
            }
            for r in results
        ]
    
    # Message History
    def log_message(self, user_id: int, chat_id: str, message: str, 
                   success: bool = True, error_message: str = None):
        """Log message to history"""
        try:
            self.pool.execute_query(
                '''INSERT INTO message_history (user_id, chat_id, message, success, error_message)
                VALUES (?, ?, ?, ?, ?)''',
                (user_id, chat_id, message, 1 if success else 0, error_message)
            )
        except Exception as e:
            logger.error(f"Failed to log message: {e}")
    
    def get_message_stats(self, user_id: int, days: int = 7) -> Dict[str, Any]:
        """Get message statistics for a user"""
        try:
            results = self.pool.execute_query(
                '''SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed,
                    DATE(sent_at) as date
                FROM message_history
                WHERE user_id = ? AND sent_at >= datetime('now', '-' || ? || ' days')
                GROUP BY DATE(sent_at)
                ORDER BY date DESC''',
                (user_id, days),
                fetch=True
            )
            
            return {
                'daily_stats': [
                    {
                        'date': r[3],
                        'total': r[0],
                        'successful': r[1],
                        'failed': r[2]
                    }
                    for r in results
                ]
            }
        
        except Exception as e:
            logger.error(f"Failed to get message stats: {e}")
            return {'daily_stats': []}
    
    # System Metrics
    def record_metric(self, metric_name: str, value: float, metadata: Optional[Dict] = None):
        """Record system metric"""
        try:
            metadata_json = json.dumps(metadata) if metadata else None
            self.pool.execute_query(
                '''INSERT INTO system_metrics (metric_name, metric_value, metadata)
                VALUES (?, ?, ?)''',
                (metric_name, value, metadata_json)
            )
        except Exception as e:
            logger.error(f"Failed to record metric: {e}")
    
    def get_metrics(self, metric_name: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get metrics for a specific name"""
        try:
            results = self.pool.execute_query(
                '''SELECT metric_name, metric_value, metadata, timestamp
                FROM system_metrics
                WHERE metric_name = ? AND timestamp >= datetime('now', '-' || ? || ' hours')
                ORDER BY timestamp DESC''',
                (metric_name, hours),
                fetch=True
            )
            
            return [
                {
                    'name': r[0],
                    'value': r[1],
                    'metadata': json.loads(r[2]) if r[2] else None,
                    'timestamp': r[3]
                }
                for r in results
            ]
        
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return []
    
    # Backup System
    def start_backup_scheduler(self):
        """Start automatic backup scheduler"""
        if self._backup_running:
            return
        
        self._backup_running = True
        self._backup_thread = threading.Thread(target=self._backup_loop, daemon=True)
        self._backup_thread.start()
        logger.info("Backup scheduler started")
    
    def _backup_loop(self):
        """Backup loop running in background"""
        while self._backup_running:
            try:
                time.sleep(self.backup_config.interval_hours * 3600)
                self.create_backup()
            except Exception as e:
                logger.error(f"Backup loop error: {e}")
    
    def create_backup(self) -> bool:
        """Create database backup"""
        if not self.backup_config.enabled:
            return False
        
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = Path(self.backup_config.backup_path)
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            backup_file = backup_dir / f"users_backup_{timestamp}.db"
            
            # Copy database file
            shutil.copy2(self.db_path, str(backup_file))
            
            if self.backup_config.compress:
                # Compress backup
                compressed_file = backup_dir / f"users_backup_{timestamp}.db.gz"
                with open(backup_file, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Remove uncompressed backup
                backup_file.unlink()
                backup_file = compressed_file
            
            logger.info(f"Backup created: {backup_file}")
            
            # Update last backup time in stats
            with self.pool._lock:
                self.pool._stats.last_backup = timestamp
            
            # Clean old backups
            self._cleanup_old_backups()
            
            return True
        
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False
    
    def _cleanup_old_backups(self):
        """Clean up old backup files"""
        try:
            backup_dir = Path(self.backup_config.backup_path)
            backup_files = sorted(backup_dir.glob("users_backup_*.db*"), 
                                key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Keep only the most recent backups
            for old_backup in backup_files[self.backup_config.max_backups:]:
                old_backup.unlink()
                logger.info(f"Deleted old backup: {old_backup}")
        
        except Exception as e:
            logger.error(f"Backup cleanup error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        pool_stats = self.pool.get_stats()
        
        return {
            'pool': {
                'total_connections': pool_stats.total_connections,
                'active_connections': pool_stats.active_connections,
                'idle_connections': pool_stats.idle_connections,
                'total_queries': pool_stats.total_queries,
                'failed_queries': pool_stats.failed_queries,
                'avg_query_time': pool_stats.avg_query_time
            },
            'database': {
                'path': self.db_path,
                'size': pool_stats.database_size,
                'last_backup': pool_stats.last_backup
            }
        }
    
    def close(self):
        """Close database manager and cleanup"""
        self._backup_running = False
        if self._backup_thread:
            self._backup_thread.join(timeout=5)
        
        self.pool.close_all()
        logger.info("DatabaseManager closed")


# Global database manager instance
db_manager = None


def get_database() -> DatabaseManager:
    """Get global database manager instance"""
    global db_manager
    if db_manager is None:
        db_manager = DatabaseManager()
    return db_manager


if __name__ == "__main__":
    # Test database manager
    print("Testing Enhanced Database Manager...")
    
    db = get_database()
    
    # Test user creation
    success, message = db.create_user("testuser", "password123", "test@example.com")
    print(f"User creation: {success} - {message}")
    
    # Test user verification
    user_id = db.verify_user("testuser", "password123")
    print(f"User verification: {user_id}")
    
    # Test config
    db.update_user_config(user_id, "123456", "Test", 30, "cookies", "Hello\nWorld")
    config = db.get_user_config(user_id)
    print(f"User config: {config}")
    
    # Test stats
    stats = db.get_stats()
    print(f"Database stats: {stats}")
    
    # Close database
    db.close()