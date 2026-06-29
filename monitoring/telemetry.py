"""
Enterprise-grade monitoring and observability for dbt + Databricks pipelines
Integrates with Application Insights, Datadog, and custom metrics
"""

import os
import time
import json
import logging
from collections import deque
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum


class MetricType(Enum):
    """Types of metrics to track"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class SeverityLevel(Enum):
    """Severity levels for events"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class Metric:
    """Custom metric for tracking"""
    name: str
    value: float
    metric_type: MetricType
    tags: Dict[str, str]
    timestamp: str


@dataclass
class Event:
    """Custom event for tracking"""
    event_name: str
    severity: SeverityLevel
    message: str
    properties: Dict[str, Any]
    timestamp: str


class TelemetryClient:
    """
    Central telemetry client for monitoring & observability
    Supports Application Insights, Datadog, and custom backends
    """

    def __init__(self, service_name: str = "dbt-databricks"):
        self.service_name = service_name
        self.logger = self._setup_logger()
        self.metrics = deque(maxlen=1000)
        self.events = deque(maxlen=1000)
        
        # Initialize backends
        self.app_insights_enabled = bool(os.getenv("APPINSIGHTS_INSTRUMENTATION_KEY"))
        self.datadog_enabled = bool(os.getenv("DD_API_KEY"))
        
        if self.app_insights_enabled:
            self._init_app_insights()
        if self.datadog_enabled:
            self._init_datadog()

    def _setup_logger(self) -> logging.Logger:
        """Setup structured logging with JSON output"""
        logger = logging.getLogger(self.service_name)
        if logger.handlers:
            return logger

        handler = logging.StreamHandler()
        
        # JSON formatter for structured logging
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"service": "' + self.service_name + '", "message": "%(message)s"}'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger

    def _init_app_insights(self):
        """Initialize Application Insights"""
        try:
            from azure.monitor.opentelemetry import configure_azure_monitor
            configure_azure_monitor()
            self.logger.info("Application Insights initialized")
        except ImportError:
            self.logger.warning("Application Insights SDK not installed")
            self.app_insights_enabled = False

    def _init_datadog(self):
        """Initialize Datadog client"""
        try:
            from datadog import initialize as dd_initialize
            options = {"api_key": os.getenv("DD_API_KEY")}
            dd_initialize(**options)
            self.logger.info("Datadog initialized")
        except ImportError:
            self.logger.warning("Datadog SDK not installed")
            self.datadog_enabled = False

    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        tags: Optional[Dict[str, str]] = None,
        properties: Optional[Dict[str, str]] = None,
    ):
        """Record a custom metric"""
        if tags is None:
            tags = {}
        if properties:
            tags.update({k: str(v) for k, v in properties.items()})
        
        tags["service"] = self.service_name
        metric = Metric(name, value, metric_type, tags, datetime.utcnow().isoformat())
        self.metrics.append(metric)
        
        # Send to backends
        if self.app_insights_enabled:
            self._send_to_app_insights(metric)
        if self.datadog_enabled:
            self._send_to_datadog(metric)

    def record_event(
        self,
        event_name: Optional[str] = None,
        severity: SeverityLevel = SeverityLevel.INFO,
        message: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
    ):
        """Record a custom event"""
        event_name = event_name or name or "event"
        message = message or event_name
        if properties is None:
            properties = {}
        
        properties["service"] = self.service_name
        event = Event(event_name, severity, message, properties, datetime.utcnow().isoformat())
        self.events.append(event)
        
        # Log to standard logger
        log_level = getattr(logging, severity.value)
        self.logger.log(log_level, f"{event_name}: {message}")
        
        # Send to backends
        if self.app_insights_enabled:
            self._send_event_to_app_insights(event)
        if self.datadog_enabled:
            self._send_event_to_datadog(event)

    def _send_to_app_insights(self, metric: Metric):
        """Send metric to Application Insights"""
        try:
            from azure.monitor.opentelemetry.api import metrics
            meter = metrics.get_meter("dbt-databricks")
            
            if metric.metric_type == MetricType.COUNTER:
                counter = meter.create_counter(metric.name)
                counter.add(int(metric.value), attributes=metric.tags)
            elif metric.metric_type == MetricType.GAUGE:
                gauge = meter.create_gauge(metric.name)
                gauge.record(metric.value, attributes=metric.tags)
        except Exception as e:
            self.logger.warning(f"Failed to send metric to App Insights: {e}")

    def _send_event_to_app_insights(self, event: Event):
        """Send event to Application Insights"""
        try:
            from azure.monitor.opentelemetry.api import trace
            tracer = trace.get_tracer("dbt-databricks")
            with tracer.start_as_current_span(event.event_name) as span:
                span.set_attribute("severity", event.severity.value)
                span.set_attribute("message", event.message)
                for key, value in event.properties.items():
                    span.set_attribute(key, str(value))
        except Exception as e:
            self.logger.warning(f"Failed to send event to App Insights: {e}")

    def _send_to_datadog(self, metric: Metric):
        """Send metric to Datadog"""
        try:
            from datadog import api
            tags = [f"{k}:{v}" for k, v in metric.tags.items()]
            
            if metric.metric_type == MetricType.GAUGE:
                api.Metric.send(
                    metric=metric.name,
                    points=metric.value,
                    tags=tags
                )
        except Exception as e:
            self.logger.warning(f"Failed to send metric to Datadog: {e}")

    def _send_event_to_datadog(self, event: Event):
        """Send event to Datadog"""
        try:
            from datadog import api
            api.Event.create(
                title=event.event_name,
                text=event.message,
                tags=[f"{k}:{v}" for k, v in event.properties.items()],
                alert_type=event.severity.value.lower()
            )
        except Exception as e:
            self.logger.warning(f"Failed to send event to Datadog: {e}")

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of collected metrics"""
        return {
            "total_metrics": len(self.metrics),
            "total_events": len(self.events),
            "metrics": [asdict(m) for m in self.metrics[-10:]],  # Last 10
            "events": [asdict(e) for e in self.events[-10:]]     # Last 10
        }


class HealthCheck:
    """Health check for dbt + Databricks infrastructure"""

    def __init__(self, telemetry: TelemetryClient):
        self.telemetry = telemetry

    def check_databricks_connection(self, host: Optional[str] = None, token: Optional[str] = None) -> bool:
        """Check Databricks connectivity"""
        try:
            from databricks.sdk import WorkspaceClient
            host = host or os.getenv("DATABRICKS_HOST")
            token = token or os.getenv("DATABRICKS_TOKEN")
            if not host or not token:
                raise ValueError("Missing DATABRICKS_HOST or DATABRICKS_TOKEN")
            ws = WorkspaceClient(host=host, token=token)
            ws.workspace.list_objects(path="/")
            self.telemetry.record_metric(
                "health.databricks.connected",
                1.0,
                MetricType.GAUGE,
                {"status": "healthy"}
            )
            return True
        except Exception as e:
            self.telemetry.record_event(
                "health_check_failed",
                SeverityLevel.ERROR,
                f"Databricks connection failed: {e}",
                {"component": "databricks"}
            )
            return False

    def check_warehouse_status(self, warehouse_id: str, ws: Any) -> bool:
        """Check Databricks warehouse status"""
        try:
            warehouse = ws.warehouses.get(warehouse_id)
            is_healthy = warehouse.state.value == "RUNNING"
            
            self.telemetry.record_metric(
                "health.warehouse.running",
                1.0 if is_healthy else 0.0,
                MetricType.GAUGE,
                {"warehouse_id": warehouse_id}
            )
            return is_healthy
        except Exception as e:
            self.telemetry.record_event(
                "warehouse_health_check_failed",
                SeverityLevel.WARNING,
                f"Warehouse health check failed: {e}",
                {"warehouse_id": warehouse_id}
            )
            return False

    def check_schema_exists(self, catalog: str, schema: str, ws: Any) -> bool:
        """Check if dbt schema exists"""
        try:
            ws.schemas.get(f"{catalog}.{schema}")
            self.telemetry.record_metric(
                "health.schema.exists",
                1.0,
                MetricType.GAUGE,
                {"catalog": catalog, "schema": schema}
            )
            return True
        except Exception as e:
            self.telemetry.record_event(
                "schema_check_failed",
                SeverityLevel.WARNING,
                f"Schema {catalog}.{schema} not found",
                {"catalog": catalog, "schema": schema}
            )
            return False

    def validate_schema(self, target: str) -> bool:
        """Compatibility wrapper used by deployment scripts."""
        try:
            from databricks.sdk import WorkspaceClient

            host = os.getenv("DATABRICKS_HOST")
            token = os.getenv("DATABRICKS_TOKEN")
            if not host or not token:
                return False

            catalog = os.getenv("CATALOG", "hive_metastore")
            schema_map = {
                "dev": os.getenv("DATA_SCHEMA", "raw"),
                "staging": os.getenv("STAGING_SCHEMA", "staging"),
                "prod": os.getenv("MARTS_SCHEMA", "marts"),
            }
            schema = schema_map.get(target, schema_map["dev"])

            ws = WorkspaceClient(host=host, token=token)
            return self.check_schema_exists(catalog, schema, ws)
        except Exception:
            return False


class PerformanceMonitor:
    """Monitor dbt model performance and query execution"""

    def __init__(self, telemetry: TelemetryClient):
        self.telemetry = telemetry

    def record_model_run(self, model_name: str, execution_time_seconds: float,
                        status: str, rows_affected: int):
        """Record dbt model execution metrics"""
        self.telemetry.record_metric(
            "dbt.model.execution_time",
            execution_time_seconds,
            MetricType.HISTOGRAM,
            {"model": model_name, "status": status}
        )
        
        self.telemetry.record_metric(
            "dbt.model.rows_affected",
            float(rows_affected),
            MetricType.GAUGE,
            {"model": model_name}
        )
        
        # Record event for slow models (threshold: 60 seconds)
        if execution_time_seconds > 60:
            self.telemetry.record_event(
                "slow_model_detected",
                SeverityLevel.WARNING,
                f"Model {model_name} took {execution_time_seconds}s",
                {"model": model_name, "execution_time": execution_time_seconds}
            )

    def record_test_execution(self, test_name: str, passed: bool,
                             execution_time_seconds: float):
        """Record dbt test execution metrics"""
        status = "passed" if passed else "failed"
        self.telemetry.record_metric(
            "dbt.test.execution_time",
            execution_time_seconds,
            MetricType.HISTOGRAM,
            {"test": test_name, "status": status}
        )
        
        if not passed:
            self.telemetry.record_event(
                "test_failure",
                SeverityLevel.ERROR,
                f"Test {test_name} failed",
                {"test": test_name}
            )

    def record_pipeline_execution(self, pipeline_name: str, total_time: float,
                                 models_run: int, tests_passed: int, tests_failed: int):
        """Record overall pipeline execution metrics"""
        self.telemetry.record_metric(
            "pipeline.total_execution_time",
            total_time,
            MetricType.TIMER,
            {"pipeline": pipeline_name}
        )
        
        self.telemetry.record_metric(
            "pipeline.models_executed",
            float(models_run),
            MetricType.GAUGE,
            {"pipeline": pipeline_name}
        )
        
        self.telemetry.record_metric(
            "pipeline.test_failures",
            float(tests_failed),
            MetricType.GAUGE,
            {"pipeline": pipeline_name}
        )
        
        if tests_failed > 0:
            self.telemetry.record_event(
                "pipeline_test_failures",
                SeverityLevel.ERROR,
                f"Pipeline {pipeline_name} had {tests_failed} test failures",
                {
                    "pipeline": pipeline_name,
                    "tests_failed": tests_failed,
                    "tests_passed": tests_passed
                }
            )


# Global telemetry client instance
_telemetry_client: Optional[TelemetryClient] = None


def get_telemetry_client() -> TelemetryClient:
    """Get or create global telemetry client"""
    global _telemetry_client
    if _telemetry_client is None:
        _telemetry_client = TelemetryClient()
    return _telemetry_client


def initialize_telemetry(service_name: str = "dbt-databricks") -> TelemetryClient:
    """Initialize telemetry system"""
    global _telemetry_client
    _telemetry_client = TelemetryClient(service_name)
    return _telemetry_client


def get_health_check() -> HealthCheck:
    """Return a health check helper bound to the global telemetry client."""
    return HealthCheck(get_telemetry_client())
