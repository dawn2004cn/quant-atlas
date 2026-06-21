# Restore Codex tool-calling for quant-atlas (fixes "unsupported call").
# Usage:  powershell -File scripts/install_codex_quant_atlas.ps1
#
# Keeps Cursor .cursor/hooks.json unchanged (git-only shell guards).

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$CodexHome = Join-Path $env:USERPROFILE ".codex"
$ProfileDest = Join-Path $CodexHome "quant-atlas.config.toml"
$ProfileSrc = Join-Path $RepoRoot ".codex\quant-atlas.profile.toml"
$UserConfig = Join-Path $CodexHome "config.toml"

# Last known-good values from ~/.codex/backups/codex-plus-live-1781594818969/
$WorkingModel = "gpt-5.3-codex"
$WorkingBaseUrl = "http://127.0.0.1:15721/v1"

New-Item -ItemType Directory -Force -Path $CodexHome | Out-Null
Copy-Item -Force $ProfileSrc $ProfileDest
Write-Host "Installed profile -> $ProfileDest"

function Set-TomlKey {
    param([string]$Path, [string]$Key, [string]$Value)
    if (-not (Test-Path $Path)) { return }
    $raw = Get-Content $Path -Raw
    $pattern = "(?m)^$([regex]::Escape($Key))\s*=.*$"
    if ($raw -match $pattern) {
        $raw = [regex]::Replace($raw, $pattern, "$Key = `"$Value`"")
    } else {
        $raw = "$Key = `"$Value`"`n" + $raw
    }
    Set-Content -Path $Path -Encoding UTF8 -Value $raw
}

if (Test-Path $UserConfig) {
    $bak = "$UserConfig.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item -Force $UserConfig $bak
    Write-Host "Backed up $UserConfig -> $bak"
    Set-TomlKey $UserConfig "model" $WorkingModel
    Set-TomlKey $UserConfig "base_url" $WorkingBaseUrl
    Write-Host "Restored global model=$WorkingModel base_url=$WorkingBaseUrl"
} else {
    Write-Warning "Missing $UserConfig — create it manually or reinstall Codex."
}

$projectKey = "[projects.'$RepoRoot']"
$trustBlock = @"
$projectKey
trust_level = "trusted"

"@

if (-not (Test-Path $UserConfig)) {
    Set-Content -Path $UserConfig -Encoding UTF8 -Value $trustBlock
} elseif ((Get-Content $UserConfig -Raw) -notmatch [regex]::Escape($projectKey)) {
    Add-Content -Path $UserConfig -Encoding UTF8 -Value "`n$trustBlock"
}

Write-Host ""
Write-Host "Done. Restart Codex Desktop, open quant-atlas, start a NEW thread."
Write-Host "Model: gpt-5.3-codex (or profile quant-atlas). Avoid @cf/deepseek-* and ep-*."
Write-Host "Ensure local proxy is up: $WorkingBaseUrl"
Write-Host "Cursor hooks (.cursor/hooks.json) are untouched."
