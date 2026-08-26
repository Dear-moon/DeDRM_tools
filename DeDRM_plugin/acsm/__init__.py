#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# acsm/__init__.py — high-level API bridging the DeDRM_tools standalone GUI to the
# ported (de-Calibred) ACSM fulfillment + Adobe ADE account/device modules.
#
# Everything below wraps the upstream Leseratte10 acsm-calibre-plugin core
# (GPL v3), which was rewritten in pure Python from the ADEPT protocol. The
# modules are imported lazily inside the functions to avoid package-initialise
# circular imports. Paths for the ADE "trio" (devicesalt / device.xml /
# activation.xml) are redirected with libadobe.update_account_path().
#
# Released under the terms of the GNU General Public License, version 3.

__license__ = 'GPL v3'

import os
import shutil
import tempfile

# '1' for ADE 2.0, '2' for ADE 3.0 (matches current ADE desktop builds).
DEFAULT_VER = 2

ACCOUNT_FILES = ('devicesalt', 'device.xml', 'activation.xml')


# --------------------------------------------------------------------------- #
# Account state helpers
# --------------------------------------------------------------------------- #

def account_status(account_dir):
    """Return {filename: bool} for the ADE trio in account_dir."""
    return {
        name: os.path.isfile(os.path.join(account_dir, name))
        for name in ACCOUNT_FILES
    }


def ensure_account(account_dir):
    """True when all three ADE activation files are present."""
    if not account_dir:
        return False
    return all(account_status(account_dir).values())


def _activate_paths(account_dir):
    os.makedirs(account_dir, exist_ok=True)
    from .libadobe import update_account_path
    update_account_path(account_dir)


def _require_account(account_dir):
    _activate_paths(account_dir)
    if not ensure_account(account_dir):
        raise RuntimeError(
            'Adobe account activation not found in %r. Use the "Adobe Keys" tab '
            'to Register/Import an ADE account, then retry.' % (account_dir,))


# --------------------------------------------------------------------------- #
# Account creation / import
# --------------------------------------------------------------------------- #

def register_account(account_type='anonymous', email='', password='',
                     account_dir=None, use_version=DEFAULT_VER):
    """Create a fresh ADE device/account — anonymous or AdobeID — writing the
    trio into account_dir. Returns True; raises RuntimeError on failure."""
    if not account_dir:
        raise ValueError('account_dir is required')
    from .libadobe import createDeviceKeyFile
    from .libadobeAccount import createDeviceFile, createUser, signIn, activateDevice

    _activate_paths(account_dir)

    createDeviceKeyFile()
    ok, err = createDeviceFile(True, use_version)
    if not ok:
        raise RuntimeError('createDeviceFile failed: %s' % (err,))
    ok, err = createUser(use_version, None)
    if not ok:
        raise RuntimeError('createUser failed: %s' % (err,))

    if account_type == 'anonymous':
        ok, err = signIn('anonymous', '', '')
    else:
        ok, err = signIn('AdobeID', email, password)
    if not ok:
        raise RuntimeError('signIn failed: %s' % (err,))

    ok, err = activateDevice(use_version, None)
    if not ok:
        raise RuntimeError('activateDevice failed: %s' % (err,))

    return True


def import_ade_account(account_dir, use_version=DEFAULT_VER):
    """Clone the locally-installed Adobe Digital Editions activation (Windows)
    into account_dir so fulfill can reuse the existing device/account."""
    if not account_dir:
        raise ValueError('account_dir is required')
    from .libadobeImportAccount import importADEactivationWindows

    _activate_paths(account_dir)
    ok, err = importADEactivationWindows(use_version)
    if not ok:
        raise RuntimeError('import ADE activation failed: %s' % (err,))
    return True


def export_ade_key(account_dir):
    """Return the bare RSA DER (strips the 26-byte PKCS#8 header) for the current
    account — the key that ineptepub/ineptpdf need. Reads activation.xml."""
    if not account_dir:
        raise ValueError('account_dir is required')
    from .libadobeAccount import exportAccountEncryptionKeyBytes
    _activate_paths(account_dir)
    return exportAccountEncryptionKeyBytes()


# --------------------------------------------------------------------------- #
# Fulfillment
# --------------------------------------------------------------------------- #

def fulfill_acsm(acsm_path, account_dir, out_dir=None):
    """Fulfill an .acsm into an encrypted epub/pdf using the activation in
    account_dir. Returns the absolute path to the produced (still-encrypted)
    epub/pdf. Raises RuntimeError on failure."""
    from .libadobeFulfill import fulfill as _fulfill
    from .fulfill import download as _download

    _require_account(account_dir)

    ok, reply = _fulfill(acsm_path)
    if not ok:
        raise RuntimeError('Fulfillment failed: %s' % (reply,))

    if out_dir is None:
        out_dir = os.path.dirname(os.path.abspath(acsm_path))

    # download() writes "bookname.epub/.pdf" to the CWD, so run it in a temp dir
    # and move the result out, avoiding clobbering the user's files.
    with tempfile.TemporaryDirectory() as tmp:
        cwd = os.getcwd()
        os.chdir(tmp)
        try:
            if not _download(reply):
                raise RuntimeError('download failed after fulfillment')
            produced = [f for f in os.listdir('.') if f.endswith(('.epub', '.pdf'))]
            if not produced:
                raise RuntimeError('no fulfilled book file was produced')
            os.makedirs(out_dir, exist_ok=True)
            dst = os.path.join(out_dir, produced[0])
            shutil.move(os.path.join(tmp, produced[0]), dst)
            return dst
        finally:
            os.chdir(cwd)
