"""
Heimdall - Alert Manager Service

Background service that monitors events and sends Telegram alerts based on configured thresholds.
Runs independently from the dashboard to provide reliable alert delivery.

Thresholds:
- Critical severity: Configurable via database (default: 4+)
- Host inactive timeout: Configurable via database (default: 15 minutes)
- Quiet hours: Optional quiet period to reduce alert spam
"""

import time
import os
import threading
from datetime import datetime, timedelta

try:
    from .database_pg import (
        check_alert_sent, record_alert_sent, get_all_events,
        get_host_status, get_config
    )
    from .telegram_alerts import send_critical_event_alert, send_host_down_alert
except ImportError:
    print("Error: Required modules not available")
    exit(1)

# Default check interval (can remain static as it controls the loop sleep)
ALERT_CHECK_INTERVAL_SECONDS = int(os.getenv("ALERT_CHECK_INTERVAL", "60"))

class AlertManager:
    """Background service for managing security alerts."""

    def __init__(self):
        self.running = False
        self.last_event_check_time = None
        self.thread = None

    # Helpers to get dynamic config from DB
    def get_severity_threshold(self) -> int:
        return int(get_config("ALERT_SEVERITY_THRESHOLD", os.getenv("ALERT_SEVERITY_THRESHOLD", "4")))

    def get_inactive_threshold(self) -> int:
        return int(get_config("ALERT_INACTIVE_THRESHOLD", os.getenv("ALERT_INACTIVE_THRESHOLD", "15")))

    def get_alerts_enabled(self) -> bool:
        val = get_config("ENABLE_TELEGRAM_ALERTS", os.getenv("ENABLE_TELEGRAM_ALERTS", "true"))
        return str(val).lower() == "true"

    def get_quiet_hours(self) -> str:
        return get_config("ALERT_QUIET_HOURS", os.getenv("ALERT_QUIET_HOURS", ""))

    def is_quiet_hour(self) -> bool:
        """Check if current time falls within quiet hours."""
        quiet_hours = self.get_quiet_hours()
        if not quiet_hours or "-" not in quiet_hours:
            return False

        try:
            start_str, end_str = quiet_hours.split("-")
            start_hour, start_min = map(int, start_str.split(":"))
            end_hour, end_min = map(int, end_str.split(":"))

            now = datetime.now()
            current_minutes = now.hour * 60 + now.minute
            start_minutes = start_hour * 60 + start_min
            end_minutes = end_hour * 60 + end_min

            if start_minutes < end_minutes:
                # Normal case: 22:00-06:00 doesn't wrap midnight
                return start_minutes <= current_minutes < end_minutes
            else:
                # Wraps midnight: 22:00-06:00
                return current_minutes >= start_minutes or current_minutes < end_minutes
        except Exception as e:
            print(f"Error parsing quiet hours: {e}")
            return False

    def check_critical_events(self):
        """Check for and alert on critical events."""
        if not self.get_alerts_enabled():
            return

        try:
            threshold = self.get_severity_threshold()
            # Get recent events (last 10 minutes)
            events = get_all_events(limit=100)

            for event in events:
                severity = event.get("severity", 0)

                # Check if meets critical threshold and hasn't been alerted
                if severity >= threshold:
                    event_id = event.get("event_id", "")

                    if event_id and not check_alert_sent(event_id, "critical"):
                        # Skip if in quiet hours
                        if self.is_quiet_hour():
                            print(f"[QUIET HOURS] Suppressing alert for event {event_id}")
                            continue

                        # Send alert
                        if send_critical_event_alert(event):
                            print(f"[✓] Alert sent for critical event: {event_id}")
                            record_alert_sent(event_id, "critical")
                        else:
                            print(f"[✗] Failed to send alert for event: {event_id}")

        except Exception as e:
            print(f"Error checking critical events: {e}")

    def check_inactive_hosts(self):
        """Check for and alert on inactive hosts."""
        if not self.get_alerts_enabled():
            return

        try:
            threshold_mins = self.get_inactive_threshold()
            host_status = get_host_status(inactive_threshold_minutes=threshold_mins)

            for host in host_status.get("inactive", []):
                hostname = host.get("hostname", "")
                event_id = f"host-down-{hostname}"

                if not check_alert_sent(event_id, "host_down"):
                    # Skip if in quiet hours
                    if self.is_quiet_hour():
                        print(f"[QUIET HOURS] Suppressing host-down alert for {hostname}")
                        continue

                    # Send alert
                    if send_host_down_alert(hostname, host.get("os_type", "UNKNOWN"), host.get("last_seen", "")):
                        print(f"[✓] Alert sent for inactive host: {hostname}")
                        record_alert_sent(event_id, "host_down")
                    else:
                        print(f"[✗] Failed to send host-down alert for: {hostname}")

        except Exception as e:
            print(f"Error checking inactive hosts: {e}")

    def run(self):
        """Main alert manager loop."""
        self.running = True
        print("[✓] Alert Manager started")
        print(f"    Check interval: {ALERT_CHECK_INTERVAL_SECONDS} seconds")

        while self.running:
            try:
                self.check_critical_events()
                self.check_inactive_hosts()

                # Wait before next check
                time.sleep(ALERT_CHECK_INTERVAL_SECONDS)

            except Exception as e:
                print(f"Error in alert manager loop: {e}")
                time.sleep(ALERT_CHECK_INTERVAL_SECONDS)

    def start_background(self):
        """Start the alert manager in a background thread."""
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the alert manager."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("[✓] Alert Manager stopped")


# Global instance
alert_manager = None

def start_alert_manager():
    """Initialize and start the global alert manager."""
    global alert_manager
    if alert_manager is None:
        alert_manager = AlertManager()
        alert_manager.start_background()
    return alert_manager

if __name__ == "__main__":
    manager = AlertManager()
    try:
        manager.run()
    except KeyboardInterrupt:
        print("\nShutting down...")
        manager.stop()
