"""
Heimdall Windows Agent

Collects Windows Security event logs and sends them to Heimdall.
Eyes on Windows Event Log - watching for threats and anomalies.

Requires pywin32 on Windows systems.
"""

import os
import sys
import requests
import json
from datetime import datetime
import time
import socket
import uuid
import psutil
import platform

# Windows-specific imports (only on Windows)
WIN32_AVAILABLE = False
if sys.platform == "win32":
        try:
            import win32evtlog
            import win32con
            import win32security
            WIN32_AVAILABLE = True
        except ImportError:
            print("[!] Warning: pywin32 not properly installed - event collection disabled")
            print("    Agent will send heartbeats only")
            WIN32_AVAILABLE = False

# Standalone agent - no core module dependency needed


class WindowsAgent:
    """Collects Windows Security event logs."""
    
    def __init__(self, api_url: str = "http://localhost:8000", api_key: str = "default-insecure-key-change-me"):
        self.api_url = api_url
        self.api_key = api_key
        self.source_host = socket.gethostname()
        self.os_type = "WINDOWS"
        self.event_log_server = "."  # Local machine
        self.event_log_name = "Security"
        
        # Event ID to severity mapping
        self.event_mapping = {
            4625: {"type": "LOGIN_FAIL", "severity": 3},      # Failed Logon
            4624: {"type": "LOGIN_SUCCESS", "severity": 1},   # Successful Logon
            4688: {"type": "PROCESS_EXEC", "severity": 1},    # Process Creation
            4720: {"type": "ACCOUNT_CREATE", "severity": 4},  # User Created
            4726: {"type": "ACCOUNT_DELETE", "severity": 3},  # User Deleted
            4728: {"type": "GROUP_ADD", "severity": 3},       # Member Added to Global Group
            4732: {"type": "GROUP_ADD", "severity": 3},       # Member Added to Local Group
            4756: {"type": "GROUP_ADD", "severity": 3},       # Member Added to Universal Group
            7045: {"type": "SERVICE_INSTALL", "severity": 3}, # Service Installed
            1102: {"type": "LOG_TAMPERING", "severity": 5},   # Log Cleared
        }
        
        # State file to persist last processed record number
        # Use log directory if available, otherwise current directory
        log_dir = os.getenv("HEIMDALL_LOG_DIR", "C:\\Heimdall\\logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        self.state_file = os.path.join(log_dir, "win_agent_state.json")
        self.last_record_number = self._load_state()
        self.pending_high_water_mark = None  # Track pending state update
    
    def _load_state(self) -> int:
        """Load the last processed record number from state file."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    record_num = state.get("last_record_number", 0)
                    print(f"[INFO] Loaded state: last_record_number = {record_num}")
                    return record_num
        except Exception as e:
            print(f"[WARN] Could not load state file: {e}")
        return 0

    def _save_state(self):
        """Save the last processed record number to state file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump({"last_record_number": self.last_record_number}, f)
        except Exception as e:
            print(f"[ERROR] Could not save state file: {e}")
    
    def _update_state_after_success(self):
        """Update state only after successful event send to prevent losing events."""
        if self.pending_high_water_mark is not None:
            self.last_record_number = self.pending_high_water_mark
            self._save_state()
            self.pending_high_water_mark = None

    def get_event_log_handle(self):
        """Open the Security event log."""
        try:
            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
            return win32evtlog.OpenEventLog(self.event_log_server, self.event_log_name)
        except Exception as e:
            print(f"Error opening event log: {e}")
            return None
    
    def parse_event(self, event) -> dict:
        """
        Parse a Windows event and extract relevant information.
        Returns None if the event is not interesting.
        PyEventLogRecord objects have attributes, not dict keys.
        """
        try:
            # Access object attributes, not dict keys
            event_id = event.EventID
            record_number = event.RecordNumber
            
            # Check if this is an event we care about
            if event_id not in self.event_mapping:
                return None
            
            mapping = self.event_mapping[event_id]
            event_type = mapping["type"]
            severity = mapping["severity"]
            
            # Extract data from event strings
            strings = event.StringInserts if hasattr(event, 'StringInserts') and event.StringInserts else []
            raw_message = " | ".join(str(s) for s in strings) if strings else f"Event ID {event_id}"
            
            # Try to extract username and IP
            user = "system"
            source_ip = "N/A"
            
            if event_id == 4625:
                # Failed logon
                user = str(strings[5]) if len(strings) > 5 else "unknown"
                source_ip = str(strings[19]) if len(strings) > 19 else "N/A"
            elif event_id == 4624:
                # Successful logon
                user = str(strings[5]) if len(strings) > 5 else "unknown"
                source_ip = str(strings[18]) if len(strings) > 18 else "N/A"
                # Filter out noisy system logons (Logon Type 5, 0, etc) if needed
                # For now, we ingest but severity is 1 (Info)
            elif event_id == 4688:
                # Process Creation
                # strings[5] is usually NewProcessName, strings[8] is CommandLine (if enabled)
                user = str(strings[1]) if len(strings) > 1 else "unknown"
                proc_path = str(strings[5]) if len(strings) > 5 else "unknown"
                cmd_line = str(strings[8]) if len(strings) > 8 else ""
                raw_message = f"Process: {proc_path} {cmd_line}"
            elif event_id == 4720:
                # User created
                user = str(strings[0]) if len(strings) > 0 else "unknown"
            elif event_id == 4726:
                # User deleted
                user = str(strings[0]) if len(strings) > 0 else "unknown"
            elif event_id in [4728, 4732, 4756]:
                # Group member added
                member = str(strings[0]) if len(strings) > 0 else "unknown"
                group = str(strings[2]) if len(strings) > 2 else "unknown"
                raw_message = f"Member {member} added to group {group}"
                user = str(strings[6]) if len(strings) > 6 else "unknown" # Actor
            elif event_id == 7045:
                # Service installed
                svc_name = str(strings[0]) if len(strings) > 0 else "unknown"
                img_path = str(strings[1]) if len(strings) > 1 else "unknown"
                raw_message = f"Service Installed: {svc_name} ({img_path})"
            elif event_id == 1102:
                user = "audit-system"
            
            # Handle timestamp
            try:
                if hasattr(event, 'TimeGenerated') and event.TimeGenerated:
                    timestamp = event.TimeGenerated.isoformat() + "Z"
                else:
                    timestamp = datetime.utcnow().isoformat() + "Z"
            except:
                timestamp = datetime.utcnow().isoformat() + "Z"
            
            # Deterministic Event ID to prevent duplicates
            # Format: HOST-EVENTID-RECORDNUMBER
            unique_id = f"{self.source_host}-{event_id}-{record_number}"
            
            return {
                "event_id": unique_id,
                "timestamp": timestamp,
                "source_host": self.source_host,
                "os_type": self.os_type,
                "event_type": event_type,
                "severity": severity,
                "source_ip": source_ip,
                "user": user,
                "raw_message": raw_message,
                "record_number": record_number  # Keep for tracking
            }
        except Exception as e:
            print(f"    Error parsing event: {e}")
            return None
    
    def collect_events(self, max_events: int = 1000) -> list[dict]:
        """
        Collect recent events from the Windows Security log.
        Reads in batches until we get max_events or run out of new events.
        Returns a list of parsed events.
        """
        events = []
        
        # If win32evtlog not available, just return empty list
        if not WIN32_AVAILABLE:
            return events
        
        try:
            handle = self.get_event_log_handle()
            if not handle:
                return events
            
            total_read = 0
            batch_num = 0
            new_high_water_mark = self.last_record_number
            stop_reading = False
            
            # Keep reading in batches until we have enough events or hit old ones
            while len(events) < max_events and not stop_reading:
                batch_num += 1
                event_list = win32evtlog.ReadEventLog(
                    handle,
                    win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ,
                    0
                )
                
                if not event_list:
                    break
                
                total_read += len(event_list)
                
                for i, event in enumerate(event_list):
                    if len(events) >= max_events:
                        break
                    
                    # Check if we've seen this record before
                    if event.RecordNumber <= self.last_record_number:
                        stop_reading = True
                        break
                    
                    # Track the highest record number we see in this session
                    if event.RecordNumber > new_high_water_mark:
                        new_high_water_mark = event.RecordNumber
                    
                    parsed = self.parse_event(event)
                    if parsed:
                        # Remove internal field before sending if desired, but it's harmless
                        if "record_number" in parsed:
                            del parsed["record_number"]
                        events.append(parsed)
            
            win32evtlog.CloseEventLog(handle)
            
            # Store the new high water mark but don't save state yet
            # State will only be saved after successful send to prevent losing events
            if new_high_water_mark > self.last_record_number:
                self.pending_high_water_mark = new_high_water_mark
            else:
                self.pending_high_water_mark = None
        
        except Exception as e:
            print(f"[ERROR] Error collecting events: {e}")
            import traceback
            traceback.print_exc()
        
        return events
    
    def send_events(self, events: list[dict]) -> bool:
        """Send events to the central API."""
        if not events:
            # Send heartbeat to keep agent active on dashboard
            return self.send_heartbeat()
        
        try:
            headers = {"api-key": self.api_key}
            payload = {"events": events}
            
            response = requests.post(
                f"{self.api_url}/ingest",
                json=payload,
                headers=headers,
                timeout=30  # Increased timeout for slow servers
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"[OK] Sent {result.get('events_processed', 0)} events to API")
                # Only update state after successful send to prevent losing events on failure
                self._update_state_after_success()
                return True
            else:
                print(f"[ERROR] API Error: {response.status_code} - {response.text}")
                # Don't update state on failure - events will be retried next time
                return False
        
        except requests.exceptions.ConnectionError as e:
            print(f"[ERROR] Connection error sending events: {e}")
            print(f"  API URL: {self.api_url}")
            print(f"  Check network connectivity and firewall rules")
            return False
        except requests.exceptions.Timeout:
            print(f"[ERROR] Timeout sending events - server may be unreachable")
            return False
        except Exception as e:
            print(f"[ERROR] Error sending events: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def send_heartbeat(self) -> bool:
        """Send a heartbeat to keep agent marked as active on dashboard."""
        try:
            headers = {
                "api-key": self.api_key,
                "source-host": self.source_host,
                "os-type": self.os_type
            }
            
            response = requests.post(
                f"{self.api_url}/heartbeat",
                headers=headers,
                timeout=30  # Increased timeout for slow servers
            )
            
            if response.status_code == 200:
                print(f"[INFO] Heartbeat sent to {self.api_url}")
                return True
            else:
                print(f"[WARN] Heartbeat failed: {response.status_code}")
                return False
        
        except Exception as e:
            print(f"[WARN] Heartbeat error: {e}")
            return False
    
    def collect_system_status(self) -> dict:
        """Collect detailed system status using psutil."""
        try:
            # CPU
            cpu_usage = psutil.cpu_percent(interval=None)
            cpu_count = psutil.cpu_count()
            
            # Memory
            mem = psutil.virtual_memory()
            
            # Disk (Iterate mounted partitions)
            disk_info = []
            try:
                for part in psutil.disk_partitions(all=False):
                    # Skip CD-ROMs or unready devices
                    if 'cdrom' in part.opts or part.fstype == '':
                        continue
                    
                    try:
                        usage = psutil.disk_usage(part.mountpoint)
                        disk_info.append({
                            "mount": part.mountpoint,
                            "total": usage.total,
                            "used": usage.used,
                            "free": usage.free,
                            "percent": usage.percent
                        })
                    except Exception:
                        # Device likely not ready
                        continue
            except Exception as e:
                print(f"[WARN] Error collecting disk info: {e}")
            
            # Network
            net_info = []
            try:
                interfaces = psutil.net_if_addrs()
                for iface, addrs in interfaces.items():
                    for addr in addrs:
                        if addr.family == socket.AF_INET:  # IPv4 only
                            net_info.append({
                                "interface": iface,
                                "ip": addr.address,
                                "mac": "N/A"
                            })
            except Exception as e:
                print(f"[WARN] Error collecting network info: {e}")
            
            # Processes (Top 10 by CPU)
            top_procs = []
            try:
                for proc in sorted(psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']), 
                                key=lambda p: p.info['cpu_percent'], reverse=True)[:10]:
                    top_procs.append(proc.info)
            except Exception as e:
                print(f"Error getting processes: {e}")
            
            # Boot Time
            boot_time = datetime.fromtimestamp(psutil.boot_time()).isoformat()
            
            return {
                "source_host": self.source_host,
                "os_type": self.os_type,
                "os_details": platform.platform(),
                "cpu_usage": cpu_usage,
                "cpu_count": cpu_count,
                "memory_total": mem.total,
                "memory_used": mem.used,
                "memory_percent": mem.percent,
                "disk_info": disk_info,
                "network_info": net_info,
                "top_processes": top_procs,
                "boot_time": boot_time,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        except Exception as e:
            print(f"[ERROR] Collecting system status: {e}")
            return None

    def send_system_status(self) -> bool:
        """Collect and send system status snapshot."""
        try:
            status_data = self.collect_system_status()
            if not status_data:
                return False
                
            headers = {"api-key": self.api_key}
            payload = {"status": status_data}
            
            response = requests.post(
                f"{self.api_url}/system-status",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"[INFO] System status sent to {self.api_url}")
                return True
            else:
                print(f"[WARN] Failed to send system status: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"[ERROR] Sending system status: {e}")
            return False

    def run(self, interval: int = 60):
        """
        Main agent loop.
        Collect events and send them to the API at regular intervals.
        """
        print(f"Windows Agent starting (host: {self.source_host})")
        print(f"API URL: {self.api_url}")
        print(f"API Key: {'*' * (len(self.api_key) - 8)}{self.api_key[-8:] if len(self.api_key) > 8 else '***'}")
        
        # Test connection on startup
        print("\nTesting API connection...")
        try:
            test_response = requests.get(
                f"{self.api_url}/health",
                headers={"api-key": self.api_key},
                timeout=10
            )
            if test_response.status_code == 200:
                print(f"[OK] API connection successful")
            elif test_response.status_code == 401:
                print(f"[ERROR] API Error: Missing API key header")
            elif test_response.status_code == 403:
                print(f"[ERROR] API Error: Invalid API key")
                print(f"  Current key ends with: ...{self.api_key[-8:]}")
            else:
                print(f"[ERROR] API Error: Status {test_response.status_code}")
        except requests.exceptions.ConnectionError as e:
            print(f"[ERROR] Cannot connect to API server: {e}")
            print(f"  Check that {self.api_url} is reachable")
            print(f"  Verify network connectivity and firewall rules")
        except requests.exceptions.Timeout:
            print(f"[ERROR] Connection timeout - server may be unreachable")
        except Exception as e:
            print(f"[ERROR] Connection test failed: {e}")
        
        print(f"\nStarting event collection loop (interval: {interval}s)...\n")
        
        loop_count = 0
        while True:
            try:
                loop_count += 1
                print(f"[Loop {loop_count}] Collecting events...")
                
                events = self.collect_events(max_events=1000)
                print(f"  Found {len(events)} events to process")
                
                # Always send (either events or heartbeat)
                success = self.send_events(events)
                if not success and events:
                    print(f"  [WARN] Failed to send events - will retry on next cycle")
                
                # Send System Status (RMM)
                self.send_system_status()
                
                print(f"  Sleeping for {interval} seconds...\n")
                time.sleep(interval)
            
            except KeyboardInterrupt:
                print("\nAgent stopped by user")
                break
            except Exception as e:
                print(f"[ERROR] Unexpected error in main loop: {e}")
                import traceback
                traceback.print_exc()
                print(f"  Sleeping for {interval} seconds before retry...\n")
                time.sleep(interval)


def main():
    """Entry point for the Windows agent."""
    
    api_url = os.getenv("SIEM_API_URL", "http://localhost:8000")
    api_key = os.getenv("SIEM_API_KEY", "default-insecure-key-change-me")
    
    agent = WindowsAgent(api_url=api_url, api_key=api_key)
    agent.run(interval=60)


if __name__ == "__main__":
    if sys.platform != "win32":
        print("This agent only runs on Windows")
        sys.exit(1)
    
    main()

