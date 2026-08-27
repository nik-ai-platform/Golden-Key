$ErrorActionPreference = "Stop"

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$projectRoot = Join-Path $PSScriptRoot ".."
$backupDirectory = Join-Path $projectRoot "backups"
$backupFile = Join-Path $backupDirectory "goldenkey-$timestamp.sql"

New-Item -ItemType Directory -Force -Path $backupDirectory | Out-Null

Push-Location $projectRoot
try {
    docker compose `
        --env-file .env.production `
        -f docker-compose.production.yml `
        exec -T db `
        sh -c `
        "pg_dump -U goldenkey goldenkey > /tmp/goldenkey-backup.sql"

    if ($LASTEXITCODE -ne 0) {
        throw "Database backup failed with exit code $LASTEXITCODE"
    }

    docker compose `
        --env-file .env.production `
        -f docker-compose.production.yml `
        cp `
        db:/tmp/goldenkey-backup.sql `
        $backupFile

    if ($LASTEXITCODE -ne 0) {
        throw "Database backup copy failed with exit code $LASTEXITCODE"
    }
}
finally {
    docker compose `
        --env-file .env.production `
        -f docker-compose.production.yml `
        exec -T db `
        rm -f /tmp/goldenkey-backup.sql `
        2>$null

    Pop-Location
}

Write-Host "Backup created: $backupFile"