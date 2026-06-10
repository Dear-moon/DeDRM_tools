# DeDRM Standalone GUI

One-click DRM removal for Kindle / Adobe / B&N / LCP ebooks. **No Calibre required.** Drag, drop, decrypt.

## Quick Start

1. Download `DeDRM_GUI.exe` from [Releases](../../releases)
2. Double-click to launch
3. Drag your encrypted ebook into the window → click **Decrypt**

First-time use requires key extraction (see below).

## Supported Formats

| DRM Scheme | Formats | Key Required |
|-----------|---------|-------------|
| Kindle for PC (KFX/KF8/Mobi/Topaz) | `.azw` `.azw3` `.mobi` `.kfx-zip` | K4PC account key |
| Kindle e-ink (KFX) | `.kfx` | Device serial number |
| Adobe ADEPT | `.epub` `.pdf` | ADE private key (.der) |
| B&N PassHash | `.epub` | Name + credit card number |
| Readium LCP | `.epub` | Passphrase |

## Usage

### Kindle for PC (most common)

**1. Extract keys** — Click **Refresh Keys** on the Decrypt Tab:
- Auto-scans local Kindle for PC registry
- Auto-runs the KFX key extractor
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

**3. Decrypt** — Drag the `.kfx` file from the folder into the window. The voucher in `assets/` and all companion files are auto-detected and packaged. Click **Decrypt**.

### Adobe / B&N / LCP

Import your keys or enter your passphrase in the corresponding tab, then drag in `.epub` / `.pdf` files to decrypt.

## Drag & Drop

Drop any supported file onto the window — it's routed automatically:

| File | Action |
|------|--------|
| `.azw` `.epub` `.pdf` `.kfx` `.mobi` etc. | Load into Decrypt Tab |
| `.k4i` | Import as Kindle account key |
| `.der` | Import as Adobe ADE key |
| `kfxkey` / `keyfile` (no extension) | Set as KFX voucher key file |

## Tabs

| Tab | Purpose |
|-----|---------|
| **Decrypt** | File selection, type detection, decryption, log |
| **Kindle Keys** | Scan/import K4PC keys, manual serial/PID entry |
| **Adobe Keys** | Scan/import ADE keys, PDF password management |
| **B&N Keys** | Scan/generate Nook PassHash keys |
| **Serials & PIDs** | Kindle serial numbers, eReader PIDs |
| **Settings** | Font deobfuscation, watermark removal, KFX voucher path |

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
