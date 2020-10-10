# Copyright (c) 2018 Stephen Wasilewski
# =======================================================================
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# =======================================================================

"""extension and interface for parsing with click and configparse

imports callbacks into namespace for convenience
"""
import types
from builtins import str
import configparser
import collections
import traceback
import functools
import sys
import shutil

import sphinx.builders.text
import sphinx.writers.text
from docutils.parsers.rst import Parser as RSTParser
import docutils.utils
from docutils.frontend import OptionParser

import clasp.click_callbacks
from clasp.click_callbacks import *

callback_help = clasp.click_callbacks.__doc__


def add_callback_info(func):
    if func.__doc__ is None:
        func.__doc__ = callback_help
    else:
        func.__doc__ += "\n\n" + callback_help
    return func


def pretty_name(r):
    def wrapper(f):
        f.prettyname = r
        return f
    return wrapper

#: Edited from click completion script to avoid running out of turn (faster)
COMPLETION_SCRIPT_BASH = '''
%(complete_func)s() {
    local cw="${COMP_WORDS[*]}"
    if [[ $cw != *">"* ]]; then
    if [[ ${COMP_WORDS[$COMP_CWORD]} != -* ]] && [[ '''\
'''${COMP_WORDS[$COMP_CWORD-1]} == -* ]]; then
        :
    else
        local IFS=$'\n'
        COMPREPLY=( $( env COMP_WORDS="${COMP_WORDS[*]}" \\
                    COMP_CWORD=$COMP_CWORD \\
                    %(autocomplete_var)s=complete $1 ) )
    fi
    fi
    return 0
}

%(complete_func)setup() {
    local COMPLETION_OPTIONS=""
    local BASH_VERSION_ARR=(${BASH_VERSION//./ })
    # Only BASH version 4.4 and later have the nosort option.
    if [ ${BASH_VERSION_ARR[0]} -gt 4 ] || ([ ${BASH_VERSION_ARR[0]} -eq 4'''\
''' ] && [ ${BASH_VERSION_ARR[1]} -ge 4 ]); then
        COMPLETION_OPTIONS="-o nosort"
    fi

    complete $COMPLETION_OPTIONS -o default -F %(complete_func)s '''\
'''%(script_names)s
}

%(complete_func)setup
'''

#: basic script template for one offs
script_template = f'''#!/usr/bin/env python
from clasp import click
import clasp.click_ext as clk
import clasp.script_tools as cst

@click.command()
@click.argument('arg1')
@clk.shared_decs(clk.command_decs('0.1'))
def main(ctx, arg1, **kwargs):
    """{callback_help}"""
    if kwargs['opts']:
        kwargs['opts'] = False
        clk.echo_args(arg1, **kwargs)
    else:
        try:
            pass
        except click.Abort:
            raise
        except Exception as ex:
            clk.print_except(ex, kwargs['debug'])
    try:
        clk.tmp_clean(ctx)
    except Exception:
        pass

if __name__ == '__main__':
    main()'''


#: basic script template for command subcommand structure (using config files)
script_template2 = f'''#!/usr/bin/env python
from clasp import click
import clasp.click_ext as clk
import clasp.script_tools as cst

@click.group()
@clk.shared_decs(clk.main_decs('0.1'))
def main(ctx, config, outconfig, configalias, inputalias):
    """docstring"""
    clk.get_config(ctx, config, outconfig, configalias, inputalias)


@main.command()
@click.argument('arg1')
@clk.shared_decs(clk.command_decs('0.1'))
def XXX(ctx, arg1, **kwargs):
    """{clasp.click_callbacks.__doc__}"""
    if kwargs['opts']:
        kwargs['opts'] = False
        clk.echo_args(arg1, **kwargs)
    else:
        try:
            pass
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


if __name__ == '__main__':
    main()'''


def click_ext(click):
    """customize click help messages and bash complete"""
    orig_init = click.core.Option.__init__

    parser = RSTParser()
    cmpt = (RSTParser,)
    settings = OptionParser(components=cmpt).get_default_values()
    settings.tab_size = 4
    document = docutils.utils.new_document('<rst-doc>', settings)

    app = types.SimpleNamespace(
            srcdir=None,
            confdir=None,
            outdir=None,
            doctreedir="/",
            events=None,
            warn=None,
            config=types.SimpleNamespace(
                    text_newlines="native",
                    text_sectionchars="=",
                    text_add_secnumbers=False,
                    text_secnumber_suffix=".",
                    ),
            tags=set(),
            registry=types.SimpleNamespace(
                    create_translator=lambda s, something,
                    new_builder: sphinx.writers.text.TextTranslator(
                            document, new_builder
                            )
                    ),
            )
    builder = sphinx.builders.text.TextBuilder(app)

    def new_init(self, *args, **kwargs):
        orig_init(self, *args, **kwargs)
        if 'show_default' not in kwargs:
            self.show_default = True

    def format_help_text(self, ctx, formatter):
        """modified help text formatter for compatibility with sphinx-click."""
        if self.help:
            formatter.write_paragraph()
            rst = _process_as_rst(self.help)
            formatter.indent()
            for line in rst.splitlines():
                formatter.write_text(line)
            formatter.dedent()
            formatter.write_paragraph()

    def _process_as_rst(text):
        parser.parse(text.replace("*", "\\*"), document)
        translator = sphinx.writers.text.TextTranslator(document,
                                                        builder)
        document.walkabout(translator)
        rst = translator.body.replace("\n\n", "\n")
        document.clear()
        return rst

    def format_options(self, ctx, formatter):
        """Writes all the options into the formatter if they exist."""
        opts = []
        twidth = max(shutil.get_terminal_size((80, 20)).columns, 80)
        sphinx.writers.text.MAXWIDTH = twidth - 10
        for param in self.get_params(ctx):
            rv = param.get_help_record(ctx)
            if rv is not None:
                a, name, _ = index_param(ctx, param)
                try:
                    try:
                        callback = param.callback.prettyname
                    except AttributeError:
                        callback = pretty_callback_names[
                            param.callback.__name__]
                except (AttributeError, KeyError):
                    pass
                else:
                    rv0 = re.split(r'(\W)', rv[0])
                    rv0[-1] = callback.upper()
                    rv = (''.join(rv0),) + rv[1:]
                opts.append((a, name, rv))
        seps = [(i[0], (f"\n{i[1]}" , '')) for i in index_seps(opts)]
        opts = [i[-1] for i in sorted(opts + seps, key=lambda x: (x[0], x[1]))]
        if opts:
            with formatter.section('Options'):
                formatter.width = sphinx.writers.text.MAXWIDTH
                indent = ' '*formatter.current_indent
                for opt in opts:
                    formatter.write(f"{indent}{opt[0]}\n")
                    rst = _process_as_rst(opt[1])
                    formatter.indent()
                    formatter.indent()
                    for line in rst.splitlines():
                        formatter.write_text(line)
                    formatter.dedent()
                    formatter.dedent()
                    formatter.write("\n")
    click.core.Option.__init__ = new_init
    click.core.Command.format_help_text = format_help_text
    click.core.Command.format_options = format_options

    import click._bashcomplete as _bc

    def get_completion_script(prog_name, complete_var, shell):
        cf_name = _bc._invalid_ident_char_re.sub('',
                                                 prog_name.replace('-', '_'))
        if shell == 'zsh':
            script = _bc.COMPLETION_SCRIPT_ZSH
        else:
            script = COMPLETION_SCRIPT_BASH
        return (script % {
            'complete_func': '_%s_completion' % cf_name,
            'script_names': prog_name,
            'autocomplete_var': complete_var,
        }).strip() + ';'

    def bashcomplete(cli, prog_name, complete_var, complete_instr):
        if complete_instr.startswith('source'):
            shell = 'zsh' if complete_instr == 'source_zsh' else 'bash'
            click.echo(get_completion_script(prog_name, complete_var, shell))
            return True
        elif complete_instr == 'complete' or complete_instr == 'complete_zsh':
            return _bc.do_complete(cli, prog_name,
                                   complete_instr == 'complete_zsh')
        return False

    def _bashcomplete(cmd, prog_name, complete_var=None):
        """Internal handler for the bash completion support."""
        if complete_var is None:
            complete_var = '_%s_COMPLETE' % (prog_name.replace('-', '_'))
            complete_var = complete_var.upper()
        complete_instr = os.environ.get(complete_var)
        if not complete_instr:
            return
        if bashcomplete(cmd, prog_name, complete_var, complete_instr):
            click.core.fast_exit(1)

    click.core._bashcomplete = _bashcomplete
    click._bashcomplete.COMPLETION_SCRIPT_BASH = COMPLETION_SCRIPT_BASH
    return click


def printconfigs(ctx, param, s):
    if s:
        for k, v in ctx.command.commands.items():
            opts = {}
            for p in v.params:
                if p.human_readable_name not in ['opts', 'debug', 'version']:
                    opts[p.human_readable_name] = p.get_default(ctx)
            print_config(ctx, (k, opts), sys.stdout, None, None, True)
        sys.exit(0)


def wrap_command():
    """decorator to execute command within standardized error handling"""
    def wrapped_call(func):
        @functools.wraps(func)
        def handle_call(ctx, *args, **kwargs):
            cname = func.__name__
            try:
                chain = ctx.parent.command.__dict__['chain']
            except KeyError:
                chain = False
            if chain:
                kwargs['opts'] = kwargs['opts'] or ctx.parent.params['opts']
                kwargs['debug'] = kwargs['debug'] or ctx.parent.params['debug']
            if kwargs['opts']:
                kwargs['opts'] = False
                click.echo(f'\n{cname} options:\n', err=True)
                echo_args(**kwargs)
            else:
                try:
                    func(ctx, *args, **kwargs)
                except click.Abort:
                    raise
                except click.exceptions.Exit as ex:
                    if ex.exit_code != 0:
                        print_except(ex, kwargs['debug'])
                        raise click.Abort
                except Exception as ex:
                    print_except(ex, kwargs['debug'])
                    raise click.Abort
            return cname, kwargs, ctx
        return handle_call
    return wrapped_call


def main_decs(v, writeconfig=True):
    """set of shared decorators for all main command groups

    Parameters
    ----------
    v: str

    Returns
    -------
    md: list
        decorator list for main command to manage config file usage
    """
    md = [
          click.option('--config', '-c', type=click.Path(exists=True),
                       help="path of config file to load"),
          click.option('--configalias', '-ca',
                       help="store config in alias section. use to store "
                       "multiple settings for same command"),
          click.option('--inputalias/--no-inputalias', default=True,
                       help="if true uses -ca for loading settings"),
          click.version_option(version=v),
          click.pass_context
    ]
    if writeconfig:
        md.append(click.option('--outconfig', '-oc',
                  type=click.Path(file_okay=True),
                  help="path of config file to write/update"))
    return md


def command_decs(v, wrap=False):
    """set of shared decorators for all sub commands

    Parameters
    ----------
    v: str

    Returns
    -------
    cd: list
        decorator list for sub command
    """
    cd = [
          click.option('--opts', '-opts', is_flag=True,
                       help="check parsed options"),
          click.option('--debug', is_flag=True,
                       help="show traceback on exceptions"),
          click.version_option(version=v),
          click.pass_context
    ]
    if wrap:
        cd.append(wrap_command())
    return cd


def shared_decs(decs):
    """decorator to add decs to function

    Parameters
    ----------
    decs: list of decorator functions to add to function

    Returns
    -------
    decorator: func
        a function that decorates function with list of decorators
    """
    def decorate(f):
        for dec in reversed(decs):
            f = dec(f)
        return f
    return decorate


def tmp_clean(ctx):
    """remove files placed int temps context object
    (called at end of scripts)"""
    for i in ctx.obj['temps']:
        try:
            os.remove(i)
        except Exception:
            pass


def invoke_dependency(ctx, cmd, *args):
    kws = ctx.parent.command.commands[cmd.name].context_settings['default_map']
    for p in ctx.parent.command.commands[cmd.name].params:
        try:
            kws[p.name] = p.process_value(ctx, kws[p.name])
        except KeyError:
            kws[p.name] = p.get_default(ctx)
    kws.update(reload=True, overwrite=False)
    cmd.callback(*args, **kws)


def read_section(Config, dict1, section, options):
    for option in options:
        try:
            opt = Config.get(section, option)
            if re.match(r'.+_\d+', option):
                opto = option.rsplit("_", 1)[0]
                try:
                    dict1[opto].append(opt)
                except Exception:
                    dict1[opto] = [opt]
            elif opt == "None":
                dict1[option] = None
            else:
                dict1[option] = opt
        except Exception as ex:
            click.echo("exception on {}! {}".format(option, ex), err=True)
            dict1[option] = None
    return dict1


def ConfigSectionMap(Config, section):
    """maps ConfigParser section to dict"""
    dict1 = {}
    try:
        options = Config.options(section)
    except Exception:
        options = []
    try:
        cvars = Config.options('globals')
    except Exception:
        cvars = []
    read_section(Config, dict1, 'globals', cvars)
    read_section(Config, dict1, section, options)
    return dict1


def format_depth(v):
    '''recursively format lists and tuples'''
    if type(v) == list:
        wv = " ".join([format_depth(i) for i in v])
    elif type(v) == tuple:
        wv = ",".join([format_depth(i) for i in v])
    else:
        wv = str(v)
    return wv


def formatarg(Parser, command, name, v):
    """formats option to write to config file"""
    try:
        v = v.name
    except AttributeError:
        pass
    wv = format_depth(v)
    try:
        Parser.set(command, name, wv)
    except configparser.NoSectionError:
        Parser.add_section(command)
        Parser.set(command, name, wv)
    return Parser


def setargs(Config, ini, section):
    """gets command section from .ini file"""
    try:
        Config.read(ini)
        return ConfigSectionMap(Config, section)
    except Exception:
        return {}


def index_param(ctx, param):
    '''tag param with index to sort by option type for help display'''
    if param.human_readable_name == 'version':
        a = 11
    elif param.human_readable_name == 'help':
        a = 10
    elif param.human_readable_name == 'debug':
        a = 9
    elif param.human_readable_name == 'opts':
        a = 8
    elif param.required:
        a = 1
    elif param.prompt:
        a = 2
    elif param.is_flag:
        if param.get_default(ctx):
            a = 4
        else:
            a = 5
    else:
        a = 3
    return a, param.human_readable_name, param


def index_seps(params):
    '''insert section headers into param list for help display'''
    seps = []
    sections = set([i[0] for i in params])
    if 1 in sections:
        seps.append((0.5, "REQUIRED:"))
    if 2 in sections:
        seps.append((1.5, "HAS PROMPT:"))
    if 3 in sections:
        seps.append((2.5, "VALUE OPTIONS:"))
    if 4 in sections:
        seps.append((3.5, "FLAGS (DEFAULT TRUE):"))
    if 5 in sections:
        seps.append((4.5, "FLAGS (DEFAULT FALSE):"))
    if [i for i in [8, 9, 10, 11] if i in sections]:
        seps.append((7.5, 'HELP:'))
    return seps


def get_config(ctx, config, outconfig, configalias, inputalias, template=None):
    """load config file into click options"""
    Parser = configparser.ConfigParser()
    com = ctx.info_name.split("_")[-1]
    subc = ctx.invoked_subcommand
    if configalias and template is not None:
        gargs = setargs(Parser, template, "{}_{}".format(com, configalias))
    elif template is not None:
        gargs = setargs(Parser, template, "{}_{}".format(com, subc))
    else:
        gargs = {}
    if configalias is not None and inputalias:
        alias = "{}_{}".format(com, configalias)
        args = setargs(Parser, config, alias)
    else:
        alias = "{}_{}".format(com, subc)
        args = setargs(Parser, config, alias)
    gargs.update(args)
    if not gargs and outconfig is None and (config is not None or configalias):
        click.echo("WARNING: {} not found in local config file: {} or "
                   "global config file: {}"
                   "".format(alias, config, template), err=True)
        raise click.Abort()
    ctx.command.commands[subc].context_settings['default_map'] = gargs


def get_config_chained(ctx, config, outconfig, configalias, inputalias):
    """load config file into click options"""
    Parser = configparser.ConfigParser()
    com = ctx.info_name.split("_")[-1]
    bad = outconfig is None and (config is not None or configalias)
    for subc in ctx.command.commands:
        if configalias is not None and inputalias:
            alias = "{}_{}".format(configalias, subc)
            gargs = setargs(Parser, config, alias)
        else:
            alias = "{}_{}".format(com, subc)
            gargs = setargs(Parser, config, alias)
        if not gargs and bad:
            click.echo("WARNING: {} not found in local config file: {}"
                       "".format(alias, config), err=True)
            raise click.Abort()
        else:
            bad = False
        ctx.command.commands[subc].context_settings['default_map'] = gargs
    if bad:
        raise click.Abort()

def match_multiple(ctx, subc):
    """identify params with multiple=True for config file parsing"""
    ismultiple = {}
    for opt in ctx.command.commands[subc].params:
        ismultiple[opt.human_readable_name] = opt.multiple
    return ismultiple


def config_comments(*args):
    """read in comments from config files"""
    comments = ['# Usage:']
    for arg in args:
        try:
            f = open(arg, 'r')
        except Exception:
            pass
        else:
            cm = [i.strip() for i in f.readlines()
                  if re.match(r'^#', i.strip())]
            f.close()
            for c in cm:
                if c not in comments:
                    comments.append(c)
    return("\n".join(comments) + "\n\n")


def add_opt_comment(comments, opts):
    """add comment lines for opts unless present"""
    comments = comments.strip()
    for opt in opts:
        if not re.search(r'#\s*\[{}\]'.format(opt), comments):
            comments += "{: <30}#".format('\n# [{}]'.format(opt))
    return comments + "\n\n"


def print_config(ctx, opts, outconfig, config, configalias, chain=False):
    """write config file from click options"""
    ismultiple = match_multiple(ctx, opts[0])
    com = ctx.info_name.split("_")[-1]
    if configalias is not None:
        if chain:
            opt = "{}_{}".format(configalias, opts[0])
        else:
            opt = "{}_{}".format(com, configalias)
    else:
        opt = "{}_{}".format(com, opts[0])
    Parser = configparser.ConfigParser()
    try:
        Parser.read(config)
    except Exception:
        pass
    try:
        Parser.read(outconfig)
    except Exception:
        pass
    comments = config_comments(config, outconfig)
    for i, v in list(opts[1].items()):
        try:
            if ismultiple[i]:
                for j, k in enumerate(v):
                    subo = "{}_{:03d}".format(i, j)
                    Parser = formatarg(Parser, opt, subo, k)
            else:
                Parser = formatarg(Parser, opt, i, v)
        except KeyError:
            pass
    comments = add_opt_comment(comments, Parser.sections())
    for s in Parser._sections:
        srt = sorted(list(Parser._sections[s].items()), key=lambda t: t[0])
        Parser._sections[s] = collections.OrderedDict(srt)
    if hasattr(outconfig, 'write'):
        Parser.write(outconfig)
    else:
        f = open(outconfig, 'w')
        f.write(comments)
        Parser.write(f)
        f.close()


def print_except(ex, debug=False):
    """general human readable exception message"""
    if debug:
        traceback.print_exc()
    click.echo("\n**************\n**************", err=True)
    click.echo("Execution failed:", err=True)
    click.echo("{}: {}".format(type(ex).__name__, ex), err=True)
    click.echo("**************\n**************\n", err=True)


def formatarg_line(v, i=None, idx=None):
    """reduce output of long lists subroutine"""
    if len(v) > 2 and len("{}".format(v)) > 80:
        sv = ""
        k = 0
        while len(sv) <= 30 and k < 10:
            sv += "{}, ".format(v[k])
            k += 1
        a = "list of length: {} [ {}... , {} ]".format(len(v), sv, v[-1])
    else:
        a = "{}".format(v)
    if i is not None:
        if idx is not None:
            i = "{}_{:03d}".format(i, idx)
        a = "{0:.<15}{1}".format(i, a)
    return a


def formatarg_stdout(v, i=None):
    """reduce output of long lists"""
    if type(v) == tuple or type(v) == list:
        if len(v) > 0 and type(v[0]) == list:
            a = []
            for j, v0 in enumerate(v):
                a += [formatarg_line(v0, i=i, idx=j)]
            a = "\n".join(a)
        else:
            a = formatarg_line(v, i)
    else:
        a = "{}".format(v)
        if i is not None:
            a = "{0:.<15}{1}".format(i, a)
    return a


def echo_args(*args, **kwargs):
    """print human readable version of parsed args"""
    print("Positonal Arguments:\n", file=sys.stderr)
    for v in args:
        try:
            v.tell()
        except AttributeError:
            pass
        else:
            try:
                v = v.name
            except Exception:
                v = "file like object"
        print(formatarg_stdout(v), file=sys.stderr)
    print("\nOptions:\n", file=sys.stderr)
    srt = sorted([(i, u) for i, u in list(kwargs.items())])
    for i, v in srt:
        print(formatarg_stdout(v, i), file=sys.stderr)
