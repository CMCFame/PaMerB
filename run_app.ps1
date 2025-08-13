# PaMerB IVR Converter - PowerShell App Runner
# This script starts or restarts the Streamlit app on port 8506

param(
    [switch]$Restart,
    [switch]$Stop,
    [switch]$Status,
    [int]$Port = 8506
)

# Configuration
$AppName = "PaMerB IVR Converter"
$AppFile = "app.py"
$ProcessName = "streamlit"

# Function to check if app is running
function Test-AppRunning {
    $processes = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue | 
                 Where-Object { $_.ProcessName -eq $ProcessName }
    
    foreach ($proc in $processes) {
        $commandLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($proc.Id)").CommandLine
        if ($commandLine -like "*$AppFile*" -and $commandLine -like "*$Port*") {
            return $proc
        }
    }
    return $null
}

# Function to stop the app
function Stop-App {
    Write-Host "[STOPPING] Checking for running $AppName instances..." -ForegroundColor Yellow
    
    $runningProcess = Test-AppRunning
    if ($runningProcess) {
        Write-Host "[INFO] Found running process (PID: $($runningProcess.Id))" -ForegroundColor Cyan
        try {
            Stop-Process -Id $runningProcess.Id -Force
            Start-Sleep -Seconds 2
            Write-Host "[OK] App stopped successfully" -ForegroundColor Green
            return $true
        }
        catch {
            Write-Host "[ERROR] Failed to stop app: $($_.Exception.Message)" -ForegroundColor Red
            return $false
        }
    }
    else {
        Write-Host "[INFO] No running instances found" -ForegroundColor Cyan
        return $true
    }
}

# Function to start the app
function Start-App {
    Write-Host "[STARTING] $AppName on port $Port..." -ForegroundColor Yellow
    
    # Check if app file exists
    if (-not (Test-Path $AppFile)) {
        Write-Host "[ERROR] $AppFile not found in current directory" -ForegroundColor Red
        Write-Host "[TIP] Make sure you're in the correct directory" -ForegroundColor Yellow
        return $false
    }
    
    # Check if Python is available
    try {
        $pythonVersion = python --version 2>&1
        Write-Host "[INFO] Using Python: $pythonVersion" -ForegroundColor Cyan
    }
    catch {
        Write-Host "[ERROR] Python not found. Please install Python first." -ForegroundColor Red
        return $false
    }
    
    # Check if Streamlit is installed
    try {
        $streamlitVersion = python -m streamlit version 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Streamlit not installed"
        }
        Write-Host "[INFO] Streamlit is available" -ForegroundColor Cyan
    }
    catch {
        Write-Host "[ERROR] Streamlit not installed" -ForegroundColor Red
        Write-Host "[TIP] Run: pip install -r requirements.txt" -ForegroundColor Yellow
        return $false
    }
    
    # Check AWS credentials configuration
    $secretsPath = "$env:USERPROFILE\.streamlit\secrets.toml"
    if (Test-Path $secretsPath) {
        Write-Host "[INFO] Streamlit secrets file found - AWS credentials configured" -ForegroundColor Green
    }
    else {
        Write-Host "[WARNING] No secrets.toml found - DynamoDB features may not work" -ForegroundColor Yellow
        Write-Host "[TIP] Create: $secretsPath with AWS credentials" -ForegroundColor Yellow
    }
    
    # Start the app
    try {
        Write-Host "[INFO] Starting Streamlit app..." -ForegroundColor Cyan
        Write-Host "[INFO] App will be available at: http://localhost:$Port" -ForegroundColor Green
        Write-Host "[INFO] Press Ctrl+C to stop the app" -ForegroundColor Yellow
        Write-Host "" # Empty line
        Write-Host "=" * 60 -ForegroundColor Gray
        
        # Start Streamlit in the background and capture the process
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = "python"
        $psi.Arguments = "-m streamlit run $AppFile --server.port $Port --server.address localhost"
        $psi.UseShellExecute = $false
        $psi.RedirectStandardOutput = $false
        $psi.RedirectStandardError = $false
        $psi.CreateNoWindow = $false
        
        $process = [System.Diagnostics.Process]::Start($psi)
        
        # Wait a moment and check if it started successfully
        Start-Sleep -Seconds 3
        
        $runningProcess = Test-AppRunning
        if ($runningProcess) {
            Write-Host "[OK] App started successfully (PID: $($runningProcess.Id))" -ForegroundColor Green
            Write-Host "[INFO] Opening browser..." -ForegroundColor Cyan
            Start-Process "http://localhost:$Port"
            
            # Keep PowerShell window open and monitor
            Write-Host "[INFO] App is running. Press any key to stop..." -ForegroundColor Yellow
            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
            
            # Stop the app when user presses a key
            Stop-App
            return $true
        }
        else {
            Write-Host "[ERROR] Failed to start app" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "[ERROR] Failed to start app: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Function to show app status
function Show-Status {
    Write-Host "=== $AppName Status ===" -ForegroundColor Cyan
    
    $runningProcess = Test-AppRunning
    if ($runningProcess) {
        Write-Host "[RUNNING] Process ID: $($runningProcess.Id)" -ForegroundColor Green
        Write-Host "[INFO] App URL: http://localhost:$Port" -ForegroundColor Cyan
        Write-Host "[INFO] Started: $($runningProcess.StartTime)" -ForegroundColor Cyan
    }
    else {
        Write-Host "[STOPPED] No running instances found" -ForegroundColor Yellow
    }
}

# Main script logic
Write-Host ""
Write-Host "=== $AppName - PowerShell Runner ===" -ForegroundColor Cyan
Write-Host ""

# Change to script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($scriptDir) {
    Set-Location $scriptDir
    Write-Host "[INFO] Working directory: $scriptDir" -ForegroundColor Cyan
}

# Handle command line arguments
if ($Status) {
    Show-Status
}
elseif ($Stop) {
    Stop-App
}
elseif ($Restart) {
    Write-Host "[RESTART] Restarting $AppName..." -ForegroundColor Yellow
    if (Stop-App) {
        Start-Sleep -Seconds 1
        Start-App
    }
    else {
        Write-Host "[ERROR] Failed to stop existing app" -ForegroundColor Red
    }
}
else {
    # Default action: start (or restart if already running)
    $runningProcess = Test-AppRunning
    if ($runningProcess) {
        Write-Host "[INFO] App is already running (PID: $($runningProcess.Id))" -ForegroundColor Yellow
        $choice = Read-Host "[QUESTION] Restart the app? (y/N)"
        if ($choice -eq "y" -or $choice -eq "Y") {
            if (Stop-App) {
                Start-Sleep -Seconds 1
                Start-App
            }
        }
        else {
            Write-Host "[INFO] Opening browser to existing app..." -ForegroundColor Cyan
            Start-Process "http://localhost:$Port"
        }
    }
    else {
        Start-App
    }
}

Write-Host ""
Write-Host "=== Script completed ===" -ForegroundColor Gray