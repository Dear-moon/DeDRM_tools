#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# lcpdedrm.py — Decrypt Readium LCP protected EPUBs.
# Copyright (c) 2021-2022 NoDRM, meaclam, uhuxybim
# Profile-1.0 master key from Readium LCP open specification.
# Released under the terms of the GNU General Public Licence, version 3.

__license__ = 'GPL v3'
__version__ = "3"

import os
import json
import hashlib
import base64
import binascii
import shutil
import tempfile
from io import BytesIO
from zipfile import ZipFile, ZipInfo, ZIP_STORED, ZIP_DEFLATED
from contextlib import closing

try:
    from Cryptodome.Cipher import AES
except ImportError:
    from Crypto.Cipher import AES


class LCPError(Exception):
    pass


# --- Profile transforms ---

MASTERKEY_PROFILE10 = bytes.fromhex(
    "b3a07c4d42880e69398e05392405050e"
    "feea0664c0b638b7c986556fa9b58d77"
    "b31a40eb6a4fdba1e4537229d9f779da"
    "ad1cc41ee968153cb71f27dc9696d40f"
)


def _transform_basic(input_hex):
    return input_hex


def _transform_profile10(input_hex):
    current = bytearray.fromhex(input_hex)
    for byte in MASTERKEY_PROFILE10:
        current.append(byte)
        current = bytearray(hashlib.sha256(current).digest())
    return binascii.hexlify(current).decode("ascii")


# --- AES-CBC decrypt helper ---

def _aes_cbc_decrypt_b64(b64_data, hex_key):
    raw = base64.b64decode(b64_data)
    iv, cipher = raw[:16], raw[16:]
    aes = AES.new(binascii.unhexlify(hex_key), AES.MODE_CBC, iv)
    plain = aes.decrypt(cipher)
    pad_len = plain[-1]
    return plain[:-pad_len]


# ---- Public API ----

def isLCPbook(inpath):
    """Check if a file is an LCP-protected EPUB."""
    try:
        with closing(ZipFile(open(inpath, 'rb'))) as zf:
            namelist = zf.namelist()
            if 'META-INF/license.lcpl' not in namelist:
                return False
            lic = json.loads(zf.read('META-INF/license.lcpl'))
            return ('id' in lic and 'encryption' in lic
                    and 'profile' in lic['encryption'])
    except Exception:
        pass
    return False


def decryptLCPbook(inpath, passphrases, parent_object=None):
    """Decrypt an LCP-protected EPUB. Returns path to decrypted file."""
    if not isLCPbook(inpath):
        raise LCPError("This is not an LCP-encrypted book")

    with closing(ZipFile(open(inpath, 'rb'))) as zf:
        namelist = zf.namelist()
        lic = json.loads(zf.read('META-INF/license.lcpl'))
        print("LCP: Found book {0}".format(lic["id"]))

        # Determine profile
        profile = lic["encryption"]["profile"]
        if profile == "http://readium.org/lcp/basic-profile":
            print("LCP: basic-profile")
            transform = _transform_basic
        elif profile == "http://readium.org/lcp/profile-1.0":
            print("LCP: profile-1.0")
            transform = _transform_profile10
        else:
            raise LCPError("Unknown LCP profile: {0}".format(profile))

        # Verify content key algorithm
        ck_algo = lic["encryption"]["content_key"].get("algorithm", "")
        if ck_algo and ck_algo != "http://www.w3.org/2001/04/xmlenc#aes256-cbc":
            raise LCPError("Unknown content key algorithm: {0}".format(ck_algo))

        key_check_b64 = lic["encryption"]["user_key"]["key_check"]
        encrypted_content_key_b64 = lic["encryption"]["content_key"]["encrypted_value"]

        # Collect candidate hashes
        hashes = []

        # Some providers embed the passphrase hash directly
        uk = lic["encryption"]["user_key"]
        if "value" in uk:
            try:
                hashes.append(binascii.hexlify(
                    base64.b64decode(uk["value"].encode())).decode("ascii"))
            except Exception:
                pass
        if "hex_value" in uk:
            hashes.append(binascii.hexlify(
                bytearray.fromhex(uk["hex_value"])).decode("ascii"))

        # Hash user-provided passphrases
        user_algo = uk.get("algorithm", "http://www.w3.org/2001/04/xmlenc#sha256")
        for pw in passphrases:
            if user_algo.endswith("#sha256"):
                hashes.append(hashlib.sha256(pw.encode("utf-8")).hexdigest())
            else:
                print("LCP: Unsupported user key algorithm: {0}".format(user_algo))

        # Try each hash
        correct_hash = None
        for h in hashes:
            transformed = transform(h)
            try:
                dec = _aes_cbc_decrypt_b64(key_check_b64, transformed)
                if dec.decode("ascii", errors="ignore") == lic["id"]:
                    correct_hash = transformed
                    break
            except Exception:
                continue

        if correct_hash is None:
            hint = uk.get("text_hint", "")
            if hint:
                print("LCP: Passphrase hint: {0}".format(hint))
            raise LCPError(
                "Tried {0} passphrase(s), none matched. {1}".format(
                    len(passphrases),
                    "Hint: " + hint if hint else ""))

        print("LCP: Passphrase accepted, decrypting content key...")
        content_key = _aes_cbc_decrypt_b64(encrypted_content_key_b64, correct_hash)

        # Determine which files are encrypted via encryption.xml
        encrypted_files = set()
        if 'META-INF/encryption.xml' in namelist:
            enc_xml = zf.read('META-INF/encryption.xml').decode('utf-8')
            import re
            for uri in re.findall(r'CipherReference\s+URI="([^"]*)"', enc_xml):
                encrypted_files.add(uri)

        # Write output epub
        outpath = inpath
        if parent_object is not None and hasattr(parent_object, 'temporary_file'):
            outpath = parent_object.temporary_file('.epub').name
        else:
            base, ext = os.path.splitext(inpath)
            outpath = base + '_nodrm' + ext

        kwds = dict(compression=ZIP_DEFLATED, allowZip64=False)
        with closing(ZipFile(open(outpath, 'wb'), 'w', **kwds)) as outf:
            for path in namelist:
                data = zf.read(path)
                zi = ZipInfo(path)
                zi.compress_type = ZIP_DEFLATED

                if path == 'mimetype':
                    zi.compress_type = ZIP_STORED
                elif path == 'META-INF/encryption.xml':
                    continue  # Remove encryption manifest
                elif path in encrypted_files:
                    # AES-256-CBC: first 16 bytes are IV
                    iv = data[:16]
                    aes = AES.new(content_key, AES.MODE_CBC, iv)
                    data = aes.decrypt(data[16:])
                    pad_len = data[-1]
                    data = data[:-pad_len]
                elif path == 'META-INF/license.lcpl':
                    continue  # Remove license

                try:
                    old_zi = zf.getinfo(path)
                    zi.date_time = old_zi.date_time
                except Exception:
                    pass

                outf.writestr(zi, data)

        print("LCP: Decryption complete: {0}".format(outpath))
        return outpath
