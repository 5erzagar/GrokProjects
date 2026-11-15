# install_ollama.ps1
# Namesti Ollama, zagotovi, da teče, prenese model in namesti Python knjižnice.
# Zagon: powershell -ExecutionPolicy Bypass -File .\install_ollama.ps1

$ErrorActionPreference = "Stop"
$Model = "qwen2.5:7b"
$Mapa = Split-Path -Parent $MyInvocation.MyCommand.Path

function Test-OllamaDosegljiva {
    try {
        Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 | Out-Null
        return $true
    } catch {
        return $false
    }
}

Write-Host "1/4 Preverjam Ollama ..." -ForegroundColor Cyan
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "winget ni na voljo. Namesti Ollama ročno z https://ollama.com/download"
    }
    winget install --id Ollama.Ollama -e --accept-package-agreements --accept-source-agreements
    # osveži PATH v tej seji
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
}
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    throw "Ollama ni v PATH. Zapri PowerShell, znova ga odpri in zaženi skripto."
}

Write-Host "2/4 Preverjam, ali Ollama teče ..." -ForegroundColor Cyan
if (-not (Test-OllamaDosegljiva)) {
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    for ($i = 0; $i -lt 15 -and -not (Test-OllamaDosegljiva); $i++) {
        Start-Sleep -Seconds 1
    }
    if (-not (Test-OllamaDosegljiva)) {
        throw "Ollama ne teče. Zaženi aplikacijo Ollama iz menija Start in poskusi znova."
    }
}

Write-Host "3/4 Prenašam model $Model (približno 4,7 GB, lahko traja) ..." -ForegroundColor Cyan
ollama pull $Model

Write-Host "4/4 Nameščam Python knjižnice ..." -ForegroundColor Cyan
python -m pip install -r (Join-Path $Mapa "requirements.txt")

Write-Host ""
Write-Host "Končano. Zaženi aplikacijo z ukazom: python main.py" -ForegroundColor Green
