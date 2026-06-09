$targetDir = "ProgressReport_Week5/figures/IRVE-3 HIAD Progress Report Figure"
New-Item -ItemType Directory -Force -Path $targetDir | Out-Null

Write-Host "Started overnight monitor for hiad-runner..."
$running = $true
while ($running) {
    Start-Sleep -Seconds 60
    $output = docker ps | Select-String "hiad-runner"
    if (-not $output) {
        $running = $false
    }
}

Write-Host "Docker simulation finished. Waiting for Python to render plots..."
Start-Sleep -Seconds 120

if (Test-Path "web/assets/plots/mach_map_smooth.png") {
    $file = Get-Item "web/assets/plots/mach_map_smooth.png"
    if ($file.Length -gt 10000) {
        Write-Host "Valid bowshock plot detected. Copying to Progress Report..."
        Copy-Item "web/assets/plots/*_smooth.png" -Destination $targetDir -Force
        Copy-Item "web/assets/plots/*_smooth.jpg" -Destination $targetDir -Force
        Write-Host "Overnight task completed successfully."
    } else {
        Write-Host "Error: Plot file is too small, might be broken."
    }
} else {
    Write-Host "Error: Plot was not produced."
}
