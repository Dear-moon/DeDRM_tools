# DeDRM Standalone GUI

独立图形化电子书 DRM 去除工具。支持 Kindle / Adobe / B&N / LCP。**无需 Calibre**，拖拽即用。

## 快速开始

1. 从 [Releases](../../releases) 下载 `DeDRM_GUI.exe`
2. 双击运行
3. 把加密电子书拖进窗口 → 点 **Decrypt**

首次使用需提取密钥（见下文）。

## 支持格式

| 来源 | DRM 方案 | 格式 | 支持 |
|------|---------|------|------|
| Kindle for PC 传统安装版 | KFX/KF8/Mobi/Topaz | `.azw` `.azw3` `.mobi` | ✅ 完整 |
| Kindle for PC 2.8+ 分离式 | KFX + 外部 voucher | `.azw` + `.voucher` + `.res` | ✅ 自动打包 |
| Kindle e-ink 设备 | KFX 设备绑定 | `.kfx` | ✅ 序列号 |
| Kindle UWP / Microsoft Store | KFX CLIENT_ID 锁定 | CONT `.azw` | ⚠️ 见下文 |
| 亚马逊网站 "通过USB传输" | Mobi/KF8 | `.azw3` | ✅ 完整 |
| Adobe Digital Editions | ADEPT | `.epub` `.pdf` | ✅ 完整 |
| B&N / Nook | PassHash | `.epub` | ✅ 完整 |
| Readium LCP | LCP (basic + profile-1.0) | `.epub` | ✅ 完整 |

### Kindle UWP / Microsoft Store 版本

Microsoft Store 版 Kindle 使用 **CLIENT_ID 锁定的 voucher**，受 TPM 芯片保护，无法静态破解。

**工作流**：
1. 运行 `standalone_gui\tools\MSIXKFXArchiver.exe`（已内置）
2. 它会 Hook 运行中的 Kindle 进程实时解密
3. 输出：`.kfx-zip` 文件（CONT 容器，已解密）+ `oldbooks.k4i`
4. 将 `.kfx-zip` 导入 **Calibre + KFX Input 插件** 转为 EPUB
5. 将 `oldbooks.k4i` 拖入 GUI 用于传统 K4PC 书籍

GUI 检测到 CONT 格式文件时会显示友好提示。

## 使用流程

### Kindle for PC（传统安装版）

**1. 提取密钥** — 点击 Decrypt Tab 的 **Refresh Keys**：
- 自动扫描本机 Kindle for PC 注册表
- 自动运行内置提取器（`KFXKeyExtractor28.exe` / `MSIXKFXArchiver.exe`）
- 弹窗显示导入结果

或手动运行：
```cmd
cd standalone_gui\tools
KFXKeyExtractor28.exe "%USERPROFILE%\Documents\My Kindle Content" kfxkey k4ikey.k4i
```
将生成的 `kfxkey` 和 `k4ikey.k4i` 拖入 GUI 窗口即可自动导入。

**2. 解密** — 拖入 `.azw` 文件（位于 `Documents\My Kindle Content\B0XXX_EBOK\`），自动检测类型，点 Decrypt。

### Kindle e-ink 设备（Paperwhite / Oasis 等）

**1. 输入序列号** — 在 **Serials & PIDs Tab** 输入 Kindle 设备序列号（亚马逊 → 管理我的设备，格式如 `G090 XXXX XXXX XXXX`）。

**2. 复制书籍** — 连接 Kindle 到电脑，复制整个书籍目录（如 `Documents/BookTitle_B07XXX.sdr/`）。

**3. 解密** — 拖入 `.kfx` 文件，自动递归检测子目录（`assets/voucher` 等）并打包，点 Decrypt。

### Adobe / B&N / LCP

在对应 Tab 导入密钥或输入密码后，拖入 `.epub` / `.pdf` 即可解密。

## 拖拽导入

所有文件均可直接拖到窗口上，自动识别：

| 拖入文件 | 行为 |
|---------|------|
| `.azw` `.epub` `.pdf` `.kfx` `.mobi` 等 | 填入 Decrypt Tab |
| `.k4i` | 导入 Kindle 账户密钥 |
| `.der` | 导入 Adobe ADE 密钥 |
| `.b64` | 导入 B&N 密钥 |
| `kfxkey` / `keyfile`（无后缀） | 设置 KFX voucher 密钥文件 |

## 界面说明

| Tab | 功能 |
|-----|------|
| **Decrypt** | 文件选择、类型检测、解密、日志、一键刷新密钥 |
| **Kindle Keys** | 扫描/导入 K4PC 密钥、手动输入序列号/PID |
| **Adobe Keys** | 扫描/导入 ADE 密钥、PDF 密码管理 |
| **B&N Keys** | 扫描/生成 Nook PassHash 密钥 |
| **Serials & PIDs** | Kindle 设备序列号、eReader PID 管理 |
| **Settings** | 字体去混淆、水印移除、KFX voucher 路径 |

## 内置工具

位于 `standalone_gui/tools/`：

| 工具 | 用途 |
|------|------|
| `KFXKeyExtractor28.exe` | 从 Kindle for PC 2.8.0+ 传统安装版提取密钥 |
| `MSIXKFXArchiver.exe` | 从 Kindle UWP（Microsoft Store）提取/解密书籍 |
| `kindleFridaInstr.py` | Frida 实时注入密钥提取（可选） |

## 从源码运行

```bash
pip install pycryptodome lxml PyQt6 legacy-cgi
python standalone_gui/main.py
```

## 构建

```bash
pip install pyinstaller
pyinstaller dedrm_gui.spec
# 输出 → dist/DeDRM_GUI.exe
```

编译 `MSIXKFXArchiver.exe`：
```bash
python Other_Tools/KRFKeyExtractor/compile_msix.py
# 需要 Visual Studio 2022 BuildTools + Windows SDK
# 输出 → Other_Tools/KRFKeyExtractor/MSIXKFXArchiver.exe
```

## 致谢

基于以下开源工作：

- [noDRM/DeDRM_tools](https://github.com/noDRM/DeDRM_tools) — Calibre DeDRM 插件
- [Satsuoni/DeDRM_tools](https://github.com/Satsuoni/DeDRM_tools) — 持续维护分支
- Apprentice Harper, Apprentice Alf — 原始 DeDRM 工具
- The Dark Reverser — MobiDeDRM
- i♥cabbages — Adobe ADEPT 脚本
- meaclam, uhuxybim — LCP 解密

## License

GPL v3
