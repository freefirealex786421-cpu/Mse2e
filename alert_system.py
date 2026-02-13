"""
Alert Notification System
Author: Darkstar Boii Sahiil
Version: 3.0 - Production Ready
Description: Advanced alert system with multiple notification channels, templates, and throttling
"""

import smtplib
import threading
import time
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import requests

import config
import logger_system
import database_enhanced as db

logger = logger_system.get_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Alert notification channels"""
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    TELEGRAM = "telegram"
    DISCORD = "discord"
    SMS = "sms"
    IN_APP = "in_app"


@dataclass
class AlertConfig:
    """Alert configuration"""
    alert_name: str
    severity: AlertSeverity
    condition: str  # Expression to evaluate
    threshold: float
    channels: List[AlertChannel]
    enabled: bool = True
    cooldown_minutes: int = 15
    throttle_max: int = 5
    throttle_window_minutes: int = 60
    template: Optional[str] = None


@dataclass
class NotificationChannel:
    """Notification channel configuration"""
    channel_type: AlertChannel
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    retry_attempts: int = 3
    retry_delay_seconds: int = 5


@dataclass
class Alert:
    """Alert information"""
    alert_id: str
    alert_name: str
    severity: AlertSeverity
    message: str
    value: float
    threshold: float
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    notified: bool = False
    channels_notified: List[str] = field(default_factory=list)
    occurrence_count: int = 1
    first_occurrence: datetime = field(default_factory=datetime.now)
    last_occurrence: datetime = field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AlertStats:
    """Alert statistics"""
    total_alerts: int = 0
    active_alerts: int = 0
    resolved_alerts: int = 0
    notifications_sent: int = 0
    notifications_failed: int = 0
    avg_notification_time: float = 0.0


class AlertManager:
    """
    Advanced alert management system with multiple notification channels
    """
    
    def __init__(self, cfg: Optional[config.AppConfig] = None):
        self.config = cfg or config.get_config()
        
        # Alert storage
        self.alerts: Dict[str, Alert] = {}
        self.alert_lock = threading.RLock()
        
        # Alert configurations
        self.alert_configs: Dict[str, AlertConfig] = {}
        self.configs_lock = threading.RLock()
        
        # Notification channels
        self.notification_channels: Dict[AlertChannel, NotificationChannel] = {}
        self.channels_lock = threading.RLock()
        
        # Statistics
        self.stats = AlertStats()
        self.stats_lock = threading.RLock()
        
        # Notification queue and thread
        self.notification_queue: List[Dict] = []
        self.queue_lock = threading.Lock()
        self.notification_thread: Optional[threading.Thread] = None
        self.notification_running = False
        
        # Throttle tracking
        self.throttle_tracking: Dict[str, List[datetime]] = defaultdict(list)
        self.throttle_lock = threading.RLock()
        
        # Database
        self.database = db.get_database()
        
        # Callbacks
        self.on_alert: Optional[Callable] = None
        self.on_notification_sent: Optional[Callable] = None
        
        # Initialize default channels
        self._initialize_default_channels()
        
        # Start notification system
        self.start()
        
        logger.info("Alert manager initialized")
    
    def _initialize_default_channels(self):
        """Initialize default notification channels"""
        
        # Email channel
        if self.config.alerts.email_enabled:
            self.notification_channels[AlertChannel.EMAIL] = NotificationChannel(
                channel_type=AlertChannel.EMAIL,
                enabled=self.config.alerts.email_enabled,
                config={
                    'smtp_server': self.config.alerts.email_smtp_server,
                    'smtp_port': self.config.alerts.email_smtp_port,
                    'username': self.config.alerts.email_username,
                    'password': self.config.alerts.email_password,
                    'from_email': self.config.alerts.email_from,
                    'to_emails': self.config.alerts.email_to
                }
            )
        
        # Webhook channel
        if self.config.alerts.webhook_enabled:
            self.notification_channels[AlertChannel.WEBHOOK] = NotificationChannel(
                channel_type=AlertChannel.WEBHOOK,
                enabled=self.config.alerts.webhook_enabled,
                config={
                    'webhook_url': self.config.alerts.webhook_url
                }
            )
        
        # In-app channel (always available)
        self.notification_channels[AlertChannel.IN_APP] = NotificationChannel(
            channel_type=AlertChannel.IN_APP,
            enabled=True,
            config={}
        )
    
    def start(self):
        """Start notification system"""
        if self.notification_running:
            return
        
        self.notification_running = True
        self.notification_thread = threading.Thread(target=self._notification_loop, daemon=True)
        self.notification_thread.start()
        
        logger.info("Alert notification system started")
    
    def stop(self):
        """Stop notification system"""
        self.notification_running = False
        if self.notification_thread:
            self.notification_thread.join(timeout=10)
        
        logger.info("Alert notification system stopped")
    
    def add_alert_config(self, config: AlertConfig):
        """Add an alert configuration"""
        with self.configs_lock:
            self.alert_configs[config.alert_name] = config
        logger.info(f"Alert config added: {config.alert_name}")
    
    def remove_alert_config(self, alert_name: str) -> bool:
        """Remove an alert configuration"""
        with self.configs_lock:
            if alert_name in self.alert_configs:
                del self.alert_configs[alert_name]
                logger.info(f"Alert config removed: {alert_name}")
                return True
        return False
    
    def add_notification_channel(self, channel: NotificationChannel):
        """Add a notification channel"""
        with self.channels_lock:
            self.notification_channels[channel.channel_type] = channel
        logger.info(f"Notification channel added: {channel.channel_type.value}")
    
    def trigger_alert(self, alert_name: str, value: float, 
                     message: Optional[str] = None, 
                     metadata: Optional[Dict] = None) -> Optional[str]:
        """Trigger an alert"""
        
        with self.configs_lock:
            if alert_name not in self.alert_configs:
                logger.warning(f"Alert config not found: {alert_name}")
                return None
            
            alert_config = self.alert_configs[alert_name]
        
        if not alert_config.enabled:
            return None
        
        # Check cooldown
        alert_id = self._generate_alert_id(alert_name)
        with self.alert_lock:
            if alert_id in self.alerts:
                existing_alert = self.alerts[alert_id]
                time_since_last = (datetime.now() - existing_alert.last_occurrence).total_seconds()
                if time_since_last < alert_config.cooldown_minutes * 60:
                    logger.debug(f"Alert {alert_id} in cooldown")
                    return alert_id
        
        # Check throttle
        if self._is_throttled(alert_name, alert_config):
            logger.debug(f"Alert {alert_name} throttled")
            return None
        
        # Create alert
        if not message:
            message = alert_config.template or f"{alert_name} threshold exceeded"
            message = message.format(
                alert_name=alert_name,
                value=value,
                threshold=alert_config.threshold
            )
        
        alert = Alert(
            alert_id=alert_id,
            alert_name=alert_name,
            severity=alert_config.severity,
            message=message,
            value=value,
            threshold=alert_config.threshold,
            metadata=metadata
        )
        
        with self.alert_lock:
            if alert_id in self.alerts:
                # Update existing alert
                existing = self.alerts[alert_id]
                existing.occurrence_count += 1
                existing.last_occurrence = datetime.now()
                existing.resolved = False
                alert = existing
            else:
                # New alert
                self.alerts[alert_id] = alert
                with self.stats_lock:
                    self.stats.total_alerts += 1
                    self.stats.active_alerts += 1
        
        # Log alert
        logger.warning(f"Alert triggered: {alert_name} - {message}")
        
        # Call callback
        if self.on_alert:
            try:
                self.on_alert(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
        
        # Log to database
        self.database.log_automation_event(
            None,
            f"ALERT-{alert_id}",
            alert.severity.value.upper(),
            message
        )
        
        # Queue notifications
        self._queue_notifications(alert, alert_config)
        
        # Track throttle
        self._track_throttle(alert_name)
        
        return alert_id
    
    def _generate_alert_id(self, alert_name: str) -> str:
        """Generate alert ID"""
        import hashlib
        content = f"{alert_name}:{datetime.now().date()}"
        return hashlib.md5(content.encode()).hexdigest()[:16].upper()
    
    def _is_throttled(self, alert_name: str, config: AlertConfig) -> bool:
        """Check if alert is throttled"""
        with self.throttle_lock:
            now = datetime.now()
            cutoff = now - timedelta(minutes=config.throttle_window_minutes)
            
            # Clean old entries
            self.throttle_tracking[alert_name] = [
                t for t in self.throttle_tracking[alert_name] if t >= cutoff
            ]
            
            # Check throttle limit
            return len(self.throttle_tracking[alert_name]) >= config.throttle_max
    
    def _track_throttle(self, alert_name: str):
        """Track alert for throttling"""
        with self.throttle_lock:
            self.throttle_tracking[alert_name].append(datetime.now())
    
    def _queue_notifications(self, alert: Alert, config: AlertConfig):
        """Queue notifications for an alert"""
        for channel in config.channels:
            with self.channels_lock:
                if channel not in self.notification_channels:
                    continue
                
                channel_config = self.notification_channels[channel]
                if not channel_config.enabled:
                    continue
            
            # Queue notification
            with self.queue_lock:
                self.notification_queue.append({
                    'alert': alert,
                    'channel': channel,
                    'queued_at': datetime.now()
                })
    
    def _notification_loop(self):
        """Notification processing loop"""
        while self.notification_running:
            try:
                with self.queue_lock:
                    if self.notification_queue:
                        item = self.notification_queue.pop(0)
                    else:
                        item = None
                
                if item:
                    self._send_notification(item['alert'], item['channel'])
                
                time.sleep(0.5)
            
            except Exception as e:
                logger.error(f"Notification loop error: {e}")
                time.sleep(5)
    
    def _send_notification(self, alert: Alert, channel: AlertChannel):
        """Send notification through a channel"""
        start_time = time.time()
        
        try:
            with self.channels_lock:
                channel_config = self.notification_channels.get(channel)
            
            if not channel_config or not channel_config.enabled:
                return
            
            success = False
            
            if channel == AlertChannel.EMAIL:
                success = self._send_email_notification(alert, channel_config)
            elif channel == AlertChannel.WEBHOOK:
                success = self._send_webhook_notification(alert, channel_config)
            elif channel == AlertChannel.IN_APP:
                success = self._send_in_app_notification(alert)
            
            # Update alert
            if success:
                with self.alert_lock:
                    alert.notified = True
                    if channel.value not in alert.channels_notified:
                        alert.channels_notified.append(channel.value)
                
                with self.stats_lock:
                    self.stats.notifications_sent += 1
                
                logger.info(f"Notification sent via {channel.value} for alert {alert.alert_id}")
                
                # Call callback
                if self.on_notification_sent:
                    try:
                        self.on_notification_sent(alert, channel)
                    except Exception as e:
                        logger.error(f"Notification callback error: {e}")
            else:
                with self.stats_lock:
                    self.stats.notifications_failed += 1
                
                logger.error(f"Notification failed via {channel.value} for alert {alert.alert_id}")
            
            # Update stats
            notification_time = time.time() - start_time
            with self.stats_lock:
                total_notifications = self.stats.notifications_sent + self.stats.notifications_failed
                self.stats.avg_notification_time = (
                    self.stats.avg_notification_time * (total_notifications - 1) + notification_time
                ) / total_notifications if total_notifications > 0 else notification_time
        
        except Exception as e:
            logger.error(f"Send notification error: {e}")
            with self.stats_lock:
                self.stats.notifications_failed += 1
    
    def _send_email_notification(self, alert: Alert, channel: NotificationChannel) -> bool:
        """Send email notification"""
        try:
            config = channel.config
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.alert_name}"
            msg['From'] = config['from_email']
            msg['To'] = ', '.join(config['to_emails'])
            
            # Create HTML body
            html = f"""
<html>
<head></head>
<body>
    <h2>Alert: {alert.alert_name}</h2>
    <p><strong>Severity:</strong> {alert.severity.value}</p>
    <p><strong>Message:</strong> {alert.message}</p>
    <p><strong>Value:</strong> {alert.value}</p>
    <p><strong>Threshold:</strong> {alert.threshold}</p>
    <p><strong>Time:</strong> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
    <hr>
    <p><small>This is an automated alert from {self.config.app_name}</small></p>
</body>
</html>
"""
            
            msg.attach(MIMEText(html, 'html'))
            
            # Send email
            with smtplib.SMTP(config['smtp_server'], config['smtp_port']) as server:
                if config.get('username'):
                    server.starttls()
                    server.login(config['username'], config['password'])
                server.send_message(msg)
            
            return True
        
        except Exception as e:
            logger.error(f"Email notification error: {e}")
            return False
    
    def _send_webhook_notification(self, alert: Alert, channel: NotificationChannel) -> bool:
        """Send webhook notification"""
        try:
            config = channel.config
            
            payload = {
                'alert_id': alert.alert_id,
                'alert_name': alert.alert_name,
                'severity': alert.severity.value,
                'message': alert.message,
                'value': alert.value,
                'threshold': alert.threshold,
                'timestamp': alert.timestamp.isoformat(),
                'metadata': alert.metadata
            }
            
            response = requests.post(
                config['webhook_url'],
                json=payload,
                timeout=10
            )
            
            response.raise_for_status()
            return True
        
        except Exception as e:
            logger.error(f"Webhook notification error: {e}")
            return False
    
    def _send_in_app_notification(self, alert: Alert) -> bool:
        """Send in-app notification"""
        # In-app notifications are stored in the database
        try:
            self.database.log_automation_event(
                None,
                f"NOTIFICATION-{alert.alert_id}",
                alert.severity.value.upper(),
                alert.message
            )
            return True
        except Exception as e:
            logger.error(f"In-app notification error: {e}")
            return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        with self.alert_lock:
            if alert_id not in self.alerts:
                return False
            
            alert = self.alerts[alert_id]
            alert.resolved = True
            
            with self.stats_lock:
                self.stats.active_alerts -= 1
                self.stats.resolved_alerts += 1
            
            logger.info(f"Alert resolved: {alert_id}")
            return True
    
    def get_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Get alert details"""
        with self.alert_lock:
            if alert_id not in self.alerts:
                return None
            
            alert = self.alerts[alert_id]
            return {
                'alert_id': alert.alert_id,
                'alert_name': alert.alert_name,
                'severity': alert.severity.value,
                'message': alert.message,
                'value': alert.value,
                'threshold': alert.threshold,
                'timestamp': alert.timestamp.isoformat(),
                'resolved': alert.resolved,
                'notified': alert.notified,
                'channels_notified': alert.channels_notified,
                'occurrence_count': alert.occurrence_count,
                'metadata': alert.metadata
            }
    
    def list_alerts(self, resolved: Optional[bool] = None, 
                   limit: int = 50) -> List[Dict[str, Any]]:
        """List alerts"""
        with self.alert_lock:
            alerts = list(self.alerts.values())
            
            if resolved is not None:
                alerts = [a for a in alerts if a.resolved == resolved]
            
            alerts.sort(key=lambda a: a.timestamp, reverse=True)
            alerts = alerts[:limit]
            
            return [
                {
                    'alert_id': a.alert_id,
                    'alert_name': a.alert_name,
                    'severity': a.severity.value,
                    'message': a.message,
                    'timestamp': a.timestamp.isoformat(),
                    'resolved': a.resolved,
                    'occurrence_count': a.occurrence_count
                }
                for a in alerts
            ]
    
    def get_stats(self) -> AlertStats:
        """Get alert statistics"""
        with self.stats_lock:
            with self.alert_lock:
                self.stats.active_alerts = sum(
                    1 for a in self.alerts.values() if not a.resolved
                )
            return self.stats
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all active (unresolved) alerts"""
        return self.list_alerts(resolved=False)


# Global alert manager instance
alert_manager = None


def get_alert_manager() -> AlertManager:
    """Get global alert manager instance"""
    global alert_manager
    if alert_manager is None:
        alert_manager = AlertManager()
    return alert_manager


if __name__ == "__main__":
    # Test alert system
    print("Testing Alert System...")
    
    manager = get_alert_manager()
    
    # Add test alert config
    from alert_system import AlertConfig, AlertSeverity, AlertChannel
    
    config = AlertConfig(
        alert_name="test_alert",
        severity=AlertSeverity.WARNING,
        condition="value > 50",
        threshold=50.0,
        channels=[AlertChannel.IN_APP],
        cooldown_minutes=5
    )
    manager.add_alert_config(config)
    
    # Trigger alert
    alert_id = manager.trigger_alert("test_alert", 75.0, "Test value exceeded threshold")
    print(f"Alert triggered: {alert_id}")
    
    # Get alerts
    alerts = manager.list_alerts(limit=10)
    print(f"Active alerts: {len(alerts)}")
    
    # Get stats
    stats = manager.get_stats()
    print(f"Alert stats: {stats}")
    
    # Resolve alert
    if alert_id:
        manager.resolve_alert(alert_id)
        print(f"Alert resolved: {alert_id}")
    
    # Wait a bit
    time.sleep(2)
    
    # Stop manager
    manager.stop()