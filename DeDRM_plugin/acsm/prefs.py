#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# acsm/prefs.py — minimal standalone substitute for the upstream Calibre prefs
# module (calibre_plugins.deacsm.prefs). The ported acsm core reads
# detailed_logging / rented-book state from this; for the standalone GUI we keep
# everything inert (v1 does no fulfillment-notification / loan-return bookkeeping).
#
# Upstream: Leseratte10 acsm-calibre-plugin (GPL v3). Adapted for DeDRM_tools.
# Released under the terms of the GNU General Public License, version 3.

__license__ = 'GPL v3'


class ACSMInput_Prefs:
    """Mirrors upstream ACSMInput_Prefs so the ported modules can read it both
    as attributes (prefs.ACSMInput_Prefs().detailed_logging) and as a subscript
    (deacsmprefs['detailed_logging']), while performing no persistence.

    refresh()/commit() are no-ops: the loan-return / rented-book flow they feed
    simply finds an empty list and does nothing, which is what we want for v1.
    """

    def __init__(self):
        self.detailed_logging = False
        self.list_of_rented_books = []
        self.return_behavior = {}

    def __getitem__(self, key):
        return getattr(self, key, None)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def refresh(self):
        return None

    def commit(self):
        return None
