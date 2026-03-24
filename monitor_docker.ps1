# ========================================================
# MC Trading System - DOCKER DASHBOARD
# ========================================================

# --- User Thresholds & Frequency ---
$MONITOR_INTERVAL = 60
$ALERT_COOLDOWN_MIN = 10
$CPU_THRESHOLD = 80.0
$MEM_THRESHOLD = 80.0
$MAX_FAILURES = 3

$global:LAST_ALERT_TIME = [DateTime]::MinValue
$global:FAILURE_TRACKER = @{}

# 1. ENV CONFIG LOADING
function Load-Config {
    $envPath = Join-Path (Get-Location).Path ".env"
    $conf = @{ Path = $envPath; Email = "example@gmail.com"; Status = "NOT FOUND"; User = ""; Pass = "" }
    
    if (Test-Path $envPath) {
        $conf.Status = "LOADED"
        $rawLines = Get-Content $envPath
        foreach ($line in $rawLines) {
            $l = $line.Trim()
            if ($l -like "WARNING_EMAIL=*") { $conf.Email = $l.Substring($l.IndexOf("=") + 1).Trim().Trim('"').Trim("'") }
            if ($l -like "ALERT_EMAIL=*")   { $conf.Email = $l.Substring($l.IndexOf("=") + 1).Trim().Trim('"').Trim("'") }
            if ($l -like "SMTP_USER=*")     { $conf.User  = $l.Substring($l.IndexOf("=") + 1).Trim().Trim('"').Trim("'") }
            if ($l -like "SMTP_PASS=*")     { $conf.Pass  = $l.Substring($l.IndexOf("=") + 1).Trim().Trim('"').Trim("'") }
        }
    }
    return $conf
}

# 2. EMAIL ALERT LOGIC
function Send-AlertEmail {
    param($cfg, [string]$Message)
    $now = Get-Date
    if (($now - $global:LAST_ALERT_TIME).TotalMinutes -lt $ALERT_COOLDOWN_MIN) { return }
    if ([string]::IsNullOrWhiteSpace($cfg.Pass) -or [string]::IsNullOrWhiteSpace($cfg.User)) { return }

    try {
        $secPass = $cfg.Pass | ConvertTo-SecureString -AsPlainText -Force
        $cred = New-Object System.Management.Automation.PSCredential($cfg.User, $secPass)
        Send-MailMessage -From $cfg.User -To $cfg.Email -Subject "[MC TRADING] DOCKER ALERT" `
                         -Body $Message -SmtpServer "smtp.gmail.com" -Port 587 -UseSsl -Credential $cred
        $global:LAST_ALERT_TIME = $now
        Write-Host "  [EMAIL] Alert successfully sent to $($cfg.Email)!" -ForegroundColor Yellow
    } catch {
        Write-Host "  [EMAIL ERROR] Failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# 3. WARM-UP
Write-Host "Waiting for Docker Engine to be ready..." -ForegroundColor Gray
while (-not (docker ps 2>$null)) { Start-Sleep -Seconds 5 }

$LOGICAL_TARGETS = @(
    "postgres", "redis", "api_server", "trading_engine", 
    "market_data_streamer", "auth_manager", "trade_manager", "frontend"
)

# 4. MONITOR LOOP
while ($true) {
    $cfg = Load-Config
    
    $existingContainers = docker ps -a --format "{{.Names}}"
    $actualNames = @()
    $nameMap = @{}
    
    foreach ($lt in $LOGICAL_TARGETS) {
        $found = $false
        $cleanTarget = $lt -replace "_", "[-_]"
        $pattern = "^(mc-)?$cleanTarget$"

        foreach ($real in $existingContainers) {
            if ($real -match $pattern) {
                $nameMap[$lt] = $real
                $actualNames += $real
                $found = $true
                break
            }
        }
        if (-not $found) { $nameMap[$lt] = $lt }
    }

    # Batch Fetch Status & Stats
    $psOut = docker ps -a --format "{{.Names}}|{{.State}}|{{.Status}}" 2>$null
    $psDict = @{}
    if ($psOut) {
        foreach ($line in $psOut) {
            $parts = $line.Split('|')
            if ($parts.Count -ge 2) { $psDict[$parts[0]] = @{ State = $parts[1].ToLower(); Status = $parts[2] } }
        }
    }
    
    $statsOut = docker stats $actualNames --no-stream --format "{{json .}}" 2>$null
    $statsDict = @{}
    if ($statsOut) {
        foreach ($line in $statsOut) {
            try { $obj = $line | ConvertFrom-Json; $statsDict[$obj.Name] = $obj } catch {}
        }
    }

    Clear-Host
    Write-Host "--- MC TRADING DOCKER MONITOR ---" -ForegroundColor Yellow
    Write-Host "Config : $($cfg.Status) | Email: $($cfg.Email)" -ForegroundColor Gray
    Write-Host "---------------------------------------------------------------------------------"
    Write-Host ("{0,-25} {1,-10} {2,-25} {3,-15}" -f "SERVICE", "CPU %", "MEM %", "STATUS")
    Write-Host "---------------------------------------------------------------------------------"

    $criticalAlerts = @()

    foreach ($lt in $LOGICAL_TARGETS) {
        $realName = $nameMap[$lt]
        $state = "missing"; if ($psDict.ContainsKey($realName)) { $state = $psDict[$realName].State }
        
        $cpu = "-"; $memPerc = "-"; $isOverloaded = $false

        if ($statsDict.ContainsKey($realName)) {
            $cpu = $statsDict[$realName].CPUPerc; $memPerc = $statsDict[$realName].MemPerc
            try {
                $cpuVal = [double]($cpu -replace "%", "")
                $memVal = [double]($memPerc -replace "%", "")
                if ($cpuVal -gt $CPU_THRESHOLD -or $memVal -gt $MEM_THRESHOLD) { $isOverloaded = $true }
            } catch {}
        }

        if ($state -eq "running" -and -not $isOverloaded) {
            $global:FAILURE_TRACKER[$lt] = 0
            Write-Host ("{0,-25} {1,-10} {2,-25} {3,-15}" -f $lt, $cpu, $memPerc, "[ONLINE]") -ForegroundColor Green
        } else {
            $global:FAILURE_TRACKER[$lt] = [int]($global:FAILURE_TRACKER[$lt]) + 1
            $curFail = $global:FAILURE_TRACKER[$lt]
            $dispColor = "Red"; if ($isOverloaded -and $state -eq "running") { $dispColor = "Yellow" }
            $statusText = if ($isOverloaded -and $state -eq "running") { "[OVERLOAD]" } else { "[$($state.ToUpper())]" }

            Write-Host ("{0,-25} {1,-10} {2,-25} {3,-15} (Fail: $curFail)" -f $lt, $cpu, $memPerc, $statusText) -ForegroundColor $dispColor

            if ($curFail -ge $MAX_FAILURES) {
                $criticalAlerts += "$lt ($statusText. CPU: $cpu, Mem: $memPerc)"
            }
        }
    }

    if ($criticalAlerts.Count -gt 0 -and $cfg.Status -eq "LOADED") {
        $msg = "MC Trading Alert! Services failing: " + ($criticalAlerts -join ", ")
        Send-AlertEmail -cfg $cfg -Message $msg
    }

    Write-Host "`n---------------------------------------------------------------------------------"
    Write-Host "Refreshing every $MONITOR_INTERVAL seconds... (Ctrl+C to quit)"
    Start-Sleep -Seconds $MONITOR_INTERVAL
}
