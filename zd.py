#!/usr/bin/env python2.3
# ##filename=zd.py, edited on 22 Oct 2020 Thu 10:21 PM
# filename=zd.py, edited on 13 Oct 2016 Thu 10:02 AM
"""
zd.py - A debugging utility

Help: ./zd.py --help
Author: Siew Kam Onn
License: GNU GPL 2
Date: 18-Feb-06 Sat 04:57:50 PM
"""

import logging
import logging.config
import yaml

import pickle
import sys
import _base
import tee

config_file = '_zd.yml'
ENCODING = 'utf-8'

# 15-Jun-16 Wed 10:09:28 AM
# so that program will always look for config file in the same
# directory of this program
config_file = _base.get_current_directory_file(config_file, __file__)
# debugfilename = "c:/1/python/debug.log"

init_log_file = False
debug = False

prefix = None

output_to_stdout = False

indent = 0

_config_file = open(config_file, 'r')
d_config = yaml.load(_config_file, Loader=yaml.FullLoader)
logging.config.dictConfig(d_config)

file_logger = logging.getLogger('file')
simple_stdout_logger = logging.getLogger('simple_stdout')
MAX_LINE_WIDTH = 80

# DEFAULT_TEE_FILE = 't.lst'
# tee_file = tee.Tee(DEFAULT_TEE_FILE)


def set_test_mode(test_mode = True):
    """
       set_test_mode to True to enable output to output_to_stdout
    """
    global output_to_stdout
    output_to_stdout = test_mode



def prefixed_message(message):
    """ Returns prefixed message
    """
    if prefix:
        prefixed_message = '[%s] %s' % (prefix, message)
    else:
        prefixed_message = message
    return prefixed_message

first_f = True

def indentation():
    global indent
    return ''.ljust(indent * 2)

def increment_indent(_indent=1):
    global indent
    indent += _indent

def decrement_indent(_indent=1):
    global indent
    indent -= _indent

def turn_on_logging_to_file():
    global init_log_file
    global debugfilename

    init_log_file = True

def output_to_stdout_logger(output):
    simple_stdout_logger.debug(output)

def format_messages_for_print(messages):

    if _base.is_iterable(messages):
        _messages = map(str, messages)
        _message = '\n'.join(_messages)
    else:
        _message = messages
    return _message

def get_formatted_message(messages):
    lap_seconds = _base.get_lap_seconds()
    _message = format_messages_for_print(messages)
    message = f'{lap_seconds} {_message}'
    return message

# print to stdoutput
def p(message, encoding=ENCODING):
    global MAX_LINE_WIDTH
    output = get_formatted_message(message)
    if len(output) > MAX_LINE_WIDTH:
        output = f'{output}\n'
    global first_f
    if first_f:
        print('\n'*3)
        first_f = False
    try:
        output_to_stdout_logger(output)
    except Exception as e:
        # encoding error
        output = output.encode(encoding)
        output_to_stdout_logger(output)

def f(message, this_indent = None, encoding=ENCODING):
    global indent
    global init_log_file
    global debug
    global file_logger
    global simple_stdout_logger

    if not message:
        return
    if not init_log_file and debug:
        turn_on_logging_to_file()
    this_indent = indent if this_indent is None else this_indent
    indent = this_indent
    this_message = '%s%s' % (indentation(), message)
    this_message = get_formatted_message(this_message)

    if init_log_file:
        file_logger.debug(prefixed_message(this_message))

    global output_to_stdout
    if output_to_stdout:
        p(message)



def warn(message):
    global simple_stdout_logger
    global init_log_file
    global file_logger

    simple_stdout_logger.warn(prefixed_message(message))
    if init_log_file:
        file_logger.warn(prefixed_message(message))

def dump(object):
    global debugfilename
    f = open(debugfilename, "a")
    pickle.dump(object, f)


