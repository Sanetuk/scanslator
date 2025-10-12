Param(
    [switch]$Detach
)

$composeArgs = @("compose", "up", "--build")
if ($Detach) {
    $composeArgs += "-d"
}

Write-Host "Running: docker $($composeArgs -join ' ')" -ForegroundColor Cyan
docker @composeArgs
if ($LASTEXITCODE -ne 0) {
    Write-Error "docker compose exited with code $LASTEXITCODE"
    exit $LASTEXITCODE
}

Write-Host "`nAll containers built and started successfully." -ForegroundColor Green
docker compose ps
