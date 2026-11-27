[CmdletBinding()]
param([string]$LogPath, [string]$ConsoleAddress, [switch]$NonInteractive)

$ErrorActionPreference = 'Stop'
if (-not $NonInteractive) {
    if (-not $LogPath) { $LogPath = Read-Host '拖入上次回传的 dt-source.log 后按回车，或直接回车跳过' }
    if (-not $ConsoleAddress) { $ConsoleAddress = Read-Host 'PS5 网络设置中的 IPv4 地址（回车跳过网卡检查）' }
}
$report = @('PS5 Pro 回传诊断 beta 1 | Windows', '')
if ($ConsoleAddress) {
    $peer = $null
    if ([ipaddress]::TryParse($ConsoleAddress.Trim(), [ref]$peer) -and
        $peer.AddressFamily -eq [Net.Sockets.AddressFamily]::InterNetwork -and
        -not [ipaddress]::IsLoopback($peer)) {
        $socket = New-Object Net.Sockets.UdpClient
        try {
            # UDP Connect selects a route; this tool sends no datagram to the peer.
            $socket.Connect($peer, 9)
            $local = $socket.Client.LocalEndPoint.Address
            $adapter = [Net.NetworkInformation.NetworkInterface]::GetAllNetworkInterfaces() | Where-Object {
                $_.OperationalStatus -eq 'Up' -and
                ($_.GetIPProperties().UnicastAddresses.Address -contains $local)
            } | Select-Object -First 1
            if (-not $adapter) { throw 'route unavailable' }
            $v6 = @($adapter.GetIPProperties().UnicastAddresses | Where-Object {
                $_.Address.IsIPv6LinkLocal -and $_.DuplicateAddressDetectionState -eq 'Preferred'
            })
            $report += if ($v6.Count) { '去往主机的网卡：有可用的 IPv6 链路本地地址。' }
                       else { '去往主机的网卡：未找到可用的 IPv6 链路本地地址。请检查该网卡的 IPv6 设置。' }
        } catch { $report += '网卡：无法识别去往主机的本机网卡。' }
        finally { $socket.Close() }
    } else { $report += '网卡：输入的主机 IPv4 地址无效。' }
} else { $report += '网卡：已跳过。' }

if ($LogPath) {
    $commandSeen = $false
    $dataSeen = $false
    $fileSeen = $false
    $tagError = $false
    try {
        $file = Get-Item -LiteralPath $LogPath.Trim().Trim('"') -ErrorAction Stop
        if ($file.PSIsContainer) { throw 'expected file' }
        foreach ($line in [IO.File]::ReadLines($file.FullName)) {
            if ($line -match '^\[tcp\] connection from ') { $commandSeen = $true }
            if ($line -match '^\[data\] connection from ') { $dataSeen = $true }
            if ($line -match '^\[data\] GFP5 file complete ') { $fileSeen = $true }
            if ($line -match '\bInvalidTag\b') { $tagError = $true }
        }
        $report += '所选日志中记录的事件（可能包含多次连接）：'
        foreach ($event in ([ordered]@{'收到控制连接'=$commandSeen;'收到数据连接'=$dataSeen;'至少一个文件发送完成'=$fileSeen;'出现数据校验错误 InvalidTag'=$tagError}).GetEnumerator()) {
            $value = if ($event.Value) { '有' } else { '未见' }
            $report += ('  {0}：{1}' -f $event.Key, $value)
        }
    } catch { $report += '日志：无法读取所选文件。' }
} else { $report += '日志：已跳过。' }

$report
if (-not $NonInteractive) {
    try {
        $name = 'PS5-Pro-report-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '.txt'
        $dest = Join-Path $PSScriptRoot $name
        $report | Out-File -LiteralPath $dest -Encoding utf8 -NoClobber
        Write-Host "可分享的摘要已保存到工具目录：$name"
    } catch { Write-Host '当前目录不可写，可以复制窗口中的摘要。' }
}
