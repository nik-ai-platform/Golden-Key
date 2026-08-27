param(
    [string]$BaseUrl = "http://localhost:8080",
    [int]$MaxAttempts = 10,
    [int]$DelaySeconds = 3,
    [string]$AuthEmail = "admin@nik.ai",
    [string]$AuthPassword = "admin123"
)

$ErrorActionPreference = "Stop"

function Invoke-WithRetry {
    param(
        [string]$Name,
        [scriptblock]$Action
    )

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        try {
            $result = & $Action
            return $result
        } catch {
            if ($attempt -eq $MaxAttempts) {
                throw "[$Name] failed after $MaxAttempts attempts. Last error: $($_.Exception.Message)"
            }

            Write-Host "[$Name] attempt $attempt/$MaxAttempts failed: $($_.Exception.Message)"
            Start-Sleep -Seconds $DelaySeconds
        }
    }
}

$results = @()

function Add-Result {
    param(
        [string]$Check,
        [bool]$Passed,
        [string]$Detail
    )

    $status = if ($Passed) { "PASS" } else { "FAIL" }

    $results += [PSCustomObject]@{
        check = $Check
        status = $status
        detail = $Detail
    }

    Write-Host "[$status] $Check - $Detail"
}

$hasFailure = $false
$token = $null

try {
    $ui = Invoke-WithRetry -Name "UI root" -Action {
        Invoke-WebRequest -Uri $BaseUrl -UseBasicParsing -TimeoutSec 10
    }
    Add-Result -Check "UI root" -Passed ($ui.StatusCode -eq 200) -Detail ("HTTP " + $ui.StatusCode)
    if ($ui.StatusCode -ne 200) { $hasFailure = $true }
} catch {
    Add-Result -Check "UI root" -Passed $false -Detail $_.Exception.Message
    $hasFailure = $true
}

try {
    $health = Invoke-WithRetry -Name "Health endpoint" -Action {
        Invoke-RestMethod -Uri "$BaseUrl/api/v1/health" -TimeoutSec 10
    }
    $ok = $health.status -eq "healthy"
    Add-Result -Check "Health endpoint" -Passed $ok -Detail ("status=" + $health.status)
    if (-not $ok) { $hasFailure = $true }
} catch {
    Add-Result -Check "Health endpoint" -Passed $false -Detail $_.Exception.Message
    $hasFailure = $true
}

try {
    $dashboard = Invoke-WithRetry -Name "Dashboard endpoint" -Action {
        Invoke-RestMethod -Uri "$BaseUrl/api/v1/dashboard" -TimeoutSec 10
    }
    $ok = ($dashboard.PSObject.Properties.Name -contains "system_health") -and
        ($dashboard.PSObject.Properties.Name -contains "overall_accuracy")
    Add-Result -Check "Dashboard endpoint" -Passed $ok -Detail ("system_health=" + $dashboard.system_health)
    if (-not $ok) { $hasFailure = $true }
} catch {
    Add-Result -Check "Dashboard endpoint" -Passed $false -Detail $_.Exception.Message
    $hasFailure = $true
}

try {
    $confidence = Invoke-WithRetry -Name "Analytics confidence" -Action {
        Invoke-RestMethod -Uri "$BaseUrl/api/v1/analytics/confidence" -TimeoutSec 10
    }
    $ok = $confidence.PSObject.Properties.Name -contains "buckets"
    $count = if ($null -ne $confidence.buckets) { $confidence.buckets.Count } else { 0 }
    Add-Result -Check "Analytics confidence" -Passed $ok -Detail ("buckets=" + $count)
    if (-not $ok) { $hasFailure = $true }
} catch {
    Add-Result -Check "Analytics confidence" -Passed $false -Detail $_.Exception.Message
    $hasFailure = $true
}

try {
    $loginBody = @{ email = $AuthEmail; password = $AuthPassword } | ConvertTo-Json
    $login = Invoke-WithRetry -Name "Auth login" -Action {
        Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/v1/auth/login" -ContentType "application/json" -Body $loginBody -TimeoutSec 10
    }
    $token = $login.access_token
    $ok = -not [string]::IsNullOrWhiteSpace($token)
    Add-Result -Check "Auth login" -Passed $ok -Detail ("token_type=" + $login.token_type)
    if (-not $ok) { $hasFailure = $true }
} catch {
    Add-Result -Check "Auth login" -Passed $false -Detail $_.Exception.Message
    $hasFailure = $true
}

try {
    if ([string]::IsNullOrWhiteSpace($token)) {
        throw "No access token available from login"
    }

    $me = Invoke-WithRetry -Name "Auth me" -Action {
        Invoke-RestMethod -Method Get -Uri "$BaseUrl/api/v1/auth/me" -Headers @{ Authorization = "Bearer $token" } -TimeoutSec 10
    }
    $ok = $me.email -eq $AuthEmail
    Add-Result -Check "Auth me" -Passed $ok -Detail ("email=" + $me.email)
    if (-not $ok) { $hasFailure = $true }
} catch {
    Add-Result -Check "Auth me" -Passed $false -Detail $_.Exception.Message
    $hasFailure = $true
}

Write-Host ""
Write-Host "Smoke Test Summary"
$results | Format-Table -AutoSize

if ($hasFailure) {
    exit 1
}

exit 0
