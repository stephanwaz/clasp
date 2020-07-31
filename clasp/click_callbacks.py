# Copyright (c) 2018 Stephen Wasilewski
# =======================================================================
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# =======================================================================

"""callbacks for special parsing of command line inputs

**Callbacks By type**

**File input**

file inputs can be given with wildcard expansion (in quotes so that the
callback handles) using glob plus the following:

    * [abc] (one of a, b, or c) 
    * [!abc] (none of a, b or c)
    * '-' (hyphen) collect the stdin into a temporary file (clasp_tmp*)
    * ~ expands user

**callback functions**

    * is_file: check if a single path exists (prompts for user input if file
      not found)
    * are_files: recursively calls parse_file_list and prompts on error
    * is_file_iter: use when multiple=True
    * are_files_iter: use when mulitple=True
    * are_files_or_str: tries to parse as files, then tries split_float, then
      split_int, then returns string
    * are_files_or_str_iter: use when mulitple=True

**String parsing**

    * split_str: split with shlex.split
    * split_str_iter: use when multiple=True
    * color_inp: return alpha string, split on whitespace,
      convert floats and parse tuples on ,
    * char0: return first character

**Number parsing**

    * tup_int: parses integer tuples from comma/space separated string
    * tup_float: parses float tuples from comma/space separated string
    * split_float: splits list of floats and extends ranges based on : notation
    * split_int: splits list of ints and extends ranges based on : notation
"""

import os
import re
import sys
import shlex
import tempfile
from glob import glob
import click
from clasp.script_tools import sglob
import clasp.script_tools as cst

pretty_callback_names = {
'is_file' : 'FILE',
'are_files': 'FILES',
'is_file_iter': 'FILES',
'are_files_iter': 'FILES',
'are_files_or_str': 'FILES,INTS,FLOATS,TEXTS',
'are_files_or_str_iter': 'FILES,INTS,FLOATS,TEXTS',
'split_str': 'TEXTS',
'split_str_iter': 'TEXTS',
'color_inp': 'COLORS',
'tup_int': 'INTS INTS,INTS',
'tup_float': 'FLOATS, FLOATS,FLOATS',
'split_float': 'FLOATS',
'split_int': 'INTS',
'are_valid_paths': 'PATHS',
'int_tups': 'INT,INT INT,INT',
'tup_list': 'TEXT',
}

def callback_error(s, param, example):
    """standard error message for exceptions raised during argument parsing

    used by custom callback functions raises ClickException

    Parameters
    ----------
    s: value
    param: click.core.Option
    example: example of valid entry format
    """
    message = "\ncan't parse: {}\nexpected input "\
              "format: '{}'".format(s, example)
    raise click.BadParameter(message)


def is_file(ctx, param, s):
    """checks input file string with recursive prompt

    use os.environ['CLASP_PIPE'] = '1' in parent script
    or set CLASP_PIPE=1
    to disable prompt and avoid hanging process
    """
    if s == '-':
        return tmp_stdin(ctx)
    if s in [None, 'None', 'none']:
        return None
    command = ctx.info_name
    name = param.name
    try:
        if os.path.exists(s):
            return s
        else:
            raise ValueError(s)
    except ValueError as e:
        try:
            nopipe = os.environ['CLASP_PIPE'] != '1'
        except KeyError:
            nopipe = True
        click.echo("{} not an existing file".format(e), err=True)
        if nopipe and not ctx.resilient_parsing:
            s2 = click.prompt("{} for {}".format(name, command))
            return is_file(ctx, param, s2)
        else:
            raise click.Abort()


def char0(ctx, param, s):
    return s[0].lower()


def are_files(ctx, param, s, prompt=True):
    """checks input file list string with recursive prompt

    use os.environ['CLASP_PIPE'] = '1' in parent script
    or set CLASP_PIPE=1
    to disable prompt and avoid hanging process
    """
    if s in [None, 'None', 'none']:
        return None
    command = ctx.info_name
    name = param.name
    try:
        return parse_file_list(ctx, s)
    except ValueError as e:
        if prompt and not ctx.resilient_parsing:
            try:
                nopipe = os.environ['CLASP_PIPE'] != '1'
            except KeyError:
                nopipe = True
            click.echo("{} not an existing file".format(e), err=True)
            if nopipe and ctx.resilient_parsing:
                s2 = click.prompt("{} for {}".format(name, command))
            else:
                raise click.Abort()
        else:
            raise ValueError(e)
        return are_files(ctx, param, s2)


def are_valid_paths(ctx, param, s):
    """checks input file list
    """
    if s in [None, 'None', 'none']:
        return None
    try:
        return parse_file_list(ctx, s, valid=True)
    except ValueError as e:
        raise ValueError(e)




def is_files_iter(ctx, param, s):
    """calls are_files for each item in iterable s use with multiple=True"""
    files = []
    for s2 in s:
        files.append(is_file(ctx, param, s2))
    return files


def are_files_iter(ctx, param, s, prompt=True):
    """calls are_files for each item in iterable s use with multiple=True"""
    files = []
    for s2 in s:
        files.append(are_files(ctx, param, s2, prompt))
    return files


def are_files_or_str(ctx, param, s):
    """tries are_files for each item then split_str"""
    try:
        return are_files(ctx, param, s, False)
    except ValueError:
        pass
    try:
        return [str(i) for i in split_int(ctx, param, s)]
    except Exception:
        pass
    try:
        return [str(i) for i in split_float(ctx, param, s)]
    except Exception:
        pass
    return split_str(ctx, param, s)


def are_files_or_str_iter(ctx, param, s):
    """tries are_files then split_str use with multiple=True"""
    files = []
    for s2 in s:
        files.append(are_files_or_str(ctx, param, s2))
    return files


#: string parsing callbacks


def split_str(ctx, param, s):
    """splits space seperated string"""
    if s in [None, 'None', 'none']:
        return None
    elif len(s) == 0:
        return ''
    elif s[0] == '@':
        if os.path.exists(s[1:]):
            f = open(s[1:], 'r')
            return shlex.split(f.read().strip())
        else:
            return shlex.split(s)
    else:
        return shlex.split(s)


def split_str_iter(ctx, param, s):
    """calls are_files for each item in iterable s use with multiple=True"""
    args = []
    for s2 in s:
        args.append(split_str(ctx, param, s2))
    return args


def color_inp(ctx, param, s):
    """parses color tuple from comma/space seperated string or cmap name"""
    if re.match(r"^([\d\.]+[, \t]+)+[\d\.]+$", s):
        so = []
        for x in s.split():
            if "," in x:
                so.append(tuple(float(i) for i in x.split(",")))
            else:
                so.append(float(x))
        return so
    else:
        return s


def tup_int(ctx, param, s, recurs=False):
    """parses integer or len 2 tuples from comma/space separated string
    with range : notation"""
    if s in [None, 'None', 'none']:
        so = None
    else:
        if param.multiple and not recurs:
            so = [tup_int(ctx, param, s2, recurs=True) for s2 in s]
            if None in so:
                return None
            else:
                return [tup_int(ctx, param, s2, recurs=True) for s2 in s]
        try:
            so = []
            for x in s.split():
                if "," in x:
                    for fis in cst.int_rng(x.split(",")[0]):
                        for col in cst.int_rng(x.split(",")[1]):
                            so.append((fis, col))
                else:
                    so.extend(cst.int_rng(x))
        except Exception as ex:
            callback_error(s, param, '0 0,1 0,3')
    return so


def int_tups(ctx, param, s):
    """parses integer tuples from comma/space separated string"""
    if s in [None, 'None', 'none']:
        so = None
    else:
        try:
            so = []
            for x in s.split():
                so.append(tuple(int(i) for i in x.split(",")))
        except Exception:
            callback_error(s, param, '0,1 0,3.6')
    return so


def tup_float(ctx, param, s):
    """parses float tuples from comma/space separated string"""
    if s in [None, 'None', 'none']:
        so = None
    else:
        try:
            so = []
            for x in s.split():
                if "," in x:
                    so.append(tuple(float(i) for i in x.split(",")))
                else:
                    so.append(float(x))
        except Exception:
            callback_error(s, param, '0 0,1 0,3.6')
    return so


def tup_list(ctx, param, s):
    """convert tuple to list"""
    if s is not None:
        return list(s)
    else:
        return None


def split_float(ctx, param, s):
    """splits list of floats and extends ranges based on : notation"""
    if s in [None, 'None', 'none']:
        result = None
    else:
        try:
            result = []
            for part in s.split():
                if ':' in part:
                    a = (float(i) for i in part.split(':'))
                    result.extend(cst.arange(*a))
                else:
                    a = float(part)
                    result.append(a)
            result = [round(i, 6) for i in result]
        except Exception:
            callback_error(s, param, '0 30.5 40')
    return result


def split_int(ctx, param, s):
    """splits list of ints and extends ranges based on : notation"""
    if s in [None, 'None', 'none']:
        result = None
    else:
        try:
            result = []
            for part in s.split():
                if ':' in part:
                    a = (int(i) for i in part.split(':'))
                    result.extend(cst.arange(*a))
                else:
                    a = int(part)
                    result.append(a)
            if len(result) == 1:
                result = [int(result[0])]
        except Exception:
            callback_error(s, param, '0 30 40')
    return result


def data_stream(ctx, param, s):
    if s in [None, 'None', 'none']:
        result = None
    elif s == '-':
        result = sys.stdin.buffer
    else:
        try:
            result = open(s, 'rb')
        except Exception:
            callback_error(s, param, 'should be an existing file')
    return result


def tmp_stdin(ctx):
    '''read stdin into temporary file

    use ctx.resilient_parsing=True to pass "-" directly
    '''
    if not ctx.resilient_parsing:
        f, path = tempfile.mkstemp(dir="./", prefix='clasp_tmp')
        f = open(path, 'wb')
        f.write(sys.stdin.buffer.read())
        f.close()
        if ctx.obj is None:
            ctx.obj = dict(temps=[path])
        else:
            ctx.obj['temps'].append(path)
        return path
    else:
        return "-"


def parse_file_list(ctx, s, valid=False):
    """parses list of files using glob expansion"""
    files = []
    for i in shlex.split(s):
        if "~" in i:
            i = os.path.expanduser(i)
        if i == '-':
            files.append(tmp_stdin(ctx))
        elif i[0] == '@':
            if os.path.exists(i[1:]):
                f = open(i[1:], 'r')
                fi = [j.strip() for j in f.readlines()]
                for l in fi:
                    files += parse_file_list(ctx, l)
            else:
                raise ValueError(i[1:])
        elif len(sglob(i)) > 0:
            for j in sglob(i):
                if os.path.exists(j):
                    files.append(j)
                else:
                    raise ValueError(j)
        else:
            if os.path.exists(i):
                files.append(i)
            elif valid and os.path.isdir(os.path.dirname(i)):
                files.append(i)
            else:
                raise ValueError(i)
    return files
