# -*- coding: utf-8 -*-

# Copyright (c) 2018 Stephen Wasilewski
# =======================================================================
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# =======================================================================


from clasp import click
import clasp.click_ext as clk


@click.command()
@click.option('--subcommands/--no-subcommands', default=False)
@clk.shared_decs(clk.command_decs('0.1'))
def main(ctx, subcommands=False, **kwargs):
    """print out script templates"""
    if kwargs['opts']:
        kwargs['opts'] = False
        clk.echo_args(arg1, **kwargs)
    else:
        try:
            if subcommands:
                print(clk.script_template2)
            else:
                print(clk.script_template)
        except click.Abort:
            raise
        except Exception as ex:
            clk.print_except(ex, kwargs['debug'])
    try:
        clk.tmp_clean(ctx)
    except Exception:
        pass