# Setup for Windows (PowerShell). Usage: .\scripts\setup.ps1 [-Voice]
# If scripts are blocked, run once:
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned




param([switch]$Voice)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}
& ".venv\Scripts\Activate.ps1"

python -m pip install --upgrade pip | Out-Null
pip install -r requirements.txt

if ($Voice) {
    Write-Host "Installing voice extras..."
    pip install -r requirements-voice.txt
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ""
    Write-Host ">>> Created .env — edit it and add your ANTHROPIC_API_KEY. <<<" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Setup complete. Run the assistant with:  .\scripts\run.ps1 [-Voice]"
