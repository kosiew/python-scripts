
# ##filename=u.py, edited on 20 May 2019 Mon 07:47 PM
# filename=u.py, edited on 11 Oct 2016 Tue 11:43 AM

__author__ = "Siew Kam Onn"
__email__ = "kosiew at gmail.com"
__version__ = "$Revision: 1.0 $"
__date__ = "$Date: 20-09-06 2:59:00 PM $"
__copyright__ = "Copyright (c) 2006 Siew Kam Onn"
__license__ = "Python"

"""a collection of useful functions"""

import datetime
import dateutil
from dateutil import relativedelta
import zd
import sys
import os
import fnmatch
import functools
import math
from _base import is_iterable

PY3 = sys.version_info[0] == 3


DATE = datetime.date(2000, 1, 1)
DATETIME = datetime.datetime(2000, 1, 1)
TEST = False

int2byte = (lambda x: bytes((x,))) if PY3 else chr

_text_characters = (
        b''.join(int2byte(i) for i in range(32, 127)) +
        b'\n\r\t\f\b')

_last_message = None

bit64 = sys.maxsize > 2**32
bit32 = not bit64

class Error(Exception):
    pass

def dprint(message):
    global TEST
    if TEST:
        print(message)

def printf(a_string, *args):
    global _last_message

    if a_string:
        message = a_string.format(*args)
        if not _last_message or (_last_message != message):
            _last_message = message
            print(message)

def pretty_table_string(table, justify = "R", columnWidth = 0):
    # table is a list/tuple of list/tuple
    # returns table formatted a pretty table
    #
    # Not enforced but
    # if provided columnWidth must be greater than max column width in table!
    if columnWidth == 0:
        # find max column width
        for row in table:
            for col in row:
                width = len(str(col))
                if width > columnWidth:
                    columnWidth = width

    outputStr = ""
    for row in table:
        rowList = []
        for col in row:
            if justify == "R": # justify right
                rowList.append(str(col).rjust(columnWidth))
            elif justify == "L": # justify left
                rowList.append(str(col).ljust(columnWidth))
            elif justify == "C": # justify center
                rowList.append(str(col).center(columnWidth))
        outputStr += ' '.join(rowList) + "\n"
    return outputStr

def string_to_list(string, delimiter = '\n',
    unique_members_only = True, sort = False):
    l = [_string for _string in string.split(delimiter) if len(_string) > 0]
    if unique_members_only:
        l = set(l)
        l = list(l)

    if sort:
        l.sort()

    return l


def round_significant_digits(num, significant_digits):
    """Round to specified number of sigfigs.
    http://code.activestate.com/recipes/578114-round-number-to-specified-number-of-significant-di/

    >>> round_significant_digits(0, significant_digits=4)
    0
    >>> int(round_significant_digits(12345, significant_digits=2))
    12000
    >>> int(round_significant_digits(-12345, significant_digits=2))
    -12000
    >>> int(round_significant_digits(1, significant_digits=2))
    1
    >>> '{0:.3}'.format(round_significant_digits(3.1415, significant_digits=2))
    '3.1'
    >>> '{0:.3}'.format(round_significant_digits(-3.1415, significant_digits=2))
    '-3.1'
    >>> '{0:.5}'.format(round_significant_digits(0.00098765, significant_digits=2))
    '0.00099'
    >>> '{0:.6}'.format(round_significant_digits(0.00098765, significant_digits=3))
    '0.000988'
    """
    if num != 0:
        return round(num, -int(math.floor(math.log10(abs(num))) - (significant_digits - 1)))
    else:
        return 0  # Can't take the log of 0


# source
# http://eli.thegreenplace.net/2011/10/19/perls-guess-if-file-is-text-or-binary-implemented-in-python/
def istextfile(file_path, blocksize=512):
    """ Uses heuristics to guess whether the given file is text or binary,
        by reading a single block of bytes from the file.
        If more than 30% of the chars in the block are non-text, or there
        are NUL ('\x00') bytes in the block, assume this is a binary file.
    """
    fileobj = file(file_path)
    block = fileobj.read(blocksize)
    if b'\x00' in block:
        # Files with null bytes are binary
        return False
    elif not block:
        # An empty file is considered a valid text file
        return True

    # Use translate's 'deletechars' argument to efficiently remove all
    # occurrences of _text_characters from the block
    nontext = block.translate(None, _text_characters)
    return float(len(nontext)) / len(block) <= 0.30


def dprint(message, number_of_times = 1, prefix = 'DEBUG:'):
    ''' Returns None
        debug print
    '''
    for i in range(number_of_times):
        _safe_print('{0}:{1}'.format(prefix, message))
    return None


def _safe_print(u, errors="replace"):
    """Safely print the given string.

    If you want to see the code points for unprintable characters then you
    can use `errors="xmlcharrefreplace"`.
    """
    s = u.encode(sys.stdout.encoding or "utf-8", errors)
    print(s)


def like_number(v):
    ''' return True if v like number

    >>> like_number('1.1')
    True
    >>> like_number(1.1)
    True
    >>> like_number('a')
    False

    '''
    try:
        t = float(v)
        return True
    except ValueError as e:
        zd.f('%s is not float' % v)
        return False


def is_dictionary(d):
    ''' Returns True if d is dictionary

    >>> d = {}
    >>> is_dictionary(d)
    True
    >>> d = []
    >>> is_dictionary(d)
    False
    '''
    try:
        v = d.get(0)
        is_dict = True
    except KeyError as ke:
        is_dict = True
    except Exception as e:
        is_dict = False

    return is_dict

#     return type(d) == type({})


def is_number(v):
    """
       Returns True is v is a number, False otherwise
    >>> is_number('1')
    False
    >>> is_number(1)
    True

    """
    try:
        n = v + 0.000000000000001
        return True
    except TypeError:
        return False

def is_boolean(b):
    """
        Returns True is v is a boolean, False otherwise
    """
    return type(b) is type(True)

def is_date(d):
    """
       Returns True if d is datetime.date
    """
    return type(d) is datetime.date

def is_datetime(d):
    """
       Returns True if d is datetime.datetime
    """
    return type(d) is datetime.datetime


def is_string(s):
    """
       Returns True is s is string
    """
    return isinstance(s, str)


def ensure_iterable(i):
    '''
            turns i into a tuple if it is not
    '''
    if i:
        return i if is_iterable(i) else (i,)
    return i

def is_odd_number(n):
    ''' Returns True if odd number

    >>> is_odd_number("123")
    True
    >>> is_odd_number(123)
    True
    >>> is_odd_number(123.1)
    True
    >>> is_odd_number(124)
    False


    '''
    try:
        a_number = int(n)
    except Exception as e:
        return False


    return a_number % 2 == 1



def today():
    """Returns today
    """
    return datetime.date.today()

def now(return_string=False):
    """Returns now
        eg datetime.datetime(2017, 4, 5, 9, 15, 49, 717472)
    """
    result = datetime.datetime.now()
    if return_string:
        result = result.strftime('%Y %b %d %H:%M:%S')
    return result

def currenttime():
    """Returns currenttime
    """
    ct = now()
    return ct.time()

def addweeks(week = 0, t = None):
    """Returns today + weeks
    """
    t = today() if t is None else t
    aw = t + relativedelta.relativedelta(weeks = week)
    return aw

def addmonths(month = 0, t = None):
    """Returns today + months
    """
    t = today() if t is None else t
    am = t + relativedelta.relativedelta(months = month)
    return am

def adddays(day = 0, t = None):
    """Returns today + days
    """
    t = today() if t is None else t
    ad = t + relativedelta.relativedelta(days = day)
    return ad

def addyears(year = 0, t = None):
    """Returns today + years
    """
    t = today() if t is None else t
    ad = t + relativedelta.relativedelta(years = year)
    return ad

from dateutil import rrule

def weeks_between(start_date, end_date):
    start_date, end_date, multiplier = ensure_end_date_is_later(start_date, end_date)
    weeks = rrule.rrule(rrule.WEEKLY, dtstart=start_date, until=end_date)
    difference = weeks.count() - 1
    return multiplier * difference

def days_between(start_date, end_date):
    start_date, end_date, multiplier = ensure_end_date_is_later(start_date, end_date)
    days = rrule.rrule(rrule.DAILY, dtstart=start_date, until=end_date)
    difference = days.count() - 1
    return multiplier * difference

def ensure_date(d):
    ''' Returns None
    '''

    d = datetime.date(d.year, d.month, d.day) if type(d) == datetime.datetime else d
    return d


def ensure_end_date_is_later(start_date, end_date):
    """will swap start_date, end_date if start_date is later than end_date
       if swapped, will return multiplier = -1
       >>> sd = datetime.date(2006, 1, 31)
       >>> ed = datetime.date(2006, 2, 1)
       >>> ensure_end_date_is_later(sd, ed)
       (datetime.date(2006, 1, 31), datetime.date(2006, 2, 1), 1)
       >>> ensure_end_date_is_later(ed, sd)
       (datetime.date(2006, 1, 31), datetime.date(2006, 2, 1), -1)
    """
    end_date = ensure_date(end_date)
    start_date = ensure_date(start_date)
    if end_date < start_date:
        start_date, end_date = end_date, start_date
        multiplier = -1
    else:
        multiplier = 1
    return start_date, end_date, multiplier


epoch = datetime.datetime(1970, 1, 1)


def translator(frm='', to='', delete='', keep=None):
    """a factory for string.translate
    """
    if len(to) == 1:
        to = to * len(frm)
    trans = ''.maketrans(frm, to)
    if keep is not None:
        allchars = ''.maketrans('', '')
        delete = allchars.translate(allchars, keep.translate(allchars, delete))
    def translate(s):
        return s.translate(trans, delete)
    return translate

notrans = ''.maketrans('', '')           # identity "translation"
def containsAny(astr, strset):
    return len(strset) != len(strset.translate(notrans, astr))
def containsAll(astr, strset):
    return not strset.translate(notrans, astr)

import struct

_cache = {}

def fields(baseformat, theline, lastfield=False, cache=_cache):
    # build the key and try getting the cached format string
    key = baseformat, len(theline), lastfield
    format = cache.get(key)
    if format is None:
        # no format string was cached, build and cache it
        numremain = len(theline)-struct.calcsize(baseformat)
        cache[key] = format = "%s %d%s" % (
            baseformat, numremain, lastfield and "s" or "x")
    return struct.unpack(format, theline)


def split_at(the_line, cuts, lastfield=False):
    """usage: a = list(u.split_at(....))"""
    last = 0
    for cut in cuts:
        yield the_line[last:cut]
        last = cut
    if lastfield:
        yield the_line[last:]

def split_by(the_line, n, lastfield=False):
    """usage: a = list(u.split_by(....))"""
    return split_at(the_line, range(n, len(the_line), n), lastfield)

def addSpaces(s, numAdd):
    white = " "*numAdd
    return white + white.join(s.splitlines(True))

def numSpaces(s):
    return [len(line)-len(line.lstrip()) for line in s.splitlines()]

def delSpaces(s, numDel):
    if numDel > min(numSpaces(s)):
        raise ValueError("removing more spaces than there are!")
    return '\n'.join([ line[numDel:] for line in s.splitlines() ])

def unIndentBlock(s):
    return delSpaces(s, min(numSpaces(s)))


def dictionary_replace(format, d, marker='%', safe=True):
    if safe:
        def lookup(w): return d.get(w, w.join(marker*2))
    else:
        def lookup(w): return d[w]
    parts = format.split(marker)
    parts[1::2] = list(map(lookup, parts[1::2]))
    return ''.join(parts)

import re

class make_translation:
    """usage
       translate = u.make_translation(aDict)
       translate(text)"""
    def __init__(self, *args, **kwds):
        self.adict = dict(*args, **kwds)
        self.rx = self.make_rx()
    def make_rx(self):
        return re.compile('|'.join(map(re.escape, self.adict)))
    def one_translation(self, match):
        return self.adict[match.group(0)]
    def __call__(self, text):
        if text is None:
            return None
        return self.rx.sub(self.one_translation, text)

class make_translation_by_whole_words(make_translation):
    """refer to make_translation"""
    def make_rx(self):
        return re.compile(r'\b%s\b' % r'\b|\b'.join(map(re.escape, self.adict)))


import itertools

def anyTrue(predicate, sequence):
    return True in map(predicate, sequence)


import heapq

def imerge(*iterables):
    '''Merge multiple sorted inputs into a single sorted output.

    >>> list(imerge([1,3,5,7], [0,2,4,8], [5,10,15,20], [], [25]))
    [0, 1, 2, 3, 4, 5, 5, 7, 8, 10, 15, 20, 25]
    '''
    heappop, heappush = heapq.heappop, heapq.heappush
    its = list(map(iter, iterables))
    h = []
    for it in its:
        try:
            v = next(it)
        except StopIteration:
            continue
        heappush(h, (v, it.__next__))
    while h:
        v, next = heappop(h)
        yield v
        try:
            v = next()
        except StopIteration:
            continue
        heappush(h, (v, next))


def counter(start):

    """Create a counter starting at ``start``."""

    # The value "curr" needs to be wrapped in a list.  Otherwise, when
    # "+=" is used in "inc", Python binds the variable at that scope
    # instead of at this scope.  We don't want to redefine a variable at
    # the inner scope.  We want to modify the variable at this outer
    # scope.  Java programmers would call this "boxing", but they would
    # use an Integer instance instead of a list.

    curr = [start]

    def inc():
        """Increment the counter and return the new value."""
        curr[0] += 1
        return curr[0]

    return inc


class iStr(str):
    """
    Case insensitive string class.
    Behaves just like str, except that all comparisons and lookups
    are case insensitive.
    """
    def __init__(self, *args):
        self._lowered = str.lower(self)
    def __repr__(self):
        return '%s(%s)' % (type(self).__name__, str.__repr__(self))
    def __hash__(self):
        return hash(self._lowered)
    def lower(self):
        return self._lowered
def _make_case_insensitive(name):
    ''' wrap one method of str into an iStr one, case-insensitive '''
    str_meth = getattr(str, name)
    def x(self, other, *args):
        ''' try lowercasing 'other', which is typically a string, but
            be prepared to use it as-is if lowering gives problems,
            since strings CAN be correctly compared with non-strings.
        '''
        try: other = other.lower()
        except (TypeError, AttributeError, ValueError): pass
        return str_meth(self._lowered, other, *args)
    # in Python 2.4, only, add the statement: x.func_name = name
    setattr(iStr, name, x)
# apply the _make_case_insensitive function to specified methods
# 22-Mar-10 Mon 11:27:39 AM
#   removed cmp after upgrading to python 2.6.5
for name in 'eq lt le gt gt ne contains'.split():
    _make_case_insensitive('__%s__' % name)
for name in 'count endswith find index rfind rindex startswith'.split():
    _make_case_insensitive(name)
# note that we don't modify methods 'replace', 'split', 'strip', ...
# of course, you can add modifications to them, too, if you prefer that.
del _make_case_insensitive    # remove helper function, not needed any more

def _make_return_iStr(name):
    str_meth = getattr(str, name)
    def x(*args):
        return iStr(str_meth(*args))
    setattr(iStr, name, x)

for name in 'center ljust rjust strip lstrip rstrip'.split():
    _make_return_iStr(name)


class iList(list):
    def __init__(self, *args):
        list.__init__(self, *args)
        # rely on __setitem__ to wrap each item into iStr...
        self[:] = self
    wrap_each_item = iStr
    def __setitem__(self, i, v):
        if isinstance(i, slice): v = list(map(self.wrap_each_item, v))
        else: v = self.wrap_each_item(v)
        list.__setitem__(self, i, v)
    def append(self, item):
        list.append(self, self.wrap_each_item(item))
    def extend(self, seq):
        list.extend(self, list(map(self.wrap_each_item, seq)))

# should use bv_symlink.get_symbolic_links instead
#
def get_symbolic_links(root, single_level = False,
    yield_folders=False, return_full_path = True,
    return_list = False):
    import bv_symlink
    return bv_symlink.get_symbolic_links(root, single_level,
            yield_folders, return_full_path, return_list)


def all_files_in(root, patterns='*', single_level=False,
    yield_folders=False, return_full_path = True,
    return_list = False, follow_link = True):
    """display list of files and files in subdirectory of root
    """

    if return_list:
        return list(_all_files_in(root, patterns, single_level,
            yield_folders, return_full_path, follow_link))
    else:
        return _all_files_in(root, patterns, single_level,
            yield_folders, return_full_path, follow_link)

# consider this for improvement
# [glob.glob(e) for e in ['*.pdf', '*.cpp']]
def _all_files_in(root, patterns='*', single_level=False,
    yield_folders=False, return_full_path = True,
    follow_link = True):
    """display list of files and files in subdirectory of root
    """
    import bv_symlink
    root = os.path.expanduser(root)

    # Expand patterns from semicolon-separated string to list
    if not patterns:
        patterns = '*'
    patterns = patterns.split(';')
    dprint(f'walking {root}..')
    _files = []
    for path, subdirs, files in os.walk(root):
        dprint('evaluating path %s, subdir %s' % (path, subdirs))
        if yield_folders:
            _files = subdirs
        else:
            _files = files
        _files.sort()
        dprint('evaluating files %s' % _files)
        for name in _files:
            dprint('evaluating %s' % name)
            for pattern in patterns:
                if fnmatch.fnmatch(name, pattern):
                    full_path = os.path.join(path, name)

                    is_link = bv_symlink.islink(full_path, True)
                    dprint(f'{full_path} {is_link}')

                    if (not follow_link and not is_link) or follow_link:
                        if return_full_path:
                            yield full_path
                        else:
                            yield name
                        break
        if single_level:
            break

def count_lines(thefilepath):
    """counts number of lines in thefilepath"""
    count = 0
    thefile = open(thefilepath, 'rb')
    while True:
        buffer = thefile.read(8192*1024)
        if not buffer:
            break
        count += buffer.count('\n')
    thefile.close()
    return count

def swapextensions(dir, before, after):
    """swap extensions of files within dir
    """
    if before[:1] != '.':
        before = '.'+before
    thelen = -len(before)
    if after[:1] != '.':
        after = '.'+after
    for path, subdirs, files in os.walk(dir):
        for oldfile in files:
            if oldfile[thelen:] == before:
                oldfile = os.path.join(path, oldfile)
                newfile = oldfile[:thelen] + after
                os.rename(oldfile, newfile)

def search_file(filename, search_path, pathsep=os.pathsep):
    """ Given a search path, find file with requested name """
    for path in search_path.split(pathsep):
        candidate = os.path.join(path, filename)
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)
    return None

import glob

def all_files(pattern, search_path, pathsep=os.pathsep):
    """ Given a search path, yield all files matching the pattern. """
    for path in search_path.split(pathsep):
        for match in glob.glob(os.path.join(path, pattern)):
            yield match




def _find(pathname, matchFunc=os.path.isfile):
    for dirname in sys.path:
        candidate = os.path.join(dirname, pathname)
        if matchFunc(candidate):
            return candidate
    raise Error("Can't find file %s" % pathname)

def findFile(pathname):
    return _find(pathname)

def findDir(path):
    return _find(path, matchFunc=os.path.isdir)


def addSysPath(new_path, import_this_path_first = False):
    """ AddSysPath(new_path): adds a directory to Python's sys.path
    Does not add the directory if it does not exist or if it's already on
    sys.path.
    if import_this_path_first then will add new_path at beginning of sys.path
    """
    if os.path.exists(new_path):
        # Standardize the path.  Windows is case-insensitive, so lowercase
        # for definiteness if we are on Windows.
        new_path = os.path.abspath(new_path)
        if sys.platform == 'win32':
            new_path = new_path.lower()
        # Check against all currently available paths
        for x in sys.path:
            x = os.path.abspath(x)
            if sys.platform == 'win32':
                x = x.lower()
            if new_path in (x, x + os.sep):
                return "%s is already in sys.path" % new_path
        if import_this_path_first:
            sys.path.insert(0, new_path)
            message = "%s inserted at beginning of sys.path" % new_path
        else:
            sys.path.append(new_path)
            message = "%s appended to sys.path" % new_path
    # Avoid adding nonexistent paths
    else:
        message = "%s is not a valid path" % new_path

    return message

def boolean_value(v):
    ''' Returns boolean value of v
    '''
    if v:
        return True
    else:
        return False



def none_value(v, value_if_none):
    ''' Returns value_if_none if v is None
    '''

    result = value_if_none if v is None else v
    return result


def all_equal(elements):
    ''' return True if all the elements are equal, otherwise False. '''
#     set returns tuple of unique values in elements
    return len(set(elements)) == 1

def common_prefix(*sequences):
    ''' return a list of common elements at the start of all sequences,
        then a list of lists that are the unique tails of each sequence. '''
    # if there are no sequences at all, we're done
    if not sequences: return [], []
    # loop in parallel on the sequences
    common = []
    for elements in zip(*sequences):
        # unless all elements are equal, bail out of the loop
        if not all_equal(elements): break
        # got one more common element, append it and keep looping
        common.append(elements[0])
    # return the common prefix and unique tails
    return common, [ sequence[len(common):] for sequence in sequences ]

def relpath(p1, p2, sep=os.path.sep, pardir=os.path.pardir):
    ''' return a relative path from p1 equivalent to path p2.
        In particular: the empty string, if p1 == p2;
                       p2, if p1 and p2 have no common prefix.
        >>> relpath('c:/1/php', 'c:/1/sql', '/')
        '../sql'
        >>> relpath('c:/1/php', 'c:/2/sql', '/')
        '../../2/sql'
    '''
    common, (u1, u2) = common_prefix(p1.split(sep), p2.split(sep))
    if not common:
        return p2      # leave path absolute if nothing at all in common
    return sep.join( [pardir]*len(u1) + u2 )

# needs win32all to work on Windows (NT, 2K, XP, _not_ /95 or /98)
if os.name == 'nt':

    if bit32:
        import win32con
        import pywintypes
        import win32file
        LOCK_EX = win32con.LOCKFILE_EXCLUSIVE_LOCK
        LOCK_SH = 0 # the default
        LOCK_NB = win32con.LOCKFILE_FAIL_IMMEDIATELY
        __overlapped = pywintypes.OVERLAPPED()
        def lock(file, flags):
            hfile = win32file._get_osfhandle(file.fileno())
            win32file.LockFileEx(hfile, flags, 0, 0xffff0000, __overlapped)
        def unlock(file):
            hfile = win32file._get_osfhandle(file.fileno())
            win32file.UnlockFileEx(hfile, 0, 0xffff0000, __overlapped)
elif os.name == 'posix':
    from fcntl import LOCK_EX, LOCK_SH, LOCK_NB
    def lock(file, flags):
        fcntl.flock(file.fileno(), flags)
    def unlock(file):
        fcntl.flock(file.fileno(), fcntl.LOCK_UN)
else:
    raise RuntimeError("PortaLocker only defined for nt and posix platforms")

def VersionFile(file_spec, vtype='copy'):
    import os, shutil
    if os.path.isfile(file_spec):
        # check the 'vtype' parameter
        if vtype not in ('copy', 'rename'):
             raise ValueError('Unknown vtype %r' % (vtype,))
        # Determine root filename so the extension doesn't get longer
        n, e = os.path.splitext(file_spec)
        # Is e a three-digits integer preceded by a dot?
        if len(e) == 4 and e[1:].isdigit():
            num = 1 + int(e[1:])
            root = n
        else:
            num = 0
            root = file_spec
        # Find next available file version
        for i in range(num, 1000):
             new_file = '%s.%03d' % (root, i)
             if not os.path.exists(new_file):
                  if vtype == 'copy':
                      shutil.copy(file_spec, new_file)
                  else:
                      os.rename(file_spec, new_file)
                  return True
        raise RuntimeError("Can't %s %r, all names taken"%(vtype,file_spec))
    return False


def transpose_array(an_array):
    """Returns a transposed array
       expecting an_array to be 2 dimensional

       >>> arr = [['a1', 'a2', 'a3', 'a4'], ['b1', 'b2', 'b3', 'b4'], ['c1', 'c2', 'c3', 'c4']]
       >>> transpose_array(arr)
       [['a1', 'b1', 'c1'], ['a2', 'b2', 'c2'], ['a3', 'b3', 'c3'], ['a4', 'b4', 'c4']]
    """
    transposed_array = list(map(list, list(zip(*an_array))))
    return transposed_array

def pick_and_reorder_columns(listofRows, column_indexes):
    """
    >>> arr = [['a1', 'a2', 'a3', 'a4'], ['b1', 'b2', 'b3', 'b4'], ['c1', 'c2', 'c3', 'c4']]
    >>> col_ind = 0, 3
    >>> pick_and_reorder_columns(arr, col_ind)
    [['a1', 'a4'], ['b1', 'b4'], ['c1', 'c4']]
    """
    return [[row[ci] for ci in column_indexes] for row in listofRows ]


def list_or_tuple(x):
    return isinstance(x, (list, tuple))

def nonstring_iterable(obj):
    try: iter(obj)
    except TypeError: return False
    else: return not isinstance(obj, str)

def flatten(sequence, to_expand=list_or_tuple):
    """flattens sequence to 1 dimension using recursion
    >>> seq = ['a', ['b.1', 'b.2', 'b.3'], 'c']
    >>> list(flatten(seq))
    ['a', 'b.1', 'b.2', 'b.3', 'c']
    >>> seq = ('a', ('b.1', 'b.2', 'b.3'), 'c')
    >>> list(flatten(seq))
    ['a', 'b.1', 'b.2', 'b.3', 'c']
    >>> tuple(flatten(seq))
    ('a', 'b.1', 'b.2', 'b.3', 'c')

    """
    for item in sequence:
        if to_expand(item):
            for subitem in flatten(item, to_expand):
                yield subitem
        else:
            yield item

def flatten_nr(sequence, to_expand=list_or_tuple):
    """flattens sequence to 1 dimension without recursion

    >>> seq = ['a', ['b.1', 'b.2', 'b.3'], 'c']
    >>> list(flatten_nr(seq))
    ['a', 'b.1', 'b.2', 'b.3', 'c']
    """
    iterators = [ iter(sequence) ]
    while iterators:
        # loop on the currently most-nested (last) iterator
        for item in iterators[-1]:
            if to_expand(item):
                # subsequence found, go loop on iterator on subsequence
                iterators.append(iter(item))
                break
            else:
                yield item
        else:
            # most-nested iterator exhausted, go back, loop on its parent
            iterators.pop()

multilist = [["%s, %s" % (row, col) for col in range(5)] for row in range(10)]


def list_get(L, i, v=None):
    """
    >>> l = [0, 1, 2, 3]
    >>> list_get(l, 0)
    0
    >>> list_get(l, 3, 4)
    3
    >>> list_get(l, 4, 5)
    5

    """
    if -len(L) <= i < len(L): return L[i]
    else: return v

def list_get_egfp(L, i, v=None):
    """
    >>> l = [0, 1, 2, 3]
    >>> list_get_egfp(l, 0)
    0
    >>> list_get_egfp(l, 3, 4)
    3
    >>> list_get_egfp(l, 4, 5)
    5

    """
    try: return L[i]
    except IndexError: return v


def workdays(start, end, holidays=0, days_off=None):
    """
    returns the workdays between start and end
      works by counting total days between start and end
        minus holidays (count)
        minus days_off (the off days in a week eg Saturday, Sunday, days_off
        = 5, 6)
    >>> start = datetime.date(2006, 11, 25)
    >>> end = datetime.date(2006, 12, 25)
    >>> days = rrule.rrule(rrule.DAILY, dtstart=start, until=end)
    >>> days.count()
    31
    >>> work_days=[x for x in range(7) if x not in (5, 6)]
    >>> days = rrule.rrule(rrule.DAILY, dtstart=start, until=end, byweekday = work_days)
    >>> days.count()
    21
    >>> days_off = range(6)
    >>> holidays = 2
    >>> workdays(start, end, holidays, days_off)
    3
    """
    if days_off is None:
        days_off = 5, 6         # default to: saturdays and sundays
    workdays = [x for x in range(7) if x not in days_off]
    days = rrule.rrule(rrule.DAILY, dtstart=start, until=end,
                       byweekday=workdays)
    return days.count() - holidays



import decimal
import a

def money_format(value, places=2, curr='RM', sep=',', dp='.', pos='', neg='-',
               overall=10):
    """ Convert Decimal ``value'' to a money-formatted string.
    places:  required number of places after the decimal point
    curr:    optional currency symbol before the sign (may be blank)
    sep:     optional grouping separator (comma, period, or blank) every 3
    dp:      decimal point indicator (comma or period); only specify as
                 blank when places is zero
    pos:     optional sign for positive numbers: "+", space or blank
    neg:     optional sign for negative numbers: "-", "(", space or blank
    overall: optional overall length of result, adds padding on the
                 left, between the currency symbol and digits
    """
    a.assert_true(isinstance(value, decimal.Decimal), '%s must be a Decimal object'
            % value)
    q = decimal.Decimal((0, (1,), -places))             # 2 places --> '0.01'
    sign, digits, exp = value.quantize(q).as_tuple()
    result = []
    digits = list(map(str, digits))
    append, next = result.append, digits.pop
    for i in range(places):
        if digits:
            append(next())
        else:
            append('0')
    append(dp)
    i = 0
    while digits:
        append(next())
        i += 1
        if i == 3 and digits:
            i = 0
            append(sep)
    while len(result) < overall:
        append(' ')
    append(curr)
    if sign: append(neg)
    else: append(pos)
    result.reverse()
    return ''.join(result)

def dictionary_get(dictionary, key, no_key_message = 'no such key', pop = False):
    """Returns the value for the dictionary key
       if pop = True will also remove the value after returning the value

       >>> d = dict(first=1, second=2, third=3)
       >>> dictionary_get(d, 'second')
       2
       >>> dictionary_get(d, 'second', 'no such key', True)
       2
       >>> dictionary_get(d, 'second', 'no such key', True)
       'no such key'

    """
    result = dictionary.get(key, no_key_message)
    if pop:
        dictionary.pop(key, None)

    return result

def dictionary_seed(keys, value):
    """Returns a dictionary where every d[key] = value
       keys can be a sequence of a string of alphabets

       >>> keys = ('first', 'second', 'third')
       >>> d = dictionary_seed(keys, 0)
       >>> d['first']
       0
       >>> d['second']
       0
       >>> d['third']
       0
       >>> import string
       >>> keys = string.ascii_lowercase
       >>> d = dictionary_seed(keys, 0)
       >>> d['a']
       0
       >>> d['b']
       0
       >>> d['z']
       0

    """
    return dict.fromkeys(keys, value)

def pairwise(iterable):
    itnext = iter(iterable).__next__
    while True:
        yield itnext(), itnext()

def dictionary_from_sequence(seq):
    """Returns dict from list of alternating keys and values
       >>> l = 'first', 1, 'second', 2, 'third', 3
       >>> d = dictionary_from_sequence(l)
       >>> d['first']
       1
       >>> d['second']
       2
    """
    return dict(pairwise(seq))


def sub_dict(somedict, somekeys):
    """Returns subset of dictionary - only the matching keys in somekeys
       >>> keys = 'first', 'second', 'third'
       >>> d = dict(first = 1, second = 2, third = 3, fourth = 4, fifth = 5)
       >>> new_d = sub_dict(d, keys)
       >>> new_d.get('first')
       1
       >>> new_d.get('second')
       2
       >>> new_d.get('fourth', 'no such value')
       'no such value'
    """
    return dict([ (k, somedict[k]) for k in somekeys if k in somedict])

def sub_dict_remove_select(somedict, somekeys):
    """Returns subset of dictionary - only those matching keys not in somekeys
       >>> keys = 'first', 'second', 'third'
       >>> d = dict(first = 1, second = 2, third = 3, fourth = 4, fifth = 5)
       >>> new_d = sub_dict_remove_select(d, keys)
       >>> d.get('second')

       >>> new_d.get('second')
       2
    """
    return dict([ (k, somedict.pop(k)) for k in somekeys if k in somedict])

def invert_dict(d):
    """Returns a dictionary d inverted
       >>> d = dict(first = 1, second = 2, third = 3, fourth = 4, fifth = 5)
       >>> new_d = invert_dict(d)
       >>> new_d[5]
       'fifth'
       >>> new_d[2]
       'second'
       >>> sorted_dictionary_values(new_d)
       ['first', 'second', 'third', 'fourth', 'fifth']

    """
    izip = itertools.izip
    return dict(zip(iter(d.values()), iter(d.keys())))


# def printf(format, *args):
#     """
#        >>> s = 'simple string'
#        >>> t = ('a', 'b', 'c')
#        >>> printf('this is a %s, %s', s, t)
#        this is a simple string, ('a', 'b', 'c')
#     """
#     sys.stdout.write(format % args)

import random

def random_pick(some_list, probabilities):
    a.assert_true(len(some_list) == len(probabilities))
    a.assert_true(0 <= min(probabilities) and max(probabilities) <= 1)
    a.assert_true(abs(sum(probabilities)-1.0) < 1.0e-5)
    x = random.uniform(0, 1)
    cumulative_probability = 0.0
    for item, item_probability in zip(some_list, probabilities):
        cumulative_probability += item_probability
        if x < cumulative_probability: break
    return item

def random_picks(sequence, relative_odds):
    table = [ z for x, y in zip(sequence, relative_odds) for z in [x]*y ]
    while True:
        yield random.choice(table)

def returns(t, f, *a, **k):
    """Return [f(*a, **k)] normally, [] if that raises an exception in t.
       >>> t = (ValueError, NameError, TypeError)
       >>> f = int
       >>> returns(t, f, 1)
       [1]
       >>> returns(t, f, 'a')
       []
       >>> t = NameError
       >>> returns(t, f, 'a')
       Traceback (most recent call last):
       ...
       ValueError: invalid literal for int() with base 10: 'a'

    """
    try:
        return [f(*a, **k)]
    except t:
        return []


def sorted_dictionary_values(adict):
    """Returns dictionary values sorted by key
       >>> d = dict(first = 1, second = 2, third = 3)
       >>> l = sorted_dictionary_values(d)
       >>> l
       [1, 2, 3]
    """
    keys = list(adict.keys())
    keys.sort()
    return [adict[key] for key in keys]


def case_insensitive_sort(string_list):
    """Returns a copy of string_list sorted
       >>> l = ['abc', 'ABC', 'bcd', 'BCD']

normal sort
       >>> l.sort()
       >>> l
       ['ABC', 'BCD', 'abc', 'bcd']

case_insensitive_sort
       >>> case_insensitive_sort(l)
       ['ABC', 'abc', 'BCD', 'bcd']

    """
    return sorted(string_list, key=str.lower)

import operator

def sort_by_attr(seq, attr):
    """returns seq sorted by attr
       >>> b1 = Bunch(key = 'a', value = 'value2')
       >>> b2 = Bunch(key = 'b', value = 'value2')
       >>> b3 = Bunch(key = 'c', value = 'value2')
       >>> t = (b3, b1, b2)
       >>> l = sort_by_attr(t, 'key')

expect l to be list of Bunch sorted already
       >>> l[0] == b1
       True
       >>> l[1] == b2
       True
       >>> l[2] == b3
       True
    """
    return sorted(seq, key=operator.attrgetter(attr))


def _sorted_keys(container, keys, reverse = False):
    ''' return list of 'keys' sorted by corresponding values in 'container' '''
    sorted_keys = sorted(keys, key=container.__getitem__, reverse=reverse)
    return [(container[k], k) for k in sorted_keys]

class hist(dict):
    def add(self, item, increment=1):
        ''' add 'increment' to the entry for 'item' '''
        self[item] = increment + self.get(item, 0)
    def counts(self, reverse=False):
        ''' return list of keys sorted by corresponding values '''
        return _sorted_keys(self, self, reverse)

class hist1(list):
    def __init__(self, n):
        ''' initialize this list to count occurrences of n distinct items '''
        list.__init__(self, n*[0])
    def add(self, item, increment=1):
        ''' add 'increment' to the entry for 'item' '''
        self[item] += increment
    def counts(self, reverse=False):
        ''' return list of indices sorted by corresponding values '''
        return _sorted_keys(self, range(len(self)), reverse)

from operator import itemgetter
def dict_items_sorted_by_value(d, reverse=False):
    """
       >>> d = dict(fourth = 4, first = 1, third = 3, second = 2, fifth = 5)
       >>> dict_items_sorted_by_value(d)
       [('first', 1), ('second', 2), ('third', 3), ('fourth', 4), ('fifth', 5)]
    """
    return sorted(iter(d.items()), key=itemgetter(1), reverse=reverse)

re_digits = re.compile(r'(\d+)')
def embedded_numbers(s):
    pieces = re_digits.split(s)             # split into digits/nondigits
    pieces[1::2] = list(map(int, pieces[1::2]))   # turn digits into numbers
    return pieces

def sort_strings_with_embedded_numbers(alist):
    """
       >>> files = 'file3.txt file11.txt file7.txt file4.txt file15.txt'.split()
       >>> print ' '.join(sort_strings_with_embedded_numbers(files))
       file3.txt file4.txt file7.txt file11.txt file15.txt
    """
    return sorted(alist, key=embedded_numbers)

def process_list_in_random_order(data, process):
    # first, put the whole list into random order
    random.shuffle(data)
    # next, just walk over the list linearly
    for elem in data: process(elem)

def smallest(n, data):
    """
       >>> t = (5, 6, 1, 2, 3, 4, 7, 8)
       >>> smallest(3, t)
       [1, 2, 3]
    """
    return heapq.nsmallest(n, data)

def largest(n, data):
    """
       >>> t = (5, 6, 1, 2, 3, 4, 7, 8)
       >>> largest(3, t)
       [8, 7, 6]
    """
    return heapq.nlargest(n, data)

import bisect
def in_sequence(haystack, needle):
    """Returns whether needle in haystack
       haystack is a sequence
       needle is value to look for

       >>> h = list(xrange(10000))
       >>> n = 9
       >>> in_sequence(h, n)
       True
       >>> n = 10000
       >>> in_sequence(h, n)
       False

       >>> h = tuple(xrange(10000))
       >>> n = 9
       >>> in_sequence(h, n)
       True
       >>> n = 10000
       >>> in_sequence(h, n)
       False

    """
    if not isinstance(haystack, list):
        haystack = list(haystack)
    haystack.sort()
    needle_insert_point = bisect.bisect_right(haystack, needle)
    needle_is_present = haystack[needle_insert_point-1:needle_insert_point] == [needle]
    return needle_is_present

def select_n_rank_element(data, n):
    """Find the nth rank ordered element (the least value has rank 0).
       >>> l = list(10000 - x for x in xrange(10000))
       >>> select_n_rank_element(l, 5)
       6
       >>> l[5] == select_n_rank_element(l, 5)
       False
    """
    # make a new list, deal with <0 indices, check for valid index
    data = list(data)
    if n<0:
        n += len(data)
    if not 0 <= n < len(data):
        raise ValueError("can't get rank %d out of %d" % (n, len(data)))
    # main loop, quicksort-like but with no need for recursion
    while True:
        pivot = random.choice(data)
        pcount = 0
        under, over = [], []
        uappend, oappend = under.append, over.append
        for elem in data:
            if elem < pivot:
                uappend(elem)
            elif elem > pivot:
                oappend(elem)
            else:
                pcount += 1
        numunder = len(under)
        if n < numunder:
            data = under
        elif n < numunder + pcount:
            return pivot
        else:
            data = over
            n -= numunder + pcount


def find_pattern_positions(text, pattern):
    """ Yields all starting positions of copies of subsequence 'pattern'
        in sequence 'text' -- each argument can be any iterable.
        At the time of each yield, 'text' has been read exactly up to and
        including the match with 'pattern' that is causing the yield.

        >>> t = 'this that this that this that'
        >>> p = 'this'
        >>> for pos in find_pattern_positions(t, p): print pos
        0
        10
        20

    """
    if is_string(text) and is_string(pattern):
        pos = -1
        while True:
            pos = text.find(pattern, pos+1)
            if pos < 0: break
            yield pos
    else:
        # KnuthMorrisPratt
        # ensure we can index into pattern, and also make a copy to protect
        # against changes to 'pattern' while we're suspended by `yield'
        pattern = list(pattern)
        length = len(pattern)
        # build the KMP "table of shift amounts" and name it 'shifts'
        shifts = [1] * (length + 1)
        shift = 1
        for pos, pat in enumerate(pattern):
            while shift <= pos and pat != pattern[pos-shift]:
                shift += shifts[pos-shift]
            shifts[pos+1] = shift
        # perform the actual search
        startPos = 0
        matchLen = 0
        for c in text:
            while matchLen == length or matchLen >= 0 and pattern[matchLen] != c:
                startPos += shifts[matchLen]
                matchLen -= shifts[matchLen]
            matchLen += 1
            if matchLen == length:
                yield startPos

def groupnames(name_iterable):
    """returns groups of names indexed by the first initial of last name
       >>> names = ['peter lim', 'peter tan', 'david siew', 'hock chuan tan']
       >>> d = groupnames(names)
       >>> expected_d = {'l': ('peter lim',), \
               's': ('david siew',), \
               't': ('hock chuan tan', 'peter tan')}
       >>> d == expected_d
       True

       did not just print out the expected result because in doctest, the
       returned d is not sorted on key, while when run from prompt, it is
       sorted on key
    """
    sorted_names = sorted(name_iterable, key=_sortkeyfunc)
    name_dict = {}
    for key, group in itertools.groupby(sorted_names, _groupkeyfunc):
        name_dict[key] = tuple(group)
    return name_dict
pieces_order = { 2: (-1, 0), 3: (-1, 0, 1) }
def _sortkeyfunc(name):
    ''' name is a string with first and last names, and an optional middle
        name or initial, separated by spaces; returns a string in order
        last-first-middle, as wanted for sorting purposes. '''
    name_parts = name.split()
    return ' '.join([name_parts[n] for n in pieces_order[len(name_parts)]])
def _groupkeyfunc(name):
    ''' returns the key for grouping, i.e. the last name's initial. '''
    return name.split()[-1][0]


# use operator.itemgetter if we're in 2.4, roll our own if we're in 2.3
try:
    from operator import itemgetter
except ImportError:
    def itemgetter(i):
        def getter(self): return self[i]
        return getter

def superTuple(typename, *attribute_names):
    """ create and return a subclass of `tuple', with named attributes
        >>> Point = superTuple('Point', 'x', 'y')
        >>> p = Point(1, 2)
        >>> p.x, p.y
        (1, 2)
        >>> Item = superTuple('Item', 'quantity', 'price', 'description')
        >>> i = Item(10, 2.50, 'sample item')
        >>> i.quantity, i.price, i.description
        (10, 2.5, 'sample item')

Cannot change tuple
        >>> i.quantity = 20
        Traceback (most recent call last):
        ...
        AttributeError: can't set attribute
    """
    # make the subclass with appropriate __new__ and __repr__ specials
    nargs = len(attribute_names)
    class supertup(tuple):
        __slots__ = ()         # save memory, we don't need per-instance dict
        def __new__(cls, *args):
            if len(args) != nargs:
                raise TypeError('%s takes exactly %d arguments (%d given)' % (
                                  typename, nargs, len(args)))
            return tuple.__new__(cls, args)
        def __repr__(self):
            return '%s(%s)' % (typename, ', '.join(map(repr, self)))
    # add a few key touches to our new subclass of `tuple'
    for index, attr_name in enumerate(attribute_names):
        setattr(supertup, attr_name, property(itemgetter(index)))
    supertup.__name__ = typename
    return supertup

def xproperty(fget, fset, fdel=None, doc=None):
    """ like property, except fget or fset can be a string which will then
        be the attribute

       >>> class Lower(object):
       ...     def __init__(self, s=''):
       ...         self.s = s
       ...     def _setS(self, s):
       ...         self._s = s.lower()
       ...     s = xproperty('_s', _setS)
       ...
       >>> c = Lower()
       >>> c.s = 'test String'
       >>> c.s
       'test string'
       >>> cc = Lower('String Lower')
       >>> cc.s
       'string lower'

    """
    if isinstance(fget, str):
        attr_name = fget
        def fget(obj): return getattr(obj, attr_name)
    elif isinstance(fset, str):
        attr_name = fset
        def fset(obj, val): setattr(obj, attr_name, val)
    else:
        raise TypeError('either fget or fset must be a str')
    return property(fget, fset, fdel, doc)


import sys, traceback
traceOutput = sys.stdout
watchOutput = sys.stdout
rawOutput = sys.stdout
# calling 'watch(secretOfUniverse)' prints out something like:
# File "trace.py", line 57, in __testTrace
#    secretOfUniverse <int> = 42
watch_format = ('File "%(fileName)s", line %(lineNumber)d, in'
                ' %(methodName)s\n   %(varName)s <%(varType)s>'
                ' = %(value)s\n\n')

def watch(variableName):
    if __debug__:
        stack = traceback.extract_stack()[-2:][0]
        actualCall = stack[3]
        if actualCall is None:
            actualCall = "watch([unknown])"
        left = actualCall.find('(')
        right = actualCall.rfind(')')
        paramDict = dict(varName=actualCall[left+1:right].strip(),
                         varType=str(type(variableName))[7:-2],
                         value=repr(variableName),
                         methodName=stack[2],
                         lineNumber=stack[1],
                         fileName=stack[0])
        watchOutput.write(watch_format % paramDict)
# calling 'trace("this line was executed")' prints out something like:
# File "trace.py", line 64, in ?
#    this line was executed
trace_format = ('File "%(fileName)s", line %(lineNumber)d, in'
                ' %(methodName)s\n   %(text)s\n\n')

def trace(text):
    if __debug__:
        stack = traceback.extract_stack()[-2:][0]
        paramDict = dict(text=text,
                         methodName=stack[2],
                         lineNumber=stack[1],
                         fileName=stack[0])
        watchOutput.write(trace_format % paramDict)

# calling 'raw("some raw text")' prints out something like:
# Just some raw text
def raw(text):
    if __debug__:
        rawOutput.write(text)

def print_exc_plus():
    """ Print the usual traceback information, followed by a listing of
        all the local variables in each frame.
    """
    tb = sys.exc_info()[2]
    while tb.tb_next:
        tb = tb.tb_next
    stack = []
    f = tb.tb_frame
    while f:
        stack.append(f)
        f = f.f_back
    stack.reverse()
    traceback.print_exc()
    print("Locals by frame, innermost last")
    for frame in stack:
        print()
        print("Frame %s in %s at line %s" % (frame.f_code.co_name,
                                             frame.f_code.co_filename,
                                             frame.f_lineno))
        for key, value in list(frame.f_locals.items()):
            print("\t%20s = " % key, end=' ')
            # we must _absolutely_ avoid propagating exceptions, and str(value)
            # COULD cause any exception, so we MUST catch any...:
            try:
                print(value)
            except:
                print("<ERROR WHILE PRINTING VALUE>")


import types
class TestException(Exception): pass
def microtest(modulename, verbose=None, log=sys.stdout, testmethod='_test'):
    ''' Execute all functions in the named module which have testmethod
        in their name and take no arguments.
    modulename:  name of the module to be tested.
    verbose:     If true, print test names as they are executed
    Returns None on success, raises exception on failure.
    '''
    module = __import__(modulename)
    total_tested = 0
    total_failed = 0
    for name in dir(module):
        if testmethod in name:
            obj = getattr(module, name)
            if (isinstance(obj, types.FunctionType) and
                not obj.__code__.co_argcount):
                if verbose:
                    print('Testing %s' % name, file=log)
                try:
                    total_tested += 1
                    obj()
                except Exception as e:
                    total_failed += 1
                    print('%s.%s FAILED' % (modulename, name), file=sys.stderr)
                    traceback.print_exc()
    message = 'Module %s failed %s out of %s unittests.' % (
               modulename, total_failed, total_tested)
    if total_failed:
        raise TestException(message)
    if verbose:
        print(message, file=log)

def pretest(modulename, force=False, deleteOnFail=False,
            runner=microtest, verbose=False, log=sys.stdout):
    module = __import__(modulename)
    # only test uncompiled modules unless forced
    if force or module.__file__.endswith('.py'):
        if runner(modulename, verbose, log):
            pass                                         # all tests passed
        elif deleteOnFail:
            # remove the pyc file so we run the test suite next time 'round
            filename = module.__file__
            if filename.endswith('.py'):
                filename = filename + 'c'
            try:
                os.remove(filename)
            except OSError:
                pass

def fibonacci():
    ''' Unbounded generator for Fibonacci numbers
        >>> list(itertools.islice(fibonacci(), 5))
        [0, 1, 1, 2, 3]
    '''
    x, y = 0, 1
    while True:
        yield x
        x, y = y, x + y

def peel(iterable, arg_cnt=1):
    """ Yield each of the first arg_cnt items of the iterable, then
        finally an iterator for the rest of the iterable.
        >>> t = range(1, 6)
        >>> a, b, c = peel(t, 2)
        >>> print a, b, list(c)
        1 2 [3, 4, 5]

    """
    iterator = iter(iterable)
    for num in range(arg_cnt):
        yield next(iterator)
    yield iterator

def strider(p, n):
    """ Split an iterable p into a list of n sublists, repeatedly taking
        the next element of p and adding it to the next sublist.  Example:
        >>> strider('abcde', 3)
        [['a', 'd'], ['b', 'e'], ['c']]

        In other words, strider's result is equal to:
            [list(p[i::n]) for i in xrange(n)]
        if iterabele p is a sequence supporting extended-slicing syntax.
    """
    # First, prepare the result, a list of n separate lists
    result = [ [] for x in range(n) ]
    # Loop over the input, appending each item to one of
    # result's lists, in "round robin" fashion
    for i, item in enumerate(p):
        result[i % n].append(item)
    return result

def average(sequence):
    """
       >>> l = [1, 2, 3]
       >>> average(l)
       2.0
    """
    return sum(sequence)/float(len(sequence))

def windows(iterable, length=2, overlap=0):
    """
       >>> seq = "foobarbazer"
       >>> t = tuple(windows(seq, 6, 1))
       >>> t
       (['f', 'o', 'o', 'b', 'a', 'r'], ['r', 'b', 'a', 'z', 'e', 'r'], ['r'])
    """
    it = iter(iterable)
    results = list(itertools.islice(it, length))
    while len(results) == length:
        yield results
        results = results[length-overlap:]
        results.extend(itertools.islice(it, length-overlap))
    if results:
        yield results

def attributesFromArguments(d):
    """ initializes instance variables from __init__ arguments
    """
    self = d.pop('self')
    try:
        # to handle aspect wrapped functions
        codeObject = self.__init__.original.__func__.__code__
    except AttributeError as e:
        codeObject = self.__init__.__func__.__code__
    argumentNames = codeObject.co_varnames[1:codeObject.co_argcount]
    for n in argumentNames:
        setattr(self, n, d[n])


import copy
def freshdefaults(f):
    "a decorator to wrap f and keep its default values fresh between calls"
    fdefaults = f.__defaults__
    def refresher(*args, **kwds):
        f.__defaults__ = copy.deepcopy(fdefaults)
        return f(*args, **kwds)
    # in 2.4, only: refresher.__name__ = f.__name__
    return refresher

def get_divided_round_lot(whole, lots_count):
    """ Returns lots_count of lots
        each lot comprises rounded up count
        all lots except for the last have the same count
        the last lot has the least count
        >>> l = get_divided_round_lot(10, 3)
        >>> l
        4
    """
    zd.f('get_divided_round_lot+')
    remainder = whole % lots_count
    lot = (whole + lots_count - remainder) / lots_count
    zd.f('get_divided_round_lot-')
    return lot

import inspect
def wrapfunc(obj, name, processor, avoid_doublewrap=True):
    """ patch obj.<name> so that calling it actually calls, instead,
            processor(original_callable, *args, **kwargs)
    """
    # get the callable at obj.<name>
    call = getattr(obj, name)
    # optionally avoid multiple identical wrappings
    if avoid_doublewrap and getattr(call, 'processor', None) is processor:
        return
    # get underlying function (if any), and anyway def the wrapper closure
    original_callable = getattr(call, 'im_func', call)
    def wrappedfunc(*args, **kwargs):
        return processor(original_callable, *args, **kwargs)
    # set attributes, for future unwrapping and to avoid double-wrapping
    wrappedfunc.original = call
    wrappedfunc.processor = processor
    # 2.4 only: wrappedfunc.__name__ = getattr(call, '__name__', name)
    # rewrap staticmethod and classmethod specifically (iff obj is a class)
    if inspect.isclass(obj):
        if hasattr(call, 'im_self'):
            if call.__self__:
                wrappedfunc = classmethod(wrappedfunc)
        else:
            wrappedfunc = staticmethod(wrappedfunc)
    # finally, install the wrapper closure as requested
    setattr(obj, name, wrappedfunc)
def unwrapfunc(obj, name):
    ''' undo the effects of wrapfunc(obj, name, processor) '''
    setattr(obj, name, getattr(obj, name).original)

def tracing_processor(original_callable, *args, **kwargs):
    r_name = getattr(original_callable, '__name__', '<unknown>')
    r_args = list(map(repr, args))
    r_args.extend(['%s=%r' % x for x in kwargs.items()])
    print("begin call to %s(%s)" % (r_name, ", ".join(r_args)))
    try:
        result = original_callable(*args, **kwargs)
    except:
        print("EXCEPTION in call to %s" %(r_name,))
        raise
    else:
        print("call to %s result: %r" %(r_name, result))
        return result
def add_tracing_prints_to_method(class_object, method_name):
    wrapfunc(class_object, method_name, tracing_processor)

def add_tracing_prints_to_all_methods(class_object):
    for method_name, v in inspect.getmembers(class_object, inspect.ismethod):
        add_tracing_prints_to_method(class_object, method_name)

def all_descendants(class_object, _memo=None):
    if _memo is None:
        _memo = {}
    elif class_object in _memo:
        return
    _memo[class_object] = None
    yield class_object
    for subclass in class_object.__subclasses__():
        for descendant in all_descendants(subclass, _memo):
            _memo[descendant] = None
            yield descendant

def add_tracing_prints_to_all_descendants(class_object):
    for c in all_descendants(class_object):
        add_tracing_prints_to_all_methods(c)

def ifNone(variable, valueIfNone=None):
    """ Returns valueIfNone if variable is None
        >>> t = ifNone(None, "oh")
        >>> t
        'oh'
    """
    if variable is None:
        return valueIfNone
    else:
        return variable

def expovariateRange(rate, iterations=1000):
    """ Returns range of expovariate random values
    """
    from SimPy.Simulation import Monitor
    from random import expovariate
    monitor = Monitor()
    for i in range(iterations):
        r = expovariate(rate)
        monitor.observe(r)

    print(('mean = %s' % monitor.mean()))
    values = monitor.yseries()
    maxValue = max(values)
    minValue = min(values)
    print(('max=%s, min=%s' % (maxValue, minValue)))
    return values

def confirm_proceed(prompt):
    i = input(prompt + ' [y/n] ')
    if not i.startswith('y'):
        print("y not pressed, aborting...", file=sys.stderr)
        sys.exit(1)

def confirm(prompt=None, resp=False):
    """prompts for yes or no response from the user. Returns True for yes and
    False for no.

    'resp' should be set to the default value assumed by the caller when
    user simply types ENTER.


    """

    if prompt is None:
        prompt = 'Confirm'

    if resp:
        prompt = '%s [%s]|%s: ' % (prompt, 'y', 'n')
    else:
        prompt = '%s [%s]|%s: ' % (prompt, 'n', 'y')

    while True:
        ans = input(prompt)
        if not ans:
            return resp
        if ans not in ['y', 'Y', 'n', 'N']:
            print('please enter y or n.')
            continue
        if ans == 'y' or ans == 'Y':
            return True
        if ans == 'n' or ans == 'N':
            return False

def append_to_list(long_list, item, unique_only):
    skip = item in long_list and unique_only

    if not skip:
        long_list.append(item)

def _test():
    import doctest
    zd.output_to_stdout = False
    doctest.testmod(optionflags=doctest.ELLIPSIS + doctest.NORMALIZE_WHITESPACE)
    doctest.master.summarize(True)

    import sys
    sys.stdout.write('completed doctest')


def remove_ending_punctuation_marks(a_string, punctuation_marks='\W'):
    ''' Returns a_string with ending punctuation marks removed

        punctuation_marks is regex pattern specification

    >>> remove_ending_punctuation_marks('abc.,?')
    'abc'
    >>> remove_ending_punctuation_marks('abcd')
    'abcd'
    >>> remove_ending_punctuation_marks(123)
    123
    '''

    try:
        return re.sub('{0}+$'.format(punctuation_marks), '', a_string)
    except Exception as e:
        return a_string


def throws(t, f, *a, **k):
    '''Return True iff f(*a, **k) raises an exception whose type is t
      (or, one of the items of _tuple_ t, if t is a tuple).'''
    try:
        f(*a, **k)
    except t:
        return True
    else:
        return False

def rev_range(*args):
    """Create a reversed range.

    eg rev_range(0, 10, 1)
    returns 9 to 0

    Equivalent to reversed(list(range(*args))), but more efficient.

    This does some simple math on the arguments instead of creating an
    intermediate list and reversing it, thus automating a simple but
    error-prone optimization often done by programmers.
    """
    # Before Python 3.0, range creates a list while xrange is an efficient
    # iterator. From 3.0 onwards, range does what xrange did earlier (and
    # xrange is gone).
    import sys
    if sys.version < "3":
        range = xrange

    if len(args) == 1:
        # start = 0, stop = args[0], step = 1
        return list(range(args[0]-1, -1, -1))

    # Unpack arguments, setting 'step' to 1 if it is not given.
    start, stop, step = (args + (1,))[:3]

    # The new 'stop' is the first item of the original range plus/minus one,
    # depending on the step's sign. Specifically:
    #   new_stop = start - (1 if step > 0 else -1)

    # The new 'start' is the last item of the original range, which is
    # between one and 'step' less than the original 'stop'. Specifically:
    #
    # * If 'stop' minus 'start' divides by 'step' then the last item of the
    #   original range is 'stop' minus 'step'.
    # * If 'stop' minus 'start' doesn't divide by 'step', then the last item of
    #   the original range is 'stop' minus the remainder of this division.
    #
    # A single expression accounts for both cases is:
    #   new_start = stop - ((stop-start-1) % step + 1)
    return list(range(stop - ((stop-start-1) % step + 1),
                 start - (1 if step > 0 else -1),
                 -step))

def round_down(a_value, digits_after_decimal_point):
    ''' Returns None

    -- doctests ----

    >>> round_down(123, -2)
    100.0
    >>> round_down(153, -2)
    100.0

    '''
    zd.f('round_down+')
    result = round(a_value, digits_after_decimal_point)
    if result > a_value:
        result = result - 10 ** -digits_after_decimal_point

    zd.f('round_down-')
    return result



def round_up(a_value, digits_after_decimal_point):
    ''' Returns None

    -- doctests ----

    >>> round_up(123, -2)
    200.0
    >>> round_up(153, -2)
    200.0

    '''
    zd.f('round_up+')
    result = round(a_value, digits_after_decimal_point)
    if result < a_value:
        result = result + 10 ** -digits_after_decimal_point

    zd.f('round_up-')
    return result


def round_to_multiple_of(x, to):
    '''returns x rounded to nearest multiple of to

    >>> round_to_multiple_of(14, 3)
    15.0
    >>> round_to_multiple_of(3500, 5000)
    5000.0
    '''
    div = x / (to + 0.0)
    multiple = round(div)
    return to * multiple

def smart_str(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Returns a bytestring version of 's', encoded as specified in 'encoding'.
    If strings_only is True, don't convert (some) non-string-like objects.

    adapted from  http://code.djangoproject.com/browser/django/trunk/django/utils/encoding.py
    """
    if is_iterable(s):
        l = []
        for _s in s:
            l.append(smart_str(_s))
#         dprint('point 1')
        return str(l)
    if strings_only and isinstance(s, (type(None), int)):
        #  dprint('point 2')
        return s
    if not isinstance(s, str):
        try:
            #  dprint('point 3')
            return str(s)
        except UnicodeEncodeError:
            if isinstance(s, Exception):
                # An Exception subclass containing non-ASCII data that doesn't
                # know how to print itself properly. We shouldn't raise a
                # further exception.

                #  dprint('point 4')
                return ' '.join([smart_str(arg, encoding, strings_only,
                        errors) for arg in s])

            #  dprint('point 5')
            return str(s).encode(encoding, errors)
    elif isinstance(s, str):
#         dprint('point 6')
#         return s.encode(encoding, errors)
        return s
    elif s and encoding != 'utf-8':

        #  dprint('point 7')
        return s.decode('utf-8', errors).encode(encoding, errors)
    else:

        #  dprint('point 8')
        return s

def split_uppercase(s):
    r = []
    l = False
    for c in s:
        # l being: last character was not uppercase
        if l and c.isupper():
            r.append(' ')
        l = not c.isupper()
        r.append(c)
    return ''.join(r)

def is_integer(i):
    ''' Returns whether i is integer or not

    -- doctests ----

    >>> is_integer("123")
    False
    >>> is_integer(123)
    True
    >>> is_integer(123.1)
    False
    '''
    result = False

    try:
        ii = int(i)
    except Exception as e:
        return result

    result = ii == i
    return result

def to_number(i, return_original_if_not_number = False):
    _i = str(i)
    _i = _i.replace(',', '')
    try:
        return int(i)
    except Exception as e:
        pass

    try:
        return float(i)
    except Exception as e:
        pass

    if return_original_if_not_number:
        return i
    return None


def to_int(i, return_original_if_not_number = False):
    _i = str(i)
    _i = _i.replace(',', '')

    try:
        return int(_i)
    except Exception as e:
        pass

    if return_original_if_not_number:
        return i
    return None

def to_float(i, return_original_if_not_number = False):
    _i = str(i)
    _i = _i.replace(',', '')

    try:
        return float(_i)
    except Exception as e:
        pass

    if return_original_if_not_number:
        return i
    return None

def cross_join(l, ll):
    ''' Returns a generator where every member of l is
    paired with every member of ll
    '''

    for _l in l:
        for _ll in ll:
            yield _l, _ll

def hyphen_range(s):
    """ Takes a range in form of "a-b" and generate a list of numbers between a and b inclusive.
    Also accepts comma separated ranges like "a-b,c-d,f" will build a list which will include
    Numbers from a to b, a to d and f"""
    s="".join(s.split())#removes white space
    r=set()
    for x in s.split(','):
        t=x.split('-')
        if len(t) not in [1,2]: raise SyntaxError("hash_range is given its arguement as "+s+" which seems not correctly formated.")
        r.add(int(t[0])) if len(t)==1 else r.update(set(range(int(t[0]),int(t[1])+1)))
    l=list(r)
    l.sort()
    return l

def get_iterator_count(it):
    ''' Returns None
    '''
    try:
        i = len(it)
        return i
    except TypeError as e:
        # it has no len
        pass


    i = 0
    for _it in it:
        i += 1
    return i

def cache(func):
    saved = {}
    @functools.wraps(func)
    def newfunc(*args):
        if args in saved:
            return newfunc(*args)
        result = func(*args)
        saved[args] = result
        return result
    return newfunc


def memoize(fn):
    memo = {}
    def memoizer(*param_tuple, **kwds_dict):
        # can't memoize if there are any named arguments
        if kwds_dict:
            return fn(*param_tuple, **kwds_dict)
        try:
            # try using the memo dict, or else update it
            try:
                return memo[param_tuple]
            except KeyError:
                memo[param_tuple] = result = fn(*param_tuple)
                return result
        except TypeError:
            # some mutable arguments, bypass memoizing
            return fn(*param_tuple)
    # 2.4 only: memoizer.__name__ = fn.__name__
    return memoizer

if __name__ == "__main__":
    _test()
