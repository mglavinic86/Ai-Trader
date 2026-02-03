"""
Watchdog Service - Monitors auto-trading service health and auto-restarts if needed.

The watchdog provides:
1. Heartbeat monitoring (detects frozen/crashed service)
2. Automatic restart on failure
3. Crash loop protection (max restarts per hour)
4. Detailed logging

Usage:
    from src.services.watchdog import Watchdog

    watchdog = Watchdog()
    watchdog.start()  # Blocking - runs forever
"""

import os
import sys
import time
import signal
import subprocess
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from src.services.heartbeat import HeartbeatManager
from src.utils.logger import logger


@dataclass
class RestartEvent:
    """Record of a service restart."""
    timestamp: datetime
    reason: str
    success: bool
    pid: Optional[int] = None


class Watchdog:
    """
    Monitors the auto-trading service and restarts it if needed.

    Features:
    - Checks heartbeat every 30 seconds
    - Restarts service if heartbeat is stale (>120s old)
    - Limits restarts to 5 per hour (crash loop protection)
    - Logs all actions to data/watchdog.log
    """

    # Configuration
    CHECK_INTERVAL_SECONDS = 30
    STALE_THRESHOLD_SECONDS = 120
    MAX_RESTARTS_PER_HOUR = 5
    GRACEFUL_SHUTDOWN_TIMEOUT = 10

    # Paths
    LOG_FILE = Path(__file__).parent.parent.parent / "data" / "watchdog.log"
    STOP_FILE = Path(__file__).parent.parent.parent / "data" / ".stop_watchdog"

    def __init__(self):
        """Initialize watchdog."""
        self._running = False
        self._process: Optional[subprocess.Popen] = None
        self._restart_history: List[RestartEvent] = []
        self._lock = threading.Lock()

        # Ensure data directory exists
        self.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

        self._log("Watchdog initialized")

    def _log(self, message: str, level: str = "INFO") -> None:
        """Log message to file and console."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}"

        # Console
        print(log_line)

        # File
        try:
            with open(self.LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(log_line + "\n")
        except Exception as e:
            print(f"Failed to write log: {e}")

    def _get_recent_restarts(self) -> int:
        """Count restarts in the last hour."""
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        return sum(1 for r in self._restart_history if r.timestamp > one_hour_ago)

    def _can_restart(self) -> bool:
        """Check if we can restart (not exceeding limit)."""
        return self._get_recent_restarts() < self.MAX_RESTARTS_PER_HOUR

    def _check_heartbeat(self) -> Dict[str, Any]:
        """Check heartbeat status."""
        status = HeartbeatManager.get_status()
        return status

    def _start_service(self) -> bool:
        """Start the auto-trading service subprocess."""
        try:
            # Get path to run_auto_trading.py
            script_path = Path(__file__).parent.parent.parent / "run_auto_trading.py"

            if not script_path.exists():
                self._log(f"Script not found: {script_path}", "ERROR")
                return False

            # Start subprocess
            self._process = subprocess.Popen(
                [sys.executable, str(script_path)],
                cwd=str(script_path.parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )

            self._log(f"Started auto-trading service (PID: {self._process.pid})")
            return True

        except Exception as e:
            self._log(f"Failed to start service: {e}", "ERROR")
            return False

    def _stop_service(self, graceful: bool = True) -> bool:
        """Stop the auto-trading service."""
        if not self._process:
            return True

        try:
            # Try graceful shutdown first
            if graceful:
                self._log("Requesting graceful shutdown...")

                # Write stop signal file
                stop_file = Path(__file__).parent.parent.parent / "data" / ".stop_service"
                stop_file.touch()

                # Wait for process to exit
                try:
                    self._process.wait(timeout=self.GRACEFUL_SHUTDOWN_TIMEOUT)
                    self._log("Service stopped gracefully")
                    return True
                except subprocess.TimeoutExpired:
                    self._log("Graceful shutdown timed out, forcing...")

            # Force kill
            if os.name == 'nt':
                self._process.terminate()
            else:
                self._process.send_signal(signal.SIGTERM)

            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()

            self._log("Service forcefully stopped")
            return True

        except Exception as e:
            self._log(f"Error stopping service: {e}", "ERROR")
            return False

    def _restart_service(self, reason: str) -> bool:
        """Restart the auto-trading service."""
        self._log(f"Restarting service: {reason}", "WARNING")

        # Check restart limit
        if not self._can_restart():
            self._log(
                f"RESTART LIMIT REACHED ({self.MAX_RESTARTS_PER_HOUR}/hour). "
                "Manual intervention required.",
                "CRITICAL"
            )
            return False

        # Stop existing process
        self._stop_service(graceful=True)

        # Wait a moment
        time.sleep(2)

        # Start new process
        success = self._start_service()

        # Record restart
        with self._lock:
            self._restart_history.append(RestartEvent(
                timestamp=datetime.now(timezone.utc),
                reason=reason,
                success=success,
                pid=self._process.pid if self._process else None
            ))

        if success:
            self._log(f"Service restarted successfully (restarts this hour: {self._get_recent_restarts()})")
        else:
            self._log("Failed to restart service", "ERROR")

        return success

    def _check_stop_signal(self) -> bool:
        """Check if stop signal file exists."""
        if self.STOP_FILE.exists():
            self.STOP_FILE.unlink()
            return True
        return False

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        consecutive_failures = 0
        last_alive_time = time.time()

        while self._running:
            try:
                # Check for stop signal
                if self._check_stop_signal():
                    self._log("Stop signal received")
                    break

                # Check heartbeat
                status = self._check_heartbeat()

                if status.get("alive"):
                    consecutive_failures = 0
                    last_alive_time = time.time()

                    # Log periodic status
                    self._log(
                        f"Service OK - State: {status.get('state')} | "
                        f"Uptime: {status.get('uptime_human')} | "
                        f"Scans: {status.get('scans_today')} | "
                        f"Trades: {status.get('trades_today')}"
                    )
                else:
                    consecutive_failures += 1
                    age = status.get("heartbeat_age_seconds", "unknown")

                    self._log(
                        f"Service NOT responding (heartbeat age: {age}s, "
                        f"failures: {consecutive_failures})",
                        "WARNING"
                    )

                    # Restart after 2 consecutive failures (60 seconds)
                    if consecutive_failures >= 2:
                        reason = f"Heartbeat stale for {age}s"
                        if not self._restart_service(reason):
                            self._log("Restart failed, will retry next cycle", "ERROR")
                        consecutive_failures = 0

                # Check if process died unexpectedly
                if self._process and self._process.poll() is not None:
                    exit_code = self._process.returncode
                    self._log(f"Process exited unexpectedly (code: {exit_code})", "WARNING")
                    self._process = None

                    if self._running:
                        self._restart_service(f"Process crashed (exit code: {exit_code})")

            except Exception as e:
                self._log(f"Monitor loop error: {e}", "ERROR")

            # Wait for next check
            time.sleep(self.CHECK_INTERVAL_SECONDS)

    def start(self, start_service: bool = True) -> None:
        """
        Start the watchdog.

        Args:
            start_service: Whether to start the auto-trading service
        """
        if self._running:
            self._log("Watchdog already running", "WARNING")
            return

        self._running = True
        self._log("=" * 50)
        self._log("WATCHDOG STARTED")
        self._log("=" * 50)
        self._log(f"Check interval: {self.CHECK_INTERVAL_SECONDS}s")
        self._log(f"Stale threshold: {self.STALE_THRESHOLD_SECONDS}s")
        self._log(f"Max restarts/hour: {self.MAX_RESTARTS_PER_HOUR}")

        # Start auto-trading service
        if start_service:
            if not self._start_service():
                self._log("Failed to start auto-trading service", "ERROR")
                self._running = False
                return

        # Run monitoring loop (blocking)
        try:
            self._monitor_loop()
        except KeyboardInterrupt:
            self._log("Keyboard interrupt received")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the watchdog and service."""
        self._log("Stopping watchdog...")
        self._running = False

        # Stop the service
        self._stop_service(graceful=True)

        self._log("Watchdog stopped")
        self._log("=" * 50)

    def get_status(self) -> Dict[str, Any]:
        """Get watchdog status."""
        return {
            "running": self._running,
            "service_pid": self._process.pid if self._process else None,
            "service_running": self._process is not None and self._process.poll() is None,
            "restarts_this_hour": self._get_recent_restarts(),
            "max_restarts_per_hour": self.MAX_RESTARTS_PER_HOUR,
            "recent_restarts": [
                {
                    "timestamp": r.timestamp.isoformat(),
                    "reason": r.reason,
                    "success": r.success
                }
                for r in self._restart_history[-10:]
            ]
        }


def create_stop_signal() -> None:
    """Create stop signal file to stop watchdog from another process."""
    stop_file = Path(__file__).parent.parent.parent / "data" / ".stop_watchdog"
    stop_file.touch()
    print(f"Stop signal created: {stop_file}")


if __name__ == "__main__":
    # Run watchdog directly
    watchdog = Watchdog()
    watchdog.start()
