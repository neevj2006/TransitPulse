[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Destination
)

$ErrorActionPreference = 'Stop'

if (-not $env:TP_DATABASE_URL) {
    throw 'TP_DATABASE_URL must be set to run a database backup.'
}

$resolvedDestination = [IO.Path]::GetFullPath($Destination)
New-Item -ItemType Directory -Force -Path $resolvedDestination | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backup = Join-Path $resolvedDestination "transitpulse-$stamp.dump"

# Custom format supports selective, verified restores. Do not print the connection URL.
pg_dump --format=custom --no-owner --file $backup $env:TP_DATABASE_URL
pg_restore --list $backup | Out-Null

Get-ChildItem -LiteralPath $resolvedDestination -Filter 'transitpulse-*.dump' |
    Where-Object { $_.LastWriteTimeUtc -lt (Get-Date).ToUniversalTime().AddDays(-14) } |
    Remove-Item -Force

Write-Output "Verified backup created: $backup"
