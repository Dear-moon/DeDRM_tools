"""Standalone KFX container to EPUB conversion using kfxlib (no Calibre needed).

Installs minimal calibre stubs in sys.modules before importing kfxlib,
so the full KFX Input plugin conversion logic works independently.
"""
import sys
import os
import tempfile
import shutil

# ---- Install calibre stubs into sys.modules ----

class _FakeCalibreModule:
    """Generic fake module that returns itself for any attribute access."""
    def __init__(self, **attrs):
        self.__dict__.update(attrs)
    def __getattr__(self, name):
        return None

# Build fake calibre module hierarchy
_calibre = _FakeCalibreModule(
    __name__='calibre',
    constants=_FakeCalibreModule(numeric_version=(6, 0, 0)),
    utils=_FakeCalibreModule(
        config_base=_FakeCalibreModule(
            tweaks={},
        ),
        resources=_FakeCalibreModule(
            get_path=lambda *a: os.path.join(*a),
        ),
        img=_FakeCalibreModule(
            load_jxr_data=lambda d: (_ for _ in ()).throw(NotImplementedError("JXR")),
            image_to_data=lambda i: b'',
        ),
    ),
    ptempfile=_FakeCalibreModule(
        PersistentTemporaryDirectory=lambda suffix='': tempfile.mkdtemp(suffix=suffix),
    ),
    ebooks=_FakeCalibreModule(
        metadata=_FakeCalibreModule(
            pdf=_FakeCalibreModule(
                page_images=lambda *a, **kw: [],
                get_tools=lambda: {},
            ),
        ),
    ),
)
_calibre_plugins = _FakeCalibreModule(
    dedrm=_FakeCalibreModule(
        ion=_FakeCalibreModule(
            DrmIon=lambda *a, **kw: _FakeCalibreModule(parse=lambda *a, **kw: None),
        ),
    ),
)

# Inject into sys.modules
sys.modules['calibre'] = _calibre
sys.modules['calibre.constants'] = _calibre.constants
sys.modules['calibre.utils'] = _calibre.utils
sys.modules['calibre.utils.config_base'] = _calibre.utils.config_base
sys.modules['calibre.utils.resources'] = _calibre.utils.resources
sys.modules['calibre.utils.img'] = _calibre.utils.img
sys.modules['calibre.ptempfile'] = _calibre.ptempfile
sys.modules['calibre.ebooks'] = _calibre.ebooks
sys.modules['calibre.ebooks.metadata'] = _calibre.ebooks.metadata
sys.modules['calibre.ebooks.metadata.pdf'] = _calibre.ebooks.metadata.pdf
sys.modules['calibre_plugins'] = _calibre_plugins
sys.modules['calibre_plugins.dedrm'] = _calibre_plugins.dedrm
sys.modules['calibre_plugins.dedrm.ion'] = _calibre_plugins.dedrm.ion

# Alias for calibre.utils.soupparser (used by original_source_epub)
try:
    from lxml import html as soupparser
except ImportError:
    import html.parser as _hp
    soupparser = _hp
sys.modules['calibre.utils.soupparser'] = _FakeCalibreModule()
sys.modules['calibre.utils.soupparser'].soupparser = soupparser

# Also stub calibre.ebooks.conversion (used by kpf_book)
sys.modules['calibre.ebooks.conversion'] = _FakeCalibreModule()
sys.modules['calibre.ebooks.conversion.plumber'] = _FakeCalibreModule()

# ---- Now import kfxlib ----
from DeDRM_plugin.kfxlib.yj_book import YJ_Book


def convert_kfx_to_epub(input_path, output_path, credentials=None):
    """Convert a KFX-ZIP (CONT container) to EPUB (no Calibre required).

    convert_to_epub() returns the EPUB as bytes — write them directly.
    """
    if credentials is None:
        credentials = []

    book = YJ_Book(input_path, credentials=credentials)
    epub_data = book.convert_to_epub()  # returns bytes (zip_epub output)

    if not epub_data:
        raise Exception("KFX conversion produced empty output")

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(epub_data)


def is_kfx_cont_format(filepath):
    """Quick check if a file is a KFX CONT container (standalone or in ZIP)."""
    import zipfile
    ext = os.path.splitext(filepath)[1].lower()

    # Check standalone CONT file
    if not ext:
        try:
            with open(filepath, 'rb') as f:
                return f.read(4) == b'CONT'
        except Exception:
            return False

    # Check inside ZIP
    if ext in ('.zip', '.kfx-zip', '.azw'):
        try:
            with zipfile.ZipFile(filepath, 'r') as zf:
                for name in zf.namelist():
                    with zf.open(name) as sf:
                        if sf.read(4) == b'CONT':
                            return True
        except Exception:
            pass
    return False
