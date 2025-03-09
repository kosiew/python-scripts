# filename=open_urls.py, edited on 31 Oct 2016 Mon 07:36 AM
"""

    call this file with -t to run doctests

"""

__author__ = "Siew Kam Onn"
__email__ = "kosiew at gmail.com"
__version__ = "$Revision: 1.0 $"
__date__ = "$Date: 15/May/2013"
__copyright__ = "Copyright (c) 2009 Siew Kam Onn"
__license__ = "Python"

"""
    This module opens urls

"""
import datetime
import re
import webbrowser
from optparse import OptionParser

# import aspect
import bv_beautiful_soup
import bv_bloomberg
import bv_config
import bv_date
import bv_speak
import bv_time
import u
import zd
import os

PAUSE_INTERVAL = 100
PAUSE_SECONDS = 10


# Get the directory containing the script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INI_FILE = os.path.join(SCRIPT_DIR, "_open_urls.ini")
cf = bv_config.Config(INI_FILE)

SECTION_URLS = "urls"
SECTION_EXTEND_URLS = "extend_urls"
ITEM_MORNING = "morning"
ITEM_PALM = "palm"
ITEM_EXCHANGE_RATES = "exchange_rates"
ITEM_DUAL_CURRENCY_INVESTMENT_RATES = "dci"
ITEM_GOOGLE_ADSENSE = "google_adsense"
ITEM_FUNDS = "funds"
ITEM_GOLD = "gold"
ITEM_NEWFIELD = "newfield"
SECTION_FILES = "files"
ITEM_PRICE_FILE = "price_file"

SECTION_SETTINGS = "settings"
ITEM_SEND_BLOOMBERG_MAIL = "send_bloomberg_mail"

MORNING = ITEM_MORNING

# ITEMS = (
#   ITEM_MORNING,
#   ITEM_PALM,
#   ITEM_EXCHANGE_RATES,
#   ITEM_DUAL_CURRENCY_INVESTMENT_RATES,
#   ITEM_GOOGLE_ADSENSE,
#   ITEM_FUNDS,
#   ITEM_GOLD,
#   ITEM_NEWFIELD,
# )
ITEMS = []

RE_URL_KEY_PATTERN = "(?P<index>\d{2})re (?P<name>\S{2,})"
RE_URL_KEY = re.compile(RE_URL_KEY_PATTERN)

BS_URL_KEY_PATTERN = "(?P<index>\d{2})bs (?P<name>\S{2,})"
BS_URL_KEY = re.compile(BS_URL_KEY_PATTERN)

SECTION_RE_PATTERNS = "re_patterns"
ITEM_RE_PATTERNS = "re_patterns"

SECTION_BS_PATTERNS = "bs_patterns"
ITEM_BS_PATTERNS = "bs_patterns"

parser = False
options = False
args = False

DEFAULT_ACTION = [MORNING]
PALM = ITEM_PALM

PALM_URLS = cf.get(SECTION_URLS, ITEM_PALM, return_eval=True)
SEND_BLOOMBERG_MAIL = cf.get(
    SECTION_SETTINGS, ITEM_SEND_BLOOMBERG_MAIL, return_eval=True
)


PRICE_CHECK_TEMPLATE = """
<h4 class='hidden'>{key}: {value}</h4>"""

PRODUCT_NAME = "product_name"
PRICE_FILE = cf.get(SECTION_FILES, ITEM_PRICE_FILE)

# a function that always increments whenever called
def get_keyprefix():
    get_keyprefix.counter += 1
    return get_keyprefix.counter
get_keyprefix.counter = 0


def get_soup(url):
    """ """
    #     r = requests.get(url)
    #     result = BeautifulSoup(r.content, PARSER)
    result = bv_beautiful_soup.Soup(url)
    return result


def get_soup_str(url):
    soup = get_soup(url)
    str_soup = str(soup)
    return str_soup


def get_re_results(url, pattern):
    if isinstance(pattern, str):
        str_soup = get_soup_str(url)
        pattern_re = re.compile(pattern)
        matches = pattern_re.search(str_soup)

        if matches:
            return matches.groupdict()
    if isinstance(pattern, dict):
        soup = get_soup(url)
        d = {}
        for k, v in pattern.items():
            tag = v[0]
            cls = v[1]
            item = soup.find(tag, {"class": cls})
            if item:
                d[k] = item.text

        if d:
            return d
        return None


def get_patterns():
    re_patterns = cf.get(SECTION_RE_PATTERNS, ITEM_RE_PATTERNS, return_eval=True)
    bs_patterns = cf.get(SECTION_BS_PATTERNS, ITEM_BS_PATTERNS, return_eval=True)
    re_patterns.update(bs_patterns)
    return re_patterns


def get_price_html(a_dict):

    global PRICE_CHECK_TEMPLATE
    patterns = get_patterns()
    l = []
    for k, url in a_dict.items():
        pattern = patterns.get(k)
        if pattern:
            re_url_name = get_re_url_name(k) or get_bs_url_name(k)
            re_results = get_re_results(url, pattern)
            if re_results:
                for re_key, re_value in re_results.items():

                    if re_key == PRODUCT_NAME:
                        link = f"""{re_url_name} <a href="{url}" target="_blank">
                        {re_value}</a>"""
                        re_value = link
                    html = PRICE_CHECK_TEMPLATE.format(key=re_key, value=re_value)

                    l.append(html)
                l.append("<hr>")
    return "".join(l)


def get_thesun_url():
    """Returns the sun epaper url"""
    template = "http://www.thesun-epaper.com/{day_string}/{date_string}/#/1/zoomed"
    td = u.today()
    date_string = td.strftime("%d%m%Y")
    day_string = td.strftime("%a").lower()
    result = template.format(day_string=day_string, date_string=date_string)
    return result

def _get_urls(section, item, return_eval=True):
    global cf

    if item != "":
        try:
            result = cf.get(section, item, return_eval=return_eval)
        except Exception:
            return {}
        # if result is a dictionary, prefix the keys with keyprefix
        if isinstance(result, dict):
            keyprefix = get_keyprefix()
            keyprefix = str(keyprefix).zfill(4)
            result = {f"{keyprefix} {k}": v for k, v in result.items()}
            
        return result
    return {}


def update_with_items_urls(urls, items):
    for  _item in items:
        _urls = get_urls(_item)
        urls.update(_urls)
    return urls


def get_urls(item):
    urls = _get_urls(SECTION_URLS, item, return_eval=True)

    try:
        items = _get_urls(SECTION_EXTEND_URLS, item, return_eval=True)
    except bv_config.NoOptionError as e:
        items = []
    urls = update_with_items_urls(urls, items)
    return urls


def get_weekday_urls():
    """ """
    urls = None
    weekday = datetime.datetime.today().weekday()
    weekday_string = bv_date.WEEKDAYS[weekday].lower()
    try:
        urls = get_urls(weekday_string)
    except SyntaxError as se:
        raise
    except bv_config.NoOptionError as nse:
        urls = []

    return urls

def get_morning_urls():
    morning_urls = get_urls(ITEM_MORNING)
    # morning_urls['05 the sun'] = get_thesun_url()

    items = [item for item in ITEMS if item != ITEM_MORNING]
    morning_urls = update_with_items_urls(morning_urls, items)

    weekday_urls = get_weekday_urls()
    if weekday_urls:
        morning_urls.update(weekday_urls)
    return morning_urls


r = re.compile("^xxooonnraves")


def get_re_url_name(url_key):
    global RE_URL_KEY
    m = RE_URL_KEY.match(url_key)
    if m:
        return m.group("name")
    return False


def get_bs_url_name(url_key):
    global BS_URL_KEY
    m = BS_URL_KEY.match(url_key)
    if m:
        return m.group("name")
    return False


def open_re_urls(urls, re_urls):
    """
    25-May-18 Fri 10:06:00 AM
      amended to include beautiful soup urls too
    """
    d = {}
    for k, v in urls.items():
        if k in re_urls:
            d[k] = v
    html = get_price_html(d)
    html = f"<h3>Price Check</h3>{html}"
    html = f"""
<html>

    <head><title>Testing javascript</title>
        <link rel="stylesheet" href="stylesheets/check_price.css">
        <script
        src="http://ajax.googleapis.com/ajax/libs/jquery/3.3.1/jquery.min.js"></script>
        <script src='scripts/check_price.js'>
        </script>
        <script src="js.js"></script>

    </head>
    {html}
</html>
    """
    with open(PRICE_FILE, "w") as f:
        f.write(html)

    open_url(PRICE_FILE)


def open_urls(urls):
    """Returns None"""
    global PAUSE_SECONDS, PAUSE_INTERVAL, SEND_BLOOMBERG_MAIL
    url_keys = list(urls.keys())
    url_keys.sort()
    url_values = []
    timer = bv_time.Timer()
    b = bv_bloomberg.BloombergUpdate()
    re_urls = []
    len_url_keys = len(url_keys)

    for i, url_key in enumerate(url_keys):
        if get_re_url_name(url_key) or get_bs_url_name(url_key):
            re_urls.append(url_key)
        else:
            if i and i % PAUSE_INTERVAL == 0:
                message = "Taking a moment .."
                bv_time.print_message(message, with_time_stamp=True, starred=True)
                timer.wait(PAUSE_SECONDS)

            url_value = urls[url_key]
            zd.f("looking at %s:%s" % (url_key, url_value))
            rm = r.search(url_key)
            if rm is None:
                _url_value = url_value.lower()
                if _url_value not in url_values:
                    try:
                        message = "opening {0}/{1} {2} {3}".format(
                            i + 1, len_url_keys, url_key, url_value
                        )
                        zd.f(message)
                        bv_time.print_message(message, False)
                        if not SEND_BLOOMBERG_MAIL or not b.collect_bloomberg_quote(
                            _url_value
                        ):
                            open_url(url_value)
                        url_values.append(_url_value)
                    except Exception as e:
                        zd.f(url_value)
                    if i > PAUSE_INTERVAL:
                        timer.wait()
    if re_urls:
        open_re_urls(urls, re_urls)
    if SEND_BLOOMBERG_MAIL:
        b.send_summary_email()


def open_url(url):
    """Returns None"""
    url = url.strip()
    return webbrowser.open(url)


def open_morning_urls():
    morning_urls = get_morning_urls()
    open_urls(morning_urls)


def show_available_items(section):
    items = cf.get_items(section)
    # sort items
    items.sort()
    bv_time.print_message("Available items", with_time_stamp=True, starred=True)
    bv_time.print_message(items, with_time_stamp=False, starred=False)

@bv_time.print_timing
def go(options=None, args=None):
    robot = bv_speak.Robot()
    if len(args) == 0:
        args = DEFAULT_ACTION

    arg1 = args[0]

    if arg1 == MORNING:
        urls = get_morning_urls()
        open_urls(urls)
    else:
        urls = get_urls(arg1)
        open_urls(urls)

    if urls:
        message = "Opened {0} links".format(len(urls))
        robot.say(message)
        bv_time.print_message(message, with_time_stamp=True, starred=True)
    else:
        message = f"No links to open for {arg1}"
        robot.say(message)
        bv_time.print_message(message, with_time_stamp=True, starred=True)
        show_available_items(SECTION_URLS)


def get_options(argv):
    """Returns None"""
    global parser

    usage = "usage: %prog [options] morning|gain|trade <stock_code1, stock_code2>"
    parser = OptionParser(
        usage=usage,
        version="%prog " + __version__,
        description="""\

%prog opens urls
""",
    )
    # {{{ options
    parser.add_option("-g", "--go", action="store_true", default=False, help="run")
    parser.add_option(
        "-v", "--verbose", action="store_true", default=False, help="verbose"
    )
    parser.add_option(
        "-t", "--test", action="store_true", default=False, help="run doctests"
    )
    # end of options }}}

    return parser.parse_args(argv)


def get_date_argument(a_date):
    """Returns a_date in oracle date format"""
    result = bv_date.oracle_date(a_date)
    return result


def _test():
    """Runs all tests"""
    zd.output_to_stdout = False
    import doctest

    doctest.testmod(
        optionflags=doctest.ELLIPSIS + doctest.NORMALIZE_WHITESPACE, verbose=False
    )
    doctest.master.summarize(True)


def main(argv=None):
    global options
    global args

    options, args = get_options(argv)

    if not options.test:
        options.go = True

    if options.test or (options.go is False):
        _test()
    else:
        zd.output_to_stdout = options.verbose
        if zd.output_to_stdout:
            aspect.set_brief(False)

        if options.go:
            go(options, args)


# aspect.wrap_module(__name__)

if __name__ == "__main__":
    main()
