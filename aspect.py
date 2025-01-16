import inspect
# ##filename=aspect.py, edited on 22 May 2018 Tue 10:30 AM
# 24-Mar-18 Sat 07:05:01 PM
#   removed wrapt
#     reverted to 14 Mar 2017 version
import zd
import time
import sys

import pprint

# seconds
LONG_PROCESS_THRESHOLD = 10
LONG_PROCESS_THRESHOLD_SUFFIX = ' !! <== long process !!'

# import functools
debug = False
indent = 0
brief = True
brief_stop = 280
NOT_SO_BRIEF = 1000
stack = {}
COMMON_DEF = ('print_message', 'get_debug_information_message',
    'get_computer_name', 'get_script_name', 'sanitize_messages',
    'add_message', 'smart_extend', 'unique_emails',
    'mailing_list_process', 'process_cc', 'get_subject',
    'sendMail', 'get_mime', 'is_valid_email',
    'remove_redundant_sendees', 'attach_attachments',
    'is_calling_def', #'get'
    'to_omit',
    'get_smtp',
    'caller',
    'get_traceback_lines',
    'get_caller',
    'islink',)

EXCLUDED_CLASSES = ('MIMEMultipart',
  'MIMEText',
  'MIMEBase',
  'MIMENonMultipart',
  'OracleConnectionAlert'
  )

EXCLUDED_CLASS_METHODS = (
  '__eq__',
  '__ge__',
  '__gt__',
  '__hash__',
  '__le__',
  '__lt__',
  '__ne__',
  '__repr__',
)

_ASPECT = True
TRACED_CLASSES = []
previous_message = False
_silent_mode = False

def set_silent_mode(mode=True):
    global _silent_mode
    _silent_mode = mode
    return _silent_mode

def debug_print(message):
    """
    """
    if debug:
        print(message)

def f(message, indent=None):
    global _silent_mode
    if not _silent_mode:
        zd.f(message, indent)

class Error (Exception):
    """
        Error is a type of Exception
        Base class for all exception raised by this module
    """
    pass


def set_brief_stop(_brief_stop):
    global brief_stop
    brief_stop = _brief_stop

def set_brief(brief_flag = True):
    global brief
    brief = brief_flag

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

# so that doctest will pick up the docstring tests within
#     wrappedfunc.__doc__ = call.__doc__
#     wrappedfunc.__module__ = call.__module__

    # rewrap staticmethod and classmethod specifically (if obj is a class)
    if inspect.isclass(obj):
        if hasattr(call, 'im_self'):
            if call.__self__:
                wrappedfunc = classmethod(wrappedfunc)
        else:
            wrappedfunc = staticmethod(wrappedfunc)
    # finally, install the wrapper closure as requested
    debug_print('setattr {0} {1}'.format(obj, name))
    setattr(obj, name, wrappedfunc)

def get_r_args(args):
    try:
        r_args = list(map(repr, args))
    except Exception as e:
        r_args = [str(e)]
    return r_args

def simple_tracing_processor(obj, call, avoid_doublewrap=True):
    global COMMON_DEF

    if avoid_doublewrap and getattr(
            call, 'processor', None) is simple_tracing_processor:
        return

    original_callable = getattr(call, 'im_func', call)

    def result(*args, **kwargs):
        global indent
        r_name = getattr(call, '__name__', '<unknown>')
        r_args = get_r_args(args)
        r_args.extend(['%s=%r' % x for x in kwargs.items()])

        output = "%s{ (%s)" % (r_name, ", ".join(r_args[1:]))
        _output = get_brief_output(output)

        global previous_message
        if r_name in COMMON_DEF:
            message = '..{0}..'.format(r_name)
            if previous_message and previous_message == message:
                message = '..'
            else:
                previous_message = message
                f(message)
        else:
            f(_output, indent)
            previous_message = False
        indent += 1

        try:
            start = time.time()
            _result = call(*args, **kwargs)
            indent -= 1
        except Error as e:
            indent -= 1
            print_duration(start, r_name, indent)
            f("EXCEPTION in call to %s}" %(r_name,), indent)
            raise
        else:
            if r_name not in COMMON_DEF:
                print_duration(start, r_name, indent)
                try:
                    output = "%s} < result: %s>" %(r_name, repr(_result))
                except Error as e:
                    output = "%s} < result: !RESULT NOT STR-able!  >" %(r_name)

                _output = get_brief_output(output)
                f(_output, indent)
            return _result
    result.original = call
    result.processor = simple_tracing_processor
    result.class_name = obj.__name__
    return result

def simple_wrapfunc(obj, name, processor, avoid_doublewrap=True):
    """ patch obj.<name> so that calling it actually calls, instead,
            processor(original_callable, *args, **kwargs)
    """
    call = getattr(obj, name)

    debug_print('setattr {0} {1}'.format(obj, name))
    wrapfunc=processor(obj, call, avoid_doublewrap)

    setattr(obj, name, wrapfunc)

def unwrapfunc(obj, name):
    ''' undo the effects of wrapfunc(obj, name, processor) '''
    setattr(obj, name, getattr(obj, name).original)


def all_descendants(class_object, _memo=None):
    if _memo is None:
        _memo = {}
    elif class_object in _memo:
        return
    yield class_object
    for subclass in class_object.__subclasses__():
        for descendant in all_descendants(subclass, _memo):
            yield descendant


def get_brief_output(output):
    global brief
    if output and brief and len(output) > brief_stop:
        return '{0} ...'.format(output[:brief_stop])
    return output

def print_duration(start, def_name, indent,
        long_process_threshold=LONG_PROCESS_THRESHOLD):
    """ Returns None
    """
    end = time.time()
    duration = end - start

    if duration > 60:
        duration_string = '%0.3f minutes' % (duration * 1.0/60)

    else:
        duration_string = '%0.3f seconds' % (duration,)

    if duration > long_process_threshold:
        suffix = LONG_PROCESS_THRESHOLD_SUFFIX
    else:
        suffix = ''

    f('{0}:duration:{1}{2}'.format(def_name, duration_string,
        suffix), indent)


def tracing_processor(original_callable, *args, **kwargs):
    global indent
    global COMMON_DEF

    r_name = getattr(original_callable, '__name__', '<unknown>')

    r_args = list(map(repr, args))
#
    r_args.extend(['%s=%r' % x for x in kwargs.items()])
    output = "%s{ (%s)" % (r_name, ", ".join(r_args))
    _output = get_brief_output(output)


    global previous_message
    if r_name in COMMON_DEF:
        message = '..{0}..'.format(r_name)
        if previous_message and previous_message == message:
            message = '..'
        else:
            previous_message = message
            f(message)
    else:
        f(_output, indent)
        previous_message = False
    indent += 1
    try:
        start = time.time()
        result = original_callable(*args, **kwargs)
        indent -= 1
    except Error as e:
        indent -= 1
        print_duration(start, r_name, indent)
        f("EXCEPTION in call to %s}" %(r_name,), indent)
        raise
    else:
        if r_name not in COMMON_DEF:
            print_duration(start, r_name, indent)
            try:
                output = "%s} < result: %s>" %(r_name, repr(result))
            except Error as e:
                output = "%s} < result: !RESULT NOT STR-able!  >" %(r_name)

            _output = get_brief_output(output)
            f(_output, indent)
        return result




def add_tracing_prints_to_method(class_object, method_name):
#     wrapfunc(class_object, method_name, tracing_processor)

    simple_wrapfunc(class_object, method_name, simple_tracing_processor)

    debug_print('wrapped {0} {1}'.format(class_object, method_name))


def add_tracing_prints_to_all_methods(class_object):
    global EXCLUDED_CLASS_METHODS
    object_name = class_object.__name__
    debug_print('add_tracing_prints_to_all_methods: {0}'.format(
        object_name))
    if object_name not in EXCLUDED_CLASSES:
        global TRACED_CLASSES
        TRACED_CLASSES.append(object_name)
        debug_print('before inspect.getmembers')
        for key, v in class_object.__dict__.items():
            if hasattr(v, '__call__'):
#         for key, v in inspect.getmembers(class_object,
#                 inspect.isfunction):
                debug_print('evaluating {0}'.format(key))
                if key not in EXCLUDED_CLASS_METHODS:
                    add_tracing_prints_to_method(class_object, key)

def add_tracing_prints_to_all_descendants(class_object):
    for c in all_descendants(class_object):
        add_tracing_prints_to_all_methods(c)

def processedby(processor):
    """
        decorator to wrap the processor around a function.
        -- doctests ----

    >>> f = 'processedby'
    >>> f
    'processedby'

    """
#     @functools.wraps(processor)
    def processedfunc(func):
        """
            processedfunc
        """
        def wrappedfunc(*args, **kwargs):
            """wrappedfunc
            """
            return processor(func, *args, **kwargs)

        # so that doctest will pick up tests within
        wrappedfunc.__doc__ = func.__doc__
        wrappedfunc.__module__ = func.__module__
        #
        #
        return wrappedfunc

    return processedfunc

def get_traced_classes():
    """
    """
    global TRACED_CLASSES

    return TRACED_CLASSES


def print_traced_classes():

    s = '\n'.join(get_traced_classes())
    print('Aspect traced classes:\n{0}'.format(s))


def wrap_module_def(name, excluded_defs):
    """
    """
    debug_print('wrap_module_def')
    module = sys.modules[name]
    for _name, f in inspect.getmembers(module,
        # to check that the member isfunction and the class is defined in
        # module[name]
        lambda member: inspect.isfunction(member) and member.__module__ == name):
#         inspect.isfunction):
        if (excluded_defs and f not in excluded_defs) or (
            not excluded_defs):
            setattr(module, _name, processedby(tracing_processor)(f))
            debug_print('wrapped def {0}'.format(_name))


def wrap_module_class(name, excluded_classes):
    debug_print('wrap_module_class')
    module = sys.modules[name]
    for class_name, c in inspect.getmembers(module,
        # to check that the member isclass and the class is defined in
        # module[name]
        lambda member: inspect.isclass(member) and member.__module__ == name):
#         inspect.isclass):
        if (excluded_classes and c not in excluded_classes) or (
            not excluded_classes):
            add_tracing_prints_to_all_methods(c)
            debug_print('wrapped class {0}'.format(class_name))

def wrap_methods( cls):
    def wrapper( fn ):
        def result( *args, **kwargs ):
            print('TEST')
            result = fn( *args, **kwargs )
            print('result = {0}'.format(result))
            return fn( *args, **kwargs )
        return result

    for key, value in cls.__dict__.items():
        if hasattr( value, '__call__' ):
            setattr( cls, key, wrapper( value ) )
            debug_print('wrapped {0}'.format(key))

def simple_wrap_module_class(name, excluded_classes):
    debug_print('simple_wrap_module_class')
    module = sys.modules[name]
    for class_name, c in inspect.getmembers(module,
        # to check that the member isclass and the class is defined in
        # module[name]
        lambda member: inspect.isclass(member) and member.__module__ == name):
#         inspect.isclass):
        wrap_methods(c)
        debug_print('wrapped class {0}'.format(class_name))

def wrap_module(name, excluded_defs = None, excluded_classes = None):
    global _ASPECT
    if _ASPECT:
        wrap_module_def(name, excluded_defs)
        wrap_module_class(name, excluded_classes)

def turn_aspect(flag=True):
    global _ASPECT
    _ASPECT = flag

