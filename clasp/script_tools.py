# Copyright (c) 2018 Stephen Wasilewski
# =======================================================================
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# =======================================================================

"""library of functions helpful for cli script development and parallel
computing particulary w/ subprocess calls."""
import sys
import shlex
import subprocess
import inspect
import tempfile
from glob import glob
import os
import re
import math
from concurrent.futures import ProcessPoolExecutor, as_completed
from clasp import click


encoding = sys.stdin.encoding
if encoding is None:
    encoding = 'UTF-8'


def try_mkdir(s):
    """silently ignore exceptions on mkdir"""
    try:
        os.mkdir(s)
    except Exception:
        pass


def arange(start, stop=None, step=1):
    """like numpy.arange for integers"""
    if stop is None:
        stop = start
        start = 0
    n = int(math.ceil((stop - start)/step))
    return [start + step*i for i in range(n)]


def int_rng(s):
    """expand start:end:inc notation into range"""
    result = []
    for part in s.split():
        if ':' in part:
            a = (int(i) for i in part.split(':'))
            result.extend(arange(*a))
        else:
            a = int(part)
            result.append(a)
    if len(result) == 1:
        result = [int(result[0])]
    return result


def rm_dup(seq):
    """removes duplicates from list while preserving order"""
    mark = set()
    mark_add = mark.add
    return [x for x in seq if not (x in mark or mark_add(x))]


def warn_match(kwargs, sargs):
    for i in sargs:
        if i not in kwargs:
            click.echo('WARNING: {} not set'.format(i), err=True)


def kwarg_match(func, kwargs, debug=False):
    """filters dict for keys used by func"""
    sargs = inspect.getfullargspec(func).args
    argsc = {i: kwargs[i] for i in sargs if i in kwargs}
    if debug:
        warn_match(kwargs, sargs)
    return argsc


def arg_match(func, kwargs, *args):
    """filters dict for positional arguments used by func"""
    sargs = inspect.getfullargspec(func).args[len(args):]
    argsc = list(args) + [kwargs[i] if i in kwargs else None for i in sargs]
    return argsc


def kwarg_arg(func, kwargs, skip=None):
    """returns ordered list of optional arg values"""
    spec = inspect.getfullargspec(func)
    if skip is not None:
        oargs = spec.args[skip:]
    else:
        oargs = spec.args[-len(spec.defaults):]
    largs = []
    for oarg, default in zip(oargs, spec.defaults):
        try:
            largs.append(kwargs[oarg])
        except Exception:
            largs.append(default)
    return largs


def crossref(l1, l2):
    '''return all possible pairs of 2 lists'''
    n = len(l1) * len(l2)
    out = [[] for i in range(n)]
    for i, l in enumerate(l1):
        for j, m in enumerate(l2):
            out[i*len(l2)+j] += [l, m]
    return [flat_list(i) for i in out]


def crossref_all(l, followers=[]):
    '''return all possible combos of list of lists'''
    la = []
    followed = [i[0] for i in followers]
    follows = [i[1] for i in followers]
    leaders = [i for i in range(len(l)) if i not in follows]
    for i in leaders:
        if i == 0:
            if i in followed:
                k = follows[followed.index(i)]
                try:
                    la = [[lb, l[k][j]] for j, lb in enumerate(l[i])]
                except Exception:
                    click.echo('length of follower must match lead', err=True)
                    raise click.Abort()
            else:
                la = l[i]
        else:
            if i in followed:
                lb = crossref(la, list(range(len(l[i]))))
                k = follows[followed.index(i)]
                try:
                    la = [j[:-1] + [l[i][j[-1]], l[k][j[-1]]] for j in lb]
                except IndexError:
                    click.echo('length of follower must match lead', err=True)
                    raise click.Abort()
            else:
                la = crossref(la, l[i])
    return list(zip(*la))


def subpipe(commands):
    '''
    parses special syntax in pipe expressions

    | $(some command) executes to a temporary file whose path is inserted in
    | the command.
    | $((expression)) evaluates a arithmetic expression in place +-*/()
    '''
    temps = []
    commands = flat_list([i.split("|") for i in commands])
    for i, command in enumerate(commands):
        if re.match(r'.*\$\(.+\).*', command):
            subs = re.findall(r'\$\(.+\)', command)
            for sub in subs:
                if "$((" in sub:
                    pt = sub[:]
                    while "$((" in pt:
                        si = pt.rfind("$((")
                        op = 2
                        sj = si+3
                        for s in pt[sj:]:
                            if op == 0:
                                break
                            if s == "(":
                                op += 1
                            if s == ")":
                                op -= 1
                            sj += 1
                        try:
                            exp = pt[si+1:sj]
                            pt = pt[:si] + str(eval(exp, {}, {})) + pt[sj:]
                        except Exception:
                            click.echo("bad expression: {}".format(exp))
                            raise click.Abort
                else:
                    f, pt = tempfile.mkstemp(dir="./", prefix='clasp_tmp')
                    temps.append(pt)
                    pipeline([sub.strip('$()')], outfile=pt)
                commands[i] = command.replace(sub, pt)
    return temps, commands


def pipeline(commands, outfile=None, inp=None, close=False, cwd=None,
             writemode='w', forceinpfile=False, caperr=False):
    """
    executes pipeline of shell commands (given as list of strings)

    special syntax:

    | $(some command) executes to a temporary file whose path is inserted in
    | the command.
    | $((expression)) evaluates a arithmetic expression in place +-*/()

    Parameters
    ----------
    commands: list
        list of commands to execute in order
    outfile: writeable file object
        optional destination for stdout
    inp: str or filebuffer
        string to feed to stdin at start of pipeline
    close: bool
        if true closes file object before returning
    cwd: str
        directory to execute pipeline (temp files and Popen cwd)
    writemode: str
        passed to open() for outfile ('w', 'wb' for write or 'a' for append)
    forceinpfile: bool
        always treat inp as a file, if a string, open the path for reading

    Returns
    -------
    out: str
        returns stdout of pipeline (will be None if outfile is given)
    """
    temps, commands = subpipe(commands)
    pops = [0]*len(commands)
    if outfile is not None and not hasattr(outfile, 'read'):
        if cwd is not None:
            outfile = open(cwd + "/" + outfile, writemode)
        else:
            outfile = open(outfile, writemode)
    for i in range(len(commands)):
        if i == 0:
            if hasattr(inp, 'read'):
                strin = False
                stdin = inp
            elif forceinpfile and inp is not None:
                strin = False
                stdin = open(inp, 'r')
            elif inp is not None:
                strin = True
                stdin = subprocess.PIPE
            else:
                strin = True
                stdin = None
        else:
            stdin = pops[i-1].stdout
        if i == len(commands) - 1 and outfile is not None:
            stdout = outfile
        else:
            stdout = subprocess.PIPE
        try:
            if caperr:
                pops[i] = subprocess.Popen(shlex.split(commands[i]),
                                           stdin=stdin, stdout=stdout, cwd=cwd,
                                           stderr=subprocess.PIPE)
            else:
                pops[i] = subprocess.Popen(shlex.split(commands[i]),
                                           stdin=stdin, stdout=stdout, cwd=cwd)
        except OSError:
            message = "invalid command / no such file: {}".format(commands[i])
            raise OSError(2, message)
    try:
        inp = inp.encode(encoding)
    except Exception as e:
        pass
    if len(commands) == 1 and strin:
        out = pops[0].communicate(inp)
    else:
        if inp is not None and strin:
            pops[0].stdin.write(inp)
            pops[0].stdin.close()
        out = pops[-1].communicate()
    try:
        output = out[0].decode(encoding)
    except Exception:
        output = out[0]
        pass
    if close:
        outfile.close()
    for temp in temps:
        os.remove(temp)
    if caperr:
        return output, out[1]
    else:
        return output


def flat_list(l):
    """flattens any depth list"""
    a = []
    try:
        if type(l) == list:
            for i in l:
                a += flat_list(i)
        else:
            a.append(l)
    except Exception:
        a.append(l)
    return a


def pool_call(func, args, kwargs={}, cwd=None, order=True, expand=False,
              handle=False, test=False):
    """
    execute func with concurrent.futures return output

    Parameters
    ----------
    func: python function
        function to execute
    args: list of tuples
        each set is mapped to function
    kwargs: dict
        constant keyword args for func
    cwd: str
        directory in which to execute function calls
    order: bool
        whether to maintain order of input
    expand: bool
        whether to expand items in args to map to function args
    handle: bool
        whether to return future objects or results
    Returns
    -------
    list of results unless handle=True then returns iterable of futures
    """
    if cwd is not None:
        os.chdir(cwd)
    if test:
        return [func(*arg, **kwargs) for arg in args]

    with ProcessPoolExecutor() as executor:
        if expand:
            futures = [executor.submit(func, *arg, **kwargs) for arg in args]
        else:
            futures = [executor.submit(func, arg, **kwargs) for arg in args]
    if order:
        it = futures
    else:
        it = as_completed(futures)
    if handle:
        return it
    else:
        return [future.result() for future in it]


def cluster_call(func, args, kwargs={}, timeout=.1, cwd=None,
                 debug=False):
    '''for backwards compatibility only'''
    args = zip(*args)
    largs = kwarg_match(func, kwargs)
    if 'debug' in kwargs:
        test = kwargs['debug'] or debug
    else:
        test = False or debug
    return pool_call(func, args, kwargs=largs, cwd=cwd, order=True, expand=True, test=test)


def read_epw(epw):
    '''read daylight sky data from epw or wea file

    Returns
    -------
    out: tuple
        (month, day, hour, dirnorn, difhoriz, globhoriz, skycover)
    '''
    if hasattr(epw, 'readlines'):
        f = epw
    else:
        f = open(epw, 'r')
    lines = f.readlines()
    f.seek(0)
    hours = [re.split(r'[ \t,]+', i) for i in lines if re.match(r"\d.*", i)]
    data = []
    for h in hours:
        if len(h) > 23:
            dp = [h[1], h[2], h[3], h[14], h[15], h[16], h[23]]
            hoff = .5
        else:
            try:
                dp = [h[0], h[1], h[2], h[3], h[4], h[5], h[6]]
            except IndexError:
                dp = [h[0], h[1], h[2], h[3], h[4], "0", "0"]
            hoff = 0
        data.append([int(i.strip()) for i in dp[0:2]] +
                    [float(dp[2]) - hoff] +
                    [float(i.strip()) for i in dp[3:]])
    return data


def isnum(s):
    """test if input can be converted to float"""
    try:
        float(s)
        return True
    except Exception:
        return False


def try_float(s):
    """attempt conversion to float"""
    try:
        a = float(s)
        return a
    except Exception:
        return s


def coerce_data(datastr, i_vals, dataf, coerce=True):
    '''ensure all data points parsed are valid numbers'''
    if datastr == [['']]:
        return [[]]
    try:
        i = None
        if coerce:
            data = [[float(j[i]) for j in datastr if isnum(j[i])]
                    for i in i_vals]
            if len(data[0]) == 0:
                raise ValueError("check if data file {} has xheaders {}"
                                 "".format(dataf, datastr))
        else:
            data = [[try_float(j[i]) for j in datastr] for i in i_vals]
    except ValueError as ex:
        raise ex
    except Exception:
        try:
            err = "list index out of range index: {} in file: {}"\
                  "".format(i, dataf)
        except Exception:
            err = "bad value or no data in file: {}, try coerce=False"\
                  "".format(dataf)
        raise IndexError(err)
    return data


def get_i(i, d_vals):
    """
    if (x, y) return y if x == i
    if y return y
    """
    ds = []
    for j in d_vals:
        if type(j) == tuple and j[0] == i:
            ds.append(j[1])
        elif type(j) != tuple:
            ds.append(j)
    return ds


def read_data_file(dataf, header=False, xheader=False, comment="#",
                   delim="\t, ", coerce=True):
    delim = '[{}]+'.format(delim)
    if comment != "#":
        comment = "^[{}].*".format(comment)
    elif not header and coerce:
        comment = r"^[^\-\d\w\.].*"
    else:
        comment = "^[{}].*".format(comment)
    f = open(dataf, 'r')
    dl = [i.strip() for i in re.split(r'[\n\r]+', f.read().strip())]
    if xheader:
        dl = [re.split(delim, i.strip(), 1)[1] for i in dl]
    dl = [i for i in dl if not bool(re.match(comment, i))]
    if len(dl) == 0:
        click.echo("File: {} has no data".format(dataf), err=True)
        raise click.Abort()
    datastr = [[j.strip() for j in re.split(delim, i.strip())] for i in dl]
    f.close()
    return datastr


def read_data(dataf, x_vals=[0], y_vals=[-1], rows=False, header=False,
              weax=None, reverse=False, autox=None, comment="#", xheader=False,
              delim="\t, ", coerce=True, weatherfile=False, drange=None):
    """read generic csv/tsv data file

    Parameters
    ----------
    dataf: str
        file to read data from
    x_vals: list of ints
        column (or row with rows=True) indices for x values
    y_vals: list of ints
        column (or row with rows=True) indices for y values
    rows: Boolean
        if True read data in rows
    header: Boolean
        return first row (or column with rows=True) as series labels
    weax: 2 item list of ints
        idx for month and day to use day number as x_vals, if given ignores
        x_val
    reverse: Boolean
        reverse order of data (use with autox)
    autox: Boolean
        assigns integers (starting at 0) as x_vals
    comment: str
        comment line signifiers (inserted in regex ^[comment].*)
    delim: str
        delimeters for parsing data (inserted in regex [delim]+)
    coerce: Boolean
        raise exception if all values are are not numbers
    weatherfile: str of file path
        handles wea and epw file formates returning daylight parameters
    drange: list of ints
        limit series output to given indices.

    Returns
    -------
    datax: list
        list of x_vals for each y_val (pads with last item if necessary)
        if there are more x_vals than y_vals does not return excess datax
    datay: list
        list for each y_val
    head: list
        if header=True list of labels for each y_val else []
    """
    if weatherfile:
        datastr = [[str(i) for i in j] for j in read_epw(dataf)]
        head = ['month', 'day', 'hour', 'direct normal', 'diffuse horizontal',
                'global horizontal', 'sky cover']
        head = [head[i] for i in y_vals]
    else:
        datastr = read_data_file(dataf, header, xheader, comment, delim,
                                 coerce=coerce)
        if rows:
            if header:
                head = datastr[0]
                datastr = list(map(list, list(zip(*datastr[1:]))))
            else:
                datastr = list(map(list, list(zip(*datastr))))
                head = []
        elif header:
            head = [datastr[0][i] for i in y_vals]
            datastr = datastr[1:]
        else:
            head = []
        if reverse:
            datastr.reverse()
    if drange is not None:
        datastr = [datastr[i] for i in drange]
    if len(y_vals) > 0:
        datay = coerce_data(datastr, y_vals, dataf, coerce)
    else:
        datay = [[]]
    if autox is not None:
        datax = []
        for i in datay:
            try:
                inc = (autox[1]-autox[0])/float(len(i)-1)
                datax.append([j*inc+autox[0] for j in range(len(i))])
            except ZeroDivisionError:
                datax.append([autox[0]])
    elif weax is not None:
        daycount = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
        datax = [[float(j[i]) for i in weax]
                 for j in datastr if isnum(j[weax[0]])]
        datax = [[daycount[int(i[0])-1] + i[1] for i in datax]]
    else:
        if len(x_vals) > 0:
            datax = coerce_data(datastr, x_vals, dataf, coerce)
        else:
            datax = [[]]
    while len(datax) < len(datay) and len(datax) > 0:
        datax += [datax[-1]]
    if len(datax) > len(datay):
        datax = datax[:len(datay)]
    return datax, datay, head


def read_all_data(datafs, x_vals=[], y_vals=[], **kwargs):
    """
    read multiple data files and pair x and y data call read_data

    Parameters
    ----------
    datafs: list of str
        files to read data from
    x_vals: list of ints or tuple int pairs
        (fileidx, colidx) or colidx to read from each file
    y_vals: list of ints or tuple int pairs
        (fileidx, colidx) or colidx to read from each file
    kwargs:
        optional arguments for read_data

    Returns
    -------
    datax: list
        list of x_vals for each y_val (pads with last item if necessary)
    datay: list
        list for each y_val
    head: list
        if header=True list of labels for each y_val else []
    """
    xds = []
    yds = []
    labels = []
    try:
        if kwargs['autox']:
            x_vals = y_vals
    except Exception:
        pass
    for x in x_vals:
        if type(x) == tuple:
            xd, _, _ = read_data(datafs[x[0]], [x[1]], [-1], **kwargs)
            xds += xd
        else:
            for d in datafs:
                xd, _, _ = read_data(d, [x], [-1], **kwargs)
                xds += xd
    for y in y_vals:
        if type(y) == tuple:
            _, yd, label = read_data(datafs[y[0]], [], [y[1]], **kwargs)
            yds += yd
            labels += label
        else:
            for d in datafs:
                _, yd, label = read_data(d, [], [y], **kwargs)
                yds += yd
                labels += label
    while len(xds) < len(yds) and len(xds) > 0:
        xds += [xds[-1]]
    return xds, yds, labels


def clean_tmp(ctx):
    f, path = tempfile.mkstemp(dir="./", prefix='clasp_tmp')
    if ctx.obj is None:
        ctx.obj = dict(temps=[path])
    else:
        ctx.obj['temps'].append(path)
    return path


def expandpat(pat, s, mark=0):
    """expand sglob pattern for each character option

    Parameters
    ----------
    pat: regex
        regex pattern to split on
    s: str
        string to split
    mark: int
        0: include splitting mark in output
        1: skip splitting mark (assume 1 character in length)

    Returns
    -------
    allpat: list of strings
        list of strings enumerating all possible combinations of pattern
    """
    if re.search(pat, s):
        parts = re.split(pat, s)
        marks = re.findall(pat, s)
        patm = []
        for i, ma in enumerate(marks):
            part = [parts[i]] * (len(ma) - (2 + mark))
            for j, mai in enumerate(ma[1 + mark:-1]):
                part[j] += mai
            patm.append(part)
        patm.append([parts[-1]])
        allpat = [''.join(i) for i in zip(*crossref_all(patm))]
        return allpat
    else:
        return []


def sglob(s):
    '''super glob includes [abc] notation + [!abc] exclude notation'''
    inre = r'\[[\w\d\-\_\.]+\]'
    exre = r'\[\![\w\d\-\_\.]+\]'
    inpat = expandpat(inre, s) + [s]
    exglob = flat_list([expandpat(exre, i, 1) for i in inpat])
    inglob = [re.sub(exre, '*', i) for i in inpat]
    infiles = set(flat_list([glob(i) for i in inglob]))
    exfiles = set(flat_list([glob(i) for i in exglob]))
    return sorted(list(infiles.difference(exfiles)))
