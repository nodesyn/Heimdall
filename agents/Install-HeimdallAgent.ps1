# Heimdall Windows Agent Installation Script (PowerShell)
# Run as Administrator for service installation
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File Install-HeimdallAgent.ps1

param(
    [string]$ApiUrl = $null,
    [string]$ApiKey = $null,
    [int]$Interval = 60,
    [string]$InstallPath = "C:\Heimdall"
)

# Ensure running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")

if (-not $isAdmin) {
    Write-Host "[ERROR] This script must be run as Administrator" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please run PowerShell as Administrator and try again"
    exit 1
}

# Load configuration from agent.env if available
$EnvFile = Join-Path $PSScriptRoot "agent.env"
if (Test-Path $EnvFile) {
    Write-Host "[*] Loading configuration from agent.env..."
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            
            switch ($key) {
                "SIEM_API_URL" { if (-not $ApiUrl) { $ApiUrl = $value } }
                "SIEM_API_KEY" { if (-not $ApiKey) { $ApiKey = $value } }
                "SIEM_AGENT_INTERVAL" { $Interval = [int]$value }
            }
        }
    }
}

# Set defaults if still null
if (-not $ApiUrl) { $ApiUrl = "http://localhost:8000" }
if (-not $ApiKey) { $ApiKey = "default-insecure-key-change-me" }

Write-Host ""
Write-Host "========================================"
Write-Host "  Heimdall Windows Agent Installer"
Write-Host "========================================"
Write-Host ""

# Create directories
Write-Host "[*] Creating directories..."
$LogDir = "$InstallPath\logs"
$DataDir = "$InstallPath\data"

foreach ($dir in $InstallPath, $LogDir, $DataDir) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "    Created: $dir"
    } else {
        Write-Host "    Exists: $dir"
    }
}

# Check for Python script source
$PyScript = Join-Path $PSScriptRoot "agent_windows.py"
$UsePython = Test-Path $PyScript

if ($UsePython) {
    Write-Host "[*] Found Python source script ($PyScript)."
    Write-Host "    Installing as direct Python service (Recommended)."
    
    # 1. Check Python
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        Write-Host "[ERROR] Python not found in PATH." -ForegroundColor Red
        Write-Host "Please install Python 3.10+ and add to PATH, then re-run."
        exit 1
    }
    
    # 2. Install Dependencies
    Write-Host "[*] Installing Python dependencies..."
    try {
        pip install --upgrade requests psutil pywin32 python-dateutil | Out-Null
        Write-Host "    Dependencies installed." -ForegroundColor Green
    } catch {
        Write-Host "[WARN] Failed to install pip packages. Ensure pip is working." -ForegroundColor Yellow
    }
    
    # 3. Download/Check NSSM
    $NssmPath = Join-Path $InstallPath "nssm.exe"
    if (-not (Test-Path $NssmPath)) {
        Write-Host "[*] Downloading NSSM..."
        $NssmUrl = "https://nssm.cc/release/nssm-2.24.zip"
        $ZipPath = Join-Path $env:TEMP "nssm.zip"
        try {
            Invoke-WebRequest -Uri $NssmUrl -OutFile $ZipPath
            Expand-Archive -Path $ZipPath -DestinationPath $env:TEMP -Force
            # Move 64-bit nssm
            Copy-Item -Path "$env:TEMP\nssm-2.24\win64\nssm.exe" -Destination $NssmPath -Force
            Write-Host "    NSSM installed to $NssmPath" -ForegroundColor Green
        } catch {
            Write-Host "[ERROR] Failed to download/install NSSM: $_" -ForegroundColor Red
            exit 1
        }
    }
    
    # 4. Copy Script (only if source is different from destination)
    $DestScript = Join-Path $InstallPath "agent_windows.py"
    if ($PyScript -ne $DestScript) {
        Copy-Item -Path $PyScript -Destination $DestScript -Force
    } else {
        Write-Host "    Python script already in target directory. Skipping copy."
    }
    
    # 5. Install Service via NSSM
    Write-Host "[*] Installing Service via NSSM..."
    $PythonExe = (Get-Command python).Source
    
    & $NssmPath stop "HeimdallAgent" 2>&1 | Out-Null
    & $NssmPath remove "HeimdallAgent" confirm 2>&1 | Out-Null
    
    & $NssmPath install "HeimdallAgent" $PythonExe "$DestScript"
    & $NssmPath set "HeimdallAgent" AppDirectory "$InstallPath"
    
    # Format Env Vars for NSSM (newline separated)
    $EnvVars = "SIEM_API_URL=$ApiUrl`nSIEM_API_KEY=$ApiKey`nSIEM_AGENT_INTERVAL=$Interval`nHEIMDALL_LOG_DIR=$LogDir`nPYTHONUNBUFFERED=1"
    & $NssmPath set "HeimdallAgent" AppEnvironmentExtra $EnvVars
    
    # Redirect I/O
    & $NssmPath set "HeimdallAgent" AppStdout "$LogDir\agent.log"
    & $NssmPath set "HeimdallAgent" AppStderr "$LogDir\agent.err.log"
    & $NssmPath set "HeimdallAgent" AppRotateFiles 1
    & $NssmPath set "HeimdallAgent" AppRotateOnline 1
    & $NssmPath set "HeimdallAgent" AppRotateSeconds 86400
    & $NssmPath set "HeimdallAgent" AppRotateBytes 5242880
    
    # Start
    Start-Service "HeimdallAgent"
    Write-Host "[OK] Service started! Check $LogDir\agent.log for output." -ForegroundColor Green
    
    exit 0
}

# Fallback to EXE logic if python script not found
Write-Host "[*] Python script not found, looking for compiled EXE..."
$SourceExe = Join-Path $PSScriptRoot "HeimdallAgent.exe"
# ... (rest of existing EXE logic continues below)
