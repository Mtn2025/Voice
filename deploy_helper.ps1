
$destination = "voice_orchestrator_deploy.zip"

Write-Host "Packaging Voice Orchestrator for VPS Deployment..." -ForegroundColor Green

# Remove old zip if exists
if (Test-Path $destination) {
    Remove-Item $destination
}

# Create Zip (requiere PowerShell 5+)
Compress-Archive -Path "app", "nginx", "Dockerfile", "docker-compose.yml", "requirements.txt" -DestinationPath $destination -Force

Write-Host "Package created: $destination" -ForegroundColor Cyan
Write-Host "Upload this file to your VPS and run: unzip voice_orchestrator_deploy.zip && docker-compose up -d --build" -ForegroundColor Yellow
