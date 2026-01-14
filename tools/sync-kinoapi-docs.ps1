<#
.SYNOPSIS
Mirrors the official KinoPub API documentation site for offline use.

.DESCRIPTION
Downloads the HTML pages and required static assets from https://www.kinoapi.com/
so you can browse the docs locally without copy/paste distortions.

Note: the downloaded files are generated artifacts. The default destination is ignored by this repo's `.gitignore`
and should not be committed.

Requires: GNU Wget OR HTTrack (recommended: wget).

.PARAMETER Destination
Directory where the mirrored site will be stored (default: docs/kinoapi/site).

.PARAMETER Url
Starting URL to mirror (default: https://www.kinoapi.com/index.html).

.PARAMETER Clean
If set, deletes the destination directory before downloading.
#>

[CmdletBinding()]
param(
  [string]$Destination,
  [string]$Url = "https://www.kinoapi.com/index.html",
  [switch]$Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"


$scriptPath = $PSCommandPath
if ([string]::IsNullOrWhiteSpace($scriptPath)) {
  $scriptPath = $MyInvocation.MyCommand.Path
}
$scriptDir = Split-Path -Parent $scriptPath

if ([string]::IsNullOrWhiteSpace($Destination)) {
  $Destination = Join-Path $scriptDir "..\docs\kinoapi\site"
  $Destination = [System.IO.Path]::GetFullPath($Destination)
}

function Get-ExePath([string]$name) {
  # In Windows PowerShell, names like "wget" may be aliases (e.g. to Invoke-WebRequest).
  # We only want real executables on PATH.
  $cmd = Get-Command $name -All -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandType -eq "Application" } |
    Select-Object -First 1

  if ($null -eq $cmd) { return $null }
  return $cmd.Source
}

if ($Clean) {
  if (Test-Path $Destination) {
    Remove-Item -Recurse -Force $Destination
  }
}

New-Item -ItemType Directory -Force -Path $Destination | Out-Null

$wget = Get-ExePath "wget"
$httrack = Get-ExePath "httrack"

if ($null -ne $wget) {
  Write-Host "Using wget: $wget"
  Write-Host "Mirroring $Url -> $Destination"

  # Notes:
  # - --mirror enables recursion + timestamping (keeps local copy in sync)
  # - --page-requisites pulls CSS/JS/images needed for correct offline rendering
  # - --no-parent prevents crawling outside the docs tree
  & $wget `
    --mirror `
    --page-requisites `
    --no-parent `
    --directory-prefix "$Destination" `
    "$Url"

  Write-Host ""
  Write-Host "Done. Look for index.html under: $Destination"
  Write-Host "Tip: try opening: $Destination\www.kinoapi.com\index.html"
  exit 0
}

if ($null -ne $httrack) {
  Write-Host "Using httrack: $httrack"
  Write-Host "Mirroring $Url -> $Destination"

  # HTTrack stores a local 'index.html' in the project folder by default.
  & $httrack `
    "$Url" `
    "-O" "$Destination" `
    "+*.kinoapi.com/*" `
    "-v"

  Write-Host ""
  Write-Host "Done. Look for index.html under: $Destination"
  exit 0
}

Write-Error @"
Neither 'wget' nor 'httrack' was found in PATH.

Install one of them, then re-run this script:
- wget (recommended): winget install --id JernejSimoncic.Wget -e --accept-package-agreements --accept-source-agreements
- httrack: https://www.httrack.com/
"@

