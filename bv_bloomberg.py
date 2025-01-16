__author__ = "Siew Kam Onn"
# ##filename=bv_bloomberg.py, edited on 10 Jul 2017 Mon 01:23 PM
__email__ = "kosiew at gmail.com"
__version__ = "$Revision: 1.0 $"
__date__ = "$Date: 10/Jul/2017"
__copyright__ = "Copyright (c) 2017 Siew Kam Onn"
__license__ = "Python"

"""
    This module contains Bloomberg utility functions

"""

import zd
import aspect
# import a
import attr
import be_mail
import bv_beautiful_soup
# import u
import bv_yaml
SETTINGS = bv_yaml.load_config()

LIMITS = SETTINGS['limits']


class Error (Exception):
    """
        Error is a type of Exception
        Base class for all exception raised by this module
    """
    pass


@attr.s
class BloombergQuote (object):
    """A BloombergQuote summarises quote information from a
    Bloomberg quote url


    Args:
        url (str):


    """
    PERCENT = '%'
    LABEL_CHANGE_PERCENT = 'Change percent'
    LABEL_CHANGE = 'Change'
    selector_name = '#content > div > div > div.basic-quote > div > h1'
    selector_price_down = '#content > div > div > div.basic-quote > div > div.price-container.down'
#     selector_price_up = '#content > div > div > div.basic-quote > div > div.price-container.up'

    div = 'div'
    attrs_dict = {
        'price': 'price',
        'currency': 'currency',
        'change': 'change-container',
        'cell_label': 'cell__label',
        'cell_value': 'cell__value cell__value_'}

    url = attr.ib()

    def __attrs_post_init__(self):
        self.triggered = False
        self.get_summary()

    def _get_text(self, _def, *args, **kwargs):
        """ uses _def to find/select element, then get the text

        Args:
            _def (a def)
            *args
            **kwargs

        Returns:
            text or None if cannot find/select the element

        """
        element = _def(*args, **kwargs)
        if element:
            try:
                _element = element[0]
            except KeyError as ke:
                _element = element
            text = _element.text
            text = text.strip()
        return text

    def get_label_values(self, soup):
        """

        Args:
            soup (bv_beautiful_soup.Soup):

        Returns:
            list of (label, value)

        """
        cell_labels = soup.find_all(BloombergQuote.div,
                attrs=self.get_attrs('cell_label'))
        cell_values = soup.find_all(BloombergQuote.div,
                attrs=self.get_attrs('cell_value'))
        _label_values = zip(cell_labels, cell_values)
        label_values = []
        for _label_value in _label_values:
            label = _label_value[0].text
            value = _label_value[1].text
            label_values.append((label, value))

        return label_values

    def get_change(self, soup):
        """

        Args:
            soup(bv_beautiful_soup.Soup)

        Returns:
            list of change label, change

        """
        prefix = self.get_prefix(soup)

        change = soup.find(BloombergQuote.div,
                attrs=self.get_attrs('change'))
        label_values = []
        for div in change.find_all(BloombergQuote.div):
            text = div.text
            if text:
                text = text.strip()
                text = f'{prefix}{text}'
                if text.find(BloombergQuote.PERCENT) > -1:
                    label_values.append((
                        BloombergQuote.LABEL_CHANGE_PERCENT, text))
                else:
                    label_values.append((
                        BloombergQuote.LABEL_CHANGE, text))
        return label_values

    def get_prefix(self, soup):
        """

        Args:
            soup (bv_beautiful_soup.Soup):

        Returns:
            - if trend is down
            + if trend is up

        """
        price_down = soup.select(BloombergQuote.selector_price_down)
        if len(price_down) > 0:
            result = '-'
        else:
            result = '+'
        return result

    def check_trigger_limit(self, name, price):
        """

        Args:
            name (str):
            price (str):

        Returns:
            trigger limit message

        """
        global LIMITS
        try:
            limits = LIMITS[name]
        except KeyError as ke:
            return ''

        if limits:
            _price = price.replace(',', '')
            _price = float(_price)
            high = float(limits['high'])
            low = float(limits['low'])

            result = '.'
            exclamation = '!' * 10
            if _price > high:
                result = f'> {high} {exclamation}'
            elif _price < low:
                result = f'< {low} {exclamation}'

            self.triggered =  result.find(exclamation) > -1
        return result

    def get_summary(self):
        """

        Args:

        Returns:
            list of str - summary

        """
        url = self.url
        soup = bv_beautiful_soup.Soup(url)
        self.name = self._get_text(soup.select,
                BloombergQuote.selector_name)
        self.price = self._get_text(soup.find,
                BloombergQuote.div,
                attrs=self.get_attrs('price'))
        trigger_limit = self.check_trigger_limit(self.name,
                self.price)
        self.currency = self._get_text(soup.find,
                BloombergQuote.div,
                attrs=self.get_attrs('currency'))

        self.label_values = self.get_change(soup)

        label_values = self.get_label_values(soup)
        self.label_values.extend(label_values)

        result = ['\n']
        result.append(self.name)
        result.append('{0} {1} {2}'.format(self.price,
            self.currency, trigger_limit))
        for label, value in self.label_values:
            line = f'{label} {value}'
            if line not in result:
                result.append(line)
        result.append(f'url: {url}\n')

        self.summary = result
        return result

    def get_attrs(self, key, attribute='class'):
        """

        Args:
            key (str): a key in attrs_dict
            attribute(str)

        Returns:
            the soup find attrs

        """
        label = BloombergQuote.attrs_dict[key]
        if label:
            result = {attribute: label}
            return result


@attr.s
class BloombergUpdate (object):
    """collects Bloomberg quote url and sends a summary of quotes
    in an email

    Args:
        list_of_recipients (list of str): emails to send summary to


    """
    bloomberg_quote_pattern = 'www.bloomberg.com/quote'
    SUBJECT = 'Bloomberg Summary'
    SUBJECT_ALERT = 'Bloomberg Trigger Summary'
    list_of_recipients = attr.ib(default=be_mail.TO, init=True)

    def __attrs_post_init__(self):
        self.urls = []

    def is_bloomberg_quote(self, url):
        """

        Args:
            url (str):

        Returns:
            True if url is bloomberg quote else False

        """
        return url.lower().find(
                BloombergUpdate.bloomberg_quote_pattern) > -1

    def send_summary_email(self):
        """

        Returns:
             count of urls summarized

        """
        aln = be_mail.Alert()
        alt = be_mail.Alert()
        for url in self.urls:
            bq = BloombergQuote(url)
            lines = bq.summary
            message = '\n'.join(lines)

            if bq.triggered:
                alt.add_message(message)
            else:
                aln.add_message(message)

        alt.send_alert_mail(subject=BloombergUpdate.SUBJECT_ALERT)
        aln.send_alert_mail(subject=BloombergUpdate.SUBJECT)

        return len(self.urls)

    def collect_bloomberg_quote(self, url):
        """

        Args:
            url (str):

        Returns:
            True if url is a Bloomberg quote
            False if otherwise

        """
        if self.is_bloomberg_quote(url):
            if url not in self.urls:
                self.urls.append(url)
            return True
        return False


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

