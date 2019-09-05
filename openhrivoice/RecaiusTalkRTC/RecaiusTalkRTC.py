#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''RECAIUS speech synthesis component

Copyright (C) 2010
    Yosuke Matsusaka
    Intelligent Systems Research Institute,
    National Institute of Advanced Industrial Science and Technology (AIST),
    Japan
    All rights reserved.
Licensed under the Eclipse Public License -v 1.0 (EPL)
http://www.opensource.org/licenses/eclipse-1.0.txt
'''

import os
import sys
import time
import urllib
import tempfile
import traceback
import codecs
import locale
import wave
import optparse
import OpenRTM_aist
import RTC
from __init__ import __version__
import utils

from VoiceSynthComponentBase import *
from recaius import RecaiusTts


__doc__ = _('German speech synthesis component using MARY.')

class RecaiusTalkWrap(VoiceSynthBase):
    def __init__(self, rtc):
        VoiceSynthBase.__init__(self)

        prop = rtc._properties
        if prop.getProperty("recaius_talk.id") :
            self._recaius_id = prop.getProperty("recaius_talk.id")

        if prop.getProperty("recaius_talk.passwd") :
            self._recaius_passwd=prop.getProperty("recaius_talk.passwd")

        self._lang = rtc._language
        self._recaius = RecaiusTts(self._recaius_id, self._recaius_passwd, self._lang[0])

    def getaudio(self, data, character):
        wavfile = self.gettempname()
        self._recaius.getaudio(data, wavfile, self._recaius.getSpeakerId(character, self._lang[0]))

        return wavfile


    def synthreal(self, data, samplerate, character):
        wavfile = self.getaudio(data, character)
        return ("", wavfile)

RecaiusTalkRTC_spec = ["implementation_id", "RecaiusTalkRTC",
                "type_name",         "RecaiusTalkRTC",
                "description",       __doc__,
                "version",           __version__,
                "vendor",            "AIST",
                "category",          "communication",
                "activity_type",     "DataFlowComponent",
                "max_instance",      "5",
                "language",          "Python",
                "lang_type",         "script",
                "conf.default.format", "int16",
                "conf.default.rate", "16000",
                "conf.default.character", "male",
                "conf.__widget__.format", "radio",
                "conf.__constraints__.format", "(int16)",
                "conf.__description__.format", "Format of output audio (fixed to 16bit).",
                "conf.__widget__.rate", "spin",
                "conf.__constraints__.rate", "x == 16000",
                "conf.__description__.rate", "Sampling frequency of output audio (fixed to 16kHz).",
                "conf.__widget__.character", "radio",
                "conf.__constraints__.character", "(male, female)",
                "conf.__description__.character", "Character of the voice.",
                "conf.default.language", "ja_JP",
                "conf.__widget__.language", "text",
                ""]

class RecaiusTalkRTC(VoiceSynthComponentBase):
    def __init__(self, manager):
        VoiceSynthComponentBase.__init__(self, manager)

    def onInitialize(self):
        VoiceSynthComponentBase.onInitialize(self)
        self._language = ["ja_JP"]
        self.bindParameter("language", self._language, "ja_JP")

        self._wrap = None

        return RTC.RTC_OK

    #
    #
    #
    def onActivated(self, ec_id):
        try:
            self._wrap = RecaiusTalkWrap(self)
        except:
            self._logger.RTC_ERROR(traceback.format_exc())
            return RTC.RTC_ERROR

        VoiceSynthComponentBase.onActivated(self, ec_id)
        return RTC.RTC_OK


class RecaiusTalkRTCManager:
    def __init__(self):
        parser = optparse.OptionParser(version=__version__, description=__doc__)
        utils.addmanageropts(parser)
        try:
            opts, args = parser.parse_args()
        except optparse.OptionError as e:
            print ('OptionError:', e, file=sys.stderr)
            sys.exit(1)
        self._comp = None
        self._manager = OpenRTM_aist.Manager.init(utils.genmanagerargs(opts))
        self._manager.setModuleInitProc(self.moduleInit)
        self._manager.activateManager()

    def start(self):
        self._manager.runManager(False)

    def moduleInit(self, manager):
        profile=OpenRTM_aist.Properties(defaults_str=RecaiusTalkRTC_spec)
        manager.registerFactory(profile, RecaiusTalkRTC, OpenRTM_aist.Delete)
        self._comp = manager.createComponent("RecaiusTalkRTC")

def main():
    manager = RecaiusTalkRTCManager()
    manager.start()

if __name__=='__main__':
    main()
