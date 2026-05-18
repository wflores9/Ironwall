# ironwall — Rust installer + launcher build script for Windows
# Run as Administrator in PowerShell:
#   Set-ExecutionPolicy Bypass -Scope Process -Force
#   .\scripts\install_rust_windows.ps1

param(
    [string]$RepoRoot = "C:\Users\wflor\Ironwall",
    [switch]$SkipRustInstall = $false
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) {
    Write-Host "`n>> $msg" -ForegroundColor Cyan
}

function Write-OK($msg) {
    Write-Host "   [OK] $msg" -ForegroundColor Green
}

function Write-Fail($msg) {
    Write-Host "   [FAIL] $msg" -ForegroundColor Red
    exit 1
}

Write-Host @"
╔══════════════════════════════════════════════╗
║   IRONWALL — Rust Launcher Setup (Windows)   ║
╚══════════════════════════════════════════════╝
"@ -ForegroundColor Cyan

# ── Step 1: Install Rust ──────────────────────────────────────────────────
Write-Step "Checking Rust installation..."

if (-not $SkipRustInstall) {
    $rustc = Get-Command rustc -ErrorAction SilentlyContinue
    if ($rustc) {
        $ver = (rustc --version)
        Write-OK "Rust already installed: $ver"
    } else {
        Write-Host "   Downloading rustup-init.exe..." -ForegroundColor Yellow
        $rustupUrl = "https://win.rustup.rs/x86_64"
        $rustupExe = "$env:TEMP\rustup-init.exe"
        Invoke-WebRequest -Uri $rustupUrl -OutFile $rustupExe -UseBasicParsing
        Write-Host "   Running rustup installer (this takes ~2 min)..." -ForegroundColor Yellow
        & $rustupExe -y --default-toolchain stable --profile minimal
        # Reload PATH
        $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" +
                    [System.Environment]::GetEnvironmentVariable("PATH", "User")
        Write-OK "Rust installed successfully"
    }
} else {
    Write-OK "Skipping Rust install (-SkipRustInstall)"
}

# Verify
try {
    $rustVer = (rustc --version 2>&1)
    $cargoVer = (cargo --version 2>&1)
    Write-OK "rustc: $rustVer"
    Write-OK "cargo: $cargoVer"
} catch {
    Write-Fail "Rust not found after install. Restart PowerShell and try again."
}

# ── Step 2: Check Visual Studio Build Tools (MSVC linker) ─────────────────
Write-Step "Checking MSVC build tools..."

$vcvars = Get-ChildItem "C:\Program Files (x86)\Microsoft Visual Studio" -Recurse -Filter "vcvarsall.bat" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($vcvars) {
    Write-OK "MSVC found: $($vcvars.FullName)"
} else {
    Write-Host "   MSVC build tools not found." -ForegroundColor Yellow
    Write-Host "   Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/" -ForegroundColor Yellow
    Write-Host "   Install 'Desktop development with C++' workload." -ForegroundColor Yellow
    Write-Host "   Then re-run this script." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   Alternatively, switch to the GNU toolchain:" -ForegroundColor Yellow
    Write-Host "   rustup toolchain install stable-x86_64-pc-windows-gnu" -ForegroundColor Yellow
    Write-Host "   rustup default stable-x86_64-pc-windows-gnu" -ForegroundColor Yellow
}

# ── Step 3: Build the launcher ────────────────────────────────────────────
Write-Step "Building ironwall-launcher (release)..."

$launcherDir = Join-Path $RepoRoot "ironwall_launcher"
if (-not (Test-Path $launcherDir)) {
    Write-Fail "Launcher directory not found: $launcherDir`nMake sure you're running from the repo root."
}

Set-Location $launcherDir
Write-Host "   Running: cargo build --release" -ForegroundColor Yellow
Write-Host "   (First build downloads dependencies — ~3 min)" -ForegroundColor Yellow

& cargo build --release 2>&1 | ForEach-Object { Write-Host "   $_" }

$binaryPath = Join-Path $launcherDir "target\release\ironwall-launcher.exe"
if (Test-Path $binaryPath) {
    $size = (Get-Item $binaryPath).Length / 1KB
    Write-OK "Build successful: $binaryPath ($([math]::Round($size))KB)"
} else {
    Write-Fail "Build failed — binary not found at $binaryPath"
}

# ── Step 4: Run Rust tests ────────────────────────────────────────────────
Write-Step "Running Rust unit tests..."
& cargo test 2>&1 | ForEach-Object { Write-Host "   $_" }
Write-OK "Tests complete"

# ── Step 5: Add to PATH (optional) ───────────────────────────────────────
Write-Step "Adding launcher to user PATH..."
$binDir = Join-Path $launcherDir "target\release"
$currentPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
if ($currentPath -notlike "*$binDir*") {
    [System.Environment]::SetEnvironmentVariable(
        "PATH", "$currentPath;$binDir", "User"
    )
    Write-OK "Added $binDir to user PATH (restart terminal to use)"
} else {
    Write-OK "Already in PATH"
}

# ── Done ──────────────────────────────────────────────────────────────────
Write-Host @"

╔══════════════════════════════════════════════╗
║              SETUP COMPLETE                  ║
╚══════════════════════════════════════════════╝

Binary:  $binaryPath

Usage:
  ironwall-launcher.exe ``
    --game-dir  "C:\cod25" ``
    --game-exe  "C:\cod25\cod.exe" ``
    --player-id "your-player-id" ``
    --broker-url "http://127.0.0.1:8766"

Start the Python broker first:
  cd $RepoRoot
  python -m ironwall.layer3_attest.attest_api

"@ -ForegroundColor Green
