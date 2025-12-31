# fix-docker-complete.ps1
Write-Host "Starting Complete Docker Fix..." -ForegroundColor Cyan

# 1. Stop Docker Desktop
Write-Host "`nStep 1: Stopping Docker Desktop..." -ForegroundColor Yellow
Get-Process "*Docker Desktop*" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 5

# 2. Configure Shecan DNS
Write-Host "`nStep 2: Configuring Shecan DNS..." -ForegroundColor Yellow
$adapter = Get-NetAdapter | Where-Object {$_.Status -eq "Up"} | Select-Object -First 1
if ($adapter) {
    Set-DnsClientServerAddress -InterfaceIndex $adapter.ifIndex -ServerAddresses ("178.22.122.100","185.51.200.2")
    Write-Host "DNS set to Shecan" -ForegroundColor Green
} else {
    Write-Host "No active network adapter found!" -ForegroundColor Red
}

# 3. Create daemon.json with Iranian mirrors
Write-Host "`nStep 3: Creating daemon.json with Iranian mirrors..." -ForegroundColor Yellow
$daemonJsonPath = "C:\ProgramData\Docker\daemon.json"
$daemonConfig = @{
    "registry-mirrors" = @(
        "https://registry.docker.ir",
        "https://docker.arvancloud.ir"
    )
    "dns" = @("178.22.122.100", "185.51.200.2")
    "insecure-registries" = @("registry.docker.ir", "docker.arvancloud.ir")
    "max-concurrent-downloads" = 10
    "max-concurrent-uploads" = 10
}

$jsonContent = $daemonConfig | ConvertTo-Json -Depth 10
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($daemonJsonPath, $jsonContent, $utf8NoBom)
Write-Host "daemon.json created" -ForegroundColor Green

# 4. Start Docker Desktop
Write-Host "`nStep 4: Starting Docker Desktop..." -ForegroundColor Yellow
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
Write-Host "Waiting for Docker to start (30 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# 5. Wait for Docker daemon
Write-Host "`nStep 5: Waiting for Docker daemon..." -ForegroundColor Yellow
$maxRetries = 12
$retryCount = 0
while ($retryCount -lt $maxRetries) {
    try {
        docker info *>$null
        Write-Host "Docker daemon is ready!" -ForegroundColor Green
        break
    } catch {
        $retryCount++
        Write-Host "Retry $retryCount/$maxRetries..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
    }
}

if ($retryCount -eq $maxRetries) {
    Write-Host "Docker daemon failed to start!" -ForegroundColor Red
    exit 1
}

# 6. Test Docker connection
Write-Host "`nStep 6: Testing Docker connection..." -ForegroundColor Yellow
docker info | Select-String "Registry"
docker info | Select-String "DNS"

# 7. Pull images from Iranian mirror
Write-Host "`nStep 7: Pulling images from Iranian mirror..." -ForegroundColor Yellow

$images = @(
    "mongo:7",
    "postgres:16-alpine",
    "redis:7-alpine",
    "rabbitmq:3-management-alpine"
)

foreach ($image in $images) {
    Write-Host "`nPulling $image..." -ForegroundColor Cyan
    try {
        docker pull $image
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Successfully pulled $image" -ForegroundColor Green
        } else {
            Write-Host "Failed to pull $image, trying with registry prefix..." -ForegroundColor Yellow
            docker pull "registry.docker.ir/$image"
        }
    } catch {
        Write-Host "Failed to pull $image : $_" -ForegroundColor Red
    }
}

# 8. List downloaded images
Write-Host "`nStep 8: Listing downloaded images..." -ForegroundColor Yellow
docker images

Write-Host "`nDocker fix completed!" -ForegroundColor Green
Write-Host "`nNow run: pnpm docker:up" -ForegroundColor Cyan