param(
    [string]$Python = "py"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $repoRoot ".venv"

Write-Host "Trail Windows install"
Write-Host "Repo: $repoRoot"

if (-not (Get-Command $Python -ErrorAction SilentlyContinue)) {
    throw "Python launcher '$Python' not found. Install Python 3.11+ and ensure 'py' is available."
}

if (-not (Test-Path $venvPath)) {
    Write-Host "Creating virtual environment..."
    & $Python -m venv $venvPath
}

$pythonExe = Join-Path $venvPath "Scripts\python.exe"
$pipExe = Join-Path $venvPath "Scripts\pip.exe"
$trailExe = Join-Path $venvPath "Scripts\trail.exe"

Write-Host "Upgrading pip..."
& $pythonExe -m pip install --upgrade pip

Write-Host "Installing Trail in editable mode..."
& $pipExe install -e $repoRoot

Write-Host ""
Write-Host "Installed successfully."
Write-Host "Run Trail with:"
Write-Host "  $trailExe --help"
Write-Host ""
Write-Host "Quick test:"
Write-Host "  cd <your-project>"
Write-Host "  $trailExe init"
Write-Host "  $trailExe project init"
