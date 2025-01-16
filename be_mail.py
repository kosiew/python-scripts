__author__ = "Siew Kam Onn"
# ##filename=be_mail.py, edited on 26 Jan 2019 Sat 07:25 PM
# filename=be_mail.py, edited on 20 Apr 2016 Wed 09:43 AM
__email__ = "kosiew at gmail.com"
__version__ = "$Revision: 1.0 $"
__date__ = "$Date: 19/Apr/2016"
__copyright__ = "Copyright (c) 2006 Siew Kam Onn"
__license__ = "Python"

"""
    This module is like kl_alert but will send from my personal
    email and not cc ske recipients

"""

import zd
import aspect
import a
import kl_alert
import bv_me

FROM_ACCOUNT = bv_me.GMAIL
TO = bv_me.GMAIL
CC = []
DEFAULT_BCC = []


TEMPLATE = '''
Hi %s,

%s

at your service,
GmailBot










script: %s

'''

class Alert (kl_alert.Alert):
    """
        Alert is a type of kl_alert.Alert
        a Alert class_definition
    """


    def __init__(self, attach_as_zip = False,
        include_auto_generated_message = True,
        simulate = False,
        from_account = FROM_ACCOUNT,
        password = None,
        use_default_bcc = False):
        import bv_gmail # import this late

        password = bv_gmail.get_password(from_account)
        super(Alert, self).__init__(attach_as_zip,
            include_auto_generated_message,
            simulate,
            from_account,
            password,
            use_default_bcc)

    def get_template(self):
        """
        """
        global TEMPLATE

        result = TEMPLATE
        return result

    def process_cc(self, cc):
        """
        """
        result = []
        return result

    def append_alertee_cc(self, cc):
        """
        """
        result = []
        return result


    def send_alert_mail(self, subject, message = None, to = TO,
        salutation = '', cc = CC, script_name = '',
        debug_information = False,
        bcc = DEFAULT_BCC):
        super(Alert, self).send_alert_mail(subject,
            message,
            to,
            salutation,
            cc,
            script_name,
            debug_information,
            bcc)

    def set_cancel_send(self, cancel_send = True):
        ''' Returns True if
        '''
        self.cancel_send = cancel_send

        return cancel_send

##aspect.add_tracing_prints_to_all_methods(Alert)

def set_test_mode(test_mode):
    """
    """
    return kl_alert.set_test_mode(test_mode)


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

