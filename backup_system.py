"""
Data Backup System
Author: Darkstar Boii Sahiil
Version: 3.0 - Production Ready
Description: Automated backup system with scheduling, compression, and cloud support
"""

import os
import gzip
import shutil
import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import hashlib

import config
import logger_system
import database_enhanced as db

logger = logger_system.get_logger(__name__)


class BackupType(Enum):
    """Backup type enumeration"""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"


class BackupStatus(Enum):
    """Backup status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackupConfig:
    """Backup configuration"""
    enabled: bool = True
    backup_dir: str = "backups"
    interval_hours: int = 24
    max_backups: int = 30
    compress: bool = True
    include_schema: bool = True
    backup_type: BackupType = BackupType.FULL
    auto_cleanup: bool = True
    encryption_enabled: bool = False
    encryption_key: Optional[str] = None
    cloud_backup: bool = False
    cloud_provider: str = "none"  # none, s3, gcs, azure
    cloud_bucket: Optional[str] = None


@dataclass
class Backup:
    """Backup information"""
    backup_id: str
    backup_type: BackupType
    status: BackupStatus
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    file_path: Optional[str] = None
    file_size: int = 0
    compressed_size: int = 0
    checksum: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BackupManager:
    """
    Automated backup manager with scheduling and compression
    """
    
    def __init__(self, db_path: str, cfg: Optional[BackupConfig] = None):
        self.db_path = db_path
        self.config = cfg or BackupConfig()
        
        # Backup storage
        self.backups: Dict[str, Backup] = {}
        self.backup_lock = threading.RLock()
        
        # Background threads
        self.scheduler_thread: Optional[threading.Thread] = None
        self.scheduler_running = False
        
        # Database
        self.database = db.get_database()
        
        # Create backup directory
        self.backup_dir = Path(self.config.backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing backups
        self._load_existing_backups()
        
        logger.info(f"Backup manager initialized: {self.db_path}")
    
    def _load_existing_backups(self):
        """Load existing backups from directory"""
        try:
            for backup_file in self.backup_dir.glob("backup_*.db*"):
                try:
                    # Extract backup info from filename
                    parts = backup_file.stem.split('_')
                    if len(parts) >= 3:
                        backup_id = f"{parts[1]}_{parts[2]}"
                        
                        # Create backup entry
                        backup = Backup(
                            backup_id=backup_id,
                            backup_type=BackupType.FULL,
                            status=BackupStatus.COMPLETED,
                            file_path=str(backup_file),
                            file_size=backup_file.stat().st_size,
                            created_at=datetime.fromtimestamp(backup_file.stat().st_mtime)
                        )
                        
                        with self.backup_lock:
                            self.backups[backup_id] = backup
                        
                        logger.debug(f"Loaded existing backup: {backup_id}")
                
                except Exception as e:
                    logger.warning(f"Failed to load backup {backup_file}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to load existing backups: {e}")
    
    def start(self):
        """Start backup scheduler"""
        if self.scheduler_running:
            logger.warning("Backup scheduler is already running")
            return
        
        self.scheduler_running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("Backup scheduler started")
    
    def stop(self):
        """Stop backup scheduler"""
        self.scheduler_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=10)
        
        logger.info("Backup scheduler stopped")
    
    def _scheduler_loop(self):
        """Backup scheduler loop"""
        while self.scheduler_running:
            try:
                # Check if it's time for a backup
                if self._should_create_backup():
                    logger.info("Scheduled backup triggered")
                    backup_id = self.create_backup()
                    
                    if backup_id:
                        logger.info(f"Scheduled backup completed: {backup_id}")
                    else:
                        logger.error("Scheduled backup failed")
                
                # Sleep for a bit
                time.sleep(300)  # Check every 5 minutes
            
            except Exception as e:
                logger.error(f"Backup scheduler error: {e}")
                time.sleep(600)
    
    def _should_create_backup(self) -> bool:
        """Check if a new backup should be created"""
        if not self.config.enabled:
            return False
        
        # Find the most recent completed backup
        with self.backup_lock:
            completed_backups = [
                b for b in self.backups.values() 
                if b.status == BackupStatus.COMPLETED
            ]
            
            if not completed_backups:
                return True
            
            latest_backup = max(completed_backups, key=lambda b: b.created_at)
            time_since_backup = (datetime.now() - latest_backup.created_at).total_seconds()
            
            return time_since_backup >= self.config.interval_hours * 3600
    
    def create_backup(self, backup_type: Optional[BackupType] = None) -> Optional[str]:
        """Create a new backup"""
        if not Path(self.db_path).exists():
            logger.error(f"Database file not found: {self.db_path}")
            return None
        
        backup_type = backup_type or self.config.backup_type
        
        # Generate backup ID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_id = f"BACKUP-{timestamp}"
        
        # Create backup entry
        backup = Backup(
            backup_id=backup_id,
            backup_type=backup_type,
            status=BackupStatus.RUNNING,
            metadata={
                'original_db': self.db_path,
                'backup_type': backup_type.value
            }
        )
        
        with self.backup_lock:
            self.backups[backup_id] = backup
        
        logger.info(f"Creating backup {backup_id}...")
        
        try:
            # Generate backup filename
            backup_filename = f"backup_{timestamp}.db"
            backup_path = self.backup_dir / backup_filename
            
            # Copy database file
            shutil.copy2(self.db_path, str(backup_path))
            
            backup.file_size = backup_path.stat().st_size
            
            # Compress if enabled
            if self.config.compress:
                logger.info(f"Compressing backup {backup_id}...")
                compressed_path = self.backup_dir / f"{backup_filename}.gz"
                
                with open(backup_path, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Remove uncompressed backup
                backup_path.unlink()
                backup.file_path = str(compressed_path)
                backup.compressed_size = compressed_path.stat().st_size
            else:
                backup.file_path = str(backup_path)
                backup.compressed_size = backup.file_size
            
            # Calculate checksum
            backup.checksum = self._calculate_checksum(backup.file_path)
            
            # Update backup status
            backup.status = BackupStatus.COMPLETED
            backup.completed_at = datetime.now()
            
            logger.info(f"Backup {backup_id} completed successfully")
            
            # Log to database
            self.database.log_automation_event(
                None,
                f"BACKUP-{backup_id}",
                "INFO",
                f"Backup created: {backup_type.value} ({backup.file_size} bytes)"
            )
            
            # Clean up old backups
            if self.config.auto_cleanup:
                self._cleanup_old_backups()
            
            return backup_id
        
        except Exception as e:
            logger.error(f"Backup {backup_id} failed: {e}")
            
            # Update backup status
            backup.status = BackupStatus.FAILED
            backup.error_message = str(e)
            
            # Log to database
            self.database.log_automation_event(
                None,
                f"BACKUP-{backup_id}",
                "ERROR",
                f"Backup failed: {str(e)}"
            )
            
            return None
    
    def restore_backup(self, backup_id: str, output_path: Optional[str] = None) -> bool:
        """Restore a backup"""
        with self.backup_lock:
            if backup_id not in self.backups:
                logger.error(f"Backup not found: {backup_id}")
                return False
            
            backup = self.backups[backup_id]
        
        if backup.status != BackupStatus.COMPLETED:
            logger.error(f"Backup {backup_id} is not completed")
            return False
        
        if not backup.file_path or not Path(backup.file_path).exists():
            logger.error(f"Backup file not found: {backup.file_path}")
            return False
        
        output_path = output_path or self.db_path
        
        try:
            logger.info(f"Restoring backup {backup_id} to {output_path}...")
            
            # Check if file is compressed
            if backup.file_path.endswith('.gz'):
                # Decompress and restore
                with gzip.open(backup.file_path, 'rb') as f_in:
                    with open(output_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                # Copy directly
                shutil.copy2(backup.file_path, output_path)
            
            logger.info(f"Backup {backup_id} restored successfully")
            
            # Log to database
            self.database.log_automation_event(
                None,
                f"RESTORE-{backup_id}",
                "INFO",
                f"Backup restored to {output_path}"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False
    
    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate MD5 checksum of a file"""
        md5_hash = hashlib.md5()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        
        return md5_hash.hexdigest()
    
    def _cleanup_old_backups(self):
        """Clean up old backups"""
        try:
            with self.backup_lock:
                # Get completed backups sorted by creation time
                completed_backups = [
                    b for b in self.backups.values() 
                    if b.status == BackupStatus.COMPLETED
                ]
                
                completed_backups.sort(key=lambda b: b.created_at, reverse=True)
                
                # Keep only the most recent backups
                to_delete = completed_backups[self.config.max_backups:]
                
                for backup in to_delete:
                    # Delete backup file
                    if backup.file_path and Path(backup.file_path).exists():
                        Path(backup.file_path).unlink()
                    
                    # Remove from backups dict
                    del self.backups[backup.backup_id]
                    
                    logger.info(f"Deleted old backup: {backup.backup_id}")
        
        except Exception as e:
            logger.error(f"Backup cleanup error: {e}")
    
    def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup"""
        with self.backup_lock:
            if backup_id not in self.backups:
                return False
            
            backup = self.backups[backup_id]
            
            # Delete file
            if backup.file_path and Path(backup.file_path).exists():
                Path(backup.file_path).unlink()
            
            # Remove from dict
            del self.backups[backup_id]
            
            logger.info(f"Backup deleted: {backup_id}")
            return True
    
    def get_backup(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Get backup information"""
        with self.backup_lock:
            if backup_id not in self.backups:
                return None
            
            backup = self.backups[backup_id]
            
            return {
                'backup_id': backup.backup_id,
                'backup_type': backup.backup_type.value,
                'status': backup.status.value,
                'created_at': backup.created_at.isoformat(),
                'completed_at': backup.completed_at.isoformat() if backup.completed_at else None,
                'file_path': backup.file_path,
                'file_size': backup.file_size,
                'compressed_size': backup.compressed_size,
                'checksum': backup.checksum,
                'error_message': backup.error_message,
                'metadata': backup.metadata
            }
    
    def list_backups(self, status: Optional[BackupStatus] = None, 
                    limit: int = 50) -> List[Dict[str, Any]]:
        """List backups"""
        with self.backup_lock:
            backups = list(self.backups.values())
            
            # Filter by status
            if status:
                backups = [b for b in backups if b.status == status]
            
            # Sort by creation time (newest first)
            backups.sort(key=lambda b: b.created_at, reverse=True)
            
            # Limit results
            backups = backups[:limit]
            
            return [
                {
                    'backup_id': b.backup_id,
                    'backup_type': b.backup_type.value,
                    'status': b.status.value,
                    'created_at': b.created_at.isoformat(),
                    'file_size': b.file_size,
                    'compressed_size': b.compressed_size
                }
                for b in backups
            ]
    
    def get_backup_stats(self) -> Dict[str, Any]:
        """Get backup statistics"""
        with self.backup_lock:
            completed = [b for b in self.backups.values() if b.status == BackupStatus.COMPLETED]
            failed = [b for b in self.backups.values() if b.status == BackupStatus.FAILED]
            
            total_size = sum(b.file_size for b in completed)
            total_compressed = sum(b.compressed_size for b in completed)
            
            return {
                'total_backups': len(self.backups),
                'completed_backups': len(completed),
                'failed_backups': len(failed),
                'total_size': total_size,
                'total_compressed_size': total_compressed,
                'compression_ratio': (total_compressed / total_size) if total_size > 0 else 0,
                'oldest_backup': min(b.created_at for b in completed).isoformat() if completed else None,
                'newest_backup': max(b.created_at for b in completed).isoformat() if completed else None
            }
    
    def export_backup(self, backup_id: str, export_path: str) -> bool:
        """Export a backup to a specific path"""
        backup_info = self.get_backup(backup_id)
        if not backup_info:
            return False
        
        try:
            # Copy backup file to export path
            if backup_info['file_path'] and Path(backup_info['file_path']).exists():
                shutil.copy2(backup_info['file_path'], export_path)
                logger.info(f"Backup exported: {backup_id} -> {export_path}")
                return True
            return False
        
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False
    
    def import_backup(self, import_path: str) -> Optional[str]:
        """Import a backup from a file"""
        try:
            # Copy backup file to backup directory
            import_file = Path(import_path)
            if not import_file.exists():
                logger.error(f"Import file not found: {import_path}")
                return None
            
            # Generate new backup ID
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_id = f"IMPORT-{timestamp}"
            
            # Copy file
            dest_path = self.backup_dir / import_file.name
            shutil.copy2(import_path, dest_path)
            
            # Create backup entry
            backup = Backup(
                backup_id=backup_id,
                backup_type=BackupType.FULL,
                status=BackupStatus.COMPLETED,
                file_path=str(dest_path),
                file_size=dest_path.stat().st_size,
                created_at=datetime.now(),
                metadata={
                    'imported_from': str(import_path),
                    'original_db': self.db_path
                }
            )
            
            with self.backup_lock:
                self.backups[backup_id] = backup
            
            logger.info(f"Backup imported: {import_path} -> {backup_id}")
            return backup_id
        
        except Exception as e:
            logger.error(f"Import failed: {e}")
            return None


# Global backup manager instance
backup_manager = None


def get_backup_manager(db_path: str) -> BackupManager:
    """Get global backup manager instance"""
    global backup_manager
    if backup_manager is None:
        backup_manager = BackupManager(db_path)
    return backup_manager


if __name__ == "__main__":
    # Test backup system
    print("Testing Backup System...")
    
    # Create a test database
    test_db = Path("test_backup.db")
    if test_db.exists():
        test_db.unlink()
    
    conn = sqlite3.connect(str(test_db))
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, data TEXT)")
    for i in range(100):
        conn.execute("INSERT INTO test (data) VALUES (?)", (f"Test data {i}",))
    conn.commit()
    conn.close()
    
    # Test backup
    backup_mgr = get_backup_manager(str(test_db))
    
    # Create backup
    backup_id = backup_mgr.create_backup()
    print(f"Created backup: {backup_id}")
    
    # List backups
    backups = backup_mgr.list_backups()
    print(f"Backups: {len(backups)}")
    
    # Get backup stats
    stats = backup_mgr.get_backup_stats()
    print(f"Backup stats: {stats}")
    
    # Cleanup
    if test_db.exists():
        test_db.unlink()
    if backup_mgr.backup_dir.exists():
        shutil.rmtree(backup_mgr.backup_dir)