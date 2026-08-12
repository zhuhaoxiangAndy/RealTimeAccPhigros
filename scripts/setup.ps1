# RealtimeAcc one-shot environment setup (PowerShell 5.1+).
# 1. python venv + deps   2. Tesseract check   3. config.toml from example
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "[1/3] Python venv + dependencies"
if (-not (Test-Path "$root\.venv\Scripts\python.exe")) {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { & $py -3.12 -m venv "$root\.venv" }
    else { python -m venv "$root\.venv" }
}
& "$root\.venv\Scripts\python.exe" -m pip install -r "$root\requirements.txt" --quiet
Write-Host "[2/3] Tesseract check"
$candidates = @(
    "C:\Program Files\Tesseract-OCR\tesseract.exe",
    "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
)
$found = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($found) {
    Write-Host "  found: $found (add its dir to PATH)"
} else {
    Write-Host "  MISSING - install with: winget install UB-Mannheim.TesseractOCR"
}
Write-Host "[3/3] config.toml"
if (-not (Test-Path "$root\config.toml")) {
    Copy-Item "$root\config.example.toml" "$root\config.toml"
    Write-Host "  copied config.example.toml -> config.toml"
} else {
    Write-Host "  config.toml already exists (kept)"
}
Write-Host "Done. Usage:  python main.py run --demo  /  python main.py video sample.mp4"