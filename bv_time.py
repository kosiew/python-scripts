
# ##filename=bv_time.py, edited on 25 Feb 2018 Sun 06:59 PM
# filename=bv_time.py, edited on 19 Sep 2016 Mon 10:47 AM

__author__ = "Siew Kam Onn"
__email__ = "kosiew at gmail.com"
__version__ = "$Revision: 1.0 $"
__date__ = "$Date: 26-08-2009 9:47:43 AM $"
__copyright__ = "Copyright (c) 2006 Siew Kam Onn"
__license__ = "Python"

"""
    This module contains time related functions

"""

import zd
import aspect
import time
# must not import bv_date because bv_date import bv_error and it will import
#   bv_time
# import bv_date
import bv_stack
import datetime
import u
import a
import sys
import textwrap
from _base import Timer, get_lap_seconds

timer = False
suppress_print = False
last_timestamp = None
STAR = ' *'
MAX_STAR_MESSAGE_LENGTH = 75




def start():
    """ Returns None
            docstring for start
    """
    global timer
    if not timer:
        timer = Timer()
    timer.start()
    return timer

##@aspect.processedby(aspect.tracing_processor)
def get_elapsed_minutes():
    """ Returns True if
            docstring
    """
    global timer
    return timer.get_elapsed_minutes()

##@aspect.processedby(aspect.tracing_processor)
def print_elapsed_time(message=None):
    """ Returns None
            prints elapsed time
    """
    global timer

    return timer.print_elapsed_time(message)

def print_timing(func):
    '''Returns duration of func

       source:http://www.daniweb.com/code/snippet368.html
    '''

    def wrapper(*arg):
        print_running_message()
        t1 = time.time()
        res = func(*arg)
        t2 = time.time()
        func_name = func.__name__
        if func_name == 'wrappedfunc':
            func_name = ''

        minutes = (t2-t1)*1.0/60
        number = minutes
        unit = 'minutes'

        if minutes < 1:
            number = minutes * 60
            unit = 'seconds'

        message = '\n%s completed in %0.3f %s' % (func_name, number, unit)

        sys.stdout.write("\r" + message + ' ' * 80 + "\r")
        sys.stdout.flush()

        return res
    return wrapper


##@aspect.processedby(aspect.tracing_processor)
def print_running_message():
    """ Returns running message
    """
    s = bv_stack.Stack()
    script_name = s.caller()

    message = '{0} running..'.format(script_name)

    return print_message(message)

##@aspect.processedby(aspect.tracing_processor)
def get_timestamp():
    """ Returns timestamp for this second
    """
    _result = time.strftime('%H%M%S')
    result = '{0}_{1}'.format(get_datestamp(), _result)
    return result

##@aspect.processedby(aspect.tracing_processor)
def get_datestamp(date=None):
    """ Returns date stamp
    """
    pattern = '%Y%m%d'
    if date is None:
        result = time.strftime(pattern)
    else:
        result = u.today().strftime(pattern)
    return result

##@aspect.processedby(aspect.tracing_processor)
def get_datetime_stamp(date = None):
    """
    """
    pattern = '%Y%m%d %H%M%S'
    if date is None:
        result = time.strftime(pattern)
    else:
        result = u.today().strftime(pattern)
    return result

def _get_starred_message_old(message):
    """
        Returns a starred message
    >>> message = 'abcd'
    >>> get_starred_message(message)
    ' * * * * *\\n * abcd  *\\n * * * * *\\n'
    >>> message = 'abcde'
    >>> get_starred_message(message)
    ' * * * * *\\n * abcde *\\n * * * * *\\n'

    """
    global STAR
    star = STAR
    _message = '{0} {1} '.format(star, message)
    message_length = len(_message)
    even_message_length = message_length % 2 == 0
    if even_message_length:
        star_count = message_length/2 + 1
    else:
        star_count = (message_length + 1)/2

    prefix = star * star_count
    end_star = prefix[message_length:]
    suffix = prefix
    result = '\n{0}\n{1}{2}\n{3}\n\n'.format(prefix, _message,
        end_star, suffix)
    return result

def _get_starred_line(line, length, prefix):
    global STAR
    star = STAR
    _line = line.ljust(length-len(star)-2)
    _line = '{0} {1} '.format(star, _line)

    end_star = prefix[length:]
    result = '{0}{1}'.format(_line, end_star)
    return result


def get_starred_lines(_lines, line_length, prefix):
    lines = []
    for _line in _lines:
        line = _get_starred_line(_line, line_length, prefix)
        lines.append(line)
    return lines

def get_starred_message(message):
    """
        Returns a starred message
    >>> message = 'abcd'
    >>> get_starred_message(message)
    ' * * * * *\\n * abcd  *\\n * * * * *\\n'
    >>> message = 'abcde'
    >>> get_starred_message(message)
    ' * * * * *\\n * abcde *\\n * * * * *\\n'

    """
    global STAR
    global MAX_STAR_MESSAGE_LENGTH

    star = STAR

    if len(message) >= MAX_STAR_MESSAGE_LENGTH:
        line_length = MAX_STAR_MESSAGE_LENGTH + len(star) + 2

        _lines = textwrap.wrap(message, MAX_STAR_MESSAGE_LENGTH)
    else:
        _line = '{0} {1} '.format(star, message)
        line_length = len(_line)
        _lines = [message]

    even_message_length = line_length % 2 == 0
    if even_message_length:
        star_count = line_length/2 + 1
    else:
        star_count = (line_length + 1)/2

    star_count = int(star_count)
    prefix = star * star_count
    end_star = prefix[line_length:]
    suffix = prefix

    _lines = get_starred_lines(_lines, line_length, prefix)


    lines = '\n'.join(_lines)

    result = '\n{0}\n{1}\n{2}\n\n'.format(prefix, lines, suffix)
    return result

##@aspect.processedby(aspect.tracing_processor)
def get_timestamped_message(message):
    """
    """
    global last_timestamp

    timestamp = time.strftime("%a, %d %b %Y %H:%M:%S")
    result = message
    if last_timestamp != timestamp:
        last_timestamp = timestamp
        _timestamp = 'TIMESTAMP: {0}'.format(timestamp)
        _timestamp = get_starred_message(_timestamp)

        result = '{0}{1}'.format(_timestamp, result)

    return result, timestamp

def print_blank_line():
    """
    """
    print('\n')

##@aspect.processedby(aspect.tracing_processor)
def print_message(message, with_time_stamp = True, starred = False):
    """ Returns timestamp
    """
    global suppress_print

    if u.is_iterable(message):
        print_blank_line()
        for _message in message:
            print_message(_message, with_time_stamp)
        print_blank_line()
    else:
        _message = message
        timestamp = None
        if starred:
            _message = get_starred_message(_message)
        if with_time_stamp:
            _message, timestamp = get_timestamped_message(_message)

        if not suppress_print:
            print(_message)

        return timestamp


def assert_datelike(dt):
    a.assert_true(isinstance(dt, (datetime.datetime, datetime.date)),
                    f'{dt} is not date or datetime')


##@aspect.processedby(aspect.tracing_processor)
def add_hours(hours, dt = None):
    """Returns dt + hours
    """
    if dt is None:
        dt = u.now()

    assert_datelike(dt)
    result = dt + datetime.timedelta(hours=hours)

    return result


##@aspect.processedby(aspect.tracing_processor)
def add_minutes(minutes, dt = None):
    """Returns dt + minutes
    """
    if dt is None:
        dt = u.now()
    assert_datelike(dt)
    result = dt + datetime.timedelta(minutes=minutes)

    return result

def _test():
    '''
    '''

#     zd.output_to_stdout = False
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS + doctest.NORMALIZE_WHITESPACE, verbose=True)
    doctest.master.summarize(True)


aspect.wrap_module(__name__)

if __name__=="__main__":
    _test()




