
# ##filename=bv_date.py, edited on 25 Feb 2018 Sun 07:11 PM
# filename=bv_date.py, edited on 28 Jun 2016 Tue 09:30 AM

__author__ = "Siew Kam Onn"
__email__ = "kosiew at gmail.com"
__version__ = "$Revision: 1.0 $"
__date__ = "$Date: 05-12-2007 5:03:26 PM $"
__copyright__ = "Copyright (c) 2006 Siew Kam Onn"
__license__ = "Python"

import sys
import zd

import dateutil.parser, time, datetime, calendar
import dateutil.relativedelta
import aspect
import u
import dateutil
import re
import a

# import these
import bv_fire
import attr
import beeprint

quarter_start_dates = {
    'q1': '1-JAN',
    'q2': '1-APR',
    'q3': '1-JUL',
    'q4': '1-OCT'
    }

quarter_end_dates = {
    'q1': '31-MAR',
    'q2': '30-JUN',
    'q3': '30-SEP',
    'q4': '31-DEC'
    }

WEEKDAYS = [
  'MONDAY',
  'TUESDAY',
  'WEDNESDAY',
  'THURSDAY',
  'FRIDAY',
  'SATURDAY',
  'SUNDAY'
]


class Error (Exception):
    """
        Error is a type of Exception
        a Error is the base class for errors
    """


    def __init__(self, error_message = None):
        _error_message = error_message
        if _error_message is None:
            _error_message = 'Generic Error'
        self.error_message = _error_message

    def __str__(self):
        return repr(self.error_message)


##aspect.add_tracing_prints_to_all_methods(Error)


class ParseDateError (Error):
    """
        ParseDateError is a type of Error
        a ParseDateError is raised when parsing an erroneous date
    """


    def __init__(self, date, error_message=None):
        suffix = error_message
        if suffix is None:
            suffix = ''

        _error_message = 'Cannot parse {0}'.format(date)

        if len(suffix) > 1:
            _error_message = '{0} - {1}'.format(_error_message,
                suffix)
        self.date = date
        super(ParseDateError, self).__init__(_error_message)



##aspect.add_tracing_prints_to_all_methods(ParseDateError)

##@aspect.processedby(aspect.tracing_processor)
def quarter_start_end_dates(year_quarter):
    ''' Returns quarter start date, end date for year_quarter
    '''
    year_quarter = year_quarter.lower()

    quarter_position = year_quarter.find('q')
    quarter = year_quarter[quarter_position:quarter_position+2]
    year = year_quarter.replace(quarter, '')
    year = re.sub('\D', '', year) #remove non-numbers
    start_date = '{0}-{1}'.format(quarter_start_dates[quarter], year)
    end_date = '{0}-{1}'.format(quarter_end_dates[quarter], year)
    return parse_date(start_date), parse_date(end_date)

##@aspect.processedby(aspect.tracing_processor)
def this_week_weekday(weekday_number):
    ''' Returns the datetime.date of weekday_number of this week
    '''
    today = u.today()
    d = today.weekday()
    return u.adddays(weekday_number - d)


##@aspect.processedby(aspect.tracing_processor)
def last_month(oracle_format = True):
    ''' Returns last month
    '''
    lm = u.addmonths(-1, u.today())
    lm = lm.strftime('%b-%Y') if oracle_format else lm
    return lm


##@aspect.processedby(aspect.tracing_processor)
def first_weekday_of_month(a_month):
    ''' Returns the first weekday of a_month
    '''
    d = parse_date(a_month)
    new_d = datetime.date(year=d.year, month=d.month, day=1)
    weekday = new_d.weekday()
    if weekday < 5:
        return new_d
    return u.adddays(7 - weekday, new_d)



def month_name(month_num):
    ''' Returns month name from month_num

    -- doctests ----

    >>> month_name(5)
    'May'

    '''
    zd.f('month_name+')
    result = datetime.date(1900,month_num,1).strftime('%B')

    zd.f('month_name-')
    return result


def oracle_period(d):

    try:
        _d = parse_date(d)
    except Exception as e:
        raise e
    pattern = '%b-%Y'

    return _d.strftime(pattern).upper()

def timestamp(d=None):
    '''return d in timestamp format

    '''
    if d is None:
        d = u.now()

    return d.strftime('%Y%m%d%H%M%S')

# strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())
# 'Thu, 28 Jun 2001 14:17:15 +0000'

def oracle_date(d, include_time = False, dayfirst = None,
    trim_leading_zero = False, fuzzy = False):
    '''
    >>> oracle_date('08 02 2012')
    '02-Aug-2012'
    >>> oracle_date('08 02 2012', dayfirst = True)
    '08-Feb-2012'
    '''
    if d is None:
        return None
    if type(d) not in (datetime.date, datetime.datetime):
        d = parse_date(d, dayfirst=dayfirst, fuzzy = False)
        return oracle_date(d)
    else:
        pattern = '%d-%b-%Y'
        if include_time:
            time_pattern = '%H:%M:%S'
            pattern = '{0} {1}'.format(pattern, time_pattern)
        result = d.strftime(pattern)
        if trim_leading_zero:
            if result.startswith('0'):
                result = result[1:]
        return result

##@aspect.processedby(aspect.tracing_processor)
def is_even_month(t = None):
    """Returns True if t or today is even month

    """
    if not t:
        t = u.today()

    result = int(t.strftime('%m')) % 2 == 0
    return result

##@aspect.processedby(aspect.tracing_processor)
def is_odd_month(t=None):
    """ Returns True if t is odd month
    """
    result = not is_even_month(t)
    return result

##@aspect.processedby(aspect.tracing_processor)
def mysql_date(d):
    ''' Returns date in mysql format
    '''
    return mssql_date(d)


##@aspect.processedby(aspect.tracing_processor)
def mssql_date(d):
    ''' Returns date in mssql format
    '''
    if d is None:
        return d
    if type(d) not in (datetime.date, datetime.datetime):
        d = parse_date(d)
        return mssql_date(d)

    return d.strftime('%Y-%m-%d')

##@aspect.processedby(aspect.tracing_processor)
def access_date(date):
    return '#{0}#'.format(date.strftime('%d-%b-%Y'))

##@aspect.processedby(aspect.tracing_processor)
def switch_day_month(a_date):
    """ Returns d with month and day switched if possible
        if not possible, returns None
    >>> d = parse_date('1-aug-2012')
    >>> nd = switch_day_month(d)
    >>> nd.month
    1
    >>> nd.day
    8
    >>> d = parse_date('13-Aug-2012')
    >>> nd = switch_day_month(d)
    >>> nd


    """
    m = a_date.month
    d = a_date.day
    y = a_date.year

    if d < 13:
        new_date = '{0}-{1}-{2}'.format(m, d, y)
        return parse_date(new_date, dayfirst=True)
    return None


def fuzzy_guess_date(a_date, anchor = None):
    ''' Returns a more plausible a_date
        to tackle cases where month was mistaken for day and vice versa

    >>> anchor = parse_date('8-Feb-2012')
    >>> test_date = parse_date('2-Aug-2012')
    >>> new_date = fuzzy_guess_date(test_date, anchor)
    >>> new_date == anchor
    True
    >>> test_date = parse_date('9-Feb-2012')
    >>> new_date = fuzzy_guess_date(test_date, anchor)
    >>> new_date == test_date
    True

    '''
    if not anchor:
        anchor = u.today()

    new_date = switch_day_month(a_date)

    if new_date:
        if abs(new_date - anchor) < abs(a_date - anchor):
            return new_date

    return a_date


def parse_date(date, print_to_stdout=False, fuzzy = True,
    dayfirst = None, return_datetime_as_date = False, **kwargs):
    """returns a date from a variable that resembles a date
       >>> d = 'Jan 3 2006'
       >>> parse_date(d, True)
       Sharp 'Jan 3 2006' -> 2006-01-03 00:00:00
       datetime.datetime(2006, 1, 3, 0, 0)
       >>> d = (5, 'Oct', 55)
       >>> parse_date(d, True)
       Sharp '5 Oct 55' -> 2055-10-05 00:00:00
       datetime.datetime(2055, 10, 5, 0, 0)
       >>> d = 'Sat Nov 25 2009'
       >>> parse_date(d, True)
       Sharp 'Sat Nov 25 2009' -> 2009-11-25 00:00:00
       datetime.datetime(2009, 11, 25, 0, 0)
       >>> d = '25-11-06'
       >>> parse_date(d, True)
       Sharp '25-11-06' -> 2006-11-25 00:00:00
       datetime.datetime(2006, 11, 25, 0, 0)
       >>> d = '11AM on the 11th day of 11th month, in the year of our Lord 1945'
       >>> parse_date(d, True)
       Fuzzy '11AM on the 11th day of 11th month, in the year of our Lord 1945' -> 1945-11-11 11:00:00
       datetime.datetime(1945, 11, 11, 11, 0)
       >>> d = datetime.datetime(12,12,12)
       >>> parse_date(d, return_datetime_as_date = True)
       datetime.date(12, 12, 12)

    """
    # dateutil.parser needs a string argument: let's make one from our
    # `date' argument, according to a few reasonable conventions...:

    date_is_integer = False
    try:
        i = int(date)
    except Exception as e:
        pass
    else:
        message = 'it is all numbers!'
        raise ParseDateError(date, message)


    if isinstance(date, (tuple, list)):
        date = ' '.join([str(x) for x in date])    # join up sequences
    elif isinstance(date, int):
        date = str(date)                           # stringify integers
    elif isinstance(date, dict):
        kwargs = update(date)                      # accept named-args dicts
        date = kwargs.pop('date')                  # with a 'date' str

    def bprint(message):
        if print_to_stdout:
            print(message)

    try:
        try:
            if isinstance(date, datetime.datetime):
                if return_datetime_as_date:
                    parsedate = date.date()
                else:
                    parsedate = date
            elif isinstance(date, datetime.date):
                parsedate = date
            else:
                parsedate = dateutil.parser.parse(date, dayfirst=dayfirst, **kwargs)
                if return_datetime_as_date:
                    parsedate = parse_date(parsedate, return_datetime_as_date = return_datetime_as_date)
            bprint('Sharp %r -> %s' % (date, parsedate))
        except ValueError:
            parsedate = dateutil.parser.parse(date, fuzzy=fuzzy, dayfirst = dayfirst, **kwargs)
            bprint('Fuzzy %r -> %s' % (date, parsedate))
    except Exception as err:
        error_message = str(err)
        # Exception: Try as I may, I cannot parse 'feb 2013' (day is out of range for mont h)
        #   the above happens when it is a month without day 31
        if error_message.find('day is out of range for month') > -1:
            return parse_date('28 {0}'.format(date))
        else:
            message = 'Try as I may, I cannot parse %r (%s)' % (date, err)
            bprint(message)
            raise Exception(message)

    return parsedate

def get_weekday_index(weekday):
    ''' Returns None

    -- doctests ----

    >>> get_weekday_index('thur')
    3

    '''
    zd.f('get_weekday_index+')
    weekday_prefix = weekday[:2].upper()

    if weekday_prefix == 'MO':
        result = 0
    elif weekday_prefix == 'TU':
        result = 1
    elif weekday_prefix == 'WE':
        result = 2
    elif weekday_prefix == 'TH':
        result = 3
    elif weekday_prefix == 'FR':
        result = 4
    elif weekday_prefix == 'SA':
        result = 5
    elif weekday_prefix == 'SU':
        result = 6
    zd.f('get_weekday_index-')
    return result



def get_weekdays_of_month(year, month, day):
    '''
    Args:
        year (int or iterable of int): The first parameter.
        month (int or iterable of int): The second parameter.
        day (int or iterable of int)

    Returns:
        generator of dates of month
    '''
    c = calendar.Calendar(firstweekday=calendar.SUNDAY)

    years = u.ensure_iterable(year)
    months = u.ensure_iterable(month)
    days = u.ensure_iterable(day)

    for _year in years:
        for _month in months:
            d = datetime.date(_year, _month, 1)
            d_weekday = d.weekday()

            while d.month == _month:
                for _day in days:
                    diff = _day - d_weekday
                    result = u.adddays(diff, d)
                    if result.month == _month:
                        yield result
                d = u.adddays(7, d)



def nth_weekday_of_month(n, a_date, weekday):
    '''
        returns the Nth weekday of the month of a_date

    >>> nth_weekday_of_month(2, '1-dec-07', 'thursday')
    datetime.datetime(2007, 12, 13, 0, 0)
    '''
    result = None
#     zd.f('nth_weekday_of_month+')
# #
    day_index = get_weekday_index(weekday)
    r = dateutil.relativedelta.relativedelta(day=1, weekday=day_index)
    a_date = parse_date(a_date)
#
    first_weekday_of_month = a_date + r
    result = first_weekday_of_month
    if n > 1:
        r = dateutil.relativedelta.relativedelta(weekday=day_index, days=+1)
        for i in range(1, n):
            result = result + r
#
#     zd.f('nth_weekday_of_month+')
    return result


def get_exception_dates(weekday, frequency_in_month, start_date, end_date):
    ''' Returns a string  of exception dates
        for use in st.andrews' calendar maintenance

        for something like
        Thursdays (4)
        every 1st and 3rd of month
        between 1-jan-08 and 31-dec-08

    -- doctests ----

    >>> l = get_exception_dates('thursday', (1, 3), '1-dec-07', '15-jan-08')
    >>> l
    [datetime.datetime(2007, 12, 13, 0, 0), datetime.datetime(2007, 12, 27, 0, 0), datetime.datetime(2008, 1, 10, 0, 0)]

    '''
    result = []
    zd.f('get_exception_dates+')
#
    weekday_index = get_weekday_index(weekday)
#
    first_weekday_of_start_month = nth_weekday_of_month(1, start_date, weekday)
#
    r = dateutil.relativedelta.relativedelta(days=-1)
    a_date = first_weekday_of_start_month + r
    r = dateutil.relativedelta.relativedelta(days=+1, weekday = weekday_index)
    i = 0
    start_date = parse_date(start_date)
    end_date = parse_date(end_date)
    while a_date <= end_date:
        old_month = a_date.month
        a_date = a_date + r
        i += 1
        new_month = a_date.month
        if new_month != old_month:
            i = 1
        if i not in frequency_in_month and a_date <= end_date and a_date >= start_date:
            result.append(a_date)
#
    zd.f('get_exception_dates-')
    return result


def print_exception_dates(weekday, frequency_in_month, start_date, end_date):
    ''' Returns None

    -- doctests ----

    >>> print_exception_dates('thur', (1,3), '1-dec-07', '31-dec-07')
    '2007-12-13', '2007-12-27'

    '''
    zd.f('print_exception_dates+')
    exception_dates = get_exception_dates(weekday, frequency_in_month, start_date, end_date)
    str_exception_dates = []
    for d in exception_dates:
        str_exception_date = "'%s-%02d-%02d'" % (d.year, d.month, d.day)
        str_exception_dates.append(str_exception_date)
    string = ', '.join(str_exception_dates)

    sys.stdout.write('%s\n' % string)
    zd.f('print_exception_dates-')
    return None

##@aspect.processedby(aspect.tracing_processor)
def days_between(start_date, end_date):
    """ Returns days between start_date and end_date
    """

    start_date = parse_date(start_date)
    end_date = parse_date(end_date)

    return u.days_between(start_date, end_date)


##@aspect.processedby(aspect.tracing_processor)
def weeks_between(start_date, end_date):
    """ Returns days between start_date and end_date
    """

    start_date = parse_date(start_date)
    end_date = parse_date(end_date)

    return u.weeks_between(start_date, end_date)


##@aspect.processedby(aspect.tracing_processor)
def count_nday_in_date_range(start_date, end_date, nday):
    """ Returns number of nday between start_date and end_date
          where nday in ('monday', 'tuesday'....'sunday')
    """
    start_date = parse_date(start_date)
    end_date = parse_date(end_date)

    a.assert_true(end_date >= start_date,
        'end_date is earlier than start_date')
    u.ensure_end_date_is_later(start_date, end_date)
    days_between = u.days_between(start_date, end_date)
    start_date_day_index = start_date.weekday()
    nday_index = get_weekday_index(nday)

    start_date_ordinal = start_date.toordinal()
    end_date_ordinal = end_date.toordinal()

    if nday_index >= start_date_day_index:
        first_nday_ordinal = start_date_ordinal + (nday_index - start_date_day_index)
    else:
        first_nday_ordinal = start_date_ordinal + (6 + nday_index - start_date_day_index)

    week_count = (end_date_ordinal - first_nday_ordinal)/7 + 1

    return week_count

##@aspect.processedby(aspect.tracing_processor)
def first_day_of_month(a_date = None):
    '''Returns first day of the month of a_date

        if a_date = None, then a_date defaults to today
    '''
    #what is the first day of the current month
    a_date = u.today() if a_date is None else a_date
    a_date = parse_date(a_date)
    ddays = int(a_date.strftime("%d"))-1 #days to subtract to get to the 1st
    delta = datetime.timedelta(days= ddays)  #create a delta datetime object
    result = a_date - delta                #Subtract delta and return
    return datetime.date(result.year, result.month, result.day)

##@aspect.processedby(aspect.tracing_processor)
def make_date_time(dateString,strFormat="%Y-%m-%d"):
    # Expects "YYYY-MM-DD" string
    # returns a datetime object
    eSeconds = time.mktime(time.strptime(dateString,strFormat))
    return datetime.datetime.fromtimestamp(eSeconds)


##@aspect.processedby(aspect.tracing_processor)
def last_day_of_month(a_date = None):
    '''Returns last day of the month for a_date
    '''
    a_date = u.today() if a_date is None else a_date
    a_date = parse_date(a_date)
    first_day = first_day_of_month(a_date)
    next_month_first_day = u.addmonths(1, first_day)
    return u.adddays(-1, next_month_first_day)


##@aspect.processedby(aspect.tracing_processor)
def get_t(t = None):
    """ Returns True if
            docstring
    """
    t = u.today() if t is None else parse_date(t)
    return t

##@aspect.processedby(aspect.tracing_processor)
def addweeks(week = 0, t = None):
    """Returns today + weeks
    """
    t = get_t(t)
    return u.addweeks(week, t)

##@aspect.processedby(aspect.tracing_processor)
def addmonths(month = 0, t = None):
    """Returns today + months
    """
    t = get_t(t)
    return u.addmonths(month, t)

##@aspect.processedby(aspect.tracing_processor)
def adddays(day = 0, t = None):
    """Returns today + days
    """
    t = get_t(t)
    return u.adddays(day, t)

##@aspect.processedby(aspect.tracing_processor)
def addyears(year = 0, t = None):
    """Returns today + years
    """
    t = get_t(t)
    return u.addyears(year, t)


##@aspect.processedby(aspect.tracing_processor)
def date1_later_than_date2(date1, date2):
    ''' Returns 1 if date1 > date2
                0 if date1 = date2
                -1 if date1 < date2
    '''

    do1 = parse_date(date1).toordinal()
    do2 = parse_date(date2).toordinal()

    if do1 > do2:
        return 1
    elif do1 == do2:
        return 0
    return -1


##@aspect.processedby(aspect.tracing_processor)
def month_string(d, short = True, uppercase = True):
    ''' Returns month string of a date
          eg FEB, MAR ..
    '''
    format = '%b' if short else '%B'
    try:
        m = d.strftime(format)
        m = m.upper() if uppercase else m
    except AttributeError as e:
        return month_string(parse_date(d), short, uppercase)

    return m


##@aspect.processedby(aspect.tracing_processor)
def month_diff(date1, date2):
    ''' Returns number of months of date1 - date2
    '''
    d1 = parse_date(date1)
    d2 = parse_date(date2)

    y1 = d1.year
    y2 = d2.year

    return (d1.year - d2.year) * 12 + (d1.month - d2.month)

##@aspect.processedby(aspect.tracing_processor)
def day_diff(date1, date2):
    """Compute days difference

    :param date1
    :param date2

    >>> day_diff('1-may-14', '30-apr-14')
    1
    >>> day_diff(datetime.datetime(12,12,12,0,0), datetime.date(12,12,12))
    0
    >>> day_diff(datetime.date(12,12,12), datetime.datetime(12,12,12,0,0))
    0
    """
    d1 = parse_date(date1, return_datetime_as_date = True)
    d2 = parse_date(date2, return_datetime_as_date = True)
    result = (d1 - d2).days
    return result

##@aspect.processedby(aspect.tracing_processor)
def week_diff(date1, date2):
    ''' Returns number of months of date1 - date2
    '''
    d1 = parse_date(date1)
    d2 = parse_date(date2)

    y1 = d1.year
    y2 = d2.year

    w1 = int(d1.strftime('%W'))
    w2 = int(d2.strftime('%W'))


    return (d1.year - d2.year) * 52 + (w1 - w2)


##@aspect.processedby(aspect.tracing_processor)
def month_range(start_month, end_month, month_format = '%b-%Y'):
    ''' Returns a generator of months
    '''
    date1 = parse_date('1-%s' % start_month)
    date2 = parse_date('1-%s' % end_month)

    start_date = min(date1, date2)
    end_date = max(date1, date2)

    less_than_end = True
    i = 0
    while less_than_end:
        d = start_date + dateutil.relativedelta.relativedelta(months = i)
        yield d.strftime(month_format).upper()
        i += 1
        new_d = start_date + dateutil.relativedelta.relativedelta(months = i)
        less_than_end = new_d <= end_date

def year_range(start_year, end_year):
    """returns a generator of years

    Args:
        start_year (int):
        end_year (int):

    Yields:
        int: The next year until end_year

    """
    start_year = min(start_year, end_year)
    end_year = max(start_year, end_year)

    less_than_end = True
    i = 0
    while less_than_end:
        y = start_year + i
        yield y
        i += 1
        new_y = start_year + i
        less_than_end = new_y <= end_year


def date_range(date1, date2, return_generator = True):
    ''' Returns a generator of dates if return_generator else
        returns a list of dates between date1, date2


    -- doctests ----

    >>> l = date_range('1-jul-08', '3-jul-08', False)
    >>> l
    [datetime.datetime(2008, 7, 1, 0, 0), datetime.datetime(2008, 7, 2, 0, 0), datetime.datetime(2008, 7, 3, 0, 0)]
    >>> l = date_range('3-jul-08', '1-jul-08', False)
    >>> l
    [datetime.datetime(2008, 7, 1, 0, 0), datetime.datetime(2008, 7, 2, 0, 0), datetime.datetime(2008, 7, 3, 0, 0)]
    >>> l = date_range('3-jul-08', '1-jul-08', True)
    >>> l.next()
    datetime.datetime(2008, 7, 1, 0, 0)
    >>> list(date_range('1-jul-08', '2-jul-08', True))
    [datetime.datetime(2008, 7, 1, 0, 0), datetime.datetime(2008, 7, 2, 0, 0)]

    '''
    zd.f('date_range+')
    date1 = parse_date(date1)
    date2 = parse_date(date2)

    start_date = min(date1, date2)
    end_date = max(date1, date2)

    r = (end_date+datetime.timedelta(days=1) - start_date).days
    zd.f('date_range-')
    g = (start_date + datetime.timedelta(days=i) for i in range(r))
    if return_generator:
        return g
    else:
        return list(g)

##@aspect.processedby(aspect.tracing_processor)
def month_quarter(d):
    ''' Returns the calendar quarter of date d
    '''

    try:
        m = d.month
    except AttributeError as e:
        m = parse_date(d).month

    q = (m-1)//3 + 1
    return q


##@aspect.processedby(aspect.tracing_processor)
def datetime_of(a_date):
    ''' Returns None

    '''
    if type(a_date) in (datetime.datetime,):
        result = a_date
    else:
        result = parse_date(a_date)

    return result

##@aspect.processedby(aspect.tracing_processor)
def is_last_day_of_month(a_date):
    ''' Returns True if a_date is last day of the month
    '''

    ld = last_day_of_month(a_date)
    d = parse_date(a_date)
    return d.year == ld.year and d.month == ld.month and d.day == ld.day

##@aspect.processedby(aspect.tracing_processor)
def is_odd_day(t = None):
    ''' Returns None
    '''

    if t is None:
        t = u.today()
    else:
        t = parse_date(t)

    d = t.day
    return u.is_odd_number(d)

##@aspect.processedby(aspect.tracing_processor)
def current_year():
    """ Returns current year
    """
    now = u.now()
    result = int(now.strftime('%Y'))
    return result

##@aspect.processedby(aspect.tracing_processor)
def get_normalized_quarter_date_ranges(qr):
    ''' Returns dictionary of normalized dates

        where qr is dictionary of date: value
        normalize is remove dates where the current value does not
        change from earlier value
    '''
    dd = {}
    previous_v = None

    for k, v in list(qr.items()):

        start_date, end_date = quarter_start_end_dates(k)
        dd[start_date] = v

    dates = list(dd.keys())
    dates.sort()
    for a_date in dates:
        v = dd.get(a_date)
        if v == previous_v:
            del dd[a_date]

        previous_v = v

    return dd

##@aspect.processedby(aspect.tracing_processor)
def is_month(month_string):
    ''' Returns first and last day of month if month_string is
    valid month
    '''
    first_day_string = '1-{0}'.format(month_string)

    try:
        first_day = parse_date(first_day_string)
    except Exception as e:
        return False

    last_day = last_day_of_month(first_day)
    return first_day, last_day


def _test():
    '''repository of all tests

    -- doctests ----

    >>> month_name(5)
    'May'

    >>> get_weekday_index('thur')
    3

    >>> l = get_exception_dates('thursday', (1, 3), '1-dec-07', '15-jan-08')
    >>> l
    [datetime.datetime(2007, 12, 13, 0, 0), datetime.datetime(2007, 12, 27, 0, 0), datetime.datetime(2008, 1, 10, 0, 0)]

    >>> print_exception_dates('thur', (1,3), '1-dec-07', '31-dec-07')
    '2007-12-13', '2007-12-27'

    >>> l = date_range('1-jul-08', '3-jul-08', False)
    >>> l
    [datetime.datetime(2008, 7, 1, 0, 0), datetime.datetime(2008, 7, 2, 0, 0), datetime.datetime(2008, 7, 3, 0, 0)]
    >>> l = date_range('3-jul-08', '1-jul-08', False)
    >>> l
    [datetime.datetime(2008, 7, 1, 0, 0), datetime.datetime(2008, 7, 2, 0, 0), datetime.datetime(2008, 7, 3, 0, 0)]
    >>> l = date_range('3-jul-08', '1-jul-08', True)
    >>> l.next()
    datetime.datetime(2008, 7, 1, 0, 0)

    >>> first_day_of_month('2-jun-09')
    datetime.date(2009, 6, 1)

    >>> d = datetime.date(2009, 7, 15)
    >>> first_day_of_month(d)
    datetime.date(2009, 7, 1)

    >>> d = datetime.date(2009, 7, 15)
    >>> last_day_of_month(d)
    datetime.date(2009, 7, 31)

    >>> d = '28-7-09'
    >>> last_day_of_month(d)
    datetime.date(2009, 7, 31)
    >>> result =last_day_of_month(parse_date('1-dec-2010'))
    >>> expected_result = datetime.date(2010, 12, 31)
    >>> test_result = True if expected_result == result else 'expected %s >>> but got <<< %s' % (expected_result,  result)
    >>> test_result
    True


    >>> d = '28-7-09'
    >>> is_last_day_of_month(d)
    False

    >>> d = '31-7-09'
    >>> is_last_day_of_month(d)
    True

    >>> d = first_weekday_of_month('AUG-2009')
    >>> d
    datetime.date(2009, 8, 3)
    >>> d = first_weekday_of_month('JUL-2009')
    >>> d
    datetime.date(2009, 7, 1)
    >>> result = list(month_range('dec-08', 'feb-09'))
    >>> expected_result = ['DEC-2008', 'JAN-2009', 'FEB-2009']
    >>> test_result = True if expected_result == result else 'expected %s but got %s' % (expected_result, result)
    >>> test_result
    True
    >>> result = month_quarter('1-FEB-2010')
    >>> expected_result = 1
    >>> test_result = True if expected_result == result else 'expected %s >>> but got <<< %s' % (expected_result,  result)
    >>> test_result
    True
    >>> result = month_quarter(parse_date('1-feb-2010'))
    >>> expected_result = 1
    >>> test_result = True if expected_result == result else 'expected %s >>> but got <<< %s' % (expected_result,  result)
    >>> test_result
    True
    >>> result = month_string('1-feb-2010')
    >>> expected_result = 'FEB'
    >>> test_result = True if expected_result == result else 'expected %s >>> but got <<< %s' % (expected_result,  result)
    >>> test_result
    True
    >>> result = month_string('1-feb-2010',short=False, uppercase = False)
    >>> expected_result = 'February'
    >>> test_result = True if expected_result == result else 'expected %s >>> but got <<< %s' % (expected_result,  result)
    >>> test_result
    True

    >>> result = month_string(parse_date('1-mar-2010'))
    >>> expected_result = 'MAR'
    >>> test_result = True if expected_result == result else 'expected %s >>> but got <<< %s' % (expected_result,  result)
    >>> test_result
    True
    >>> result = date1_later_than_date2(datetime.date.today(), datetime.datetime.now())
    >>> expected_result = 0
    >>> test_result = True if expected_result == result else 'expected %s >>> but got <<< %s' % (expected_result,  result)
    >>> test_result
    True
    >>> result = is_odd_day('27-Jan-10')
    >>> expected_result = True
    >>> test_result = True if expected_result == result else 'expected %s but got %s' % (expected_result,  result)
    >>> test_result
    True
    >>> result = is_odd_day('26-Jan-10')
    >>> expected_result = False
    >>> test_result = True if expected_result == result else 'expected %s but got %s' % (expected_result,  result)
    >>> test_result
    True
    >>> result = month_diff('1-may-10', '1-may-10')
    >>> expected_result = 0
    >>> test_result = True if expected_result == result else 'expected %s >>> but got <<< %s' % (expected_result,  result)
    >>> test_result
    True
    >>> result = month_diff('15-may-10', '1-may-10')
    >>> expected_result = 0
    >>> test_result = True if expected_result == result else 'expected %s >>> but got <<< %s' % (expected_result,  result)
    >>> test_result
    True
    >>> result = month_diff('1-may-10', '15-may-10')
    >>> expected_result = 0
    >>> test_result = True if expected_result == result else 'expected %s >>> but got <<< %s' % (expected_result,  result)
    >>> test_result
    True
    >>> result = month_diff('1-jun-10', '15-may-10')
    >>> expected_result = 1
    >>> test_result = True if expected_result == result else 'expected %s >>> but got <<< %s' % (expected_result,  result)
    >>> test_result
    True
    >>> result = month_diff('1-apr-10', '15-may-10')
    >>> expected_result = -1
    >>> test_result = True if expected_result == result else 'expected %s >>> but got <<< %s' % (expected_result,  result)
    >>> test_result
    True
    >>> result = month_diff('1-jun-10', '1-may-10')
    >>> expected_result = 1
    >>> test_result = True if expected_result == result else 'expected %s >>> but got <<< %s' % (expected_result,  result)
    >>> test_result
    True
    >>> result = week_diff('5-may-10', '7-may-10')
    >>> expected_result = 0
    >>> test_result = True if expected_result == result else 'expected %s >>> but got <<< %s' % (expected_result,  result)
    >>> test_result
    True
    >>> result = week_diff('5-may-10', '1-may-10')
    >>> expected_result = 1
    >>> test_result = True if expected_result == result else 'expected %s >>> but got <<< %s' % (expected_result,  result)
    >>> test_result
    True
    >>> quarter_start_end_dates('2009q1')
    (datetime.datetime(2009, 1, 1, 0, 0), datetime.datetime(2009, 3, 31, 0, 0))
    >>> quarter_start_end_dates('09q1')
    (datetime.datetime(2009, 1, 1, 0, 0), datetime.datetime(2009, 3, 31, 0, 0))
    >>> quarter_start_end_dates('q109')
    (datetime.datetime(2009, 1, 1, 0, 0), datetime.datetime(2009, 3, 31, 0, 0))
    >>> quarter_start_end_dates('q12009')
    (datetime.datetime(2009, 1, 1, 0, 0), datetime.datetime(2009, 3, 31, 0, 0))
    >>> quarter_start_end_dates('q1-2009')
    (datetime.datetime(2009, 1, 1, 0, 0), datetime.datetime(2009, 3, 31, 0, 0))
    >>> get_normalized_quarter_date_ranges({'q12009' : 10, 'q22009': 20, 'q32009': 20})
    {datetime.datetime(2009, 4, 1, 0, 0): 20, datetime.datetime(2009, 1, 1, 0, 0): 10}
    >>> get_normalized_quarter_date_ranges({'q12009' : 10, 'q22009': 10, 'q32009': 20})
    {datetime.datetime(2009, 7, 1, 0, 0): 20, datetime.datetime(2009, 1, 1, 0, 0): 10}

    >>> t = is_month('JUL-10')
    >>> t != None
    True
    >>> is_month('xxx-10')
    False
    >>> count_nday_in_date_range('1-mar-11', '15-mar-11', 'mon')
    2
    >>> count_nday_in_date_range('1-mar-11', '15-mar-11', 'tue')
    3
    >>> count_nday_in_date_range('1-mar-11', '5-mar-11', 'mon')
    0
    >>> count_nday_in_date_range('1-mar-11', '5-mar-10', 'mon')
    Traceback (most recent call last):
    ...
    AssertionError: end_date is earlier than start_date
    '''
    from minimock import Mock
    import doctest
    zd.output_to_stdout = False
    doctest.testmod(optionflags=doctest.ELLIPSIS + doctest.NORMALIZE_WHITESPACE)
    doctest.master.summarize(True)



aspect.wrap_module(__name__)




# def main
def fire():
    bv_fire.Fire(Runner)

@attr.s
class Runner (bv_fire._Runner):
    """
        This is a collection of xintila tasks

        Usage:
        sl  to do_something
    """
    def test(self):
        """
        run tests within this module

        Args:
            parameter(str): the path_file of the leads file

        """
        _test()

    def list_days_of_month(self, year, month, day):
        """
        firstweekday=calendar.SUNDAY

        Args:
            year (int or iterable of int): The first parameter.
            month (int or iterable of int): The second parameter.
            day (int or iterable of int)

        Returns:
            list of dates of month

        """
        for d in get_weekdays_of_month(year, month, day):
            beeprint.pp(d)


if __name__=="__main__":
    fire()


