"""
AI Trader - Error Monitoring and Alert System

Provides centralized error tracking, health monitoring, and alerting.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path

from loguru import logger


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for tracking."""
    MT5_CONNECTION = "mt5_connection"
    MT5_ORDER = "mt5_order"
    API_ERROR = "api_error"
    DATABASE = "database"
    ANALYSIS = "analysis"
    CONFIG = "config"
    UNKNOWN = "unknown"


@dataclass
class ErrorRecord:
    """Single error record."""
    timestamp: str
    category: str
    message: str
    context: Dict[str, Any]
    resolved: bool = False


@dataclass
class Alert:
    """Alert record."""
    timestamp: str
    level: str
    message: str
    source: str
    acknowledged: bool = False


@dataclass
class HealthStatus:
    """System health status."""
    healthy: bool
    mt5_connected: bool
    database_ok: bool
    last_check: str
    issues: List[str]
    warnings: List[str]


class ErrorTracker:
    """
    Tracks and manages application errors.

    Stores errors in a JSON file for persistence and provides
    methods for querying and analyzing error patterns.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize error tracker."""
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data"

        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.errors_file = self.data_dir / "errors.json"
        self._load_errors()

    def _load_errors(self) -> None:
        """Load errors from file."""
        if self.errors_file.exists():
            try:
                with open(self.errors_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.errors = [ErrorRecord(**e) for e in data]
            except Exception as e:
                logger.error(f"Failed to load errors file: {e}")
                self.errors = []
        else:
            self.errors = []

    def _save_errors(self) -> None:
        """Save errors to file."""
        try:
            with open(self.errors_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(e) for e in self.errors], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save errors file: {e}")

    def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        category: ErrorCategory = ErrorCategory.UNKNOWN
    ) -> ErrorRecord:
        """
        Log an error with context.

        Args:
            error: The exception that occurred
            context: Additional context information
            category: Error category for grouping

        Returns:
            The created ErrorRecord
        """
        record = ErrorRecord(
            timestamp=datetime.now().isoformat(),
            category=category.value,
            message=str(error),
            context=context or {},
            resolved=False
        )

        self.errors.append(record)
        self._save_errors()

        # Also log to standard logger
        logger.error(f"[{category.value}] {error}", extra=context or {})

        return record

    def get_recent_errors(self, hours: int = 24) -> List[ErrorRecord]:
        """
        Get errors from the last N hours.

        Args:
            hours: Number of hours to look back

        Returns:
            List of recent errors
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        cutoff_str = cutoff.isoformat()

        return [
            e for e in self.errors
            if e.timestamp >= cutoff_str
        ]

    def get_error_summary(self) -> Dict[str, Any]:
        """
        Get error statistics summary.

        Returns:
            Dictionary with error counts by category and time period
        """
        now = datetime.now()

        # Count by category
        by_category = {}
        for e in self.errors:
            cat = e.category
            by_category[cat] = by_category.get(cat, 0) + 1

        # Count by time period
        last_hour = (now - timedelta(hours=1)).isoformat()
        last_24h = (now - timedelta(hours=24)).isoformat()
        last_7d = (now - timedelta(days=7)).isoformat()

        return {
            "total": len(self.errors),
            "unresolved": len([e for e in self.errors if not e.resolved]),
            "by_category": by_category,
            "last_hour": len([e for e in self.errors if e.timestamp >= last_hour]),
            "last_24h": len([e for e in self.errors if e.timestamp >= last_24h]),
            "last_7d": len([e for e in self.errors if e.timestamp >= last_7d]),
        }

    def resolve_error(self, timestamp: str) -> bool:
        """Mark an error as resolved."""
        for e in self.errors:
            if e.timestamp == timestamp:
                e.resolved = True
                self._save_errors()
                return True
        return False

    def clear_old_errors(self, days: int = 30) -> int:
        """
        Remove errors older than N days.

        Args:
            days: Number of days to keep

        Returns:
            Number of errors removed
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        original_count = len(self.errors)
        self.errors = [e for e in self.errors if e.timestamp >= cutoff]
        self._save_errors()
        return original_count - len(self.errors)

    def check_health(self) -> HealthStatus:
        """
        Check overall system health.

        Returns:
            HealthStatus with current system state
        """
        issues = []
        warnings = []
        mt5_connected = False
        database_ok = False

        # Check MT5 connection - actually try to get account data
        try:
            from src.trading.mt5_client import MT5Client
            client = MT5Client()
            # Actually try to fetch account info to verify connection
            account = client.get_account()
            if account and account.get('balance', 0) > 0:
                mt5_connected = True
            else:
                mt5_connected = False
                issues.append("MT5 returned invalid account data")
        except Exception as e:
            mt5_connected = False
            issues.append(f"MT5 not connected: {str(e)[:50]}")

        # Check database
        try:
            from src.utils.database import Database
            db = Database()
            # Simple connection test - just instantiating is enough
            # The __init__ calls _init_tables which verifies DB access
            database_ok = True
        except Exception as e:
            issues.append(f"Database error: {e}")

        # Check recent error rate
        recent = self.get_recent_errors(hours=1)
        if len(recent) > 10:
            warnings.append(f"High error rate: {len(recent)} errors in last hour")
        elif len(recent) > 5:
            warnings.append(f"Elevated error rate: {len(recent)} errors in last hour")

        # Check for repeated errors
        summary = self.get_error_summary()
        for cat, count in summary.get("by_category", {}).items():
            if count > 20:
                warnings.append(f"Many {cat} errors: {count} total")

        healthy = len(issues) == 0 and mt5_connected and database_ok

        return HealthStatus(
            healthy=healthy,
            mt5_connected=mt5_connected,
            database_ok=database_ok,
            last_check=datetime.now().isoformat(),
            issues=issues,
            warnings=warnings
        )


class AlertManager:
    """
    Manages system alerts and notifications.

    Currently logs alerts to file. Can be extended to support
    email, SMS, or push notifications.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize alert manager."""
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data"

        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.alerts_file = self.data_dir / "alerts.json"
        self._load_alerts()

    def _load_alerts(self) -> None:
        """Load alerts from file."""
        if self.alerts_file.exists():
            try:
                with open(self.alerts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.alerts = [Alert(**a) for a in data]
            except Exception as e:
                logger.error(f"Failed to load alerts file: {e}")
                self.alerts = []
        else:
            self.alerts = []

    def _save_alerts(self) -> None:
        """Save alerts to file."""
        try:
            with open(self.alerts_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(a) for a in self.alerts], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save alerts file: {e}")

    def send_alert(
        self,
        level: AlertLevel,
        message: str,
        source: str = "system"
    ) -> Alert:
        """
        Send an alert.

        Currently logs to file. Future: email, SMS, push.

        Args:
            level: Alert severity level
            message: Alert message
            source: Source of the alert

        Returns:
            The created Alert
        """
        alert = Alert(
            timestamp=datetime.now().isoformat(),
            level=level.value,
            message=message,
            source=source,
            acknowledged=False
        )

        self.alerts.append(alert)
        self._save_alerts()

        # Log based on level
        if level == AlertLevel.CRITICAL:
            logger.critical(f"[ALERT] {message}")
        elif level == AlertLevel.ERROR:
            logger.error(f"[ALERT] {message}")
        elif level == AlertLevel.WARNING:
            logger.warning(f"[ALERT] {message}")
        else:
            logger.info(f"[ALERT] {message}")

        return alert

    def check_critical_conditions(
        self,
        account: Optional[Dict[str, Any]] = None,
        positions: Optional[List[Dict[str, Any]]] = None,
        config: Optional[Any] = None
    ) -> List[Alert]:
        """
        Check for critical conditions and generate alerts.

        Args:
            account: Account information from MT5
            positions: List of open positions
            config: Trading configuration

        Returns:
            List of alerts generated
        """
        alerts = []

        # Check MT5 connection
        try:
            from src.trading.mt5_client import MT5Client
            client = MT5Client()
            if not client.is_connected():
                alert = self.send_alert(
                    AlertLevel.CRITICAL,
                    "MT5 disconnected - cannot execute trades",
                    "mt5_monitor"
                )
                alerts.append(alert)
        except Exception as e:
            alert = self.send_alert(
                AlertLevel.ERROR,
                f"Cannot check MT5 status: {e}",
                "mt5_monitor"
            )
            alerts.append(alert)

        # Check account conditions
        if account:
            # Daily loss check
            if config:
                daily_limit = getattr(config, 'MAX_DAILY_DRAWDOWN_PCT', 0.03)
                # Calculate daily PnL (simplified - would need daily starting balance)
                balance = account.get('balance', 0)
                equity = account.get('equity', 0)
                if balance > 0:
                    current_drawdown = (balance - equity) / balance
                    if current_drawdown > daily_limit:
                        alert = self.send_alert(
                            AlertLevel.CRITICAL,
                            f"Daily loss limit exceeded: {current_drawdown:.1%} > {daily_limit:.1%}",
                            "risk_monitor"
                        )
                        alerts.append(alert)
                    elif current_drawdown > daily_limit * 0.8:
                        alert = self.send_alert(
                            AlertLevel.WARNING,
                            f"Approaching daily loss limit: {current_drawdown:.1%}",
                            "risk_monitor"
                        )
                        alerts.append(alert)

            # Margin level check
            margin_level = account.get('margin_level', 0)
            if margin_level > 0:
                if margin_level < 100:
                    alert = self.send_alert(
                        AlertLevel.CRITICAL,
                        f"Margin call warning! Level: {margin_level:.0f}%",
                        "risk_monitor"
                    )
                    alerts.append(alert)
                elif margin_level < 150:
                    alert = self.send_alert(
                        AlertLevel.WARNING,
                        f"Low margin level: {margin_level:.0f}%",
                        "risk_monitor"
                    )
                    alerts.append(alert)

        # Check for positions in significant loss
        if positions:
            for pos in positions:
                pnl = pos.get('unrealized_pl', 0)
                if pnl < -100:  # > 100 EUR loss
                    alert = self.send_alert(
                        AlertLevel.WARNING,
                        f"Position {pos.get('instrument', 'Unknown')} in significant loss: {pnl:.2f}",
                        "position_monitor"
                    )
                    alerts.append(alert)

        # Check error rate
        tracker = ErrorTracker(self.data_dir)
        recent_errors = tracker.get_recent_errors(hours=1)
        if len(recent_errors) > 10:
            alert = self.send_alert(
                AlertLevel.ERROR,
                f"High error rate: {len(recent_errors)} errors in last hour",
                "error_monitor"
            )
            alerts.append(alert)

        return alerts

    def get_recent_alerts(self, hours: int = 24) -> List[Alert]:
        """Get alerts from the last N hours."""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        return [a for a in self.alerts if a.timestamp >= cutoff]

    def get_unacknowledged(self) -> List[Alert]:
        """Get all unacknowledged alerts."""
        return [a for a in self.alerts if not a.acknowledged]

    def acknowledge_alert(self, timestamp: str) -> bool:
        """Mark an alert as acknowledged."""
        for a in self.alerts:
            if a.timestamp == timestamp:
                a.acknowledged = True
                self._save_alerts()
                return True
        return False

    def acknowledge_all(self) -> int:
        """Acknowledge all unacknowledged alerts."""
        count = 0
        for a in self.alerts:
            if not a.acknowledged:
                a.acknowledged = True
                count += 1
        self._save_alerts()
        return count

    def clear_old_alerts(self, days: int = 7) -> int:
        """Remove alerts older than N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        original_count = len(self.alerts)
        self.alerts = [a for a in self.alerts if a.timestamp >= cutoff]
        self._save_alerts()
        return original_count - len(self.alerts)


# Convenience functions for quick access
def log_error(error: Exception, context: Optional[Dict] = None, category: str = "unknown") -> None:
    """Quick function to log an error."""
    tracker = ErrorTracker()
    cat = ErrorCategory(category) if category in [e.value for e in ErrorCategory] else ErrorCategory.UNKNOWN
    tracker.log_error(error, context, cat)


def send_alert(level: str, message: str, source: str = "system") -> None:
    """Quick function to send an alert."""
    manager = AlertManager()
    lvl = AlertLevel(level) if level in [l.value for l in AlertLevel] else AlertLevel.INFO
    manager.send_alert(lvl, message, source)


def check_system_health() -> Dict[str, Any]:
    """Quick function to check system health."""
    tracker = ErrorTracker()
    health = tracker.check_health()
    return asdict(health)
