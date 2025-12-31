# check-images.ps1

Write-Host "=== Checking Required Images ===" -ForegroundColor Cyan

$requiredImages = @{
    "postgres:16-alpine" = "Postgres"
    "mongo:7" = "MongoDB"
    "elasticsearch:8.11.0" = "Elasticsearch"
    "redis:7-alpine" = "Redis"
    "rabbitmq:3-management-alpine" = "RabbitMQ"
    "minio/minio:latest" = "MinIO"
    "prom/prometheus:v2.48.0" = "Prometheus"
    "grafana/grafana:10.2.0" = "Grafana"
    "oliver006/redis_exporter:latest" = "Redis Exporter"
    "prometheuscommunity/postgres-exporter:latest" = "Postgres Exporter"
    "percona/mongodb_exporter:0.40.0" = "MongoDB Exporter"
    "prom/blackbox-exporter:latest" = "Blackbox Exporter"
}

$missing = @()
$found = @()

Write-Host "`nChecking images..." -ForegroundColor Yellow

foreach ($image in $requiredImages.Keys) {
    $check = docker images -q $image 2>$null
    
    if ($check) {
        Write-Host "  [OK] $($requiredImages[$image]) ($image)" -ForegroundColor Green
        $found += $image
    } else {
        Write-Host "  [MISSING] $($requiredImages[$image]) ($image)" -ForegroundColor Red
        $missing += $image
    }
}

Write-Host "`n$('='*60)" -ForegroundColor Cyan
Write-Host "Found: $($found.Count) | Missing: $($missing.Count)" -ForegroundColor Yellow
Write-Host "$('='*60)" -ForegroundColor Cyan

if ($missing.Count -gt 0) {
    Write-Host "`nImages to download:" -ForegroundColor Yellow
    $missing | ForEach-Object { Write-Host "  - $_" -ForegroundColor Gray }
} else {
    Write-Host "`n[READY] All images available!" -ForegroundColor Green
}
