#!/usr/bin/env python
from __future__ import print_function

from clasp import click
import clasp.click_ext as clk
import clasp.script_tools as mgr


def add(a,b,c=1):
    d = (a+b)*c
    print(d)
    return d


@click.command()
@click.argument('arg1', type=int)
@click.option('--opts','-opts', is_flag=True,
              help="check parsed options")
@click.option('--order/--no-order', default=True,
              help="order output")
@click.option('--debug/--no-debug', default=True,
              help="show traceback on exceptions")
@click.pass_context
def main(ctx, arg1, **kwargs):
    """
    callbacks:

    File input
    ~~~~~~~~~~

    file inputs can be given with wildcard expansion (in quotes so that the callback handles)
    using glob plus the following:

        * [abc] (one of a, b, or c) 
        * [!abc] (none of a, b or c)
        * '-' (hyphen) collect the stdin into a temporary file (clasp_tmp*)
        * ~ expands user

    The file input callbacks are:

        * parse_file_list: returns list of files (raise error if file not found)
        * is_file: check if a single path exists (prompts for user input if file not found)
        * are_files: recursively calls parse_file_list and prompts on error
        * is_file_iter: use when multiple=True
        * are_files_iter: use when mulitple=True
        * are_files_or_str: tries to parse as files, then tries split_float, then split_int, then returns string
        * are_files_or_str_iter: use when mulitple=True

    String parsing
    ~~~~~~~~~~~~~~

        * split_str: split with shlex.split
        * split_str_iter: use when multiple=True
        * color_inp: return alphastring, split on whitespace, convert floats and parse tuples on ,

    Number parsing
    ~~~~~~~~~~~~~~

        * tup_int: parses integer tuples from comma/space seperated string
        * tup_float: parses float tuples from comma/space seperated string
        * split_float: splits list of floats and extends ranges based on : notation
        * split_int: splits list of ints and extends ranges based on : notation
    """
    if kwargs['opts']:
        kwargs['opts'] = False
        clk.echo_args(arg1, **kwargs)
    else:
        try:
            a = mgr.pool_call(add, [(i,i+1) for i in range(arg1)], dict(c=10), order=kwargs['order'])
            print(a)
        except click.Abort:
            raise
        except Exception as ex:
            clk.print_except(ex, kwargs['debug'])
    try:
        clk.tmp_clean(ctx)
    except Exception:
        pass

if __name__ == '__main__':
    main()
