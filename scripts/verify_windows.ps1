param(
    [string]$PythonExe = $(if ($env:PYTHON) { $env:PYTHON } else { 'python' }),
    [switch]$Elevate,
    [string]$EvidenceName = ('windows-verify-' + [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ'))
)
$ErrorActionPreference = 'Stop'
if ($EvidenceName -notmatch '^windows-verify-[A-Za-z0-9-]+$') {
    throw 'EvidenceName must be a simple windows-verify- name, without path separators.'
}
$taskPython = (Get-Command $PythonExe -CommandType Application -ErrorAction Stop).Source
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskOutput = Join-Path $taskRoot ('.execution/' + $EvidenceName)
$taskPrincipal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if ($Elevate -and -not $taskPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    # Standard UAC consent, limited to this child process. No policy or account-right changes.
    $taskShell = (Get-Process -Id $PID).Path
    $taskArguments = @('-NoProfile', '-File', ('"' + $PSCommandPath + '"'),
                      '-PythonExe', ('"' + $taskPython + '"'), '-EvidenceName', $EvidenceName)
    $taskChild = Start-Process -FilePath $taskShell -ArgumentList $taskArguments -Verb RunAs -WindowStyle Hidden -PassThru
    $taskChild.WaitForExit()
    $taskReport = Join-Path $taskOutput 'report.json'
    if (-not (Test-Path -LiteralPath $taskReport)) { throw 'Elevated verification did not produce a report.' }
    $taskReceipt = Get-Content -LiteralPath $taskReport -Raw | ConvertFrom-Json
    Write-Output ($taskReceipt.status + ': ' + $taskReport)
    if ($taskChild.ExitCode -ne 0 -or $taskReceipt.status -ne 'PASS') { exit 1 }
    exit 0
}
& $taskPython -B (Join-Path $PSScriptRoot 'verify_windows.py') --output $taskOutput
exit $LASTEXITCODE
