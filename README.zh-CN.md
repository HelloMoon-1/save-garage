# GTA6 剧情存档编辑器（PS5）

[English](README.md) · [下载最新版](../../releases/latest) · [GPL-3.0 许可证](LICENSE)

如果这个工具帮到了你，欢迎给原作者 NotHGM 的 [Save Garage 原仓库点个 Star ⭐](https://github.com/NotHGM/save-garage)，支持他的存档研究与开发。

> **这是 NotHGM 的 [Save Garage](https://github.com/NotHGM/save-garage) 的简体中文修改版，并非官方版本。** 官方版本发布于 https://github.com/NotHGM/save-garage/releases

本工具原名 MoonSlot，用于编辑 PS5 版 GTA VI 的剧情存档。通过 PS5 的“数据传输”功能将存档下载到电脑，在浏览器中编辑，再传回主机。浏览器使用简体中文时会自动显示中文，也可以在编辑器右上方手动切换语言。

本版同步原作者的 `1.30.1`，支持游戏编号 `PPSA01547`、`PPSA38500` 和 `PPSA29660`。[查看 1.30.1 中文更新日志](docs/releases/v1.30.1.md)

## 可以修改什么

| 功能 | 内容 |
| --- | --- |
| 金钱 | 修改银行账户、家庭储蓄及露西亚和杰森的现金。钱包上限为 20,000 美元。 |
| 武器和弹药 | 查看两位主角各自的武器与弹药，补满已有弹种，也可添加列表中该角色未持有的武器。 |
| 统计 | 编辑游玩时长、生命与体力增益、通缉、击杀、收入、收藏等统计。历史收入与钱包余额分别记录。 |
| 完成度 | 查看 100% 清单，可批量处理特技、图鉴、地图发现、挑战、健身房会籍和冥想地点。 |
| 世界 | 修改游戏内时间、当前生命和护甲，查看或调整两位主角的成长值、特殊能力槽和犯罪侧写，在剧情允许的范围内调整关系分数，也可揭开已识别区域的地图迷雾。 |
| 全部统计与存档数据 | 通过名称或编号查看更细的字段。请先保留备份，每次尝试修改少量数据。 |
| 奖杯 | 查看原项目整理的奖杯说明。奖杯由 PS5 单独存储。 |

每项编辑会显示其验证状态。编辑器会保留下载时的原始存档，后续修改以原始存档为基础。

发行包请解压到可写目录。每次下载会在启动器旁的 `saves/consoles/<主机编号>/sessions/<下载时间>/` 生成一个目录，`orig` 存放原始备份，`dec` 存放解密后的槽位。

Based on Save Garage by NotHGM (https://github.com/NotHGM/save-garage)

## 使用步骤

首次使用时点击「注册 GarlicSaves 账号」，在官网完成注册后回到编辑器，点击「登录 GarlicSaves」。已有账号可直接点击「我已有账号，直接登录」。随后在官网登录自己的账号，核对页面显示的设备码后批准 GTA6 Story Save Editor，再回到编辑器。可以在账号菜单退出或切换账号。官网队列详情所需的浏览器会话与设备授权分别管理。


点击「下载存档」后，多个剧情槽位会分批解密。同一批共享一个服务器排位，最多 64 个槽位、通常不超过 64 MiB。返回结果会按槽位核对。保存修改仍按当前选中的槽位加密。编辑页的「存档时间」来自游戏写入的时间戳，按电脑时区显示，精确到秒。

排队时可以点「在 GarlicSaves 官网查看排位」。请先在同一浏览器登录官网，再点这个链接。官网的 `position` 是当前任务的排位，`total` 是全站排队任务数。若要在编辑器内自动显示数字，可将仅含 GarlicSaves 登录会话的 Netscape 格式 Cookie 文件保存在本机，在启动前将环境变量 `GARLIC_QUEUE_COOKIE_FILE` 设为该文件的完整路径。Windows PowerShell 示例为 `$env:GARLIC_QUEUE_COOKIE_FILE = 'C:\Private\garlicsaves-cookies.txt'`，然后在同一窗口运行启动脚本。请将该文件保存在私人目录。编辑器约每 15 秒向官网查询一次；未登录或数字不可用时会显示提示。

1. 在与 PS5 连接同一家庭网络的电脑上启动编辑器。编辑器默认打开在 `http://127.0.0.1:7283`，使用期间请保持启动窗口打开。
2. 点“查找我的 PS5”，或手动输入主机的 IP 地址。
3. 每台主机首次使用时点击“开始配对”。在 PS5 打开“设置 → 系统 → 系统软件 → 数据传输”，选择 **Save Garage Pairing**。出现无法传输的提示后，可返回编辑器查看配对状态。
4. 在游戏中保存进度，返回 PS5 主界面。点击“下载存档”，根据提示按一次 PS5 电源键，听到提示音后松开。主机会为传输重启。
5. 选择要修改的存档。游戏的“继续”会载入自动存档。完成编辑后点击“将修改保存至此存档”。
6. 在 PS5 另存一份备份，并在测试期间关闭 GTA VI 自动同步。PS5 传输时不会覆盖已有存档，需要先删除主机上的旧 GTA VI 存档。点击“发送存档至 PS5”，再在 PS5 的“数据传输”里选择 **Save Garage** 并开始传输。

如果编辑后的存档无法载入，可以使用“恢复原始存档”并重新传回。各操作的主机菜单路径也会显示在编辑器中。

## 启动与常见问题

- Windows 版解压后运行 `Start MoonSlot.bat`。如系统防火墙询问，允许它通过家庭网络所用的专用网络。
- macOS 版解压后运行 `Start MoonSlot.command`。Linux 版解压后运行 `./MoonSlot --open`。从源码启动需要 Python 3.10 或更高版本和 curl，详见[英文启动说明](README.md#run-from-source)。
- 找不到主机时，确认电脑和 PS5 在同一网络，使用的端口为 TCP 1004–1005 和 UDP 1006。Linux 低端口权限见[原项目 Linux 说明](README.md#linux-notes)。
- 金钱余额为 0 或角色尚未持有某弹种时，存档通常没有对应的可编辑条目。可以在游戏中取得少量对应物品后重新保存并下载。
- 加解密依赖 [GarlicSaves](https://garlicsaves.com)。该服务会接收处理存档所需的数据，其中包含存档关联的 PSN 账号 ID。本地备份路径可查阅[英文隐私与备份说明](README.md#what-leaves-your-computer)。

## 署名与许可

- **Save Garage** 由 NotHGM 开发：存档引擎与研究、全部编辑功能（金钱、统计、完成度、世界、武器等）、GarlicSaves 登录、自动更新和界面。本简体中文版基于其 [Save Garage 原项目](https://github.com/NotHGM/save-garage)，是修改版而非官方版本。
- **原版存档修改器**由 CoreyLyu76 开发。Save Garage 的本地服务和金钱编辑功能源自其 [gta6-save-editor](https://github.com/CoreyLyu76/gta6-save-editor)。
- **PS5 数据传输**使用 earthonion 开发的 [GarlicTransfer](https://github.com/earthonion/GarlicTransfer)。

Save Garage 和上述两个基础项目均采用 [GPL-3.0 许可证](LICENSE)。组件版本与其他贡献者署名见 [CREDITS.md](CREDITS.md)。

Grand Theft Auto 和 PlayStation 是其各自权利人的商标。Save Garage 由社区维护，适用于个人故事模式存档。
