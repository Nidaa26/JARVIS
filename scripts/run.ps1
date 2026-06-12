# Run the assistant on Windows (PowerShell). Usage: .\scripts\run.ps1 [-Voice]

param([switch]$Voice)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".venv")) {
    Write-Error "No virtual environment found — run .\scripts\setup.ps1 first."
}
& ".venv\Scripts\Activate.ps1"

if ($Voice) {
    python -m assistant --voice
} else {
    python -m assistant
}
