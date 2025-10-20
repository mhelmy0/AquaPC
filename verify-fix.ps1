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
    Write-Host "⚠️  No connection events found yet" -ForegroundColor Yellow
}

Write-Host "`n=== Summary ===" -ForegroundColor Cyan
Write-Host "Configuration: 1920x1080" -ForegroundColor White
Write-Host "Check results above" -ForegroundColor White
Write-Host ""
