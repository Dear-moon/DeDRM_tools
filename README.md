# DeDRM Standalone GUI

一键去除 Kindle / Adobe / B&N 电子书 DRM 的独立图形化工具。**无需 Calibre**，无需命令行，拖拽即用。

## 快速开始

1. 从 [Releases](../../releases) 下载 `DeDRM_GUI.exe`
2. 双击运行
3. 把加密的电子书文件拖进窗口 → 点 **Decrypt**

首次使用需要提取一次密钥（见下文）。

## 功能

| DRM 类型 | 支持格式 | 状态 |
|---------|---------|------|
| Amazon Kindle (KFX/KF8/Mobi/Topaz) | `.azw` `.azw3` `.azw4` `.mobi` `.kfx-zip` | 完整支持 |
| Adobe ADEPT | `.epub` `.pdf` | 完整支持 |
| B&N PassHash | `.epub` | 完整支持 |
| Readium LCP | `.epub` | 完整支持 |

## 使用流程（Kindle KFX）

### 1. 提取密钥（仅首次或密钥刷新后）

**自动方式** — 点击 Decrypt Tab 的 **Refresh Keys**：
- 自动扫描本机已安装的 Kindle for PC / ADE
- 自动运行 KFX 密钥提取器
- 弹窗显示导入结果

**手动方式** — 如果自动扫描未找到：
```cmd
cd standalone_gui\tools
KFXKeyExtractor28.exe "%USERPROFILE%\Documents\My Kindle Content" kfxkey k4ikey.k4i
```
然后将生成的 `kfxkey` 和 `k4ikey.k4i` 拖入 GUI 窗口即可自动导入。

### 2. 解密

把 `.azw` 文件（位于 `Documents\My Kindle Content\B0XXX_EBOK\` 目录中）拖入窗口：

- 自动检测文件类型（KFX raw / MOBI / KFX-ZIP / PDF 等）
- KFX raw 文件自动检测同目录 voucher 并打包为 KFX-ZIP
- 点击 **Decrypt**，输出 `*_nodrm.*` 文件

### 3. 拖拽导入

所有文件都可以直接拖到窗口上，自动识别：

| 拖入文件 | 自动操作 |
|---------|---------|
| `.azw` `.epub` `.pdf` 等 | 填入 Decrypt Tab，准备解密 |
| `.k4i` | 导入为 Kindle 账户密钥 |
| `.der` | 导入为 Adobe ADE 密钥 |
| `kfxkey` / `keyfile`（无后缀） | 设置为 KFX voucher 密钥文件 |

## 手动配置密钥

如果自动提取不成功，也可以在各 Tab 中手动配置：

- **Kindle Keys Tab** — 导入 `.k4i` 文件、手动输入序列号/PID
- **Adobe Keys Tab** — 扫描 ADE、导入 `.der` 文件、添加 PDF 密码
- **B&N Keys Tab** — 扫描 Nook、用姓名+信用卡号生成密钥
- **Serials & PIDs Tab** — 管理 Kindle 序列号和 eReader PID
- **Settings Tab** — 字体去混淆、水印移除、KFX voucher 路径

## 从源码运行

```bash
pip install pycryptodome lxml PyQt6 legacy-cgi
python standalone_gui/main.py
```

## 构建 EXE

```bash
pip install pyinstaller
pyinstaller dedrm_gui.spec
# 输出在 dist/DeDRM_GUI.exe
```

## 致谢

本项目基于以下开源工作：

- [noDRM/DeDRM_tools](https://github.com/noDRM/DeDRM_tools) — Calibre DeDRM 插件
- [Satsuoni/DeDRM_tools](https://github.com/Satsuoni/DeDRM_tools) — 持续维护的分支
- Apprentice Harper, Apprentice Alf — 原始 DeDRM 工具
- The Dark Reverser — MobiDeDRM
- i♥cabbages — Adobe ADEPT 脚本
- meaclam, uhuxybim — LCP 解密

## License

GPL v3
