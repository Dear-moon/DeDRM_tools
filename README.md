# DeDRM Standalone GUI

One-click DRM removal for Kindle / Adobe / B&N / LCP ebooks. **No Calibre required. Drag, drop, decrypt.**

## Quick Start

1. Download `DeDRM_GUI.exe` from [Releases](../../releases)
2. Double-click to launch
3. Drag your encrypted ebook into the window → click **Decrypt**

First use: click **Refresh Keys** once (auto-extracts keys from installed Kindle/ADE apps).

## Supported Formats

| Source | Format | Handler | Output |
|--------|--------|---------|--------|
| Kindle for PC (traditional) | `.azw` `.azw3` `.mobi` | `mobidedrm` / `kfxdedrm` | `.azw3` |
| Kindle for PC 2.8+ (separated) | `.azw` + `.voucher` + `.res` | auto-wrap → `kfxdedrm` | `.azw3` |
| Kindle e-ink (Paperwhite/Oasis) | `.kfx` + `assets/voucher` | recursive auto-wrap → `k4mobidedrm` | `.azw3` |
| Kindle UWP / MS Store | `.kfx-zip` (CONT container) | **`kfxlib` (zero deps)** | `.epub` |
| Amazon "Download & transfer via USB" | `.azw3` | `mobidedrm` | `.azw3` |
| Adobe Digital Editions | `.epub` `.pdf` | `ineptepub` / `ineptpdf` | `.epub` / `.pdf` |
| B&N / Nook | `.epub` | `ineptepub` (PassHash) | `.epub` |
| Readium LCP | `.epub` | `lcpdedrm` | `.epub` |

## Workflows

### Kindle for PC (traditional installer)

Click **Refresh Keys** — auto-scans registry, runs `KFXKeyExtractor28.exe`. Then drag `.azw` → Decrypt.

### Kindle UWP / Microsoft Store

Click **Refresh Keys** — auto-runs `MSIXKFXArchiver.exe` (hooks running Kindle process, needs ~400MB temp space). Output `.kfx-zip` can be dragged in directly for **zero-dependency** CONT→EPUB conversion via bundled `kfxlib`.

### Kindle e-ink device

Enter serial in **Serials & PIDs Tab**. Copy book folder from device via USB. Drag `.kfx` — auto-detects `assets/voucher` recursively.

### Adobe / B&N / LCP

Use **Adobe Keys** / **B&N Keys** tabs to scan or import keys. Drag `.epub`/`.pdf` → Decrypt.

## Key Extraction (Refresh Keys)

```
① kindlekey.kindlekeys()      ← Registry scan (K4PC traditional)
② KFXKeyExtractor28.exe       ← Memory extraction (Kindle 2.8+)
③ MSIXKFXArchiver.exe         ← TPM + Hook (UWP/MS Store)
④ Frida (optional)            ← pip install frida frida-tools
```

Collected keys are automatically de-duplicated and imported.

## Drag & Drop

| File | Action |
|------|--------|
| `.azw` `.epub` `.pdf` `.kfx` `.mobi` `.kfx-zip` | Load into Decrypt Tab |
| `.k4i` | Import Kindle account key |
| `.der` | Import Adobe ADE key |
| `.b64` | Import B&N key |
| `kfxkey` / `keyfile` (no extension) | Set KFX voucher key file |

## Tabs

| Tab | Purpose |
|-----|---------|
| **Decrypt** | File input, type detection, decrypt, log, Refresh Keys |
| **Kindle Keys** | Scan/import K4PC keys, manual serial/PID |
| **Adobe Keys** | Scan/import ADE keys, PDF passwords |
| **B&N Keys** | Scan/generate Nook PassHash keys |
| **Serials & PIDs** | Kindle serial numbers, eReader PIDs |
| **Settings** | Font deobfuscation, watermark removal, KFX voucher path |

## Architecture

```
standalone_gui/
├── main.py              ← Entry point
├── compat.py             ← DeDRM import bootstrap
├── app_config.py         ← JSON config manager
├── main_window.py        ← QMainWindow + drag-drop
├── tabs/                 ← 6 tab widgets
├── workers/              ← QThread decrypt + key scan
└── tools/                ← KFXKeyExtractor28.exe + MSIXKFXArchiver.exe

DeDRM_plugin/
├── kfxlib/               ← CONT container parser (35 files, zero Calibre deps)
├── kfxlib_standalone.py  ← Calibre stub injection → YJ_Book → EPUB
├── (original DeDRM code unchanged)
```

## Run from Source

```bash
pip install pycryptodome lxml PyQt6
python standalone_gui/main.py
```

## Build

```bash
pip install pyinstaller
pyinstaller dedrm_gui.spec
# → dist/DeDRM_GUI.exe
```

To compile `MSIXKFXArchiver.exe` (requires VS 2022 BuildTools):
```bash
python Other_Tools/KRFKeyExtractor/compile_msix.py
```

## Credits

- [noDRM/DeDRM_tools](https://github.com/noDRM/DeDRM_tools) — Calibre DeDRM plugin
- [Satsuoni/DeDRM_tools](https://github.com/Satsuoni/DeDRM_tools) — maintained fork
- KFX Input plugin by John Howell (`kfxlib/`) — CONT container parsing
- Apprentice Harper, Apprentice Alf — original DeDRM tools
- The Dark Reverser — MobiDeDRM
- i♥cabbages — Adobe ADEPT scripts
- meaclam, uhuxybim — LCP decryption

## License

GPL v3
