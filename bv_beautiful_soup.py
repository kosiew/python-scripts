__author__ = "Siew Kam Onn"
# ##filename=bv_beautiful_soup.py, edited on 10 Jun 2019 Mon 09:46 PM
__email__ = "kosiew at gmail.com"
__version__ = "$Revision: 1.0 $"
__date__ = "$Date: 10/Jul/2017"
__copyright__ = "Copyright (c) 2017 Siew Kam Onn"
__license__ = "Python"

"""
    This module contains BeautifulSoup utility functions

"""

import zd
import aspect
# import a
import attr
from bs4 import BeautifulSoup, NavigableString
import requests
import collections
from dataclasses import dataclass
# import bv_file

TagDict = collections.namedtuple('TagDict', 'tag dic')

PARSER = 'lxml'

class Error (Exception):
    """
        Error is a type of Exception
        Base class for all exception raised by this module
    """
    pass

# allowed_types = (float, int)
# def x_smaller_than_y(self, attribute, value):
#     if value >= self._y:
#         raise ValueError("'x' has to be smaller than 'y'!")

class _Soup(BeautifulSoup):
    """A BeautifulSoup
    """

    def init_content(self, content):
        global PARSER
        super().__init__(content, PARSER)
        self.content = content

    def find_all_tag_dicts(self, tag_dicts):
        for i, tag_dict in enumerate(tag_dicts):
            matches = self.find_all(tag_dict.tag, tag_dict.dic)
            if len(matches) > 0:
                return matches, i
        return None




@attr.s
class Soup (_Soup):
    """A BeautifulSoup


    Args:
        url (str):

    """

    url = attr.ib(default=None)
    req = attr.ib(default=None)


    def __attrs_post_init__(self):
        if self.req:
            req = self.req
        else:
            req = requests
        if self.url:
            r = req.get(self.url)
            self.init_content(r.content)




def strip_html(src):
    p = BeautifulSoup(src, 'lxml')
    text = p.findAll(text=lambda text:isinstance(text, NavigableString))

    return u" ".join(text)


def _test():
    '''Runs all tests

    '''

    zd.output_to_stdout = False
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS + doctest.NORMALIZE_WHITESPACE, verbose=False)
    doctest.master.summarize(True)

aspect.wrap_module(__name__)

if __name__ == "__main__":
    _test()

