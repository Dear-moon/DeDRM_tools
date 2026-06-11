# DeDRM Standalone GUI

One-click DRM removal for Kindle / Adobe / B&N / LCP ebooks. **No Calibre required.** Drag, drop, decrypt.

## Quick Start

1. Download `DeDRM_GUI.exe` from [Releases](../../releases)
2. Double-click to launch
3. Drag your encrypted ebook into the window → click **Decrypt**

First-time use requires key extraction (see below).

## Supported Formats

| Source | DRM Scheme | Formats | GUI Support |
|--------|-----------|---------|-------------|
| Kindle for PC (traditional installer) | KFX/KF8/Mobi/Topaz | `.azw` `.azw3` `.mobi` | Full |
| Kindle for PC 2.8+ (separated KFX) | KFX + external voucher | `.azw` + `.voucher` + `.res` | Full (auto-wrap) |
| Kindle e-ink (Paperwhite / Oasis) | KFX device-bound | `.kfx` | Full (serial number) |
| Kindle UWP / Microsoft Store | KFX with CLIENT_ID voucher | CONT `.azw` | **See below** |
| Amazon "Download & transfer via USB" | Mobi/KF8 | `.azw3` | Full |
| Adobe Digital Editions | ADEPT | `.epub` `.pdf` | Full |
| B&N / Nook | PassHash | `.epub` | Full |
| Readium LCP | LCP (basic + profile-1.0) | `.epub` | Full |

### Kindle UWP / Microsoft Store

The Microsoft Store version of Kindle uses **CLIENT_ID-locked vouchers** protected by TPM. These cannot be statically decrypted.

**Workflow**:
1. Run `standalone_gui\tools\MSIXKFXArchiver.exe` (bundled)
2. It hooks the running Kindle process to decrypt books in real-time
3. Output: `.kfx-zip` files (CONT container format, already decrypted) + `oldbooks.k4i`
4. Import the `.kfx-zip` into **Calibre with the KFX Input plugin** to convert to EPUB
5. Drag `oldbooks.k4i` into the GUI for use with traditional K4PC books

The GUI will detect CONT-format files and show a helpful message.

## Usage

### Kindle for PC (traditional installer)

**1. Extract keys** — Click **Refresh Keys** on the Decrypt Tab:
- Auto-scans local Kindle for PC registry
- Auto-runs the bundled key extractors (`KFXKeyExtractor28.exe` or `MSIXKFXArchiver.exe`)
- Shows import summary

Or manually:
```cmd
cd standalone_gui\tools
KFXKeyExtractor28.exe "%USERPROFILE%\Documents\My Kindle Content" kfxkey k4ikey.k4i
```
Then drag the generated `kfxkey` and `k4ikey.k4i` into the GUI window.

**2. Decrypt** — Drag the `.azw` file (from `Documents\My Kindle Content\B0XXX_EBOK\`) into the window. File type is auto-detected. Click **Decrypt**.

### Kindle e-ink (Paperwhite / Oasis etc.)

**1. Enter serial number** — In the **Serials & PIDs Tab**, enter your Kindle device serial number (find it at Amazon → Manage Your Devices, format like `G090 XXXX XXXX XXXX`).

**2. Copy book folder** — Connect your Kindle via USB and copy the entire book folder (e.g. `Documents/BookTitle_B07XXX.sdr/`) to your PC.

**3. Decrypt** — Drag the `.kfx` file from the folder into the window. Companion files in subdirectories (`assets/voucher`, etc.) are auto-detected and packaged recursively. Click **Decrypt**.

### Adobe / B&N / LCP

Import your keys or enter your passphrase in the corresponding tab, then drag in `.epub` / `.pdf` files to decrypt.

## Drag & Drop

Drop any supported file onto the window — it's routed automatically:

| File | Action |
|------|--------|
| `.azw` `.epub` `.pdf` `.kfx` `.mobi` etc. | Load into Decrypt Tab |
| `.k4i` | Import as Kindle account key |
| `.der` | Import as Adobe ADE key |
| `.b64` | Import as B&N key |
| `kfxkey` / `keyfile` (no extension) | Set as KFX voucher key file |

## Tabs

| Tab | Purpose |
|-----|---------|
| **Decrypt** | File selection, type detection, decryption, log, Refresh Keys |
| **Kindle Keys** | Scan/import K4PC keys, manual serial/PID entry |
| **Adobe Keys** | Scan/import ADE keys, PDF password management |
| **B&N Keys** | Scan/generate Nook PassHash keys |
| **Serials & PIDs** | Kindle serial numbers, eReader PIDs |
| **Settings** | Font deobfuscation, watermark removal, KFX voucher path |

## Bundled Tools

Located in `standalone_gui/tools/`:

| Tool | Purpose |
|------|---------|
| `KFXKeyExtractor28.exe` | Extract keys from Kindle for PC 2.8.0+ (traditional installer) |
| `MSIXKFXArchiver.exe` | Extract/decrypt books from Kindle UWP (Microsoft Store) |
| `kindleFridaInstr.py` | Optional Frida-based live key extraction |

## Run from Source

```bash
pip install pycryptodome lxml PyQt6 legacy-cgi
python standalone_gui/main.py
```

## Build

```bash
pip install pyinstaller
pyinstaller dedrm_gui.spec
# Output → dist/DeDRM_GUI.exe
```

To compile `MSIXKFXArchiver.exe` from source:
```bash
python Other_Tools/KRFKeyExtractor/compile_msix.py
# Requires Visual Studio 2022 Build Tools with Windows SDK
# Output → Other_Tools/KRFKeyExtractor/MSIXKFXArchiver.exe
```

## Credits

Based on the following open-source projects:

- [noDRM/DeDRM_tools](https://github.com/noDRM/DeDRM_tools) — Calibre DeDRM plugin
- [Satsuoni/DeDRM_tools](https://github.com/Satsuoni/DeDRM_tools) — maintained fork
- Apprentice Harper, Apprentice Alf — original DeDRM tools
- The Dark Reverser — MobiDeDRM
- i♥cabbages — Adobe ADEPT scripts
- meaclam, uhuxybim — LCP decryption

## License

GPL v3
