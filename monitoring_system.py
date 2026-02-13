"""
Monitoring and Health Check System
Author: Darkstar Boii Sahiil
Version: 3.0 - Production Ready
Description: Comprehensive monitoring with health checks, metrics collection, and performance tracking
"""

import time
import threading
import psutil
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import deque
import statistics

import config
import logger_system
import database_enhanced as db

logger = logger_system.get_logger(__name__)


class HealthStatus(Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Health check configuration"""
    name: str
    check_func: Callable
    interval: int = 60  # seconds
    timeout: int = 30
    enabled: bool = True
    last_check: Optional[datetime] = None
    last_status: HealthStatus = HealthStatus.UNKNOWN
    last_result: Optional[str] = None
    failure_count: int = 0
    max_failures: int = 3


@dataclass
class Metric:
    """Metric data point"""
    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None
    labels: Optional[Dict[str, str]] = None


@dataclass
class Alert:
    """Alert configuration"""
    alert_id: str
    name: str
    condition: Callable[[float], bool]
    severity: str = "warning"  # info, warning, critical
    enabled: bool = True
    cooldown: int = 300  # seconds
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    threshold: float = 0.0
    message_template: str = "{name}: value {value} exceeds threshold {threshold}"


@dataclass
class SystemStats:
    """System statistics"""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used: int = 0
    memory_total: int = 0
    disk_percent: float = 0.0
    disk_used: int = 0
    disk_total: int = 0
    network_sent: int = 0
    network_recv: int = 0
    process_count: int = 0
    uptime: float = 0.0
    load_average: List[float] = field(default_factory=list)


class MetricsCollector:
    """
    Collects and stores metrics for monitoring
    """
    
    def __init__(self, retention_hours: int = 24, max_points: int = 1000):
        self.retention_hours = retention_hours
        self.max_points = max_points
        self.metrics: Dict[str, deque] = {}
        self.lock = threading.RLock()
        self.cleanup_thread: Optional[threading.Thread] = None
        self.cleanup_running = False
        
        # Start cleanup thread
        self._start_cleanup_thread()
    
    def record_metric(self, metric: Metric):
        """Record a metric"""
        with self.lock:
            if metric.name not in self.metrics:
                self.metrics[metric.name] = deque(maxlen=self.max_points)
            
            self.metrics[metric.name].append(metric)
    
    def record_value(self, name: str, value: float, 
                    metadata: Optional[Dict] = None, labels: Optional[Dict] = None):
        """Record a simple metric value"""
        metric = Metric(
            name=name,
            value=value,
            metadata=metadata,
            labels=labels
        )
        self.record_metric(metric)
    
    def get_metrics(self, name: str, since: Optional[datetime] = None) -> List[Metric]:
        """Get metrics for a name"""
        with self.lock:
            if name not in self.metrics:
                return []
            
            metrics = list(self.metrics[name])
            
            if since:
                metrics = [m for m in metrics if m.timestamp >= since]
            
            return metrics
    
    def get_latest_metric(self, name: str) -> Optional[Metric]:
        """Get the latest metric for a name"""
        with self.lock:
            if name not in self.metrics or not self.metrics[name]:
                return None
            return self.metrics[name][-1]
    
    def get_metric_stats(self, name: str, hours: int = 1) -> Dict[str, float]:
        """Get statistics for a metric"""
        since = datetime.now() - timedelta(hours=hours)
        metrics = self.get_metrics(name, since)
        
        if not metrics:
            return {}
        
        values = [m.value for m in metrics]
        
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': statistics.mean(values),
            'median': statistics.median(values),
            'stddev': statistics.stdev(values) if len(values) > 1 else 0.0
        }
    
    def get_all_metric_names(self) -> List[str]:
        """Get all metric names"""
        with self.lock:
            return list(self.metrics.keys())
    
    def _start_cleanup_thread(self):
        """Start cleanup thread for old metrics"""
        self.cleanup_running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
    
    def _cleanup_loop(self):
        """Cleanup old metrics"""
        while self.cleanup_running:
            try:
                time.sleep(300)  # Check every 5 minutes
                cutoff = datetime.now() - timedelta(hours=self.retention_hours)
                
                with self.lock:
                    for name, metrics in self.metrics.items():
                        # Remove old metrics
                        while metrics and metrics[0].timestamp < cutoff:
                            metrics.popleft()
            
            except Exception as e:
                logger.error(f"Metrics cleanup error: {e}")
    
    def close(self):
        """Close metrics collector"""
        self.cleanup_running = False
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)


class HealthChecker:
    """
    Health check system with multiple checks
    """
    
    def __init__(self):
        self.health_checks: Dict[str, HealthCheck] = {}
        self.lock = threading.RLock()
        self.check_thread: Optional[threading.Thread] = None
        self.check_running = False
        self.on_health_change: Optional[Callable] = None
    
    def add_health_check(self, health_check: HealthCheck):
        """Add a health check"""
        with self.lock:
            self.health_checks[health_check.name] = health_check
        logger.info(f"Added health check: {health_check.name}")
    
    def remove_health_check(self, name: str):
        """Remove a health check"""
        with self.lock:
            if name in self.health_checks:
                del self.health_checks[name]
                logger.info(f"Removed health check: {name}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        with self.lock:
            checks = {}
            overall_status = HealthStatus.HEALTHY
            
            for name, check in self.health_checks.items():
                checks[name] = {
                    'status': check.last_status.value,
                    'last_check': check.last_check.isoformat() if check.last_check else None,
                    'last_result': check.last_result,
                    'failure_count': check.failure_count
                }
                
                if check.last_status == HealthStatus.CRITICAL:
                    overall_status = HealthStatus.CRITICAL
                elif check.last_status == HealthStatus.WARNING and overall_status != HealthStatus.CRITICAL:
                    overall_status = HealthStatus.WARNING
            
            return {
                'overall_status': overall_status.value,
                'checks': checks,
                'timestamp': datetime.now().isoformat()
            }
    
    def start(self):
        """Start health check thread"""
        if self.check_running:
            return
        
        self.check_running = True
        self.check_thread = threading.Thread(target=self._check_loop, daemon=True)
        self.check_thread.start()
        logger.info("Health checker started")
    
    def stop(self):
        """Stop health check thread"""
        self.check_running = False
        if self.check_thread:
            self.check_thread.join(timeout=5)
        logger.info("Health checker stopped")
    
    def _check_loop(self):
        """Health check loop"""
        while self.check_running:
            try:
                with self.lock:
                    for name, check in list(self.health_checks.items()):
                        if not check.enabled:
                            continue
                        
                        # Check if it's time to run this check
                        if check.last_check:
                            time_since_check = (datetime.now() - check.last_check).total_seconds()
                            if time_since_check < check.interval:
                                continue
                        
                        # Run health check
                        try:
                            result = check.check_func()
                            check.last_check = datetime.now()
                            check.last_result = str(result)
                            
                            if result:
                                check.last_status = HealthStatus.HEALTHY
                                check.failure_count = 0
                            else:
                                check.failure_count += 1
                                if check.failure_count >= check.max_failures:
                                    check.last_status = HealthStatus.CRITICAL
                                else:
                                    check.last_status = HealthStatus.WARNING
                        
                        except Exception as e:
                            logger.error(f"Health check {name} failed: {e}")
                            check.last_check = datetime.now()
                            check.last_result = f"Error: {str(e)}"
                            check.failure_count += 1
                            check.last_status = HealthStatus.CRITICAL
                
                # Notify of health changes
                if self.on_health_change:
                    try:
                        self.on_health_change(self.get_health_status())
                    except Exception as e:
                        logger.error(f"Health change callback error: {e}")
                
                time.sleep(10)  # Check every 10 seconds
            
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                time.sleep(30)


class MonitoringSystem:
    """
    Comprehensive monitoring system with metrics, health checks, and alerts
    """
    
    def __init__(self, cfg: Optional[config.AppConfig] = None):
        self.config = cfg or config.get_config()
        
        # Components
        self.metrics_collector = MetricsCollector(
            retention_hours=self.config.automation.metrics_retention_hours,
            max_points=1000
        )
        
        self.health_checker = HealthChecker()
        
        self.alerts: Dict[str, Alert] = {}
        self.alert_lock = threading.RLock()
        
        # System monitoring thread
        self.system_thread: Optional[threading.Thread] = None
        self.system_running = False
        
        # Alert callbacks
        self.on_alert: Optional[Callable] = None
        
        # Database
        self.db = db.get_database()
        
        # Initialize default health checks
        self._initialize_default_checks()
        
        # Start monitoring
        self.start()
        
        logger.info("Monitoring system initialized")
    
    def _initialize_default_checks(self):
        """Initialize default health checks"""
        
        # Database health check
        def check_database():
            try:
                stats = self.db.get_stats()
                return stats['pool']['active_connections'] < stats['pool']['total_connections']
            except Exception:
                return False
        
        self.health_checker.add_health_check(HealthCheck(
            name="database",
            check_func=check_database,
            interval=60,
            max_failures=3
        ))
        
        # Disk space health check
        def check_disk_space():
            try:
                disk = psutil.disk_usage('/')
                return disk.percent < 90
            except Exception:
                return False
        
        self.health_checker.add_health_check(HealthCheck(
            name="disk_space",
            check_func=check_disk_space,
            interval=300,
            max_failures=3
        ))
        
        # Memory health check
        def check_memory():
            try:
                memory = psutil.virtual_memory()
                return memory.percent < 90
            except Exception:
                return False
        
        self.health_checker.add_health_check(HealthCheck(
            name="memory",
            check_func=check_memory,
            interval=60,
            max_failures=5
        ))
        
        # CPU health check
        def check_cpu():
            try:
                cpu = psutil.cpu_percent(interval=1)
                return cpu < 95
            except Exception:
                return False
        
        self.health_checker.add_health_check(HealthCheck(
            name="cpu",
            check_func=check_cpu,
            interval=60,
            max_failures=5
        ))
    
    def start(self):
        """Start monitoring system"""
        self.health_checker.start()
        self.system_running = True
        self.system_thread = threading.Thread(target=self._system_monitoring_loop, daemon=True)
        self.system_thread.start()
        logger.info("Monitoring system started")
    
    def stop(self):
        """Stop monitoring system"""
        self.health_checker.stop()
        self.system_running = False
        if self.system_thread:
            self.system_thread.join(timeout=5)
        self.metrics_collector.close()
        logger.info("Monitoring system stopped")
    
    def _system_monitoring_loop(self):
        """System monitoring loop"""
        while self.system_running:
            try:
                # Collect system stats
                stats = self._get_system_stats()
                
                # Record metrics
                self.metrics_collector.record_value("system.cpu_percent", stats.cpu_percent)
                self.metrics_collector.record_value("system.memory_percent", stats.memory_percent)
                self.metrics_collector.record_value("system.disk_percent", stats.disk_percent)
                self.metrics_collector.record_value("system.process_count", stats.process_count)
                
                # Record to database
                self.db.record_metric("cpu_percent", stats.cpu_percent)
                self.db.record_metric("memory_percent", stats.memory_percent)
                self.db.record_metric("disk_percent", stats.disk_percent)
                
                # Check alerts
                self._check_alerts(stats)
                
                # Sleep
                time.sleep(30)
            
            except Exception as e:
                logger.error(f"System monitoring loop error: {e}")
                time.sleep(60)
    
    def _get_system_stats(self) -> SystemStats:
        """Get system statistics"""
        try:
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            net_io = psutil.net_io_counters()
            processes = len(psutil.pids())
            
            load_avg = list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else []
            
            return SystemStats(
                cpu_percent=cpu,
                memory_percent=memory.percent,
                memory_used=memory.used,
                memory_total=memory.total,
                disk_percent=disk.percent,
                disk_used=disk.used,
                disk_total=disk.total,
                network_sent=net_io.bytes_sent,
                network_recv=net_io.bytes_recv,
                process_count=processes,
                uptime=time.time() - psutil.boot_time(),
                load_average=load_avg
            )
        
        except Exception as e:
            logger.error(f"Failed to get system stats: {e}")
            return SystemStats()
    
    def add_alert(self, alert: Alert):
        """Add an alert"""
        with self.alert_lock:
            self.alerts[alert.alert_id] = alert
        logger.info(f"Added alert: {alert.name}")
    
    def remove_alert(self, alert_id: str):
        """Remove an alert"""
        with self.alert_lock:
            if alert_id in self.alerts:
                del self.alerts[alert_id]
                logger.info(f"Removed alert: {alert_id}")
    
    def _check_alerts(self, stats: SystemStats):
        """Check if any alerts should be triggered"""
        with self.alert_lock:
            for alert in self.alerts.values():
                if not alert.enabled:
                    continue
                
                try:
                    # Check cooldown
                    if alert.last_triggered:
                        time_since_trigger = (datetime.now() - alert.last_triggered).total_seconds()
                        if time_since_trigger < alert.cooldown:
                            continue
                    
                    # Map metric names to stats
                    metric_map = {
                        'cpu_percent': stats.cpu_percent,
                        'memory_percent': stats.memory_percent,
                        'disk_percent': stats.disk_percent
                    }
                    
                    # Check condition
                    if alert.name in metric_map:
                        value = metric_map[alert.name]
                        if alert.condition(value):
                            # Trigger alert
                            alert.last_triggered = datetime.now()
                            alert.trigger_count += 1
                            
                            message = alert.message_template.format(
                                name=alert.name,
                                value=value,
                                threshold=alert.threshold
                            )
                            
                            logger.warning(f"Alert triggered: {message}")
                            
                            # Call callback
                            if self.on_alert:
                                try:
                                    self.on_alert(alert, message)
                                except Exception as e:
                                    logger.error(f"Alert callback error: {e}")
                            
                            # Record to database
                            self.db.log_automation_event(
                                None,
                                f"ALERT-{alert.alert_id}",
                                alert.severity.upper(),
                                message
                            )
                
                except Exception as e:
                    logger.error(f"Alert check error: {e}")
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        stats = self._get_system_stats()
        return {
            'cpu': {
                'percent': stats.cpu_percent,
                'load_average': stats.load_average
            },
            'memory': {
                'percent': stats.memory_percent,
                'used': stats.memory_used,
                'total': stats.memory_total
            },
            'disk': {
                'percent': stats.disk_percent,
                'used': stats.disk_used,
                'total': stats.disk_total
            },
            'network': {
                'sent': stats.network_sent,
                'recv': stats.network_recv
            },
            'process_count': stats.process_count,
            'uptime': stats.uptime
        }
    
    def get_metrics(self, name: str, hours: int = 1) -> List[Dict[str, Any]]:
        """Get metrics for a name"""
        metrics = self.metrics_collector.get_metrics(name)
        
        cutoff = datetime.now() - timedelta(hours=hours)
        metrics = [m for m in metrics if m.timestamp >= cutoff]
        
        return [
            {
                'name': m.name,
                'value': m.value,
                'timestamp': m.timestamp.isoformat(),
                'metadata': m.metadata,
                'labels': m.labels
            }
            for m in metrics
        ]
    
    def get_metric_stats(self, name: str, hours: int = 1) -> Dict[str, float]:
        """Get metric statistics"""
        return self.metrics_collector.get_metric_stats(name, hours)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status"""
        return self.health_checker.get_health_status()
    
    def get_all_metric_names(self) -> List[str]:
        """Get all metric names"""
        return self.metrics_collector.get_all_metric_names()
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for monitoring dashboard"""
        return {
            'system_stats': self.get_system_stats(),
            'health_status': self.get_health_status(),
            'metric_names': self.get_all_metric_names(),
            'timestamp': datetime.now().isoformat()
        }


# Global monitoring system instance
monitoring_system = None


def get_monitoring_system() -> MonitoringSystem:
    """Get global monitoring system instance"""
    global monitoring_system
    if monitoring_system is None:
        monitoring_system = MonitoringSystem()
    return monitoring_system


if __name__ == "__main__":
    # Test monitoring system
    print("Testing Monitoring System...")
    
    monitor = get_monitoring_system()
    
    # Add custom alert
    alert = Alert(
        alert_id="cpu_high",
        name="cpu_percent",
        condition=lambda x: x > 80,
        severity="warning",
        threshold=80.0,
        message_template="CPU usage is {value}%"
    )
    monitor.add_alert(alert)
    
    # Wait a bit
    time.sleep(5)
    
    # Get system stats
    stats = monitor.get_system_stats()
    print(f"System stats: {json.dumps(stats, indent=2)}")
    
    # Get health status
    health = monitor.get_health_status()
    print(f"Health status: {json.dumps(health, indent=2)}")
    
    # Get metric stats
    cpu_stats = monitor.get_metric_stats("system.cpu_percent")
    print(f"CPU stats: {json.dumps(cpu_stats, indent=2)}")
    
    # Get dashboard data
    dashboard = monitor.get_dashboard_data()
    print(f"Dashboard data keys: {list(dashboard.keys())}")
    
    # Stop monitoring
    monitor.stop()