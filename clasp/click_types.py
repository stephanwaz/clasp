# Copyright (c) 2018 Stephen Wasilewski
# =======================================================================
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# =======================================================================

import os
import re
import sys
import shlex
import tempfile
from glob import glob
import click

import clasp.script_tools as cst


class IsFile(click.Path):
    """extends click.Path to change defaults and handle stdin pipe
    by reading to a temporary file
    """
    def __init__(self,):
        super(IsFile, self).__init__(exists=True, file_okay=True,
                                     dir_okay=False, writable=False,
                                     readable=True, resolve_path=False,
                                     allow_dash=True, path_type=str)
        self.name = 'file'
        self.path_type = 'File'

    def convert(self, value, param, ctx):
        rv = super(IsFile, self).convert(value, param, ctx)
        # if rv in (b'-', '-'):
        #     rv = tmp_stdin(ctx)
        return rv
