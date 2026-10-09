<#
The visual probe in the test VM (#155), run from this PC:

    vmtest begin
    powershell -File tools\ui_probe_vm.ps1 [-Variant light-100,dark-100] [-Surface settings] [-Out folder]

Copies this checkout into the VM, installs Python and the app's packages
there the first time, runs tools\ui_probe_guest.ps1 for each variant in
tools\ui_probe_plan.json (all of them by default), and copies the pictures
and descriptions back to -Out (a new folder under %TEMP%\tcp-ui-probe by
default). Nothing opens on this PC: the windows, the theme changes and the
scaling all happen in the VM, through vmtest (TheWorkBench\vmtest).
#>
param(
    [string[]]$Variant = @(),
    [string[]]$Surface = @(),
    [string]$Out = '',
    [string]$VmTest = $(if ($env:VMTEST_HOME) { $env:VMTEST_HOME } else { 'C:\Users\kelly\GitHub\TheWorkBench\vmtest' })
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot
Import-Module (Join-Path $VmTest 'VmTest.psm1') -Force
Push-Location $repo
try { Assert-TaskHasVM } finally { Pop-Location }

$plan = Get-Content (Join-Path $PSScriptRoot 'ui_probe_plan.json') -Raw | ConvertFrom-Json
$variants = @($plan.windows | Where-Object { -not $Variant -or $Variant -contains $_.tag })
if (-not $variants) { throw "No Windows variant called $($Variant -join ', ') in ui_probe_plan.json." }
if (-not $Out) { $Out = Join-Path $env:TEMP ("tcp-ui-probe\" + (Get-Date -Format 'yyyyMMdd-HHmmss')) }
New-Item $Out -ItemType Directory -Force | Out-Null

function Invoke-Vm([string]$Command, [int]$Timeout = 600) {
    Push-Location $repo
    try {
        & powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $VmTest 'vmtest.ps1') run $Command -Timeout $Timeout
        return $LASTEXITCODE
    } finally { Pop-Location }
}

$config = Get-VmTestConfig
$credential = New-Object System.Management.Automation.PSCredential($config.UserName,
    (ConvertTo-SecureString $config.Password -AsPlainText -Force))
$session = New-PSSession -VMName $config.VMName -Credential $credential
try {
    # This checkout as it stands (tracked and new files, not ignored ones).
    $zip = Join-Path $env:TEMP 'tcp-probe-source.zip'
    if (Test-Path $zip) { Remove-Item $zip }
    $files = git -C $repo ls-files -co --exclude-standard | Where-Object { Test-Path (Join-Path $repo $_) -PathType Leaf }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::Open($zip, 'Create')
    try {
        foreach ($file in $files) {
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, (Join-Path $repo $file), $file) | Out-Null
        }
    } finally { $archive.Dispose() }
    Invoke-Command -Session $session -ScriptBlock {
        Remove-Item C:\vmtest\tcp, C:\vmtest\probe-out -Recurse -Force -ErrorAction SilentlyContinue
        New-Item C:\vmtest -ItemType Directory -Force | Out-Null
    }
    Copy-Item $zip -Destination C:\vmtest\tcp-source.zip -ToSession $session -Force
    Invoke-Command -Session $session -ScriptBlock { Expand-Archive C:\vmtest\tcp-source.zip C:\vmtest\tcp -Force }

    $ready = Invoke-Command -Session $session -ScriptBlock { Test-Path C:\vmtest\tcp-venv\Scripts\python.exe }
    if (-not $ready) {
        "Installing Python and the app's packages in the VM (first run only)..."
        if ((Invoke-Vm 'py -3.12 --version') -ne 0) {
            Invoke-Vm 'winget install --id Python.Python.3.12 -e --silent --scope user --accept-source-agreements --accept-package-agreements' 1200 | Out-Host
        }
        if ((Invoke-Vm 'py -3.12 -m venv C:\vmtest\tcp-venv') -ne 0) { throw "Couldn't make the VM's venv." }
        if ((Invoke-Vm 'C:\vmtest\tcp-venv\Scripts\python.exe -m pip install -q -r C:\vmtest\tcp\requirements-dev.txt' 1800) -ne 0) {
            throw "Couldn't install the app's packages in the VM."
        }
    }

    $failed = @()
    foreach ($v in $variants) {
        "== $($v.tag)"
        $hc = if ($v.hc_theme) { $v.hc_theme } else { 'aquatic' }
        $command = "powershell -NoProfile -ExecutionPolicy Bypass -File C:\vmtest\tcp\tools\ui_probe_guest.ps1 -Tag $($v.tag) -Theme $($v.theme) -HcTheme `"$hc`" -Scale $($v.scale)"
        $names = if ($Surface) { $Surface } elseif ($v.surfaces) { $v.surfaces } else { @() }
        if ($names) { $command += " -Surface " + ($names -join ',') }
        if ((Invoke-Vm $command 1800) -ne 0) { $failed += $v.tag }
    }
    Copy-Item C:\vmtest\probe-out\* -Destination $Out -FromSession $session -Recurse -Force
} finally {
    Remove-PSSession $session
}
"Pictures and descriptions: $Out"
if ($failed) { "Variants with failures: $($failed -join ', ')"; exit 1 }
