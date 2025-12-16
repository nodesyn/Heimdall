"""
Heimdall - Telegram Alert Module

Sends security alerts to Telegram channel for real-time notifications.
"""

import requests
import os
from datetime import datetime

# Try to import database functions for alert deduplication
try:
    from .database_pg import check_alert_sent, record_alert_sent
    HAS_DB = True
except ImportError:
    HAS_DB = False

# Telegram configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"


def send_alert(title: str, details: dict, severity: int = 3) -> bool:
    """
    Send an alert to Telegram channel.

    Args:
        title: Alert title/heading
        details: Dictionary with event details
        severity: Event severity level (1-5)

    Returns:
        bool: True if successful, False otherwise
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram not configured - skipping alert")
        return False

    try:
        # Format severity as emoji
        severity_emoji = {
            1: "ℹ️",  # Info
            2: "⚠️",  # Low
            3: "🟠",  # Medium
            4: "🔴",  # High
            5: "🚨",  # Critical
        }.get(severity, "⚠️")

        # Build message
        message = f"{severity_emoji} *{title}*\n\n"

        # Add event details
        for key, value in details.items():
            if key in ["source_host", "os_type", "event_type", "source_ip", "user"]:
                if key == "event_type":
                    message += f"📋 *Type*: `{value}`\n"
                elif key == "source_host":
                    message += f"🖥️ *Host*: `{value}`\n"
                elif key == "os_type":
                    message += f"🐧 *OS*: `{value}`\n"
                elif key == "source_ip":
                    message += f"🌐 *Source IP*: `{value}`\n"
                elif key == "user":
                    message += f"👤 *User*: `{value}`\n"

        # Add raw message if available
        if "raw_message" in details:
            raw = details["raw_message"]
            # Truncate if too long
            if len(raw) > 200:
                raw = raw[:197] + "..."
            message += f"\n📝 *Details*: ```\n{raw}\n```"

        # Add timestamp
        message += f"\n⏰ *Time*: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"

        # Send to Telegram
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
        }

        response = requests.post(TELEGRAM_API_URL, json=payload, timeout=10)

        if response.status_code == 200:
            return True
        else:
            print(f"Telegram API error: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"Error sending Telegram alert: {e}")
        return False


def send_host_down_alert(hostname: str, os_type: str, last_seen: str) -> bool:
    """Send alert when host goes inactive."""
    # Use hostname as event_id for deduplication
    event_id = f"host-down-{hostname}"

    # Check if already sent to prevent duplicates
    if HAS_DB and check_alert_sent(event_id, "host_down"):
        return False

    details = {
        "source_host": hostname,
        "os_type": os_type,
        "last_seen": last_seen,
        "event_type": "HOST_OFFLINE",
    }
    result = send_alert(f"🚨 Host Offline: {hostname}", details, severity=4)

    # Record alert if successfully sent
    if result and HAS_DB:
        record_alert_sent(event_id, "host_down")

    return result


def send_critical_event_alert(event: dict) -> bool:
    """Send alert for critical security events."""
    event_id = event.get("event_id", "")

    # Check if already sent to prevent duplicates
    if HAS_DB and event_id and check_alert_sent(event_id, "critical"):
        return False

    title = f"🔴 {event.get('event_type', 'CRITICAL_EVENT')}"
    result = send_alert(title, event, severity=event.get("severity", 4))

    # Record alert if successfully sent
    if result and HAS_DB and event_id:
        record_alert_sent(event_id, "critical")

    return result


def send_attack_pattern_alert(attacker_ip: str, attempt_count: int) -> bool:
    """Send alert for repeated attack patterns."""
    details = {
        "source_ip": attacker_ip,
        "event_type": "ATTACK_PATTERN",
        "raw_message": f"Multiple failed login attempts detected from {attacker_ip} ({attempt_count} attempts)",
    }
    return send_alert(f"🚨 Attack Pattern Detected: {attacker_ip}", details, severity=4)
