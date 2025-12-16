"""
Heimdall - Database Layer

SQLite database management for Heimdall.
Uses WAL mode for concurrent read/write support.
Provides unified query interface for all event data.
"""

import sqlite3
import os
from datetime import datetime, timezone
from pathlib import Path

# Get database path from environment variable, default to mini_siem.db
DATABASE_PATH = os.getenv("SIEM_DATABASE_PATH", "mini_siem.db")


def init_database():
    """Initialize the SQLite database with WAL mode and create the logs table."""
    
    # Ensure directory exists
    db_path = Path(DATABASE_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Enable WAL mode for better concurrency
    cursor.execute("PRAGMA journal_mode=WAL")
    
    # Create logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT UNIQUE NOT NULL,
            timestamp TEXT NOT NULL,
            source_host TEXT NOT NULL,
            os_type TEXT NOT NULL,
            event_type TEXT NOT NULL,
            severity INTEGER NOT NULL,
            source_ip TEXT NOT NULL,
            user TEXT NOT NULL,
            raw_message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indices for fast queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp ON logs(timestamp DESC)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_event_type ON logs(event_type)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_source_ip ON logs(source_ip)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_os_type ON logs(os_type)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_severity ON logs(severity)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp_ostype ON logs(timestamp DESC, os_type)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_source_ip_count ON logs(source_ip)
    """)
    
    # Create heartbeat table for agent status tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS heartbeats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_host TEXT NOT NULL UNIQUE,
            os_type TEXT NOT NULL,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_heartbeat_host ON heartbeats(source_host)
    """)
    
    conn.commit()
    conn.close()
    
    print(f"Database initialized at {DATABASE_PATH}")


def insert_event(event_dict: dict) -> bool:
    """
    Insert a single event into the database.
    
    Args:
        event_dict: Dictionary with event data
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO logs (
                event_id, timestamp, source_host, os_type, event_type,
                severity, source_ip, user, raw_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_dict["event_id"],
            event_dict["timestamp"],
            event_dict["source_host"],
            event_dict["os_type"],
            event_dict["event_type"],
            event_dict["severity"],
            event_dict["source_ip"],
            event_dict["user"],
            event_dict["raw_message"]
        ))
        
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Duplicate event_id
        return False
    except Exception as e:
        print(f"Error inserting event: {e}")
        return False


def insert_events_batch(events: list[dict]) -> tuple[int, int]:
    """
    Insert multiple events efficiently in a single batch.

    Args:
        events: List of event dictionaries

    Returns:
        tuple: (inserted_count, failed_count)
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        inserted = 0
        failed = 0

        for event_dict in events:
            try:
                cursor.execute("""
                    INSERT INTO logs (
                        event_id, timestamp, source_host, os_type, event_type,
                        severity, source_ip, user, raw_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_dict["event_id"],
                    event_dict["timestamp"],
                    event_dict["source_host"],
                    event_dict["os_type"],
                    event_dict["event_type"],
                    event_dict["severity"],
                    event_dict["source_ip"],
                    event_dict["user"],
                    event_dict["raw_message"]
                ))
                inserted += 1
            except sqlite3.IntegrityError:
                failed += 1
            except Exception as e:
                failed += 1

        conn.commit()
        conn.close()
        return (inserted, failed)
    except Exception as e:
        print(f"Error inserting batch: {e}")
        return (0, len(events))


def get_all_events(limit: int = 1000) -> list[dict]:
    """Get recent events from the database."""
    try:
        # Open in read-only mode to avoid locking
        conn = sqlite3.connect(f"file:{DATABASE_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM logs 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error retrieving events: {e}")
        return []


def get_events_by_filter(os_type: str = None, severity: int = None,
                         event_type: str = None, limit: int = 1000,
                         severity_min: int = None, source_ip: str = None,
                         user: str = None, source_host: str = None,
                         raw_message: str = None, start_date: str = None,
                         end_date: str = None, offset: int = 0) -> dict:
    """Get events with optional filters and pagination.

    Args:
        os_type: Filter by OS type (exact match)
        severity: Filter by exact severity level
        severity_min: Filter by minimum severity level
        event_type: Filter by event type (exact match)
        source_ip: Filter by source IP (exact match)
        user: Filter by username (case-insensitive partial match)
        source_host: Filter by source hostname (exact match)
        raw_message: Filter by raw message content (case-insensitive)
        start_date: Filter events on/after this date (ISO format: YYYY-MM-DD)
        end_date: Filter events on/before this date (ISO format: YYYY-MM-DD)
        limit: Maximum number of events to return (default 1000)
        offset: Number of events to skip for pagination (default 0)

    Returns:
        Dictionary with 'events' list, 'total_count', 'offset', and 'limit'
    """
    try:
        # Open in read-only mode to avoid locking
        conn = sqlite3.connect(f"file:{DATABASE_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Build WHERE clause
        query = "SELECT * FROM logs WHERE 1=1"
        params = []

        if os_type:
            query += " AND os_type = ?"
            params.append(os_type)
        if severity is not None:
            query += " AND severity = ?"
            params.append(severity)
        if severity_min is not None:
            query += " AND severity >= ?"
            params.append(severity_min)
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        if source_ip:
            query += " AND source_ip = ?"
            params.append(source_ip)
        if user:
            query += " AND LOWER(user) LIKE ?"
            params.append(f"%{user.lower()}%")
        if source_host:
            query += " AND source_host = ?"
            params.append(source_host)
        if raw_message:
            query += " AND LOWER(raw_message) LIKE ?"
            params.append(f"%{raw_message.lower()}%")
        if start_date:
            query += " AND timestamp >= ?"
            params.append(f"{start_date} 00:00:00")
        if end_date:
            query += " AND timestamp <= ?"
            params.append(f"{end_date} 23:59:59")

        # Get total count before pagination
        count_query = query.replace("SELECT *", "SELECT COUNT(*) as cnt")
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()['cnt']

        # Add ordering and pagination
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.append(limit)
        params.append(offset)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return {
            'events': [dict(row) for row in rows],
            'total_count': total_count,
            'offset': offset,
            'limit': limit
        }
    except Exception as e:
        print(f"Error retrieving filtered events: {e}")
        return {'events': [], 'total_count': 0, 'offset': offset, 'limit': limit}


def get_metrics_24h() -> dict:
    """Get metrics for the last 24 hours."""
    try:
        # Open in read-only mode to avoid locking
        conn = sqlite3.connect(f"file:{DATABASE_PATH}?mode=ro", uri=True)
        cursor = conn.cursor()

        # Set a timeout for queries
        cursor.execute("PRAGMA busy_timeout = 5000")

        # Total alerts in last 24 hours
        cursor.execute("""
            SELECT COUNT(*) as count FROM logs 
            WHERE datetime(timestamp) >= datetime('now', '-24 hours')
        """)
        total_alerts = cursor.fetchone()[0]
        
        # Threats by OS
        cursor.execute("""
            SELECT os_type, COUNT(*) as count FROM logs 
            WHERE datetime(timestamp) >= datetime('now', '-24 hours')
            GROUP BY os_type
        """)
        threats_by_os = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Most blocked domain (from DNS_BLOCK events)
        cursor.execute("""
            SELECT raw_message, COUNT(*) as count FROM logs 
            WHERE event_type = 'DNS_BLOCK' 
            AND datetime(timestamp) >= datetime('now', '-24 hours')
            GROUP BY raw_message 
            ORDER BY count DESC 
            LIMIT 1
        """)
        result = cursor.fetchone()
        most_blocked_domain = result[0] if result else None
        
        conn.close()
        
        return {
            "total_alerts_24h": total_alerts,
            "threats_by_os": threats_by_os,
            "most_blocked_domain": most_blocked_domain
        }
    except Exception as e:
        print(f"Error calculating metrics: {e}")
        return {
            "total_alerts_24h": 0,
            "threats_by_os": {},
            "most_blocked_domain": None
        }


def get_top_attacking_ips(limit: int = 10) -> list[tuple[str, int]]:
    """Get top attacking IPs by frequency."""
    try:
        # Open in read-only mode to avoid locking
        conn = sqlite3.connect(f"file:{DATABASE_PATH}?mode=ro", uri=True)
        cursor = conn.cursor()

        # Set a timeout for queries
        cursor.execute("PRAGMA busy_timeout = 5000")

        cursor.execute("""
            SELECT source_ip, COUNT(*) as count FROM logs 
            WHERE source_ip != 'N/A'
            GROUP BY source_ip 
            ORDER BY count DESC 
            LIMIT ?
        """, (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        return results
    except Exception as e:
        print(f"Error getting top attacking IPs: {e}")
        return []


def get_events_per_minute(hours: int = 24) -> list[dict]:
    """Get event count per minute for the last N hours."""
    try:
        # Open in read-only mode to avoid locking
        conn = sqlite3.connect(f"file:{DATABASE_PATH}?mode=ro", uri=True)
        cursor = conn.cursor()

        # Set a timeout for the query
        cursor.execute("PRAGMA busy_timeout = 5000")

        cursor.execute(f"""
            SELECT
                strftime('%Y-%m-%d %H:%M', timestamp) as minute,
                os_type,
                COUNT(*) as count
            FROM logs
            WHERE datetime(timestamp) >= datetime('now', '-{hours} hours')
            GROUP BY minute, os_type
            ORDER BY minute
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{"minute": row[0], "os_type": row[1], "count": row[2]} for row in rows]
    except Exception as e:
        print(f"Error getting events per minute: {e}")
        return []


def record_heartbeat(source_host: str, os_type: str) -> bool:
    """
    Record a heartbeat from an agent.
    Updates or creates a heartbeat entry for the host.
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Use Python generated UTC timestamp for consistency with logs
        current_time = datetime.utcnow().isoformat() + "Z"
        
        cursor.execute("""
            INSERT INTO heartbeats (source_host, os_type, last_seen, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(source_host) DO UPDATE SET
                last_seen = ?,
                updated_at = ?
        """, (source_host, os_type, current_time, current_time, current_time, current_time))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error recording heartbeat: {e}")
        return False


def get_host_status(inactive_threshold_minutes: int = 15) -> dict:
    """
    Get status of all hosts (active/inactive).
    Checks both heartbeats and logs for host activity.

    Args:
        inactive_threshold_minutes: Hosts without activity in this many minutes are considered inactive

    Returns:
        dict with 'active' and 'inactive' lists of host info
    """
    try:
        # Open in read-only mode to avoid locking
        conn = sqlite3.connect(f"file:{DATABASE_PATH}?mode=ro", uri=True)
        cursor = conn.cursor()

        # Set a timeout for queries
        cursor.execute("PRAGMA busy_timeout = 5000")
        
        # Get all unique hosts from both heartbeats and logs
        # Heartbeats take precedence for active status
        # Use UNION to avoid FULL OUTER JOIN (not available in older SQLite versions)
        cursor.execute("""
            SELECT 
                source_host,
                os_type,
                last_seen,
                total_events
            FROM (
                -- Get all heartbeats with event counts
                SELECT 
                    h.source_host,
                    h.os_type,
                    h.last_seen,
                    COALESCE((SELECT COUNT(*) FROM logs WHERE source_host = h.source_host), 0) as total_events
                FROM heartbeats h
                
                UNION
                
                -- Get hosts that only have logs (no heartbeats)
                SELECT 
                    l.source_host,
                    l.os_type,
                    MAX(l.timestamp) as last_seen,
                    COUNT(l.id) as total_events
                FROM logs l
                WHERE l.source_host NOT IN (SELECT source_host FROM heartbeats)
                GROUP BY l.source_host, l.os_type
            )
            ORDER BY last_seen DESC
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        # Calculate threshold time
        from datetime import datetime, timedelta
        threshold_time = datetime.utcnow() - timedelta(minutes=inactive_threshold_minutes)
        
        active_hosts = []
        inactive_hosts = []
        
        for row in rows:
            # Parse timestamp and compare
            try:
                last_seen_str = row[2]
                
                # Parse the timestamp
                if isinstance(last_seen_str, str):
                    # Handle both ISO format and SQLite format
                    if "T" in last_seen_str:
                        # ISO format (with or without Z)
                        if last_seen_str.endswith("Z"):
                            last_seen_str = last_seen_str[:-1]
                        last_seen_dt = datetime.fromisoformat(last_seen_str).replace(tzinfo=timezone.utc)
                    else:
                        # SQLite format: "2025-12-03 20:58:08" - assume UTC
                        last_seen_dt = datetime.fromisoformat(last_seen_str).replace(tzinfo=timezone.utc)
                else:
                    last_seen_dt = last_seen_str
                
                # Convert to ISO format with Z suffix for API response
                iso_timestamp = last_seen_dt.isoformat() + "Z"
                
                host_info = {
                    "hostname": row[0],
                    "os_type": row[1],
                    "last_seen": iso_timestamp,
                    "total_events": row[3]
                }
                
                if last_seen_dt >= threshold_time:
                    active_hosts.append(host_info)
                else:
                    inactive_hosts.append(host_info)
            except Exception as e:
                # If timestamp parsing fails, consider inactive
                print(f"Error parsing timestamp for {row[0]}: {e}")
                host_info = {
                    "hostname": row[0],
                    "os_type": row[1],
                    "last_seen": str(row[2]),
                    "total_events": row[3]
                }
                inactive_hosts.append(host_info)
        
        return {
            "active": active_hosts,
            "inactive": inactive_hosts,
            "threshold_minutes": inactive_threshold_minutes
        }
    except Exception as e:
        print(f"Error getting host status: {e}")
        return {"active": [], "inactive": [], "threshold_minutes": inactive_threshold_minutes}


if __name__ == "__main__":
    init_database()

