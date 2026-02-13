"""
Analytics and Reporting System
Author: Darkstar Boii Sahiil
Version: 3.0 - Production Ready
Description: Comprehensive analytics with reporting, data analysis, and visualization support
"""

import time
import threading
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict
import json
import statistics

import config
import logger_system
import database_enhanced as db

logger = logger_system.get_logger(__name__)


class MetricType(Enum):
    """Metric type enumeration"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricData:
    """Metric data point"""
    name: str
    type: MetricType
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    labels: Optional[Dict[str, str]] = None
    tags: Optional[List[str]] = None


@dataclass
class ReportConfig:
    """Report configuration"""
    report_name: str
    description: str
    metrics: List[str]
    time_range: str = "24h"  # 1h, 6h, 24h, 7d, 30d
    aggregation: str = "avg"  # avg, sum, min, max, count
    enabled: bool = True
    schedule: Optional[str] = None  # cron expression


@dataclass
class AnalyticsStats:
    """Analytics statistics"""
    total_metrics_collected: int = 0
    total_reports_generated: int = 0
    unique_metric_names: int = 0
    data_points_per_hour: float = 0.0
    storage_usage: float = 0.0


class AnalyticsEngine:
    """
    Advanced analytics engine for metrics collection and reporting
    """
    
    def __init__(self, cfg: Optional[config.AppConfig] = None):
        self.config = cfg or config.get_config()
        
        # Metric storage
        self.metrics: Dict[str, List[MetricData]] = defaultdict(list)
        self.metric_types: Dict[str, MetricType] = {}
        self.metrics_lock = threading.RLock()
        
        # Reports configuration
        self.reports: Dict[str, ReportConfig] = {}
        self.reports_lock = threading.RLock()
        
        # Statistics
        self.stats = AnalyticsStats()
        self.stats_lock = threading.RLock()
        
        # Database
        self.database = db.get_database()
        
        # Initialize default reports
        self._initialize_default_reports()
        
        logger.info("Analytics engine initialized")
    
    def _initialize_default_reports(self):
        """Initialize default reports"""
        
        self.reports["system_performance"] = ReportConfig(
            report_name="System Performance",
            description="Overall system performance metrics",
            metrics=["system.cpu_percent", "system.memory_percent", "system.disk_percent"],
            time_range="24h",
            aggregation="avg"
        )
        
        self.reports["automation_stats"] = ReportConfig(
            report_name="Automation Statistics",
            description="Automation engine performance",
            metrics=["total_messages_sent", "active_workers", "failed_tasks", "avg_task_time"],
            time_range="7d",
            aggregation="sum"
        )
        
        self.reports["database_performance"] = ReportConfig(
            report_name="Database Performance",
            description="Database connection and query metrics",
            metrics=["total_queries", "failed_queries", "avg_query_time", "active_connections"],
            time_range="24h",
            aggregation="avg"
        )
        
        self.reports["error_summary"] = ReportConfig(
            report_name="Error Summary",
            description="Error occurrence and recovery metrics",
            metrics=["total_errors", "recovered_errors", "escalated_errors"],
            time_range="7d",
            aggregation="sum"
        )
    
    def record_metric(self, metric: MetricData):
        """Record a metric data point"""
        with self.metrics_lock:
            # Store metric
            self.metrics[metric.name].append(metric)
            
            # Keep only last 1000 points per metric
            if len(self.metrics[metric.name]) > 1000:
                self.metrics[metric.name] = self.metrics[metric.name][-1000:]
            
            # Store metric type
            self.metric_types[metric.name] = metric.type
            
            # Update statistics
            with self.stats_lock:
                self.stats.total_metrics_collected += 1
        
        # Also record to database
        self.database.record_metric(metric.name, metric.value, metric.labels)
    
    def increment_counter(self, name: str, value: float = 1.0, 
                         labels: Optional[Dict] = None, tags: Optional[List[str]] = None):
        """Increment a counter metric"""
        metric = MetricData(
            name=name,
            type=MetricType.COUNTER,
            value=value,
            labels=labels,
            tags=tags
        )
        self.record_metric(metric)
    
    def set_gauge(self, name: str, value: float, 
                 labels: Optional[Dict] = None, tags: Optional[List[str]] = None):
        """Set a gauge metric value"""
        metric = MetricData(
            name=name,
            type=MetricType.GAUGE,
            value=value,
            labels=labels,
            tags=tags
        )
        self.record_metric(metric)
    
    def record_histogram(self, name: str, value: float,
                        labels: Optional[Dict] = None, tags: Optional[List[str]] = None):
        """Record a histogram metric value"""
        metric = MetricData(
            name=name,
            type=MetricType.HISTOGRAM,
            value=value,
            labels=labels,
            tags=tags
        )
        self.record_metric(metric)
    
    def record_summary(self, name: str, value: float,
                      labels: Optional[Dict] = None, tags: Optional[List[str]] = None):
        """Record a summary metric value"""
        metric = MetricData(
            name=name,
            type=MetricType.SUMMARY,
            value=value,
            labels=labels,
            tags=tags
        )
        self.record_metric(metric)
    
    def get_metrics(self, name: str, hours: int = 24) -> List[MetricData]:
        """Get metrics for a name"""
        since = datetime.now() - timedelta(hours=hours)
        
        with self.metrics_lock:
            if name not in self.metrics:
                return []
            
            return [m for m in self.metrics[name] if m.timestamp >= since]
    
    def get_all_metric_names(self) -> List[str]:
        """Get all metric names"""
        with self.metrics_lock:
            return list(self.metrics.keys())
    
    def get_metric_summary(self, name: str, hours: int = 24) -> Dict[str, Any]:
        """Get summary statistics for a metric"""
        metrics = self.get_metrics(name, hours)
        
        if not metrics:
            return {}
        
        values = [m.value for m in metrics]
        
        return {
            'name': name,
            'type': self.metric_types.get(name, MetricType.GAUGE).value,
            'count': len(values),
            'sum': sum(values),
            'avg': statistics.mean(values),
            'min': min(values),
            'max': max(values),
            'median': statistics.median(values),
            'stddev': statistics.stdev(values) if len(values) > 1 else 0.0,
            'first_timestamp': metrics[0].timestamp.isoformat(),
            'last_timestamp': metrics[-1].timestamp.isoformat()
        }
    
    def get_metric_percentiles(self, name: str, hours: int = 24, 
                              percentiles: List[float] = None) -> Dict[str, float]:
        """Get percentiles for a metric"""
        if percentiles is None:
            percentiles = [50, 75, 90, 95, 99]
        
        metrics = self.get_metrics(name, hours)
        
        if not metrics:
            return {}
        
        values = sorted([m.value for m in metrics])
        
        result = {}
        for p in percentiles:
            index = int((p / 100) * len(values))
            if index >= len(values):
                index = len(values) - 1
            result[f'p{p}'] = values[index]
        
        return result
    
    def aggregate_metrics(self, names: List[str], hours: int = 24, 
                         aggregation: str = "avg") -> Dict[str, float]:
        """Aggregate multiple metrics"""
        result = {}
        
        for name in names:
            summary = self.get_metric_summary(name, hours)
            
            if summary:
                if aggregation == "sum":
                    result[name] = summary['sum']
                elif aggregation == "avg":
                    result[name] = summary['avg']
                elif aggregation == "min":
                    result[name] = summary['min']
                elif aggregation == "max":
                    result[name] = summary['max']
                elif aggregation == "count":
                    result[name] = summary['count']
                else:
                    result[name] = summary['avg']
        
        return result
    
    def get_time_series(self, name: str, hours: int = 24, 
                       interval_minutes: int = 5) -> List[Dict[str, Any]]:
        """Get time series data for a metric"""
        metrics = self.get_metrics(name, hours)
        
        if not metrics:
            return []
        
        # Group by time interval
        intervals = defaultdict(list)
        for metric in metrics:
            timestamp = metric.timestamp
            interval_start = timestamp.replace(
                minute=(timestamp.minute // interval_minutes) * interval_minutes,
                second=0,
                microsecond=0
            )
            intervals[interval_start].append(metric.value)
        
        # Aggregate each interval
        time_series = []
        for interval_start in sorted(intervals.keys()):
            values = intervals[interval_start]
            
            time_series.append({
                'timestamp': interval_start.isoformat(),
                'avg': statistics.mean(values),
                'min': min(values),
                'max': max(values),
                'count': len(values)
            })
        
        return time_series
    
    def generate_report(self, report_name: str) -> Optional[Dict[str, Any]]:
        """Generate a report"""
        with self.reports_lock:
            if report_name not in self.reports:
                logger.error(f"Report not found: {report_name}")
                return None
            
            report_config = self.reports[report_name]
        
        # Parse time range
        hours = self._parse_time_range(report_config.time_range)
        
        # Aggregate metrics
        aggregated = self.aggregate_metrics(
            report_config.metrics,
            hours,
            report_config.aggregation
        )
        
        # Get time series for each metric
        time_series = {}
        for metric_name in report_config.metrics:
            time_series[metric_name] = self.get_time_series(metric_name, hours)
        
        # Generate report
        report = {
            'report_name': report_name,
            'description': report_config.description,
            'generated_at': datetime.now().isoformat(),
            'time_range': report_config.time_range,
            'aggregation': report_config.aggregation,
            'metrics': aggregated,
            'time_series': time_series
        }
        
        # Update statistics
        with self.stats_lock:
            self.stats.total_reports_generated += 1
        
        logger.info(f"Report generated: {report_name}")
        return report
    
    def _parse_time_range(self, time_range: str) -> int:
        """Parse time range string to hours"""
        time_range = time_range.lower()
        
        if time_range.endswith('h'):
            return int(time_range[:-1])
        elif time_range.endswith('d'):
            return int(time_range[:-1]) * 24
        elif time_range.endswith('w'):
            return int(time_range[:-1]) * 24 * 7
        else:
            return 24  # Default to 24 hours
    
    def add_report(self, report: ReportConfig):
        """Add a custom report"""
        with self.reports_lock:
            self.reports[report.report_name] = report
        logger.info(f"Report added: {report.report_name}")
    
    def remove_report(self, report_name: str) -> bool:
        """Remove a report"""
        with self.reports_lock:
            if report_name in self.reports:
                del self.reports[report_name]
                logger.info(f"Report removed: {report_name}")
                return True
        return False
    
    def list_reports(self) -> List[Dict[str, Any]]:
        """List all reports"""
        with self.reports_lock:
            return [
                {
                    'report_name': name,
                    'description': report.description,
                    'metrics': report.metrics,
                    'time_range': report.time_range,
                    'aggregation': report.aggregation,
                    'enabled': report.enabled
                }
                for name, report in self.reports.items()
            ]
    
    def get_stats(self) -> AnalyticsStats:
        """Get analytics statistics"""
        with self.stats_lock:
            with self.metrics_lock:
                self.stats.unique_metric_names = len(self.metrics)
            return self.stats
    
    def export_metrics(self, output_file: str, hours: int = 24):
        """Export metrics to a file"""
        metrics_data = []
        
        for metric_name in self.get_all_metric_names():
            metrics = self.get_metrics(metric_name, hours)
            
            for metric in metrics:
                metrics_data.append({
                    'name': metric.name,
                    'type': metric.type.value,
                    'value': metric.value,
                    'timestamp': metric.timestamp.isoformat(),
                    'labels': metric.labels,
                    'tags': metric.tags
                })
        
        # Write to file
        with open(output_file, 'w') as f:
            json.dump(metrics_data, f, indent=2)
        
        logger.info(f"Metrics exported to: {output_file}")
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for analytics dashboard"""
        # Get key metrics
        system_metrics = self.aggregate_metrics(
            ["system.cpu_percent", "system.memory_percent", "system.disk_percent"],
            hours=1,
            aggregation="avg"
        )
        
        automation_metrics = self.aggregate_metrics(
            ["total_messages_sent", "active_workers", "failed_tasks"],
            hours=24,
            aggregation="sum"
        )
        
        # Get trends
        cpu_trend = self.get_time_series("system.cpu_percent", hours=24)
        
        return {
            'system_metrics': system_metrics,
            'automation_metrics': automation_metrics,
            'trends': {
                'cpu': cpu_trend[-10:] if cpu_trend else []
            },
            'stats': {
                'total_metrics': self.stats.total_metrics_collected,
                'unique_metrics': len(self.get_all_metric_names()),
                'total_reports': self.stats.total_reports_generated
            },
            'timestamp': datetime.now().isoformat()
        }


class AnalyticsReporter:
    """
    Generate and format analytics reports
    """
    
    def __init__(self, analytics: AnalyticsEngine):
        self.analytics = analytics
    
    def generate_text_report(self, report_name: str) -> Optional[str]:
        """Generate a plain text report"""
        report = self.analytics.generate_report(report_name)
        if not report:
            return None
        
        lines = [
            "=" * 60,
            f"REPORT: {report['report_name']}",
            f"Generated: {report['generated_at']}",
            f"Time Range: {report['time_range']}",
            "=" * 60,
            ""
        ]
        
        lines.append(f"Description: {report['description']}")
        lines.append("")
        
        lines.append("METRICS SUMMARY:")
        lines.append("-" * 60)
        for metric_name, value in report['metrics'].items():
            lines.append(f"  {metric_name}: {value:.2f}")
        lines.append("")
        
        return "\n".join(lines)
    
    def generate_html_report(self, report_name: str) -> Optional[str]:
        """Generate an HTML report"""
        report = self.analytics.generate_report(report_name)
        if not report:
            return None
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{report['report_name']}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .metrics {{ margin-top: 20px; }}
        .metric {{ margin: 10px 0; padding: 10px; background: #fafafa; border-left: 4px solid #007bff; }}
        .timestamp {{ color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{report['report_name']}</h1>
        <p class="timestamp">Generated: {report['generated_at']}</p>
        <p>{report['description']}</p>
    </div>
    
    <div class="metrics">
        <h2>Metrics Summary</h2>
"""
        
        for metric_name, value in report['metrics'].items():
            html += f"""
        <div class="metric">
            <strong>{metric_name}:</strong> {value:.2f}
        </div>
"""
        
        html += """
    </div>
</body>
</html>
"""
        
        return html
    
    def generate_json_report(self, report_name: str) -> Optional[str]:
        """Generate a JSON report"""
        report = self.analytics.generate_report(report_name)
        if not report:
            return None
        
        return json.dumps(report, indent=2, default=str)


# Global analytics engine instance
analytics_engine = None


def get_analytics_engine() -> AnalyticsEngine:
    """Get global analytics engine instance"""
    global analytics_engine
    if analytics_engine is None:
        analytics_engine = AnalyticsEngine()
    return analytics_engine


if __name__ == "__main__":
    # Test analytics system
    print("Testing Analytics System...")
    
    analytics = get_analytics_engine()
    
    # Record some test metrics
    for i in range(100):
        analytics.set_gauge("test.metric", i * 1.5)
        time.sleep(0.01)
    
    # Get metric summary
    summary = analytics.get_metric_summary("test.metric")
    print(f"Metric summary: {summary}")
    
    # Get percentiles
    percentiles = analytics.get_metric_percentiles("test.metric")
    print(f"Percentiles: {percentiles}")
    
    # Get time series
    time_series = analytics.get_time_series("test.metric", hours=1)
    print(f"Time series points: {len(time_series)}")
    
    # Generate report
    report = analytics.generate_report("system_performance")
    print(f"Report keys: {list(report.keys()) if report else 'None'}")
    
    # Get dashboard data
    dashboard = analytics.get_dashboard_data()
    print(f"Dashboard keys: {list(dashboard.keys())}")