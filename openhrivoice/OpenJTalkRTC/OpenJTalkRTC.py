#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''OpenJTalk speech synthesis component

Copyright (C) 2010
    Yosuke Matsusaka
    Intelligent Systems Research Institute,
    National Institute of Advanced Industrial Science and Technology (AIST),
    Japan
    All rights reserved.

Copyright (C) 2017
    Isao Hara,
    National Institute of Advanced Industrial Science and Technology (AIST), Japan
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
import optparse
import wave
import socket
import OpenRTM_aist
import RTC
from openhrivoice.__init__ import __version__
from openhrivoice import utils
from openhrivoice.config import config
from openhrivoice.OpenJTalkRTC.parseopenjtalk import parseopenjtalk
from openhrivoice.VoiceSynthComponentBase import *
try:
    import gettext
    _ = gettext.translation(domain='openhrivoice', localedir=os.path.dirname(__file__)+'/../share/locale').ugettext
except:
    _ = lambda s: s

__doc__ = _('Japanese speech synthesis component.')

'''
NAIST Japanese Dictionary
Version 0.6.1-20090630 (http://naist-jdic.sourceforge.jp/)
Copyright (C) 2009 Nara Institute of Science and Technology
All rights reserved.

open_jtalk - The Japanese TTS system "Open JTalk"

  usage:
       open_jtalk [ options ] [ infile ]
  options:                                                                   [  def][ min-- max]
    -x  dir        : dictionary directory                                    [  N/A]
    -m  htsvoice   : HTS voice files                                         [  N/A]
    -ow s          : filename of output wav audio (generated speech)         [  N/A]
    -ot s          : filename of output trace information                    [  N/A]
    -s  i          : sampling frequency                                      [ auto][   1--    ]
    -p  i          : frame period (point)                                    [ auto][   1--    ]
    -a  f          : all-pass constant                                       [ auto][ 0.0-- 1.0]
    -b  f          : postfiltering coefficient                               [  0.0][ 0.0-- 1.0]
    -r  f          : speech speed rate                                       [  1.0][ 0.0--    ]
    -fm f          : additional half-tone                                    [  0.0][    --    ]
    -u  f          : voiced/unvoiced threshold                               [  0.5][ 0.0-- 1.0]
    -jm f          : weight of GV for spectrum                               [  1.0][ 0.0--    ]
    -jf f          : weight of GV for log F0                                 [  1.0][ 0.0--    ]
    -g  f          : volume (dB)                                             [  0.0][    --    ]
    -z  i          : audio buffer size (if i==0, turn off)                   [    0][   0--    ]
  infile:
    text file                                                                [stdin]
'''

#
#  OpenJTalk Process Wrapper
#
class OpenJTalkWrap(VoiceSynthBase):
    #
    #
    #
    def __init__(self, prop):
        VoiceSynthBase.__init__(self)
        self._conf = config()
        self._args = ()

        if prop.getProperty("openjtalk.3rdparty_dir") :
            self._conf.openjtalk(prop.getProperty("openjtalk.3rdparty_dir"))

        openjtalk_bin=prop.getProperty("openjtalk.bin")
        if not openjtalk_bin : openjtalk_bin = self._conf._openjtalk_bin

        cmdarg = [ openjtalk_bin ]
        (stdoutstr, stderrstr) = subprocess.Popen(cmdarg, stdout = subprocess.PIPE, stderr = subprocess.PIPE).communicate()

        #
        #  Read Copyright Files of Phonemodels
        #
        self._copyrights = []
        for l in stderrstr.replace('\r', '').split('\n\n'):
            if l.count('All rights reserved.') > 0:
                self._copyrights.append(l)
        #
        #  read copyright
        self._copyrights.append(utils.read_file_contents('hts_voice_copyright.txt'))
        self._copyrights.append(utils.read_file_contents('mmdagent_mei_copyright.txt'))

   #
   #  TTS conversion
   #
    def synthreal(self, data, samplerate, character):
        textfile = self.gettempname()
        wavfile  = self.gettempname()
        logfile  = self.gettempname()

        # text file which specifies synthesized string
        fp = codecs.open(textfile, 'w', 'utf-8')
        fp.write(u"%s\n" % (data,))
        fp.close()

        # command line for OpenJTalk 
        cmdarg = [ self._conf._openjtalk_bin ]
        #
        #  select phonemodel
        if character == "female":
            cmdarg.extend(["-m", self._conf._openjtalk_phonemodel_female_ja])
        else:
            cmdarg.extend(["-m", self._conf._openjtalk_phonemodel_male_ja])
        #
        #  audio buffer size
        #cmdarg.extend(["-z", "2000"])
        #
        #  sampling rate
        #if samplerate > 0:
        #    cmdarg.extend(["-s", str(samplerate)])
        #
        # dictionary directory
        cmdarg.extend(["-x", self._conf._openjtalk_dicfile_ja])
        #
        # filename of output wav audio and filename of output trace information
        cmdarg.extend(["-ow", wavfile, "-ot", logfile])
        #
        # text file(input)
        cmdarg.append(textfile)

        # run OpenJTalk
        #    String ---> Wav data
        p = subprocess.Popen(cmdarg)
        p.wait()

        # convert samplerate
        # normally openjtalk outputs 48000Hz sound.
        wavfile2 = self.gettempname()
        cmdarg = [self._conf._sox_bin, "-t", "wav", wavfile, "-r", str(samplerate), "-t", "wav", wavfile2]
        print cmdarg
        p = subprocess.Popen(cmdarg)
        p.wait()

        os.remove(wavfile)
        wavfile = wavfile2

        # read duration data
        d = parseopenjtalk()
        d.parse(logfile)
        durationdata = d.toseg().encode("utf-8")
        os.remove(textfile)
        os.remove(logfile)
        return (durationdata, wavfile)

    #
    #  terminated
    #
    def terminate(self):
        pass
#
#  for RTC specification
#
OpenJTalkRTC_spec = ["implementation_id", "OpenJTalkRTC",
                     "type_name",         "OpenJTalkRTC",
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
                     "conf.__constraints__.format", "(int16)",
                     "conf.__description__.format", _("Format of output audio (fixed to 16bit).").encode('UTF-8'),
                     "conf.default.rate", "16000",
                     "conf.__widget__.rate", "spin",
                     "conf.__constraints__.rate", "16000",
                     "conf.__description__.rate", _("Sampling frequency of output audio (fixed to 16kHz).").encode('UTF-8'),
                     "conf.default.character", "male",
                     "conf.__widget__.character", "radio",
                     "conf.__constraints__.character", "(male, female)",
                     "conf.__description__.character", _("Character of the voice.").encode('UTF-8'),
                     ""]
#
#  OpenJTalkRTC class
#
class OpenJTalkRTC(VoiceSynthComponentBase):
    #
    # Constructor
    #
    def __init__(self, manager):
        VoiceSynthComponentBase.__init__(self, manager)

    #
    #  OnInitialize
    #
    def onInitialize(self):
        VoiceSynthComponentBase.onInitialize(self)

        self._wrap = OpenJTalkWrap(self._properties)
        self._logger.RTC_INFO("This component depends on following softwares and datas:")
        self._logger.RTC_INFO('')
        for c in self._wrap._copyrights:
            for l in c.strip('\n').split('\n'):
                self._logger.RTC_INFO('  '+l)
            self._logger.RTC_INFO('')
        return RTC.RTC_OK

#
#  OpenJTalkRTC Manager class
#
class OpenJTalkRTCManager:
    #
    # Constructor
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
    #  Start RTC_Manager
    #
    def start(self):
        self._manager.runManager(False)

    #
    #  Module Initializer
    #
    def moduleInit(self, manager):
        profile=OpenRTM_aist.Properties(defaults_str=OpenJTalkRTC_spec)
        manager.registerFactory(profile, OpenJTalkRTC, OpenRTM_aist.Delete)
        self._comp = manager.createComponent("OpenJTalkRTC")

#
#  Main Function
#
if __name__=='__main__':
    manager = OpenJTalkRTCManager()
    manager.start()
