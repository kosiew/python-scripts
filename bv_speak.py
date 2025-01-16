
# ##filename=bv_speak.py, edited on 26 Oct 2022 Wed 09:50 AM

__author__ = "Siew Kam Onn"
__email__ = "kosiew at gmail.com"
__version__ = "$Revision: 1.0 $"
__date__ = "$Date: 01/May/2018"
__copyright__ = "Copyright (c) 2018 Siew Kam Onn"
__license__ = "Python"

"""
    This module contains text to speech utilties

"""

import zd
import aspect
import a
import attr
import random
# https://pyttsx3.readthedocs.io/en/latest/engine.html
import pyttsx3


PRINT_SAY = True
ROBOT = None
MUTE = False

class Error (Exception):
    """
        Error is a type of Exception
        Base class for all exception raised by this module
    """
    pass


class Robot:

    RATE = 6
    VOLUME = 100
    DEFAULT_VOICE_INDEX = 17

    ENGLISH_VOICES = (0, 7, 10, 11, 17, 18, 29, 33, 34, 37, 39, 42, 43,)
    CHINESE_VOICES = (26, 41)
    CANTONESE_VOICE = (38,)

    # english voices 0,7,11, 33, 34, 37, 42, 43
    # english voices 10, 17, 18
    # chinese voices 26, 41
    # cantonese voice 38

    def __init__(self):
        self.engine = self.get_engine()
        try:
            self.voices = self.get_voices()
            self.set_voice_index(Robot.DEFAULT_VOICE_INDEX)
        except Exception as e:
            self.voices = []
            zd.p('Using default voice')

    def get_voices(self):
        voices = engine.getProperty('voices')
        return voices


    def set_voice_index(self, voice_index):
        voice_id = self.get_voice_id(voice_index)
        self.set_voice_id(voice_id)

    def randomize_voice(self, voices = ENGLISH_VOICES):
        voice_index = random.choice(voices)
        self.set_voice_index(voice_index)
        zd.p(f'random voice index {voice_index}')

    def set_voice_id(self, voice_id):
        self.engine.setProperty('voice', voice_id)

    def list_voices(self):
        for i in range(9):
            try:
                description = self.engine.GetVoices().Item(i).GetDescription()
                print(i, description)
            except Exception as e:
                pass

    def get_voice_id(self, voice_index):
        for i, voice in enumerate(self.voices):
            if i == voice_index:
                return voice.id
        return 0

    def get_engine(self, rate=RATE, volume=VOLUME):
        engine = pyttsx3.init()
        return engine

    def test_voices(self):
        """
        """
        for i, voice in enumerate(self.voices):
            self.engine.setProperty('voice', voice.id)
            self._say(f'Number {i}.  This is a test')

    def _say(self, text, print_say=PRINT_SAY):
        global MUTE
        if not MUTE:
            self.engine.say(text)
        if print_say:
            print(text)
        if not MUTE:
            self.engine.runAndWait()

    def say(self, text, print_say=PRINT_SAY):
        count = 0
        if isinstance(text, (list, tuple)):
            for _text in text:
                self._say(_text, print_say)
                count += 1
        else:
            self._say(text, print_say)
            count = 1
        return count

def mute(flag=True):
    global MUTE
    MUTE = flag

def _test():
    '''Runs all tests

    '''

    zd.output_to_stdout = False
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS + doctest.NORMALIZE_WHITESPACE, verbose=False)
    doctest.master.summarize(True)

def get_robot():
    global ROBOT
    if ROBOT:
        return ROBOT
    else:
        ROBOT = Robot()
        return ROBOT

aspect.wrap_module(__name__)

if __name__ == "__main__":
    _test()

