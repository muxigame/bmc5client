# muxigame BMC5 干净客户端

Minecraft **1.21.1** / NeoForge **21.1.250** / muxi-game-core **1.9.1**。
核心 JAR 与 [服务端仓库](https://github.com/muxigame/bmc5server) 的 1.9.1 校验值一致。
这是供协作修改的客户端内容仓库，不含启动器账号、Minecraft 游戏运行库或 Java。

## 拉取与准备

安装 Git 和 Python 3.10+（Windows 可用 `py -3.12` 代替 python）：

```sh
git clone -c core.longpaths=true https://github.com/muxigame/bmc5client.git
cd bmc5client
python tools/client.py setup
python tools/client.py verify
```

setup 从 GitHub Release 下载约 1.32 GB 的资源包并校验，从原作者地址下载 Simple Nicknames，在忽略提交的 `game/` 生成干净客户端内容。
Windows 建议放在 `C:\Games\bmc5client` 等短路径。光影文件夹层级较深，克隆命令已为本仓库启用 Git 长路径支持，不改全局设置。
它不打开游戏窗口，不登录账号，也不修改你现有的启动器实例。

然后用支持 NeoForge 的启动器新建 **Minecraft 1.21.1 + NeoForge 21.1.250** 实例，使用 **Java 21+**，建议分配 6–8 GB 堆内存。
将实例的游戏目录设为本仓库的 `game/`；若启动器不支持自定义游戏目录，则把 `game/` 内全部内容复制到该**新建实例**的游戏目录。
登录你自己的游戏账号后启动。不要将此包直接合并进装有另一套模组的实例。
启动器负责下载 Minecraft/NeoForge 运行库；单独下载 GitHub 的源码 ZIP 不包含模组二进制。

## 内容与协作

- `pack/`：可编辑的配置、任务、脚本、模型描述和光影源码等文本。
- `runtime-lock.json`：版本、资源 URL 和逐文件 SHA-256；二进制存放在 Release。
- `defaults/options.txt`：由整合包维护配置生成的默认按键/音量，不来自个人 options.txt。
- `pack-policy.json`：原整合包的配置覆盖规则和可选模组说明。setup 只对首次生成的文件应用规则，重跑保留本地修改。
- C2ME 按原包策略默认关闭，放在 `game/optional-mods/`；需要时自行移动到 mods，并自行测试兼容性。
- Simple Nicknames 保留原作者下载渠道，不在 ZIP 中重新托管。

修改 `pack/` 后提交分支/PR，不提交 `game/` 中的账号、世界、缓存和运行日志。为了保护本机设置，setup 不覆盖已有文本配置；测试配置改动时，将指定文件从 pack 复制到隔离测试实例，或另建干净 checkout。
更换二进制时使用新的 Release 和锁定清单，不覆盖现有同名资源；遇到已修改的本地二进制，setup 会中止。
核心 Java 源码在[服务端对应提交](https://github.com/muxigame/bmc5server/tree/b952651d7e9fd33a0098c554a2ae1def4786c797/modules/muxi-game-core)，来源 core 提交 `7e3863e`。

## 排除内容与验证边界

未上传账号/令牌、世界、截图、日志、崩溃报告、缓存、备份、个人 options、最近世界记录、原机器的版本目录和运行库。
网页配置管理密码不分发，各实例自行生成。不要把真实密钥写入公开配置。
资源完整性、核心一致性和配置生成可以无界面验证；这不等于已用图形客户端登录服务器完成所有玩法验收。
本次发布不修改或重启正式服。第三方模组、光影、模型和素材遵循各自作者许可，保留原始署名/许可；本仓库不声明拥有其版权。
