"""
Heimdall - PostgreSQL Database Layer

PostgreSQL database management for Heimdall.
Replaces SQLite for better concurrency and reliability.
Provides unified query interface for all event data.
"""

import psycopg2
from psycopg2 import pool, extras
import os
from datetime import datetime, timezone, timedelta

# PostgreSQL connection configuration
DB_HOST = os.getenv("SIEM_DB_HOST", "postgres")
DB_PORT = int(os.getenv("SIEM_DB_PORT", "5432"))
DB_NAME = os.getenv("SIEM_DB_NAME", "heimdall")
DB_USER = os.getenv("SIEM_DB_USER", "heimdall")
DB_PASSWORD = os.getenv("SIEM_DB_PASSWORD", "heimdall")

# Connection pool for better performance
conn_pool = None

def init_connection_pool():
    """Initialize PostgreSQL connection pool."""
    global conn_pool
    try:
        conn_pool = psycopg2.pool.SimpleConnectionPool(
            1, 20,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            connect_timeout=5
        )
        print(f"PostgreSQL connection pool initialized")
    except Exception as e:
        print(f"Error initializing connection pool: {e}")
        raise

def get_conn():
    """Get a connection from the pool."""
    if conn_pool is None:
        init_connection_pool()
    return conn_pool.getconn()

def return_conn(conn):
    """Return a connection to the pool."""
    if conn_pool:
        conn_pool.putconn(conn)

def init_database():
    """Initialize PostgreSQL database with tables and indexes."""
    try:
        conn = get_conn()
        cursor = conn.cursor()

        # Create config table for dynamic settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create system status table for RMM features
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_status (
                id SERIAL PRIMARY KEY,
                source_host TEXT UNIQUE NOT NULL,
                os_type TEXT NOT NULL,
                os_details TEXT,
                cpu_usage FLOAT,
                cpu_count INTEGER,
                memory_total BIGINT,
                memory_used BIGINT,
                memory_percent FLOAT,
                disk_info JSONB,
                network_info JSONB,
                top_processes JSONB,
                boot_time TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id SERIAL PRIMARY KEY,
                event_id TEXT UNIQUE NOT NULL,
                timestamp TEXT NOT NULL,
                source_host TEXT NOT NULL,
                os_type TEXT NOT NULL,
                event_type TEXT NOT NULL,
                severity INTEGER NOT NULL,
                source_ip TEXT NOT NULL,
                "user" TEXT NOT NULL,
                raw_message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for fast queries
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

        # Create heartbeat table for agent status tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS heartbeats (
                id SERIAL PRIMARY KEY,
                source_host TEXT UNIQUE NOT NULL,
                os_type TEXT NOT NULL,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_heartbeat_host ON heartbeats(source_host)
        """)

        # Create alert history table to prevent duplicate alerts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alert_history (
                id SERIAL PRIMARY KEY,
                event_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(event_id, alert_type)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_alert_history_event ON alert_history(event_id)
        """)

        conn.commit()
        return_conn(conn)
        print(f"PostgreSQL database initialized")
    except Exception as e:
        print(f"Error initializing database: {e}")
        if conn:
            conn.rollback()
            return_conn(conn)
        raise

def insert_event(event_dict: dict) -> bool:
    """Insert a single event into the database."""
    try:
        conn = get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO logs (
                event_id, timestamp, source_host, os_type, event_type,
                severity, source_ip, "user", raw_message
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
        return_conn(conn)
        return True
    except psycopg2.IntegrityError:
        conn.rollback()
        return_conn(conn)
        return False
    except Exception as e:
        print(f"Error inserting event: {e}")
        conn.rollback()
        return_conn(conn)
        return False

def insert_events_batch(events: list[dict]) -> tuple[int, int]:
    """Insert multiple events efficiently in a single batch."""
    try:
        conn = get_conn()
        cursor = conn.cursor()

        inserted = 0
        failed = 0

        for event_dict in events:
            try:
                cursor.execute("""
                    INSERT INTO logs (
                        event_id, timestamp, source_host, os_type, event_type,
                        severity, source_ip, "user", raw_message
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            except psycopg2.IntegrityError:
                failed += 1
            except Exception as e:
                failed += 1

        conn.commit()
        return_conn(conn)
        return (inserted, failed)
    except Exception as e:
        print(f"Error inserting batch: {e}")
        conn.rollback()
        return_conn(conn)
        return (0, len(events))

def get_all_events(limit: int = 1000) -> list[dict]:
    """Get recent events from the database."""
    try:
        conn = get_conn()
        cursor = conn.cursor(cursor_factory=extras.DictCursor)

        cursor.execute("""
            SELECT * FROM logs
            ORDER BY timestamp DESC
            LIMIT %s
        """, (limit,))

        rows = cursor.fetchall()
        return_conn(conn)

        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error retrieving events: {e}")
        return_conn(conn)
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
        conn = get_conn()
        cursor = conn.cursor(cursor_factory=extras.DictCursor)

        query = "SELECT * FROM logs WHERE 1=1"
        params = []

        if os_type:
            query += " AND os_type = %s"
            params.append(os_type)
        if severity is not None:
            query += " AND severity = %s"
            params.append(severity)
        if severity_min is not None:
            query += " AND severity >= %s"
            params.append(severity_min)
        if event_type:
            query += " AND event_type = %s"
            params.append(event_type)
        if source_ip:
            query += " AND source_ip = %s"
            params.append(source_ip)
        if user:
            query += " AND LOWER(\"user\") LIKE %s"
            params.append(f"%{user.lower()}%")
        if source_host:
            query += " AND source_host = %s"
            params.append(source_host)
        if raw_message:
            query += " AND LOWER(raw_message) LIKE %s"
            params.append(f"%{raw_message.lower()}%")
        if start_date:
            query += " AND timestamp::date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND timestamp::date <= %s"
            params.append(end_date)

        # Get total count before pagination
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]

        # Add ordering and pagination
        query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
        params.append(limit)
        params.append(offset)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return_conn(conn)

        return {
            'events': [dict(row) for row in rows],
            'total_count': total_count,
            'offset': offset,
            'limit': limit
        }
    except Exception as e:
        print(f"Error retrieving filtered events: {e}")
        return_conn(conn)
        return {'events': [], 'total_count': 0, 'offset': offset, 'limit': limit}

def get_metrics_24h() -> dict:
    """Get metrics for the last 24 hours."""
    try:
        conn = get_conn()
        cursor = conn.cursor()

        # Total alerts in last 24 hours
        cursor.execute("""
            SELECT COUNT(*) as count FROM logs
            WHERE timestamp::timestamp >= NOW() - INTERVAL '24 hours'
        """)
        total_alerts = cursor.fetchone()[0]

        # Threats by OS
        cursor.execute("""
            SELECT os_type, COUNT(*) as count FROM logs
            WHERE timestamp::timestamp >= NOW() - INTERVAL '24 hours'
            GROUP BY os_type
        """)
        threats_by_os = {row[0]: row[1] for row in cursor.fetchall()}

        # Most blocked domain (from DNS_BLOCK events)
        cursor.execute("""
            SELECT raw_message, COUNT(*) as count FROM logs
            WHERE event_type = 'DNS_BLOCK'
            AND timestamp::timestamp >= NOW() - INTERVAL '24 hours'
            GROUP BY raw_message
            ORDER BY count DESC
            LIMIT 1
        """)
        result = cursor.fetchone()
        most_blocked_domain = result[0] if result else None

        return_conn(conn)

        return {
            "total_alerts_24h": total_alerts,
            "threats_by_os": threats_by_os,
            "most_blocked_domain": most_blocked_domain
        }
    except Exception as e:
        print(f"Error calculating metrics: {e}")
        return_conn(conn)
        return {
            "total_alerts_24h": 0,
            "threats_by_os": {},
            "most_blocked_domain": None
        }

def get_top_attacking_ips(limit: int = 10) -> list[tuple[str, int]]:
    """Get top attacking IPs by frequency."""
    try:
        conn = get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT source_ip, COUNT(*) as count FROM logs
            WHERE source_ip != 'N/A'
            GROUP BY source_ip
            ORDER BY count DESC
            LIMIT %s
        """, (limit,))

        results = cursor.fetchall()
        return_conn(conn)

        return results
    except Exception as e:
        print(f"Error getting top attacking IPs: {e}")
        return_conn(conn)
        return []

def get_events_per_minute(hours: int = 24) -> list[dict]:
    """Get event count per minute for the last N hours."""
    try:
        conn = get_conn()
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT
                TO_CHAR(timestamp::timestamp, 'YYYY-MM-DD HH24:MI') as minute,
                os_type,
                COUNT(*) as count
            FROM logs
            WHERE timestamp::timestamp >= NOW() - INTERVAL '{hours} hours'
            GROUP BY minute, os_type
            ORDER BY minute
        """)

        rows = cursor.fetchall()
        return_conn(conn)

        return [{"minute": row[0], "os_type": row[1], "count": row[2]} for row in rows]
    except Exception as e:
        print(f"Error getting events per minute: {e}")
        return_conn(conn)
        return []

def record_heartbeat(source_host: str, os_type: str) -> bool:
    """Record a heartbeat from an agent."""
    try:
        conn = get_conn()
        cursor = conn.cursor()

        # Use Python generated UTC timestamp for consistency with logs
        current_time = datetime.utcnow().isoformat() + "Z"

        cursor.execute("""
            INSERT INTO heartbeats (source_host, os_type, last_seen, updated_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (source_host) DO UPDATE SET
                last_seen = %s,
                updated_at = %s
        """, (source_host, os_type, current_time, current_time, current_time, current_time))

        conn.commit()
        return_conn(conn)
        return True
    except Exception as e:
        print(f"Error recording heartbeat: {e}")
        conn.rollback()
        return_conn(conn)
        return False

def get_host_status(inactive_threshold_minutes: int = 15) -> dict:
    """Get status of all hosts (active/inactive)."""
    try:
        conn = get_conn()
        cursor = conn.cursor()

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
                    MAX(l.timestamp::timestamp) as last_seen,
                    COUNT(l.id) as total_events
                FROM logs l
                WHERE l.source_host NOT IN (SELECT source_host FROM heartbeats)
                GROUP BY l.source_host, l.os_type
            ) combined
            ORDER BY last_seen DESC
        """)

        rows = cursor.fetchall()
        return_conn(conn)

        # Calculate threshold time
        threshold_time = datetime.utcnow() - timedelta(minutes=inactive_threshold_minutes)

        active_hosts = []
        inactive_hosts = []

        for row in rows:
            try:
                last_seen_str = row[2]

                # Parse the timestamp
                if isinstance(last_seen_str, str):
                    if "T" in last_seen_str:
                        if last_seen_str.endswith("Z"):
                            last_seen_str = last_seen_str[:-1]
                        last_seen_dt = datetime.fromisoformat(last_seen_str).replace(tzinfo=timezone.utc)
                    else:
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
        return_conn(conn)
        return {"active": [], "inactive": [], "threshold_minutes": inactive_threshold_minutes}

def check_alert_sent(event_id: str, alert_type: str = "critical") -> bool:
    """Check if an alert has already been sent for this event."""
    try:
        conn = get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id FROM alert_history
            WHERE event_id = %s AND alert_type = %s
            LIMIT 1
        """, (event_id, alert_type))

        result = cursor.fetchone()
        return_conn(conn)
        return result is not None
    except Exception as e:
        print(f"Error checking alert history: {e}")
        return_conn(conn)
        return False

def record_alert_sent(event_id: str, alert_type: str = "critical") -> bool:
    """Record that an alert has been sent for this event."""
    try:
        conn = get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO alert_history (event_id, alert_type)
            VALUES (%s, %s)
            ON CONFLICT (event_id, alert_type) DO NOTHING
        """, (event_id, alert_type))

        conn.commit()
        return_conn(conn)
        return True
    except Exception as e:
        print(f"Error recording alert history: {e}")
        conn.rollback()
        return_conn(conn)
        return False

def delete_host_events(source_host: str) -> bool:
    """Delete all events from a specific host."""
    try:
        conn = get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM logs
            WHERE source_host = %s
        """, (source_host,))

        conn.commit()
        deleted_count = cursor.rowcount
        return_conn(conn)
        print(f"Deleted {deleted_count} events from host {source_host}")
        return True
    except Exception as e:
        print(f"Error deleting host events: {e}")
        conn.rollback()
        return_conn(conn)
        return False

def get_config(key: str, default: str = None) -> str:
    """Get a configuration value from the database."""
    try:
        conn = get_conn()
        cursor = conn.cursor()
        
        cursor.execute("SELECT value FROM config WHERE key = %s", (key,))
        result = cursor.fetchone()
        
        return_conn(conn)
        
        if result:
            return result[0]
        return default
    except Exception as e:
        print(f"Error getting config '{key}': {e}")
        if conn:
            return_conn(conn)
        return default

def set_config(key: str, value: str) -> bool:
    """Set a configuration value in the database."""
    try:
        conn = get_conn()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO config (key, value, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (key) DO UPDATE SET
                value = EXCLUDED.value,
                updated_at = EXCLUDED.updated_at
        """, (key, str(value)))
        
        conn.commit()
        return_conn(conn)
        return True
    except Exception as e:
        print(f"Error setting config '{key}': {e}")
        if conn:
            conn.rollback()
            return_conn(conn)
        return False

def upsert_system_status(status: dict) -> bool:
    """Insert or update system status for a host."""
    try:
        conn = get_conn()
        cursor = conn.cursor()
        
        # Helper to dump dicts/lists to JSON string for Postgres
        import json
        
        cursor.execute("""
            INSERT INTO system_status (
                source_host, os_type, os_details,
                cpu_usage, cpu_count,
                memory_total, memory_used, memory_percent,
                disk_info, network_info, top_processes,
                boot_time, last_updated
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (source_host) DO UPDATE SET
                os_type = EXCLUDED.os_type,
                os_details = EXCLUDED.os_details,
                cpu_usage = EXCLUDED.cpu_usage,
                cpu_count = EXCLUDED.cpu_count,
                memory_total = EXCLUDED.memory_total,
                memory_used = EXCLUDED.memory_used,
                memory_percent = EXCLUDED.memory_percent,
                disk_info = EXCLUDED.disk_info,
                network_info = EXCLUDED.network_info,
                top_processes = EXCLUDED.top_processes,
                boot_time = EXCLUDED.boot_time,
                last_updated = CURRENT_TIMESTAMP
        """, (
            status["source_host"], status["os_type"], status["os_details"],
            status["cpu_usage"], status["cpu_count"],
            status["memory_total"], status["memory_used"], status["memory_percent"],
            json.dumps(status["disk_info"]), 
            json.dumps(status["network_info"]), 
            json.dumps(status["top_processes"]),
            status["boot_time"]
        ))
        
        conn.commit()
        return_conn(conn)
        return True
    except Exception as e:
        print(f"Error upserting system status: {e}")
        if conn:
            conn.rollback()
            return_conn(conn)
        return False

def get_system_status(source_host: str) -> dict:
    """Get the latest system status for a host."""
    try:
        conn = get_conn()
        cursor = conn.cursor(cursor_factory=extras.DictCursor)
        
        cursor.execute("""
            SELECT * FROM system_status WHERE source_host = %s
        """, (source_host,))
        
        result = cursor.fetchone()
        return_conn(conn)
        
        if result:
            return dict(result)
        return None
    except Exception as e:
        print(f"Error getting system status: {e}")
        if conn:
            return_conn(conn)
        return None

if __name__ == "__main__":
    init_database()
