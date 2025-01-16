# filename=bv_yaml.py, edited on 11 Aug 2016 Thu 03:09 PM
# ##filename=bv_yaml.py, edited on 22 Oct 2020 Thu 10:20 PM


__author__ = "Siew Kam Onn"
__email__ = "kosiew at gmail.com"
__version__ = "$Revision: 1.0 $"
__date__ = "$Date: 02/Jun/2016"
__copyright__ = "Copyright (c) 2016 Siew Kam Onn"
__license__ = "Python"

"""
    This module contains YAML functions

"""

import zd
import aspect
import a
import bv_file64 as bv_file
import bv_stack
import yaml
import ruamel.yaml
import os

FILE_EXTENSION = 'yml'

class Error (Exception):
    """
        Error is a type of Exception
        Base class for all exception raised by this module
    """
    pass



##@aspect.processedby(aspect.tracing_processor)
def get_config_file(calling_filename):
    """
    """
    p, f, e = bv_file.get_path_file_extension_tuple(calling_filename)

    result = '_{0}.{1}'.format(f, FILE_EXTENSION)
    result = os.path.join(p, result)
    return result

def get_default_config_file():
    """get_default_config_file


    Returns:
        str: default config file

    """
    stack = bv_stack.Stack(ignored_files = ('bv_stack', 'bv_yaml','aspect'))
    caller = stack.get_current_file()
    config_file = get_config_file(caller)
    return config_file


def write_config_file(data, config_file=None, round_trip_dump=False):
    """write_config_file writes data to config_file

    Args:
        config_file (str): path file of config file
        data (dict): dictionary of data
        round_trip_dump(bool): if yes, will use ruamel.yaml, else yaml

    Returns:
        dict: dict of config_file if successful, None otherwise.

    """
    if config_file is None:
        config_file = get_default_config_file()

    with open(config_file, 'w') as outfile:
        if round_trip_dump:
            ruamel.yaml.round_trip_dump(data, outfile)
        else:
            yaml.dump(data, outfile, default_flow_style=False)

    return load_config(config_file, round_trip_dump)




##@aspect.processedby(aspect.tracing_processor)
def load_config(config_file = None, round_trip_load=False):
    """
    """
    if config_file is None:
        config_file = get_default_config_file()

    if round_trip_load:
        f = open(config_file, 'r')
        d_config = ruamel.yaml.round_trip_load(f)
    else:

        config = open(config_file, 'r')
        d_config = yaml.load(config, Loader=yaml.FullLoader)


    return d_config

def _test():
    '''Runs all tests

    '''

    zd.output_to_stdout = False
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS + doctest.NORMALIZE_WHITESPACE, verbose=False)
    doctest.master.summarize(True)


aspect.wrap_module(__name__)

if __name__=="__main__":
    _test()

