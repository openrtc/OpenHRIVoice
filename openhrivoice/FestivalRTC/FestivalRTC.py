#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Festival speech synthesis component

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
import subprocess
import signal
import tempfile
import traceback
import platform
import codecs
import locale
import wave
import optparse
import OpenRTM_aist
import RTC
from openhrivoice.__init__ import __version__
from openhrivoice import utils
from openhrivoice.config import config
from openhrivoice.VoiceSynthComponentBase import *
try:
    import gettext
    _ = gettext.translation(domain='openhrivoice', localedir=os.path.dirname(__file__)+'/../share/locale').ugettext
except:
    _ = lambda s: s

__doc__ = _('English speech synthesis component.')

#
#  Festival Wrapper class
#
class FestivalWrap(VoiceSynthBase):
    #
    # Constructor
    def __init__(self, prop):
        VoiceSynthBase.__init__(self)
        self._config = config()

        if prop.getProperty("festival.3rdparty_dir") :
            self._config.festival(prop.getProperty("festival.3rdparty_dir"))

        self._cmdline =[self._config._festival_bin, '--pipe']
        self._cmdline.extend(self._config._festival_opt)
        self._copyrights = []
        self._copyrights.append(utils.read_file_contents('festival_copyright.txt'))
        self._copyrights.append(utils.read_file_contents('diphone_copyright.txt'))

    #
    #  Syntheseizer 
    def synthreal(self, data, samplerate, character):
        textfile = self.gettempname()
        durfile = self.gettempname().replace("\\", "\\\\")
        wavfile = self.gettempname().replace("\\", "\\\\")
        # text file which specifies synthesized string
        fp = codecs.open(textfile, 'w', 'utf-8')
        fp.write('(set! u (Utterance Text "' + data + '"))')
        fp.write('(utt.synth u)')
        fp.write('(utt.save.segs u "' + durfile + '")')
        fp.write('(utt.save.wave u "' + wavfile + '")')
        fp.close()

        # run Festival
        cmdarg =[self._config._festival_bin,] + self._config._festival_opt + ['-b', textfile]
        p = subprocess.Popen(cmdarg)
        p.wait()
        #p = subprocess.Popen(self._cmdline, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        #p.stdin.write('(set! u (Utterance Text "' + data + '"))')
        #p.stdin.write('(utt.synth u)')
        #p.stdin.write('(utt.save.segs u "' + durfile + '")')
        #p.stdin.write('(utt.save.wave u "' + wavfile + '")')
        #p.communicate()

        # read data
        df = open(durfile, 'r')
        durationdata = df.read().encode("utf-8")
        df.close()
        os.remove(durfile)
        return (durationdata, wavfile)


#
#  RT-Component
#
FestivalRTC_spec = ["implementation_id", "FestivalRTC",
                    "type_name",         "FestivalRTC",
                    "description",       __doc__.encode('UTF-8'),
                    "version",           __version__,
                    "vendor",            "AIST",
                    "category",          "communication",
                    "activity_type",     "DataFlowComponent",
                    "max_instance",      "5",
                    "language",          "Python",
                    "lang_type",         "script",
                    "conf.default.format", "int16",
                    "conf.__widget__.format", "radio",
                    "conf.__constraints__.format", "int16",
                    "conf.__description__.format", _("Format of output audio (fixed to 16bit).").encode('UTF-8'),
                    "conf.default.rate", "16000",
                    "conf.__widget__.rate", "spin",
                    "conf.__constraints__.rate", "x == 16000",
                    "conf.__description__.rate", _("Sampling frequency of output audio (fixed to 16kHz).").encode('UTF-8'),
                    "conf.default.character", "male",
                    "conf.__widget__.character", "radio",
                    "conf.__constraints__.character", "(male)",
                    "conf.__description__.character", _("Character of the voice (fixed to male).").encode('UTF-8'),
                    ""]

#
#  FestivalRTC class
#
class FestivalRTC(VoiceSynthComponentBase):
    #
    # Constructor
    def __init__(self, manager):
        VoiceSynthComponentBase.__init__(self, manager)

    #
    #  OnInitialize
    def onInitialize(self):
        VoiceSynthComponentBase.onInitialize(self)
        try:
            self._wrap = FestivalWrap(self._properties)
        except:
            self._logger.RTC_ERROR(traceback.format_exc())
            return RTC.RTC_ERROR
        self._logger.RTC_INFO("This component depends on following softwares and datas:")
        self._logger.RTC_INFO('')
        for c in self._wrap._copyrights:
            for l in c.strip('\n').split('\n'):
                self._logger.RTC_INFO('  '+l)
            self._logger.RTC_INFO('')
        return RTC.RTC_OK

#
#   RTC Manager
#
class FestivalRTCManager:
    #
    #
    def __init__(self):
        encoding = locale.getpreferredencoding()
        sys.stdout = codecs.getwriter(encoding)(sys.stdout, errors = "replace")
        sys.stderr = codecs.getwriter(encoding)(sys.stderr, errors = "replace")

        parser = utils.MyParser(version=__version__, description=__doc__)
        utils.addmanageropts(parser)
        try:
            opts, args = parser.parse_args()
        except optparse.OptionError, e:
            print >>sys.stderr, 'OptionError:', e
            sys.exit(1)
        self._comp = None
        self._manager = OpenRTM_aist.Manager.init(utils.genmanagerargs(opts))
        self._manager.setModuleInitProc(self.moduleInit)
        self._manager.activateManager()

    #
    #
    def start(self):
        self._manager.runManager(False)

    #
    #
    def moduleInit(self, manager):
        profile=OpenRTM_aist.Properties(defaults_str=FestivalRTC_spec)
        manager.registerFactory(profile, FestivalRTC, OpenRTM_aist.Delete)
        self._comp = manager.createComponent("FestivalRTC")

#
#
#
def main():
    manager = FestivalRTCManager()
    manager.start()

if __name__=='__main__':
    main()
