# ##filename=bv_config.py, edited on 24 Sep 2018 Mon 03:04 PM
# filename=bv_config.py, edited on 28 Jun 2016 Tue 10:56 AM

__author__ = "Siew Kam Onn"
__email__ = "kosiew at gmail.com"
__version__ = "$Revision: 1.0 $"
__date__ = "$Date: 02-10-2009 9:39:39 AM $"
__copyright__ = "Copyright (c) 2006 Siew Kam Onn"
__license__ = "Python"

"""
    This module is utility for config (ini) files

"""

# import ast
import configparser
import os

import aspect
import bv_date
import bv_file
import u
import zd

ENCODING = "utf-8"
STATUS = "status"
LAST_RUN_DATE = "last_run_date"

INI_PATHS = (".", os.environ["PYTHON_SOURCE"])

NoOptionError = configparser.NoOptionError
NoSectionError = configparser.NoSectionError


class Config(object):
    """
    Config class
      provides utility functions to manage config files
    """

    def __init__(self, config_file, encoding=ENCODING):

        self.config_file = config_file
        self.encoding = encoding
        _config_file = self.assert_config_file_exists(config_file)
        if _config_file:
            self.config_file = _config_file
            self.cf = False
            self.cf = self.read_config()
        else:
            raise Exception("cannot find {0} in {1}".format(config_file, INI_PATHS))

    def assert_config_file_exists(self, config_file):
        """Returns path_file of config_file if can find config_file in INI_PATHS"""
        for p in INI_PATHS:
            pf = os.path.join(p, config_file)
            if bv_file.exists(pf):
                return pf

        return False

    def get_items(self, section):
        items = []
        if section in self.cf:
            for key, value in self.cf.items(section):
                items.append(key)
        return items

    def get(self, section, item, raw=True, return_eval=False):

        try:
            result = self.cf.get(section, item, raw=True)
        except NoOptionError as e:
            raise e

        if return_eval:
            return eval(result)
        return result

    def read_config(self):
        if not self.cf:
            cf = configparser.ConfigParser(interpolation=None)
            cf.read(self.config_file, self.encoding)
            return cf
        else:
            return self.cf

    def toggle(self, section, item):
        """ """
        value = eval(self.get(section, item))
        new_value = not value
        _new_value = str(new_value)
        self.update_config(section, item, _new_value, True)
        return new_value

    def update_config(self, section, item, value, write_to_file=False):
        """Returns None"""
        self.cf = self.read_config()
        self.cf.set(section, item, value)

        if write_to_file:
            self.update_config_file()
        return None

    def set(self, section, item, value):
        """Returns None"""
        self.update_config(section, item, value)
        return None

    def update_config_file(self):
        """Returns None"""
        with open(self.config_file, "w") as f:
            self.cf.write(f)

        return None


##aspect.add_tracing_prints_to_all_methods(Config)


##@aspect.processedby(aspect.tracing_processor)
def get_last_run_date(config):
    """Returns last run date"""

    ld = config.get(STATUS, LAST_RUN_DATE)
    result = bv_date.parse_date(ld)

    return result


##@aspect.processedby(aspect.tracing_processor)
def set_last_run_date(config, ini_file):
    config.set(STATUS, LAST_RUN_DATE, bv_date.oracle_date(u.today()))
    f = file(ini_file, "w")
    config.write(f)


def _test():
    """Runs all tests

    -- doctests ----
    """

    zd.output_to_stdout = False
    import doctest

    doctest.testmod(
        optionflags=doctest.ELLIPSIS + doctest.NORMALIZE_WHITESPACE, verbose=False
    )
    doctest.master.summarize(True)


excluded_classes = None
excluded_defs = None
aspect.wrap_module(__name__, excluded_defs, excluded_classes)

if __name__ == "__main__":
    _test()
