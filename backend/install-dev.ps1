$ErrorActionPreference = "Stop"

$BackendDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $BackendDir
$VenvDir = Join-Path $BackendDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$Requirements = Join-Path $BackendDir "requirements-dev.txt"

Set-Location $RepoRoot

$needsVenv = -not (Test-Path $VenvPython)
if (-not $needsVenv) {
    $pythonItem = Get-Item -LiteralPath $VenvPython
    $needsVenv = $pythonItem.Length -eq 0
}

if ($needsVenv) {
    if (Test-Path $VenvDir) {
        Remove-Item -LiteralPath $VenvDir -Recurse -Force
    }
    python -m venv $VenvDir
}

$env:PIP_CONFIG_FILE = "NUL"

& $VenvPython -m pip install --isolated -i https://pypi.org/simple -r $Requirements
& $VenvPython -m pytest backend
