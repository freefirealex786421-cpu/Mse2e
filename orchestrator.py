"""
Main Application Orchestrator
Author: Darkstar Boii Sahiil
Version: 3.0 - Production Ready
Description: Central orchestrator coordinating all system components for 24/7 operation
"""

import os
import sys
import signal
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import json

# Import all system components
import config
import logger_system
import database_enhanced as db
import browser_manager
import automation_engine
import monitoring_system
import error_recovery
import backup_system
import analytics_system
import alert_system

# Get logger
logger = logger_system.get_logger(__name__)


class ApplicationOrchestrator:
    """
    Central orchestrator for all system components
    Manages lifecycle, coordination, and health of all subsystems
    """
    
    def __init__(self, config_file: Optional[str] = None):
        # Load configuration
        if config_file:
            self.config = config.load_config(config_file)
        else:
            self.config = config.get_config()
        
        # Component instances
        self.database = None
        self.browser_pool = None
        self.automation_engine = None
        self.monitoring_system = None
        self.error_recovery = None
        self.backup_manager = None
        self.analytics = None
        self.alert_manager = None
        
        # Control flags
        self.running = False
        self.shutdown_requested = False
        self.startup_time = None
        
        # Thread locks
        self.lock = threading.RLock()
        
        # Signal handlers
        self._setup_signal_handlers()
        
        logger.info("Application Orchestrator initialized")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown")
        self.shutdown()
    
    def initialize(self):
        """Initialize all system components"""
        logger.info("=" * 80)
        logger.info("Initializing Darkstar E2EE Automation System v3.0")
        logger.info("=" * 80)
        
        try:
            # 1. Initialize Database
            logger.info("Step 1/8: Initializing Database...")
            self.database = db.get_database()
            self.database.initialize()
            logger.info("✓ Database initialized successfully")
            
            # 2. Initialize Browser Pool
            logger.info("Step 2/8: Initializing Browser Pool...")
            self.browser_pool = browser_manager.get_browser_manager(
                pool_size=self.config.browser.pool_size
            )
            logger.info("✓ Browser pool initialized successfully")
            
            # 3. Initialize Monitoring System
            logger.info("Step 3/8: Initializing Monitoring System...")
            self.monitoring_system = monitoring_system.get_monitoring_system()
            self.monitoring_system.start()
            logger.info("✓ Monitoring system started successfully")
            
            # 4. Initialize Error Recovery
            logger.info("Step 4/8: Initializing Error Recovery System...")
            self.error_recovery = error_recovery.ErrorRecoverySystem(self.config)
            logger.info("✓ Error recovery system initialized successfully")
            
            # 5. Initialize Backup Manager
            logger.info("Step 5/8: Initializing Backup Manager...")
            backup_path = Path(self.config.database.path)
            self.backup_manager = backup_system.BackupManager(
                db_path=str(backup_path),
                cfg=backup_system.BackupConfig(
                    enabled=self.config.database.backup_enabled,
                    interval_hours=self.config.database.backup_interval_hours
                )
            )
            self.backup_manager.start_scheduler()
            logger.info("✓ Backup manager initialized successfully")
            
            # 6. Initialize Analytics Engine
            logger.info("Step 6/8: Initializing Analytics Engine...")
            self.analytics = analytics_system.AnalyticsEngine(self.config)
            logger.info("✓ Analytics engine initialized successfully")
            
            # 7. Initialize Alert Manager
            logger.info("Step 7/8: Initializing Alert Manager...")
            self.alert_manager = alert_system.AlertManager(self.config)
            logger.info("✓ Alert manager initialized successfully")
            
            # 8. Initialize Automation Engine
            logger.info("Step 8/8: Initializing Automation Engine...")
            self.automation_engine = automation_engine.get_automation_engine(
                max_workers=self.config.automation.max_workers
            )
            logger.info("✓ Automation engine initialized successfully")
            
            # Setup component integration
            self._setup_integration()
            
            logger.info("=" * 80)
            logger.info("All components initialized successfully!")
            logger.info("=" * 80)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}", exc_info=True)
            return False
    
    def _setup_integration(self):
        """Setup integration between components"""
        logger.info("Setting up component integration...")
        
        # Connect error recovery to automation engine
        if self.error_recovery and self.automation_engine:
            self.error_recovery.on_error = lambda error: self._handle_error(error)
        
        # Connect monitoring to analytics
        if self.monitoring_system and self.analytics:
            self.monitoring_system.on_metrics_collected = lambda metrics: self._record_metrics(metrics)
        
        # Connect alert manager to monitoring
        if self.alert_manager and self.monitoring_system:
            self.monitoring_system.on_alert_triggered = lambda alert: self.alert_manager.trigger_alert(alert)
        
        logger.info("✓ Component integration complete")
    
    def _handle_error(self, error):
        """Handle error from error recovery system"""
        logger.error(f"Handling error: {error.message}")
        
        # Record in analytics
        if self.analytics:
            self.analytics.record_metric(
                analytics_system.MetricData(
                    name="errors.total",
                    type=analytics_system.MetricType.COUNTER,
                    value=1.0,
                    labels={"severity": error.severity.value}
                )
            )
    
    def _record_metrics(self, metrics):
        """Record metrics from monitoring"""
        for metric in metrics:
            if self.analytics:
                self.analytics.record_metric(
                    analytics_system.MetricData(
                        name=metric.name,
                        type=analytics_system.MetricType.GAUGE,
                        value=metric.value,
                        timestamp=metric.timestamp
                    )
                )
    
    def start(self):
        """Start the application and all subsystems"""
        if self.running:
            logger.warning("Application is already running")
            return
        
        logger.info("Starting application...")
        
        try:
            # Initialize if not already done
            if not self.database:
                self.initialize()
            
            # Start automation engine
            if self.automation_engine:
                self.automation_engine.start()
                logger.info("✓ Automation engine started")
            
            self.running = True
            self.startup_time = datetime.now()
            
            logger.info("=" * 80)
            logger.info("Application started successfully!")
            logger.info(f"Uptime: {self.get_uptime()}")
            logger.info("=" * 80)
            
            # Start health check loop
            self._start_health_check_loop()
            
        except Exception as e:
            logger.error(f"Failed to start application: {e}", exc_info=True)
            self.running = False
    
    def _start_health_check_loop(self):
        """Start background health check loop"""
        def health_check_loop():
            while self.running and not self.shutdown_requested:
                try:
                    time.sleep(60)  # Check every minute
                    
                    if self.shutdown_requested:
                        break
                    
                    # Perform health checks
                    health = self.get_health_status()
                    
                    # Log health status
                    if health['overall_status'] == 'healthy':
                        logger.debug(f"Health check passed: {health}")
                    else:
                        logger.warning(f"Health check warning: {health}")
                
                except Exception as e:
                    logger.error(f"Health check error: {e}", exc_info=True)
        
        health_thread = threading.Thread(target=health_check_loop, daemon=True)
        health_thread.start()
        logger.info("Health check loop started")
    
    def stop(self):
        """Stop the application gracefully"""
        if not self.running:
            logger.warning("Application is not running")
            return
        
        logger.info("Stopping application...")
        
        # Set shutdown flag
        self.shutdown_requested = True
        
        try:
            # Stop automation engine
            if self.automation_engine:
                self.automation_engine.stop()
                logger.info("✓ Automation engine stopped")
            
            # Stop backup scheduler
            if self.backup_manager:
                self.backup_manager.stop_scheduler()
                logger.info("✓ Backup manager stopped")
            
            # Stop monitoring system
            if self.monitoring_system:
                self.monitoring_system.stop()
                logger.info("✓ Monitoring system stopped")
            
            # Close browser pool
            if self.browser_pool:
                self.browser_pool.close_all()
                logger.info("✓ Browser pool closed")
            
            # Close database
            if self.database:
                self.database.close()
                logger.info("✓ Database closed")
            
            self.running = False
            
            logger.info("=" * 80)
            logger.info("Application stopped successfully!")
            logger.info(f"Total uptime: {self.get_uptime()}")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)
    
    def shutdown(self):
        """Shutdown the application (alias for stop)"""
        self.stop()
        sys.exit(0)
    
    def get_uptime(self) -> str:
        """Get application uptime as formatted string"""
        if not self.startup_time:
            return "Not started"
        
        uptime = datetime.now() - self.startup_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return f"{hours}h {minutes}m {seconds}s"
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status of all components"""
        health_status = {
            'overall_status': 'healthy',
            'uptime': self.get_uptime(),
            'components': {}
        }
        
        try:
            # Check database
            if self.database:
                db_stats = self.database.get_stats()
                health_status['components']['database'] = {
                    'status': 'healthy' if db_stats.active_connections < db_stats.total_connections else 'warning',
                    'connections': db_stats.active_connections,
                    'queries': db_stats.total_queries,
                    'failed_queries': db_stats.failed_queries
                }
            
            # Check browser pool
            if self.browser_pool:
                browser_stats = self.browser_pool.get_stats()
                health_status['components']['browser_pool'] = {
                    'status': 'healthy' if browser_stats.idle_browsers > 0 else 'warning',
                    'total': browser_stats.total_browsers,
                    'active': browser_stats.active_browsers,
                    'idle': browser_stats.idle_browsers
                }
            
            # Check automation engine
            if self.automation_engine:
                auto_stats = self.automation_engine.get_stats()
                health_status['components']['automation'] = {
                    'status': 'healthy' if auto_stats.active_workers > 0 else 'warning',
                    'workers': auto_stats.total_workers,
                    'active': auto_stats.active_workers,
                    'tasks_completed': auto_stats.completed_tasks
                }
            
            # Check monitoring system
            if self.monitoring_system:
                monitor_health = self.monitoring_system.get_health_status()
                health_status['components']['monitoring'] = {
                    'status': monitor_health['overall_status'],
                    'checks': len(monitor_health['checks'])
                }
            
            # Determine overall status
            component_statuses = [c['status'] for c in health_status['components'].values()]
            if 'critical' in component_statuses:
                health_status['overall_status'] = 'critical'
            elif 'warning' in component_statuses:
                health_status['overall_status'] = 'warning'
        
        except Exception as e:
            logger.error(f"Error getting health status: {e}", exc_info=True)
            health_status['overall_status'] = 'critical'
        
        return health_status
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        return {
            'app_name': self.config.app_name,
            'app_version': self.config.app_version,
            'running': self.running,
            'uptime': self.get_uptime(),
            'startup_time': self.startup_time.isoformat() if self.startup_time else None,
            'config': {
                'debug_mode': self.config.debug_mode,
                'log_level': self.config.log_level,
                'max_workers': self.config.automation.max_workers,
                'browser_pool_size': self.config.browser.pool_size,
                'health_check_enabled': self.config.enable_health_checks,
            },
            'health': self.get_health_status()
        }
    
    def run_forever(self):
        """Run the application forever (main loop)"""
        if not self.running:
            self.start()
        
        logger.info("Application running in foreground...")
        
        try:
            while self.running and not self.shutdown_requested:
                time.sleep(1)
        
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            self.shutdown()
        
        except Exception as e:
            logger.error(f"Fatal error in main loop: {e}", exc_info=True)
            self.shutdown()


# Global orchestrator instance
_orchestrator_instance: Optional[ApplicationOrchestrator] = None
_orchestrator_lock = threading.Lock()


def get_orchestrator() -> ApplicationOrchestrator:
    """Get the global orchestrator instance"""
    global _orchestrator_instance
    
    with _orchestrator_lock:
        if _orchestrator_instance is None:
            _orchestrator_instance = ApplicationOrchestrator()
        
        return _orchestrator_instance


def main():
    """Main entry point for the application"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Darkstar E2EE Automation System v3.0')
    parser.add_argument('--config', type=str, help='Path to configuration file')
    parser.add_argument('--initialize', action='store_true', help='Initialize and exit')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    parser.add_argument('--status', action='store_true', help='Show status and exit')
    
    args = parser.parse_args()
    
    # Get orchestrator
    orchestrator = get_orchestrator()
    
    if args.status:
        # Show status
        info = orchestrator.get_system_info()
        print(json.dumps(info, indent=2))
        return
    
    # Initialize
    if not orchestrator.initialize():
        logger.error("Failed to initialize application")
        sys.exit(1)
    
    if args.initialize:
        logger.info("Initialization complete")
        return
    
    # Run
    if args.daemon:
        logger.info("Starting application as daemon...")
        orchestrator.start()
        
        # Keep running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            orchestrator.shutdown()
    else:
        orchestrator.run_forever()


if __name__ == "__main__":
    main()