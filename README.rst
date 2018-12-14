About
-----
Clasp (command line and subprocess) extends click (https://palletsprojects.com/p/click/)
and provides a library of functions that aid in the development of command line 
tools that require frequent calls to system exectubles.  A particular structure
program [options] command arguments [options] has been implemented for click that
sets up an easy way to read and write config files and group commands under common
programs to allow for organized development of suites of command line tools.

https://clasp.readthedocs.io/


Installation
------------

::

    pip install clasp


Usage
-----

a command line program has the following structure::

    """template file."""
    
    from __future__ import print_function
    
    import clasp.click as click
    import clasp.click_ext as clk

    
    
    @click.group()
    @clk.shared_decs(clk.main_decs)
    def main(ctx, config, outconfig, configalias, inputalias):
        """template file for script development."""
        clk.get_config(ctx, config, outconfig, configalias, inputalias)
    
    
    @main.command('XXX')
    @click.argument('arg1')
    @click.option('--opts','-opts', is_flag=True,
                  help="check parsed options")
    @click.option('--debug', is_flag=True,
                  help="show traceback on exceptions")
    @click.pass_context
    def XXX(ctx, arg1, **kwargs):
        """
        docstring with full help text for command
        """
        if kwargs['opts']:
            kwargs['opts'] = False
            clk.echo_args(arg1,**kwargs)
        else:
            try:
                ##########
                #code body
                ##########
            except click.Abort:
                raise
            except Exception as ex:
                clk.print_except(ex, kwargs['debug'])
        return 'XXX', kwargs, ctx
    
    
    @main.resultcallback()
    @click.pass_context
    def printconfig(ctx, opts, **kwargs):
        """callback to save config file"""
        try:
            clk.tmp_clean(opts[2])
        except Exception:
            pass
        if kwargs['outconfig']:
            clk.print_config(ctx, opts, kwargs['outconfig'], kwargs['config'],
                             kwargs['configalias'])

to make an entry point in setup::

    entry_points={"console_scripts":'program=package.program:main'}


and then to execute::

    program XXX arg1 [options]

to enable autocomple for options::

    _PROGRAM_COMPLETE=source program > bash_complete.sh
    # put this in .bash_profile (with path)
    source bash_complete.sh


scripting
~~~~~~~~~

see script_tools documentation for helpful functions matching parsed args
to functions, calling subprocesses, and parallel processing using ipyparallel
locally and via ssh.

Callbacks
---------

in addition to the powerful option parsing provided by click a number of 
callbacks are part of clasp which help with commonly used argument parsing

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

Documentation
-------------

Click and sphinx_click make help and documentation super easy, but there are
a few conflicts in formatting docstrings both for --help and for sphinx.
clasp.sphinx_click_ext attempts to resolve these conflicts and does some sorting of options
and help display based on the script template shown above.  To use with sphinx
add 'clasp.sphinx_click_ext' to extensions in your conf.py


Source Code
-----------

* clasp: https://bitbucket.org/stephenwasilewski/clasp

Licence
-------

| Copyright (c) 2018 Stephen Wasilewski
| This Source Code Form is subject to the terms of the Mozilla Public
| License, v. 2.0. If a copy of the MPL was not distributed with this
| file, You can obtain one at http://mozilla.org/MPL/2.0/.

