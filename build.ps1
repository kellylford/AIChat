<#
.SYNOPSIS
    Builds TheClaudeHub on this PC: tests, the app, a smoke test, and the Velopack installer
    and portable zip. The same steps as .github/workflows/release-theclaudehub.yml, unsigned.

.DESCRIPTION
    Runs in its own virtual environment (.venv-build in this folder), so your own Python
    packages are never changed. The first run takes a few minutes to install what it needs;
    later runs reuse it.

    What you get, in .\releases (or -OutputDir too):
      TheClaudeHub-theclaudehub-Setup.exe     installs for you only, adds a Start menu item
      TheClaudeHub-theclaudehub-Portable.zip  runs without installing
    and the app folder itself in .\dist\TheClaudeHub.

    The build isn't signed, so Windows SmartScreen may warn when you run Setup: choose
    More info, then Run anyway. Signed builds come from the GitHub workflow.

.PARAMETER OutputDir
    Also copy Setup and the portable zip here, for example C:\Users\kelly\OneDrive\thehub.

.PARAMETER SkipTests
    Don't run the tests first (faster; the CI build always runs them).

.PARAMETER AppOnly
    Build and smoke-test the app folder only; skip the installer and zip.

.EXAMPLE
    .\build.ps1
.EXAMPLE
    .\build.ps1 -OutputDir C:\Users\kelly\OneDrive\thehub
.EXAMPLE
    .\build.ps1 -SkipTests -AppOnly
#>
[CmdletBinding()]
param(
    [string]$OutputDir = "",
    [switch]$SkipTests,
    [switch]$AppOnly
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
Set-Location $root

# Pinned to what the release workflow uses, so a local build matches a CI one.
$PyInstallerVersion = '6.22.3'
$VpkVersion = '1.2.161'
$Channel = 'theclaudehub'

function Step([string]$text) { Write-Host ""; Write-Host "== $text ==" }

function Run([string]$exe, [string[]]$arguments) {
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) { throw "$exe $($arguments -join ' ') failed (exit $LASTEXITCODE)." }
}

# -- Python and the build environment -------------------------------------------------------

Step 'Python'
$python = (Get-Command py -ErrorAction SilentlyContinue)
if ($python) { $basePython = @('py', '-3') } else { $basePython = @('python') }
$venv = Join-Path $root '.venv-build'
$venvPython = Join-Path $venv 'Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
    Write-Host "Creating the build environment in $venv"
    $first = $basePython[0]
    $rest = @($basePython | Select-Object -Skip 1)
    Run $first ($rest + @('-m', 'venv', $venv))
}
Run $venvPython @('--version')

Step 'Installing what the build needs'
Run $venvPython @('-m', 'pip', 'install', '--quiet', '--upgrade', 'pip')
Run $venvPython @('-m', 'pip', 'install', '--quiet', '-r', 'requirements-dev.txt',
                  "pyinstaller==$PyInstallerVersion")

# -- tests and version -----------------------------------------------------------------------

if (-not $SkipTests) {
    Step 'Tests'
    Run $venvPython @('-m', 'pytest', '-q', 'tests')
}

Step 'Version'
$version = (& $venvPython tools/check_version.py).Trim()
if ($LASTEXITCODE -ne 0 -or -not $version) { throw 'Could not read the version.' }
Write-Host "TheClaudeHub $version"

# -- the app ---------------------------------------------------------------------------------

Step 'Building the app (PyInstaller)'
Run $venvPython @('tools/make_version_info.py')
# The same options as the workflow: --onedir because Velopack swaps an app folder in place;
# velopack is imported lazily so it's named; --collect-binaries wx brings WebView2Loader.dll,
# which the formatted message view needs; the speech scripts are data files.
Run $venvPython @('-m', 'PyInstaller', '--noconfirm', '--clean', '--noconsole', '--onedir',
                  '--name', 'TheClaudeHub', '--version-file', 'build/version_info.txt',
                  '--hidden-import', 'velopack', '--collect-binaries', 'wx',
                  '--add-data', 'theclaudehub/speech;theclaudehub/speech',
                  'TheClaudeHub.pyw')

Step 'Smoke test'
$smoke = Join-Path $root 'smoke-local.json'
Remove-Item $smoke -ErrorAction SilentlyContinue
$process = Start-Process (Join-Path $root 'dist\TheClaudeHub\TheClaudeHub.exe') `
    -ArgumentList '--smoke-test', $smoke -Wait -PassThru
if (Test-Path $smoke) { Get-Content $smoke | Write-Host }
if ($process.ExitCode -ne 0) { throw "The built app's smoke test failed (exit $($process.ExitCode))." }

if ($AppOnly) {
    Step 'Done'
    Write-Host "The app is in $(Join-Path $root 'dist\TheClaudeHub'). Run TheClaudeHub.exe there."
    exit 0
}

# -- installer and portable zip (Velopack) ---------------------------------------------------

Step 'Velopack'
$vpk = Get-Command vpk -ErrorAction SilentlyContinue
if (-not $vpk) {
    if (-not (Get-Command dotnet -ErrorAction SilentlyContinue)) {
        throw ('The installer needs the .NET SDK (for the vpk tool). Install it from ' +
               'https://dotnet.microsoft.com/download, or use -AppOnly to build just the app.')
    }
    Run 'dotnet' @('tool', 'install', '-g', 'vpk', '--version', $VpkVersion)
    $env:PATH = "$env:PATH;$env:USERPROFILE\.dotnet\tools"
}

Step 'Packing the installer and portable zip'
$releases = Join-Path $root 'releases'
if (Test-Path $releases) { Remove-Item $releases -Recurse -Force }
$packArgs = @('pack', '--packId', 'TheClaudeHub', '--packVersion', $version,
              '--packDir', 'dist/TheClaudeHub', '--mainExe', 'TheClaudeHub.exe',
              '--packTitle', 'TheClaudeHub', '--packAuthors', 'Kelly Ford',
              '--channel', $Channel, '--outputDir', 'releases',
              '--instLocation', 'PerUser', '--shortcuts', 'StartMenuRoot')
$notes = "release-notes/v$version.md"
if (Test-Path $notes) { $packArgs += @('--releaseNotes', $notes) }
Run 'vpk' $packArgs

$setup = Join-Path $releases "TheClaudeHub-$Channel-Setup.exe"
$portable = Join-Path $releases "TheClaudeHub-$Channel-Portable.zip"
foreach ($file in @($setup, $portable)) {
    if (-not (Test-Path $file)) { throw "vpk didn't make $file." }
}

if ($OutputDir) {
    Step "Copying to $OutputDir"
    New-Item -ItemType Directory -Force $OutputDir | Out-Null
    try {
        Copy-Item $setup, $portable -Destination $OutputDir -Force
    } catch {
        throw ("Couldn't copy into $OutputDir ($($_.Exception.Message)). If OneDrive is " +
               'syncing an older copy, wait a moment and run again with -SkipTests.')
    }
}

Step 'Done'
Write-Host "TheClaudeHub $version (unsigned):"
Get-Item $setup, $portable | ForEach-Object {
    Write-Host ("  {0}  ({1:N1} MB)" -f $_.FullName, ($_.Length / 1MB))
}
if ($OutputDir) { Write-Host "  copied to $OutputDir" }
