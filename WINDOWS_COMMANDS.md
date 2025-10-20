# Windows Commands for Log Monitoring

## PowerShell Commands (Windows)

### Check Resolution in Logs

```powershell
# View recent app log entries
Get-Content logs\app.log -Tail 20

# Search for resolution in logs
Select-String -Path logs\app.log -Pattern "resolution" -CaseSensitive:$false

# Watch logs in real-time (PowerShell 3.0+)
Get-Content logs\app.log -Wait -Tail 10

# Search for resolution while watching
Get-Content logs\app.log -Wait | Select-String "resolution"
```

### Check Error Log

```powershell
# View all errors
Get-Content logs\errors.log

# Check if errors.log has content
Get-Item logs\errors.log | Select-Object Length, LastWriteTime
```

### Check Events Log

```powershell
# View all events
Get-Content logs\events.log

# View last 10 events
Get-Content logs\events.log -Tail 10
```

### Check Warnings Log

```powershell
# View all warnings
Get-Content logs\warnings.log

# Count warnings
(Get-Content logs\warnings.log).Count
```

## Quick Verification Commands

### 1. Check if Resolution is Confirmed

```powershell
# Should show "Resolution confirmed: 1920x1080"
Select-String -Path logs\app.log -Pattern "Resolution confirmed"
```

**Expected Output**:
```
logs\app.log:XX:INFO - Resolution confirmed: 1920x1080
```

### 2. Check for Resolution Mismatch Errors

```powershell
# Should be empty (no output)
Select-String -Path logs\errors.log -Pattern "RESOLUTION MISMATCH"
```

**Expected**: No output (good!)

### 3. Check Last Few Log Entries

```powershell
# See what's happening
Get-Content logs\app.log -Tail 20
```

### 4. Check All Logs at Once

```powershell
# Quick overview of all logs
Write-Host "`n=== APP LOG ===" -ForegroundColor Cyan
Get-Content logs\app.log -Tail 5

Write-Host "`n=== ERRORS ===" -ForegroundColor Red
Get-Content logs\errors.log -Tail 5

Write-Host "`n=== EVENTS ===" -ForegroundColor Green
Get-Content logs\events.log -Tail 5

Write-Host "`n=== WARNINGS ===" -ForegroundColor Yellow
Get-Content logs\warnings.log -Tail 5
```

## Common Searches

### Find All Errors

```powershell
Select-String -Path logs\*.log -Pattern "ERROR"
```

### Find Stream Events

```powershell
Select-String -Path logs\events.log -Pattern "STREAM|CONNECTION|RECORDING"
```

### Find Frame Issues

```powershell
Select-String -Path logs\warnings.log -Pattern "frame|incomplete"
```

## Create PowerShell Script

Save this as `check-logs.ps1`:

```powershell
# Quick log checker script
param(
    [switch]$Follow,
    [string]$Pattern = ""
)

Write-Host "=== RTP Stream Client - Log Viewer ===" -ForegroundColor Cyan
Write-Host ""

if ($Follow) {
    Write-Host "Watching logs (Press Ctrl+C to stop)..." -ForegroundColor Yellow
    if ($Pattern) {
        Get-Content logs\app.log -Wait | Select-String $Pattern
    } else {
        Get-Content logs\app.log -Wait
    }
} else {
    # Show recent entries
    Write-Host "--- Last 10 App Log Entries ---" -ForegroundColor Green
    Get-Content logs\app.log -Tail 10

    Write-Host "`n--- Last 5 Events ---" -ForegroundColor Green
    Get-Content logs\events.log -Tail 5

    Write-Host "`n--- Errors (if any) ---" -ForegroundColor Red
    $errors = Get-Content logs\errors.log -ErrorAction SilentlyContinue
    if ($errors) {
        $errors | Select-Object -Last 5
    } else {
        Write-Host "No errors found!" -ForegroundColor Green
    }

    Write-Host "`n--- Warnings (if any) ---" -ForegroundColor Yellow
    $warnings = Get-Content logs\warnings.log -ErrorAction SilentlyContinue
    if ($warnings) {
        $warnings | Select-Object -Last 5
    } else {
        Write-Host "No warnings!" -ForegroundColor Green
    }
}
```

**Usage**:
```powershell
# View recent logs
.\check-logs.ps1

# Watch logs in real-time
.\check-logs.ps1 -Follow

# Watch and filter for resolution
.\check-logs.ps1 -Follow -Pattern "resolution"
```

## Alternative: Use CMD Commands

If you prefer Command Prompt (CMD):

```cmd
REM View last 20 lines
powershell -Command "Get-Content logs\app.log -Tail 20"

REM Search for resolution
powershell -Command "Select-String -Path logs\app.log -Pattern 'resolution'"

REM View errors
type logs\errors.log

REM View events
type logs\events.log
```

## Quick Verification Script

Save as `verify-fix.ps1`:

```powershell
Write-Host "=== Resolution Fix Verification ===" -ForegroundColor Cyan
Write-Host ""

# Check for resolution confirmation
Write-Host "Checking resolution confirmation..." -ForegroundColor Yellow
$confirmed = Select-String -Path logs\app.log -Pattern "Resolution confirmed" -ErrorAction SilentlyContinue

if ($confirmed) {
    Write-Host "✅ PASS: " -ForegroundColor Green -NoNewline
    Write-Host $confirmed[-1].Line
} else {
    Write-Host "❌ FAIL: Resolution not confirmed yet" -ForegroundColor Red
}

# Check for mismatch errors
Write-Host "`nChecking for resolution mismatch errors..." -ForegroundColor Yellow
$mismatch = Select-String -Path logs\errors.log -Pattern "RESOLUTION MISMATCH" -ErrorAction SilentlyContinue

if ($mismatch) {
    Write-Host "❌ FAIL: Resolution mismatch detected:" -ForegroundColor Red
    $mismatch | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
} else {
    Write-Host "✅ PASS: No resolution mismatch errors" -ForegroundColor Green
}

# Check for incomplete frames
Write-Host "`nChecking for incomplete frame warnings..." -ForegroundColor Yellow
$incomplete = Select-String -Path logs\warnings.log -Pattern "Incomplete frame" -ErrorAction SilentlyContinue

if ($incomplete) {
    $count = ($incomplete | Measure-Object).Count
    Write-Host "⚠️  WARNING: $count incomplete frame warnings found" -ForegroundColor Yellow
} else {
    Write-Host "✅ PASS: No incomplete frame warnings" -ForegroundColor Green
}

# Check connection status
Write-Host "`nChecking connection events..." -ForegroundColor Yellow
$connected = Select-String -Path logs\events.log -Pattern "CONNECTED" -ErrorAction SilentlyContinue

if ($connected) {
    Write-Host "✅ PASS: Connection established" -ForegroundColor Green
    Write-Host "  $($connected[-1].Line)" -ForegroundColor Gray
} else {
    Write-Host "⚠️  No connection events found" -ForegroundColor Yellow
}

Write-Host "`n=== Summary ===" -ForegroundColor Cyan
Write-Host "Configuration: 1920x1080" -ForegroundColor White
Write-Host "Check logs above for any issues" -ForegroundColor White
```

**Usage**:
```powershell
.\verify-fix.ps1
```

## Real-Time Monitoring (Best Option)

```powershell
# Open 4 PowerShell windows side by side and run:

# Window 1 - App Log
Get-Content logs\app.log -Wait

# Window 2 - Errors
Get-Content logs\errors.log -Wait

# Window 3 - Events
Get-Content logs\events.log -Wait

# Window 4 - Warnings
Get-Content logs\warnings.log -Wait
```

## One-Line Checks

```powershell
# Quick resolution check
Select-String -Path logs\app.log -Pattern "resolution|Resolution" | Select-Object -Last 3

# Quick error check
if (Test-Path logs\errors.log) { Get-Content logs\errors.log } else { "No errors!" }

# Quick status
Select-String -Path logs\events.log -Pattern "STARTUP|CONNECTED|RECORDING" | Select-Object -Last 5
```

## After Starting Application

Run this immediately after starting the app:

```powershell
# Wait 5 seconds for logs to populate
Start-Sleep -Seconds 5

# Check results
Write-Host "Resolution check:"
Select-String -Path logs\app.log -Pattern "Resolution" | Select-Object -Last 1

Write-Host "`nConnection check:"
Select-String -Path logs\events.log -Pattern "CONNECTED" | Select-Object -Last 1

Write-Host "`nAny errors:"
Get-Content logs\errors.log -Tail 5
```

---

## TL;DR - Quick Commands

```powershell
# See if resolution is confirmed (MOST IMPORTANT)
Select-String -Path logs\app.log -Pattern "Resolution confirmed"

# Check for errors
Get-Content logs\errors.log

# Check recent activity
Get-Content logs\app.log -Tail 20

# Watch logs live
Get-Content logs\app.log -Wait
```

**Expected Good Output**:
```
Resolution confirmed: 1920x1080  ✅
```

**Bad Output (if still wrong)**:
```
RESOLUTION MISMATCH! Config: 1920x1080, Actual: XXXX  ❌
```
