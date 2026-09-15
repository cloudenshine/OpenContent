[CmdletBinding()]
param([Parameter(Position = 0)][string]$Vault = 'F:\Obsidian_vault')
$ErrorActionPreference = 'Stop'
$python = (Get-Command python -ErrorAction Stop).Source
& $python (Join-Path $PSScriptRoot 'scripts/install_plugin.py') --vault $Vault --configure --live-safe
if ($LASTEXITCODE -ne 0) { throw 'Installation failed. See the error above.' }
Write-Host 'Installed successfully. Reload OpenContent in Obsidian to use the update.'
