# DeDRM Standalone GUI

一键去除 Kindle / Adobe / B&N / LCP 电子书 DRM 的独立图形化工具。**无需 Calibre**，拖拽即用。

## 快速开始

1. 从 [Releases](../../releases) 下载 `DeDRM_GUI.exe`
2. 双击运行
3. 把加密电子书拖进窗口 → 点 **Decrypt**

首次使用需提取密钥（见下文）。

## 支持格式

| DRM 类型 | 格式 | 密钥要求 |
|---------|------|---------|
| Kindle for PC (KFX/KF8/Mobi/Topaz) | `.azw` `.azw3` `.mobi` `.kfx-zip` | K4PC 账户密钥 |
| Kindle e-ink 设备 (KFX) | `.kfx` | 设备序列号 |
| Adobe ADEPT | `.epub` `.pdf` | ADE 私钥 (.der) |
| B&N PassHash | `.epub` | 姓名+信用卡号 |
| Readium LCP | `.epub` | 密码短语 |

## 使用流程

### Kindle for PC (最常用)

**1. 提取密钥** — 点击 Decrypt Tab 的 **Refresh Keys**：
- 自动扫描本机 Kindle for PC 注册表
- 自动运行 KFX 密钥提取器
- 弹窗显示导入结果

或手动运行：
```cmd
cd standalone_gui\tools
KFXKeyExtractor28.exe "%USERPROFILE%\Documents\My Kindle Content" kfxkey k4ikey.k4i
```
将生成的 `kfxkey` 和 `k4ikey.k4i` 拖入 GUI 窗口自动导入。

**2. 解密** — 拖入 `.azw` 文件（位于 `Documents\My Kindle Content\B0XXX_EBOK\`），自动检测类型，点 Decrypt。

### Kindle e-ink 设备 (Paperwhite / Oasis 等)

**1. 输入序列号** — 在 **Serials & PIDs Tab** 输入 Kindle 设备序列号（可在亚马逊账户 → 管理设备页面找到，格式如 `G090 XXXX XXXX XXXX`）。

**2. 复制书籍** — 将 Kindle 连接电脑，复制整个书籍目录（如 `Documents/火星三部曲_B07XXX.sdr/`）到桌面。

**3. 解密** — 拖入目录中的 `.kfx` 文件，自动检测 voucher 并递归打包全部配套文件（含子目录 `assets/`），点 Decrypt。

### Adobe / B&N / LCP

在对应 Tab 中导入密钥或输入密码后，拖入 `.epub` / `.pdf` 即可解密。

## 拖拽导入

所有文件均可直接拖到窗口上，自动识别：

| 拖入文件 | 行为 |
|---------|------|
| `.azw` `.epub` `.pdf` `.kfx` `.mobi` 等 | 填入 Decrypt Tab |
| `.k4i` | 导入 Kindle 账户密钥 |
| `.der` | 导入 Adobe ADE 密钥 |
| `kfxkey` / `keyfile`（无后缀） | 设置 KFX voucher 密钥文件 |

## 界面说明

| Tab | 功能 |
|-----|------|
| **Decrypt** | 文件选择、类型检测、解密、日志 |
| **Kindle Keys** | 扫描/导入 K4PC 密钥、手动输入序列号/PID |
| **Adobe Keys** | 扫描/导入 ADE 密钥、PDF 密码管理 |
| **B&N Keys** | 扫描/生成 Nook PassHash 密钥 |
| **Serials & PIDs** | Kindle 设备序列号、eReader PID 管理 |
| **Settings** | 字体去混淆、水印移除、KFX voucher 路径 |

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
