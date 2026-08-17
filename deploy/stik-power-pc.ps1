# Sample this PC's power draw and push it to stik.wtf.
#
# GPU watts come from nvidia-smi (measured, per card). CPU package watts come from
# LibreHardwareMonitor's web server if it is running on http://localhost:8085 — without
# it the CPU is simply left out rather than guessed at. Nothing here needs admin.
#
# Setup:  copy to C:\Users\<you>\stik\, set $Token/$PushUrl below, then register a task:
#   schtasks /create /tn "stik power" /sc minute /mo 1 /f `
#     /tr "powershell -NoProfile -WindowStyle Hidden -File C:\Users\<you>\stik\stik-power-pc.ps1"
# Remove any time:  schtasks /delete /tn "stik power" /f
# Test once:  powershell -File stik-power-pc.ps1 -Print

param([switch]$Print)

# Token: env var if present, else token.txt beside this script. The scheduled task runs
# as SYSTEM (so no console window ever flashes), and SYSTEM does not see user env vars —
# hence the file.
$Token = $env:STIK_POWER_TOKEN
if (-not $Token) {
    $tf = Join-Path $PSScriptRoot "token.txt"
    if (Test-Path $tf) { $Token = (Get-Content $tf -Raw).Trim() }
}
$PushUrl = "https://stik.wtf/api/power"

$detail = @{}
$total  = 0.0

# --- GPUs (always available with the NVIDIA driver) ---
try {
    $lines = & nvidia-smi --query-gpu=index,name,power.draw --format=csv,noheader,nounits 2>$null
    foreach ($l in $lines) {
        if (-not $l) { continue }
        $f = $l -split ',\s*'
        $w = [double]$f[2]
        $key = "gpu" + $f[0]
        $detail[$key] = [math]::Round($w, 1)
        $total += $w
    }
} catch { }

# --- CPU package, only if LibreHardwareMonitor is serving its JSON ---
try {
    $lhm = Invoke-RestMethod -Uri "http://localhost:8085/data.json" -TimeoutSec 3 -ErrorAction Stop
    $stack = New-Object System.Collections.Stack
    $stack.Push($lhm)
    while ($stack.Count -gt 0) {
        $n = $stack.Pop()
        if ($n.Text -match 'Package' -and $n.Value -match 'W$') {
            $w = [double]($n.Value -replace '[^\d\.]', '')
            if ($w -gt 0 -and -not $detail.ContainsKey('cpu')) {
                $detail['cpu'] = [math]::Round($w, 1)
                $total += $w
            }
        }
        foreach ($c in $n.Children) { $stack.Push($c) }
    }
} catch { }

if ($Print) {
    $detail.GetEnumerator() | Sort-Object Name | ForEach-Object { "{0,-8} {1,6:N1} W" -f $_.Key, $_.Value }
    "{0,-8} {1,6:N1} W" -f "TOTAL", $total
}

if (-not $Token -or $total -le 0) {
    if ($Print) { "not pushing (no token, or nothing measured)" }
    exit 0
}

$body = @{ source = "pc"; watts = [math]::Round($total, 1); detail = $detail } | ConvertTo-Json -Compress
try {
    $r = Invoke-RestMethod -Uri $PushUrl -Method Post -Body $body -ContentType "application/json" `
         -Headers @{ "X-Power-Token" = $Token } -TimeoutSec 15
    if ($Print) { "pushed: " + ($r.ok) }
} catch {
    if ($Print) { "push failed: $_" }
    exit 1
}
