"""
Heimdall - REST API Server

Central API hub for the Heimdall security monitoring platform.
Handles event ingestion from all agents, validation, storage, and analytics queries.

Heimdall stands guard with a comprehensive REST API for security intelligence.
"""

from fastapi import FastAPI, HTTPException, Header, status, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from datetime import datetime, timedelta

# Try to load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, proceed without it
    pass

from .models import LogEvent, IngestRequest, IngestResponse, MetricsResponse, SystemStatusRequest
from .database_pg import (
    init_database, insert_event, insert_events_batch, get_all_events, get_events_by_filter,
    get_metrics_24h, get_top_attacking_ips, get_events_per_minute, get_host_status,
    record_heartbeat, delete_host_events, get_config, set_config,
    upsert_system_status, get_system_status
)
from .alert_manager import start_alert_manager

# Configuration - load from environment variables with sensible defaults
API_KEY = os.getenv("SIEM_API_KEY", "default-insecure-key-change-me")
DATABASE_PATH = os.getenv("SIEM_DATABASE_PATH", "mini_siem.db")
VALID_API_KEYS = {API_KEY}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and start background services on startup."""
    init_database()
    start_alert_manager()
    yield


app = FastAPI(
    title="Heimdall API",
    description="Heimdall - Standing Guard Over Your Infrastructure. Central event ingestion and security intelligence API.",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def validate_api_key(api_key: str = Header(None)):
    """Validate API key from request header."""
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key"
        )
    if api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "Mini-SIEM API is running",
        "version": "1.0.0"
    }


@app.post("/ingest", response_model=IngestResponse, tags=["Ingestion"])
async def ingest_logs(request: IngestRequest, api_key: str = Header(None)):
    """
    Ingest log events from agents.

    The request must include an API key header for authentication.
    All events must conform to the unified data schema.
    """

    # Validate API key
    validate_api_key(api_key)

    try:
        # Convert events to dictionaries for batch insertion
        event_dicts = [event.model_dump() for event in request.events]

        # Use batch insert for better performance
        processed, failed = insert_events_batch(event_dicts)

        # Update heartbeats for hosts that successfully sent events
        # This ensures they appear "Active" on the dashboard immediately
        if processed > 0:
            unique_hosts = {(e.source_host, e.os_type) for e in request.events}
            for host, os_type in unique_hosts:
                try:
                    record_heartbeat(host, os_type)
                except Exception as e:
                    print(f"Failed to update implicit heartbeat for {host}: {e}")

        return IngestResponse(
            success=True,
            message=f"Processed {processed} events" + (f", {failed} duplicates skipped" if failed > 0 else ""),
            events_processed=processed
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error processing events: {str(e)}",
                "events_processed": 0
            }
        )


@app.get("/events", tags=["Query"])
async def get_events(
    os_type: str = None,
    severity: int = None,
    severity_min: int = None,
    event_type: str = None,
    source_ip: str = None,
    user: str = None,
    source_host: str = None,
    raw_message: str = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = 1000,
    offset: int = 0,
    api_key: str = Header(None)
):
    """
    Retrieve events from the database with optional filters and pagination.

    Query Parameters:
    - os_type: Filter by OS type (exact match)
    - severity: Filter by exact severity level
    - severity_min: Filter by minimum severity level (inclusive)
    - event_type: Filter by event type (exact match)
    - source_ip: Filter by source IP (exact match)
    - user: Filter by username (case-insensitive partial match)
    - source_host: Filter by source hostname (exact match)
    - raw_message: Filter by raw message content (case-insensitive)
    - start_date: Filter events on/after this date (ISO format: YYYY-MM-DD)
    - end_date: Filter events on/before this date (ISO format: YYYY-MM-DD)
    - limit: Maximum number of events to return (default 1000, max 10000)
    - offset: Number of events to skip for pagination (default 0)

    Returns:
    {
        "success": true,
        "total_count": 12345,
        "offset": 0,
        "limit": 100,
        "count": 100,
        "events": [...]
    }
    """

    validate_api_key(api_key)

    try:
        # Limit the maximum number of events that can be returned
        limit = min(limit, 10000)

        # Call the database function with all available filters
        result = get_events_by_filter(
            os_type=os_type,
            severity=severity,
            severity_min=severity_min,
            event_type=event_type,
            source_ip=source_ip,
            user=user,
            source_host=source_host,
            raw_message=raw_message,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )

        return {
            "success": True,
            "total_count": result['total_count'],
            "offset": result['offset'],
            "limit": result['limit'],
            "count": len(result['events']),
            "events": result['events']
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error retrieving events: {str(e)}",
                "total_count": 0,
                "offset": offset,
                "limit": limit,
                "count": 0,
                "events": []
            }
        )


@app.get("/metrics", response_model=dict, tags=["Analytics"])
async def get_metrics(api_key: str = Header(None)):
    """
    Get key metrics for the dashboard.
    Includes alerts in last 24h, threats by OS, top attacking IPs, etc.
    """
    
    validate_api_key(api_key)
    
    try:
        metrics = get_metrics_24h()
        top_ips = get_top_attacking_ips(10)
        events_per_min = get_events_per_minute(24)
        
        return {
            "success": True,
            "total_alerts_24h": metrics["total_alerts_24h"],
            "threats_by_os": metrics["threats_by_os"],
            "most_blocked_domain": metrics["most_blocked_domain"],
            "top_attacking_ips": [{"ip": ip, "count": count} for ip, count in top_ips],
            "events_per_minute": events_per_min
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error calculating metrics: {str(e)}"
            }
        )


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "api_version": "1.0.0"
    }


@app.get("/hosts", tags=["Monitoring"])
async def get_hosts_status(
    inactive_threshold: int = 15,
    api_key: str = Header(None)
):
    """
    Get status of all monitored hosts (active/inactive).
    
    Args:
        inactive_threshold: Minutes since last event to consider host inactive (default: 15)
    """
    validate_api_key(api_key)
    
    try:
        host_status = get_host_status(inactive_threshold_minutes=inactive_threshold)
        return {
            "success": True,
            "active_hosts": host_status["active"],
            "inactive_hosts": host_status["inactive"],
            "threshold_minutes": host_status["threshold_minutes"],
            "total_active": len(host_status["active"]),
            "total_inactive": len(host_status["inactive"])
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error retrieving host status: {str(e)}"
            }
        )


@app.post("/heartbeat", tags=["Monitoring"])
async def receive_heartbeat(
    source_host: str = Header(None, alias="source-host"),
    os_type: str = Header(None, alias="os-type"),
    api_key: str = Header(None)
):
    """
    Record a heartbeat from an agent.
    
    This endpoint updates the last_seen timestamp for a host without creating a database event.
    Used to keep track of active agents without cluttering the event log with heartbeat events.
    
    Args:
        source_host: Hostname of the agent sending the heartbeat (header)
        os_type: OS type of the agent (header)
        api_key: API key for authentication (header)
    """
    validate_api_key(api_key)
    
    if not source_host:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing source_host header"
        )
    
    if not os_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing os_type header"
        )
    
    try:
        success = record_heartbeat(source_host, os_type)
        
        if success:
            return {
                "success": True,
                "message": f"Heartbeat recorded for {source_host}",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": f"Failed to record heartbeat for {source_host}"
                }
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error recording heartbeat: {str(e)}"
            }
        )


@app.get("/alert-config", tags=["Alerts"])
async def get_alert_config(api_key: str = Header(None)):
    """Get current alert configuration."""
    validate_api_key(api_key)

    # Fetch from DB, fallback to env vars
    severity = int(get_config("ALERT_SEVERITY_THRESHOLD", os.getenv("ALERT_SEVERITY_THRESHOLD", "4")))
    inactive = int(get_config("ALERT_INACTIVE_THRESHOLD", os.getenv("ALERT_INACTIVE_THRESHOLD", "15")))
    enable_val = get_config("ENABLE_TELEGRAM_ALERTS", os.getenv("ENABLE_TELEGRAM_ALERTS", "true"))
    quiet = get_config("ALERT_QUIET_HOURS", os.getenv("ALERT_QUIET_HOURS", ""))

    return {
        "success": True,
        "config": {
            "severity_threshold": severity,
            "inactive_threshold_minutes": inactive,
            "check_interval_seconds": int(os.getenv("ALERT_CHECK_INTERVAL", "60")),
            "enable_alerts": str(enable_val).lower() == "true",
            "quiet_hours": quiet,
            "telegram_configured": bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"))
        }
    }


@app.post("/alert-config/severity-threshold", tags=["Alerts"])
async def set_severity_threshold(threshold: int, api_key: str = Header(None)):
    """Update alert severity threshold (requires restart to take effect)."""
    validate_api_key(api_key)

    if threshold < 1 or threshold > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Severity threshold must be between 1 and 5"
        )

    # Persist to database
    set_config("ALERT_SEVERITY_THRESHOLD", str(threshold))

    return {
        "success": True,
        "message": f"Severity threshold updated to {threshold}",
        "note": "Changes applied immediately",
        "env_variable": "ALERT_SEVERITY_THRESHOLD"
    }


@app.post("/alert-config/inactive-threshold", tags=["Alerts"])
async def set_inactive_threshold(minutes: int, api_key: str = Header(None)):
    """Update inactive host threshold (requires restart to take effect)."""
    validate_api_key(api_key)

    if minutes < 1 or minutes > 1440:  # Max 24 hours
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive threshold must be between 1 and 1440 minutes"
        )

    # Persist to database
    set_config("ALERT_INACTIVE_THRESHOLD", str(minutes))

    return {
        "success": True,
        "message": f"Inactive threshold updated to {minutes} minutes",
        "note": "Changes applied immediately",
        "env_variable": "ALERT_INACTIVE_THRESHOLD"
    }


@app.post("/alert-config/quiet-hours", tags=["Alerts"])
async def set_quiet_hours(quiet_hours: str, api_key: str = Header(None)):
    """Set quiet hours to suppress alerts (format: HH:MM-HH:MM or empty to disable)."""
    validate_api_key(api_key)

    if quiet_hours and "-" in quiet_hours:
        try:
            start_str, end_str = quiet_hours.split("-")
            start_hour, start_min = map(int, start_str.split(":"))
            end_hour, end_min = map(int, end_str.split(":"))

            if not (0 <= start_hour < 24 and 0 <= start_min < 60):
                raise ValueError("Invalid start time")
            if not (0 <= end_hour < 24 and 0 <= end_min < 60):
                raise ValueError("Invalid end time")
        except (ValueError, IndexError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid quiet hours format. Use HH:MM-HH:MM (e.g., 22:00-06:00)"
            )
    elif quiet_hours:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid quiet hours format. Use HH:MM-HH:MM (e.g., 22:00-06:00)"
        )

    # Persist to database
    set_config("ALERT_QUIET_HOURS", quiet_hours)

    return {
        "success": True,
        "message": f"Quiet hours updated to: {quiet_hours if quiet_hours else 'disabled'}",
        "note": "Changes applied immediately",
        "env_variable": "ALERT_QUIET_HOURS"
    }


@app.post("/alert-config/enable", tags=["Alerts"])
async def enable_alerts(enabled: bool, api_key: str = Header(None)):
    """Enable or disable alert sending."""
    validate_api_key(api_key)

    # Persist to database
    set_config("ENABLE_TELEGRAM_ALERTS", "true" if enabled else "false")

    return {
        "success": True,
        "message": f"Alerts {'enabled' if enabled else 'disabled'}",
        "note": "Changes applied immediately",
        "env_variable": "ENABLE_TELEGRAM_ALERTS",
        "value": "true" if enabled else "false"
    }


@app.delete("/hosts/{hostname}", tags=["Hosts"])
async def delete_host(hostname: str, api_key: str = Header(None)):
    """Delete all events from a specific host."""
    validate_api_key(api_key)

    try:
        success = delete_host_events(hostname)
        if success:
            return {
                "success": True,
                "message": f"All events from host '{hostname}' have been deleted"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete host events"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/alerts/telegram/test", tags=["Alerts"])
async def test_telegram_connection(request: Request, api_key: str = Header(None)):
    """Test Telegram bot connection."""
    validate_api_key(api_key)

    body = await request.json()
    bot_token = body.get("bot_token", "")
    chat_id = body.get("chat_id", "")

    if not bot_token or not chat_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing bot_token or chat_id"
        )

    try:
        import urllib.request
        import json as json_lib

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": "Heimdall Security Monitor - Connection Test ✓\n\nTelegram alerts are working properly!"
        }

        # Prepare the request
        json_data = json_lib.dumps(data).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=json_data,
            headers={'Content-Type': 'application/json'}
        )

        # Make the request
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    return {
                        "success": True,
                        "message": "Telegram connection test successful"
                    }
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Telegram API error: {error_body}"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test Telegram connection: {str(e)}"
        )


@app.post("/alerts/telegram/config", tags=["Alerts"])
async def save_telegram_config(request: Request, api_key: str = Header(None)):
    """Save Telegram bot configuration."""
    validate_api_key(api_key)

    body = await request.json()
    bot_token = body.get("bot_token", "")
    chat_id = body.get("chat_id", "")

    if not bot_token or not chat_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing bot_token or chat_id"
        )

    try:
        # Store in environment or file
        with open(".env.telegram", "w") as f:
            f.write(f"TELEGRAM_BOT_TOKEN={bot_token}\n")
            f.write(f"TELEGRAM_CHAT_ID={chat_id}\n")

        return {
            "success": True,
            "message": "Telegram configuration saved successfully",
            "note": "Restart API server for changes to take effect"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save configuration: {str(e)}"
        )


@app.post("/system-status", tags=["Monitoring"])
async def ingest_system_status(request: SystemStatusRequest, api_key: str = Header(None)):
    """Ingest detailed system status from an agent."""
    validate_api_key(api_key)
    
    try:
        # Also update heartbeat since the agent is alive
        record_heartbeat(request.status.source_host, request.status.os_type)
        
        success = upsert_system_status(request.status.model_dump())
        if success:
            return {"success": True, "message": "System status updated"}
        else:
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": "Failed to store system status"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Error: {str(e)}"}
        )

@app.get("/system-status/{hostname}", tags=["Monitoring"])
async def retrieve_system_status(hostname: str, api_key: str = Header(None)):
    """Get detailed system status for a specific host."""
    validate_api_key(api_key)
    
    status = get_system_status(hostname)
    if status:
        return {"success": True, "status": status}
    else:
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "Host status not found"}
        )

if __name__ == "__main__":
    import uvicorn
    server_host = os.getenv("SIEM_SERVER_HOST", "0.0.0.0")
    server_port = int(os.getenv("SIEM_SERVER_PORT", "8010"))
    uvicorn.run(app, host=server_host, port=server_port)

