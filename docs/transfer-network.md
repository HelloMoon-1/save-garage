# Windows 回传出现 NW-102264-5

如果详情连续出现主机连接、IPv6 监听就绪、随后断开，始终没有 `[data] connection from`，说明数据连接还没有到达应用。这个现象有多种可能原因。两台设备先接到同一家庭局域网，检查访客 Wi-Fi、无线客户端隔离和网卡 IPv6。

如果 Windows 防火墙拦截了便携版的入站连接，可以在自己信任的家庭网络上，打开管理员 PowerShell，进入当前版本的 `MoonSlot` 解压目录，执行以下命令。规则只对当前便携版的 Python、本地子网、专用网络配置文件和 TCP 1005 生效。

```powershell
$program = (Resolve-Path -LiteralPath '.\app\python\python.exe' -ErrorAction Stop).Path
New-NetFirewallRule -DisplayName 'MoonSlot PS5 transfer TCP 1005' -Direction Inbound -Action Allow -Program $program -Profile Private -Protocol TCP -LocalPort 1005 -RemoteAddress LocalSubnet
```

保持编辑器打开，在 PS5 重新搜索并选择 Save Garage。出现 `[data] connection from` 表示连接已到达数据端口。如果仍失败，反馈系统、连接方式，以及首次出现这行前后的日志。需要撤销规则时运行：

```powershell
Remove-NetFirewallRule -DisplayName 'MoonSlot PS5 transfer TCP 1005'
```
