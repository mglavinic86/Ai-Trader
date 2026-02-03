"""
Heartbeat Manager - Keeps track of service health for 24/7 operation.

The heartbeat system provides:
1. Regular heartbeat writes (proves service is alive)
2. Health metrics tracking
3. Stale detection (service frozen/crashed)
4. Activity logging for monitoring

Usage:
    from src.services.heartbeat import heartbeat_manager

    # In main loop:
    heartbeat_manager.beat()

    # Check if alive from another process:
    if heartbeat_manager.is_alive():
        print("Service is running")
"""

import json
import time
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

from src.utils.logger import logger


@dataclass
class HeartbeatData:
    """Heartbeat data structure."""
    timestamp: str  # ISO format
    unix_time: float
    pid: int
    state: str
    scans_today: int = 0
    trades_today: int = 0
    errors_today: int = 0
    last_scan: Optional[str] = None
    last_trade: Optional[str] = None
    uptime_seconds: float = 0
    memory_mb: float = 0
    version: str = "1.0.0"


class HeartbeatManager:
    """
    Manages service heartbeat for monitoring and auto-recovery.

    Writes heartbeat to a JSON file at regular intervals.
    Another process (watchdog) can monitor this file.
    """

    # Heartbeat file location
    HEARTBEAT_FILE = Path(__file__).parent.parent.parent / "data" / ".heartbeat.json"

    # Consider service dead if no heartbeat for this long
    STALE_THRESHOLD_SECONDS = 120  # 2 minutes

    # Normal heartbeat interval
    BEAT_INTERVAL_SECONDS = 10

    def __init__(self):
        """Initialize heartbeat manager."""
        self._start_time = time.time()
        self._last_beat_time = 0
        self._state = "INITIALIZING"
        self._stats = {
            "scans_today": 0,
            "trades_today": 0,
            "errors_today": 0,
            "last_scan": None,
            "last_trade": None
        }
        self._lock = threading.Lock()
        self._running = False
        self._beat_thread: Optional[threading.Thread] = None

        # Ensure data directory exists
        self.HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)

    def start_background_beats(self) -> None:
        """Start automatic heartbeat in background thread."""
        if self._running:
            return

        self._running = True
        self._beat_thread = threading.Thread(target=self._background_beat_loop, daemon=True)
        self._beat_thread.start()
        logger.info("Heartbeat background thread started")

    def stop_background_beats(self) -> None:
        """Stop background heartbeat thread."""
        self._running = False
        if self._beat_thread:
            self._beat_thread.join(timeout=5)
        logger.info("Heartbeat background thread stopped")

    def _background_beat_loop(self) -> None:
        """Background thread that sends regular heartbeats."""
        while self._running:
            try:
                self.beat()
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
            time.sleep(self.BEAT_INTERVAL_SECONDS)

    def beat(self, state: Optional[str] = None) -> None:
        """
        Record a heartbeat.

        Args:
            state: Optional state override (e.g., "SCANNING", "EXECUTING")
        """
        import os

        now = datetime.now(timezone.utc)

        with self._lock:
            if state:
                self._state = state

            # Get memory usage
            try:
                import psutil
                process = psutil.Process(os.getpid())
                memory_mb = process.memory_info().rss / 1024 / 1024
            except ImportError:
                memory_mb = 0

            data = HeartbeatData(
                timestamp=now.isoformat(),
                unix_time=time.time(),
                pid=os.getpid(),
                state=self._state,
                scans_today=self._stats["scans_today"],
                trades_today=self._stats["trades_today"],
                errors_today=self._stats["errors_today"],
                last_scan=self._stats["last_scan"],
                last_trade=self._stats["last_trade"],
                uptime_seconds=time.time() - self._start_time,
                memory_mb=memory_mb
            )

            self._last_beat_time = time.time()

        # Write to file atomically
        try:
            temp_file = self.HEARTBEAT_FILE.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(asdict(data), f, indent=2)
            temp_file.replace(self.HEARTBEAT_FILE)
        except Exception as e:
            logger.error(f"Failed to write heartbeat: {e}")

    def update_state(self, state: str) -> None:
        """Update service state."""
        with self._lock:
            self._state = state

    def update_stats(self,
                    scans: Optional[int] = None,
                    trades: Optional[int] = None,
                    errors: Optional[int] = None,
                    last_scan: Optional[datetime] = None,
                    last_trade: Optional[datetime] = None) -> None:
        """Update statistics."""
        with self._lock:
            if scans is not None:
                self._stats["scans_today"] = scans
            if trades is not None:
                self._stats["trades_today"] = trades
            if errors is not None:
                self._stats["errors_today"] = errors
            if last_scan:
                self._stats["last_scan"] = last_scan.isoformat()
            if last_trade:
                self._stats["last_trade"] = last_trade.isoformat()

    def increment_scans(self) -> None:
        """Increment scan counter."""
        with self._lock:
            self._stats["scans_today"] += 1
            self._stats["last_scan"] = datetime.now(timezone.utc).isoformat()

    def increment_trades(self) -> None:
        """Increment trade counter."""
        with self._lock:
            self._stats["trades_today"] += 1
            self._stats["last_trade"] = datetime.now(timezone.utc).isoformat()

    def increment_errors(self) -> None:
        """Increment error counter."""
        with self._lock:
            self._stats["errors_today"] += 1

    def reset_daily_stats(self) -> None:
        """Reset daily statistics (call at midnight)."""
        with self._lock:
            self._stats["scans_today"] = 0
            self._stats["trades_today"] = 0
            self._stats["errors_today"] = 0
        logger.info("Heartbeat daily stats reset")

    def get_uptime(self) -> timedelta:
        """Get service uptime."""
        return timedelta(seconds=time.time() - self._start_time)

    @classmethod
    def read_heartbeat(cls) -> Optional[HeartbeatData]:
        """
        Read heartbeat data from file.

        Can be called from any process to check service status.

        Returns:
            HeartbeatData if file exists, None otherwise
        """
        try:
            if not cls.HEARTBEAT_FILE.exists():
                return None

            with open(cls.HEARTBEAT_FILE, 'r') as f:
                data = json.load(f)

            return HeartbeatData(**data)
        except Exception as e:
            logger.error(f"Failed to read heartbeat: {e}")
            return None

    @classmethod
    def is_alive(cls, threshold_seconds: Optional[int] = None) -> bool:
        """
        Check if the service is alive based on heartbeat.

        Args:
            threshold_seconds: Custom stale threshold

        Returns:
            True if heartbeat is recent enough
        """
        threshold = threshold_seconds or cls.STALE_THRESHOLD_SECONDS

        heartbeat = cls.read_heartbeat()
        if not heartbeat:
            return False

        age = time.time() - heartbeat.unix_time
        return age < threshold

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """
        Get detailed service status from heartbeat.

        Returns:
            Status dictionary
        """
        heartbeat = cls.read_heartbeat()

        if not heartbeat:
            return {
                "alive": False,
                "reason": "No heartbeat file found"
            }

        age = time.time() - heartbeat.unix_time
        alive = age < cls.STALE_THRESHOLD_SECONDS

        return {
            "alive": alive,
            "state": heartbeat.state,
            "pid": heartbeat.pid,
            "uptime_seconds": heartbeat.uptime_seconds,
            "uptime_human": str(timedelta(seconds=int(heartbeat.uptime_seconds))),
            "last_heartbeat": heartbeat.timestamp,
            "heartbeat_age_seconds": round(age, 1),
            "scans_today": heartbeat.scans_today,
            "trades_today": heartbeat.trades_today,
            "errors_today": heartbeat.errors_today,
            "last_scan": heartbeat.last_scan,
            "last_trade": heartbeat.last_trade,
            "memory_mb": round(heartbeat.memory_mb, 1)
        }

    @classmethod
    def clear_heartbeat(cls) -> None:
        """Remove heartbeat file (service stopped)."""
        try:
            if cls.HEARTBEAT_FILE.exists():
                cls.HEARTBEAT_FILE.unlink()
        except Exception as e:
            logger.error(f"Failed to clear heartbeat: {e}")


# Global instance
heartbeat_manager = HeartbeatManager()
