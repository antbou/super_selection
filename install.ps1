# Installe (ou met a jour) superselection sur Windows, en partant de zero.
# Usage, dans PowerShell :
#   powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/antbou/super_selection/main/install.ps1 | iex"

$ErrorActionPreference = "Stop"
$Source = "https://github.com/antbou/super_selection/archive/refs/heads/main.zip"

Write-Host ""
Write-Host "=== Installation de superselection ===" -ForegroundColor Cyan

# 1. uv (il installera Python tout seul)
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "-> Installation de uv..."
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    # rendre uv utilisable tout de suite, sans rouvrir le terminal
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
} else {
    Write-Host "-> uv deja installe."
}

# 2. superselection (telecharge la derniere version, remplace l'ancienne)
Write-Host "-> Installation de superselection (la premiere fois, Python est telecharge : ~1 min)..."
uv tool install --force --reinstall --refresh $Source
if ($LASTEXITCODE -ne 0) { throw "L'installation de superselection a echoue." }

# 3. mettre la commande dans le PATH pour les prochains terminaux
uv tool update-shell | Out-Null

Write-Host ""
Write-Host "Termine !" -ForegroundColor Green
Write-Host "Ferme ce terminal, rouvre-le, puis tape :  superselection"
Write-Host ""
