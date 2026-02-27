# ============================================================
# Flux — Development Environment Setup (Windows / PowerShell)
# Installs frontend and backend dependencies, copies .env files,
# and validates that required tools are present.
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
# ============================================================

$ErrorActionPreference = "Stop"

# ---------- Colored output helpers ----------
function Write-Info  { param($msg) Write-Host "[OK]    $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "[WARN]  $msg" -ForegroundColor Yellow }
function Write-Err   { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red; exit 1 }

# ---------- Resolve project root ----------
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

Write-Host ""
Write-Host "=============================="
Write-Host "  Flux - Project Setup"
Write-Host "=============================="
Write-Host ""

# ---------- 1. Check Node.js >= 18 ----------
try {
    $nodeVersion = (node -v) -replace 'v', ''
    $nodeMajor = [int]($nodeVersion.Split('.')[0])
    if ($nodeMajor -lt 18) {
        Write-Err "Node.js 18+ is required (found v$nodeVersion). Please upgrade."
    }
    Write-Info "Node.js v$nodeVersion detected"
} catch {
    Write-Err "Node.js is not installed. Please install Node.js 18+ from https://nodejs.org"
}

# ---------- 2. Check Python >= 3.11 ----------
$pythonCmd = $null
try {
    $null = python --version 2>&1
    $pythonCmd = "python"
} catch {
    try {
        $null = python3 --version 2>&1
        $pythonCmd = "python3"
    } catch {
        Write-Err "Python is not installed. Please install Python 3.11+ from https://python.org"
    }
}

$pythonVersionStr = & $pythonCmd --version 2>&1
$pythonVersion = ($pythonVersionStr -split ' ')[1]
$pyParts = $pythonVersion.Split('.')
$pyMajor = [int]$pyParts[0]
$pyMinor = [int]$pyParts[1]
if ($pyMajor -lt 3 -or ($pyMajor -eq 3 -and $pyMinor -lt 11)) {
    Write-Err "Python 3.11+ is required (found $pythonVersion). Please upgrade."
}
Write-Info "Python $pythonVersion detected"

# ---------- 3. Frontend setup ----------
Write-Host ""
Write-Host "--- Frontend Setup ---"

Set-Location "$ProjectRoot\frontend"
npm install
Write-Info "Frontend dependencies installed"

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Info "Created frontend\.env from .env.example"
} else {
    Write-Warn "frontend\.env already exists - skipping copy"
}

# ---------- 4. Backend setup ----------
Write-Host ""
Write-Host "--- Backend Setup ---"

Set-Location "$ProjectRoot\backend"

if (-not (Test-Path "requirements.txt")) {
    Write-Warn "backend\requirements.txt not found - skipping Python dependency install"
} else {
    & $pythonCmd -m venv venv
    # Activate venv on Windows
    & ".\venv\Scripts\Activate.ps1"
    pip install --upgrade pip --quiet
    pip install -r requirements.txt
    Write-Info "Backend dependencies installed in venv"
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Info "Created backend\.env from .env.example"
} else {
    Write-Warn "backend\.env already exists - skipping copy"
}

# ---------- 5. Done ----------
Set-Location $ProjectRoot

Write-Host ""
Write-Host "=============================="
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "=============================="
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Set up Supabase (Git Bash): bash scripts/supabase_setup.sh"
Write-Host "  2. Fill in API keys in backend\.env"
Write-Host "  3. Start frontend:  cd frontend; npm run dev"
Write-Host "  4. Start backend:   cd backend; .\venv\Scripts\Activate.ps1; make dev"
Write-Host "  5. Open http://localhost:5173 in your browser"
Write-Host ""
