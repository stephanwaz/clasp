# Copyright (c) 2018 Stephen Wasilewski
# =======================================================================
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# =======================================================================

# The MIT License
#
# Copyright (c) 2017 Stephen Finucane http://that.guru/
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

"""modify sphinx_click for more consistent behavior in html docs and --help

usage: in sphinx docs/conf.py add to extensions (list): 'clasp.sphinx_click_ext'
"""
import re
from clasp import click
import sphinx_click.ext as ext
from clasp.click_ext import index_param, index_seps
from clasp.click_callbacks import pretty_callback_names as pcn


def _filter_commands(ctx, commands=None):
    """Return list of used commands."""
    lookup = getattr(ctx.command, 'commands', {})
    if not lookup and isinstance(ctx.command, click.MultiCommand):
        lookup = _get_lazyload_commands(ctx.command)

    if commands is None:
        return lookup.values()

    names = [name.strip() for name in commands.split(',')]
    return [lookup[name] for name in names if name in lookup]
    

def _format_options(ctx):
    """Format all `click.Option` for a `click.Command`."""
    # the hidden attribute is part of click 7.x only hence use of getattr
    params = [
        index_param(ctx, x) for x in ctx.command.params
        if isinstance(x, ext.click.Option) and not getattr(x, 'hidden', False)
    ]
    seps = index_seps(params)
    opts = sorted(params + seps, key=lambda x: (x[0], x[1]))
    for param in opts:
        if type(param[0]) == float:
            yield ''
            yield '.. rubric:: {}'.format(param[1])
            yield ''
        else:
            for line in ext._format_option(param[-1]):
                if re.match(r'^\.\. option::.*<.+>', line):
                    try:
                        # click_callbacks.pretty_callback_names
                        name = pcn[param[2].callback.__name__]
                    except (AttributeError, KeyError):
                        try:
                            name = param[2].type.name.upper()
                        except AttributeError:
                            name = str(param[2].type).upper()
                    if name == '':
                        name = 'TEXT'
                    line = re.sub(r'<.+>', f'<{name}>', line)
                yield line
            yield ''


def _format_command(ctx, show_nested, commands=None):
    """Format the output of `click.Command`."""
    # description

    for line in ext._format_usage(ctx):
        yield line

    for line in ext._format_description(ctx):
        yield line

    yield '.. program:: {}'.format(ctx.command_path)
    

    # arguments

    lines = list(ext._format_arguments(ctx))
    if lines:
        yield '.. rubric:: Arguments'
        yield ''

    for line in lines:
        yield line

    # options

    lines = list(_format_options(ctx))
    if lines:
        # we use rubric to provide some separation without exploding the table
        # of contents
        yield '.. rubric:: Options'
        yield ''

    for line in lines:
        if ':default:' in line:
            line = line.replace("*", "\\*")
        yield line

    # environment variables

    lines = list(ext._format_envvars(ctx))
    if lines:
        yield '.. rubric:: Environment variables'
        yield ''

    for line in lines:
        yield line

    # sub commands
    commands = ext._filter_commands(ctx, commands)

    if commands:
        yield '.. rubric:: Commands'
        yield ''

    for command in commands:
        for line in ext._format_subcommand(command):
            yield line
        yield ''


ext._filter_commands = _filter_commands
ext._format_options = _format_options
ext._format_command = _format_command


class ClaspClickDirective(ext.ClickDirective):
    pass


def setup(app):
    app.add_directive('click', ClaspClickDirective)
