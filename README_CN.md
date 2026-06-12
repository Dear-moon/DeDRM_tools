# DeDRM Standalone GUI

独立图形化电子书 DRM 去除工具。支持 Kindle / Adobe / B&N / LCP。**无需 Calibre**，拖拽即用。

## 快速开始

1. 从 [Releases](../../releases) 下载 `DeDRM_GUI.exe`
2. 双击运行
3. 拖入加密电子书 → 点 **Decrypt**

首次使用：点一下 **Refresh Keys**（自动从已安装的 Kindle/ADE 提取密钥）。

## 支持格式

| 来源 | 格式 | 处理引擎 | 输出 |
|------|------|---------|------|
| Kindle for PC 传统安装版 | `.azw` `.azw3` `.mobi` | `mobidedrm` / `kfxdedrm` | `.azw3` |
| Kindle for PC 2.8+ 分离式 | `.azw` + `.voucher` + `.res` | 自动打包 → `kfxdedrm` | `.azw3` |
| Kindle e-ink 设备 | `.kfx` + `assets/voucher` | 递归打包 → `k4mobidedrm` | `.azw3` |
| Kindle UWP / MS Store | `.kfx-zip` (CONT 容器) | **`kfxlib` (零依赖)** | `.epub` |
| 亚马逊 "下载并传输至USB" | `.azw3` | `mobidedrm` | `.azw3` |
| Adobe Digital Editions | `.epub` `.pdf` | `ineptepub` / `ineptpdf` | `.epub` / `.pdf` |
| B&N / Nook | `.epub` | `ineptepub` (PassHash) | `.epub` |
| Readium LCP | `.epub` | `lcpdedrm` | `.epub` |

## 使用流程

### Kindle for PC 传统安装版

点 **Refresh Keys** — 自动扫描注册表、运行 `KFXKeyExtractor28.exe`。然后拖入 `.azw` → Decrypt。

### Kindle UWP / Microsoft Store

点 **Refresh Keys** — 自动运行 `MSIXKFXArchiver.exe`（Hook 运行中的 Kindle 进程，需 ~400MB 临时空间）。输出的 `.kfx-zip` 可直接拖入，通过内置 `kfxlib` **零依赖**转换为 EPUB。

### Kindle e-ink 设备

在 **Serials & PIDs Tab** 输入序列号。USB 连接 Kindle，复制书籍文件夹到电脑。拖入 `.kfx` — 自动递归检测 `assets/voucher`。

### Adobe / B&N / LCP

在 **Adobe Keys** / **B&N Keys** Tab 扫描或导入密钥。拖入 `.epub`/`.pdf` → Decrypt。

## 密钥提取（Refresh Keys）

```
① kindlekey.kindlekeys()      ← 注册表扫描 (K4PC 传统版)
② KFXKeyExtractor28.exe       ← 内存提取 (Kindle 2.8+)
③ MSIXKFXArchiver.exe         ← TPM + Hook (UWP/MS Store)
④ Frida (可选)                ← pip install frida frida-tools
```

提取到的密钥自动去重导入并弹窗汇总。

## 拖拽导入

| 拖入文件 | 行为 |
|---------|------|
| `.azw` `.epub` `.pdf` `.kfx` `.mobi` `.kfx-zip` | 填入 Decrypt Tab |
| `.k4i` | 导入 Kindle 账户密钥 |
| `.der` | 导入 Adobe ADE 密钥 |
| `.b64` | 导入 B&N 密钥 |
| `kfxkey` / `keyfile`（无后缀） | 设置 KFX voucher 密钥文件 |

## 界面

| Tab | 功能 |
|-----|------|
| **Decrypt** | 文件选择、类型检测、解密、日志、一键刷新密钥 |
| **Kindle Keys** | 扫描/导入 K4PC 密钥、手动输入序列号/PID |
| **Adobe Keys** | 扫描/导入 ADE 密钥、PDF 密码管理 |
| **B&N Keys** | 扫描/生成 Nook PassHash 密钥 |
| **Serials & PIDs** | Kindle 序列号、eReader PID |
| **Settings** | 字体去混淆、水印移除、KFX voucher 路径 |

## 架构

```
standalone_gui/
├── main.py              ← 入口
├── compat.py             ← DeDRM 导入引导
├── app_config.py         ← JSON 配置管理
├── main_window.py        ← QMainWindow + 全局拖放
├── tabs/                 ← 6 个功能 Tab
├── workers/              ← QThread 解密 + 密钥扫描
└── tools/                ← KFXKeyExtractor28.exe + MSIXKFXArchiver.exe

DeDRM_plugin/
├── kfxlib/               ← CONT 容器解析 (35 文件，零 Calibre 依赖)
├── kfxlib_standalone.py  ← Calibre stub 注入 → YJ_Book → EPUB
├── (原始 DeDRM 代码未修改)
```

## 从源码运行

```bash
pip install pycryptodome lxml PyQt6
python standalone_gui/main.py
```

## 构建

```bash
pip install pyinstaller
pyinstaller dedrm_gui.spec
# → dist/DeDRM_GUI.exe
```

编译 `MSIXKFXArchiver.exe`（需 VS 2022 BuildTools）：
```bash
python Other_Tools/KRFKeyExtractor/compile_msix.py
```

## 致谢

- [noDRM/DeDRM_tools](https://github.com/noDRM/DeDRM_tools) — Calibre DeDRM 插件
- [Satsuoni/DeDRM_tools](https://github.com/Satsuoni/DeDRM_tools) — 持续维护分支
- KFX Input 插件 (John Howell, `kfxlib/`) — CONT 容器解析
- Apprentice Harper, Apprentice Alf — 原始 DeDRM 工具
- The Dark Reverser — MobiDeDRM
- i♥cabbages — Adobe ADEPT 脚本
- meaclam, uhuxybim — LCP 解密

## License

GPL v3
