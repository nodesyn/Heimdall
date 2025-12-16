import sys
import os
import logging
from pathlib import Path

log_dir = Path(os.getenv("HEIMDALL_LOG_DIR", "C:\\Heimdall\\logs"))
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "heimdall-agent.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

try:
    import win32serviceutil
    import win32service
    import servicemanager
    import win32timezone  # Required by win32serviceutil.HandleCommandLine
except ImportError as e:
    logger.error("pywin32 not installed: " + str(e))
    sys.exit(1)

from agent_windows import WindowsAgent


class HeimdallWindowsService(win32serviceutil.ServiceFramework):
    """Heimdall Windows Service"""

    _svc_name_ = "HeimdallAgent"
    _svc_display_name_ = "Heimdall Security Agent"
    _svc_description_ = "Monitors Windows Security logs and sends events to Heimdall SIEM"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.is_alive = True
        self.agent = None

    def SvcStop(self):
        logger.info("Service stop requested")
        self.is_alive = False

    def SvcDoRun(self):
        logger.info("Heimdall Windows Agent Service starting")

        try:
            api_url = os.getenv("SIEM_API_URL", "http://localhost:8000")
            api_key = os.getenv("SIEM_API_KEY", "default-insecure-key-change-me")
            interval = int(os.getenv("SIEM_AGENT_INTERVAL", "60"))

            logger.info("Starting agent with API URL: " + api_url)
            logger.info("Event collection interval: " + str(interval) + "s")

            self.agent = WindowsAgent(api_url=api_url, api_key=api_key)
            
            # Test API connection on startup
            try:
                import requests
                logger.info("Testing API connection...")
                test_response = requests.get(
                    f"{api_url}/health",
                    headers={"api-key": api_key},
                    timeout=10
                )
                if test_response.status_code == 200:
                    logger.info("API connection successful")
                elif test_response.status_code == 401:
                    logger.error("API Error: Missing API key header")
                elif test_response.status_code == 403:
                    logger.error("API Error: Invalid API key")
                else:
                    logger.warning("API returned status: " + str(test_response.status_code))
            except requests.exceptions.ConnectionError as e:
                logger.error("Cannot connect to API server: " + str(e))
                logger.error("Check that " + api_url + " is reachable and firewall rules allow connections")
            except Exception as e:
                logger.warning("API connection test failed: " + str(e))

            loop_count = 0
            while self.is_alive:
                try:
                    loop_count += 1
                    logger.info("Loop " + str(loop_count) + " collecting events...")

                    events = self.agent.collect_events(max_events=1000)
                    logger.info("Found " + str(len(events)) + " events to send")

                    success = self.agent.send_events(events)
                    if success:
                        if events:
                            logger.info("Successfully sent " + str(len(events)) + " events to " + api_url)
                        else:
                            logger.info("Sent heartbeat to " + api_url)
                    else:
                        if events:
                            logger.warning("Failed to send " + str(len(events)) + " events to " + api_url + " - will retry on next cycle")
                            logger.warning("Events will be retried to prevent data loss")
                        else:
                            logger.warning("Failed to send heartbeat to " + api_url + " - server may be slow or unreachable")

                    if not self.is_alive:
                        break

                    for _ in range(interval):
                        if not self.is_alive:
                            break
                        import time
                        time.sleep(1)

                except Exception as e:
                    logger.error("Error in main loop: " + str(e), exc_info=True)
                    import time
                    time.sleep(interval)

        except Exception as e:
            logger.error("Service error: " + str(e), exc_info=True)

        finally:
            logger.info("Heimdall Windows Agent Service stopping")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd in ["install", "remove", "start", "stop", "restart", "debug"]:
            try:
                # Use HandleCommandLine for standard service commands
                # This is the recommended way for ServiceFramework classes
                win32serviceutil.HandleCommandLine(HeimdallWindowsService)
                
                # After install, set service to auto-start
                if cmd == "install":
                    try:
                        import time
                        time.sleep(1)  # Give Windows time to register the service
                        scm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
                        try:
                            service = win32service.OpenService(scm, HeimdallWindowsService._svc_name_, win32service.SERVICE_ALL_ACCESS)
                            try:
                                # Query current service configuration first
                                config = win32service.QueryServiceConfig(service)
                                # config returns: (serviceType, startType, errorControl, binaryPath, 
                                #                  loadOrderGroup, tagId, dependencies, serviceStartName, 
                                #                  displayName)
                                
                                # ChangeServiceConfig takes 11 arguments:
                                # hService, dwServiceType, dwStartType, dwErrorControl, 
                                # lpBinaryPathName, lpLoadOrderGroup, lpdwTagId, lpDependencies,
                                # lpServiceStartName, lpPassword, lpDisplayName
                                # Use current values from QueryServiceConfig, only change startType
                                win32service.ChangeServiceConfig(
                                    service,                              # hService
                                    config[0],                            # dwServiceType (keep current)
                                    win32service.SERVICE_AUTO_START,      # dwStartType (change this)
                                    config[2],                            # dwErrorControl (keep current)
                                    config[3],                            # lpBinaryPathName (keep current)
                                    config[4],                            # lpLoadOrderGroup (keep current)
                                    config[5],                            # lpdwTagId (keep current)
                                    config[6],                            # lpDependencies (keep current)
                                    config[7],                            # lpServiceStartName (keep current)
                                    None,                                 # lpPassword (keep current)
                                    config[8]                             # lpDisplayName (keep current)
                                )
                                logger.info("Service set to auto-start")
                            finally:
                                win32service.CloseServiceHandle(service)
                        finally:
                            win32service.CloseServiceHandle(scm)
                    except Exception as e:
                        logger.warning("Could not set auto-start: " + str(e))
            except Exception as e:
                print("Error: " + str(e))
                logger.error("Command error: " + str(e))
                sys.exit(1)
        else:
            print("Unknown command: " + cmd)
            print("Available commands: install, remove, start, stop, restart, debug")
    else:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(HeimdallWindowsService)
        servicemanager.StartServiceCtrlDispatcher()
