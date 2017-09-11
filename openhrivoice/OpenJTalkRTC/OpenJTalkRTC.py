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

        self._sampling_rate = 0
        self._frame_period = 0
        self._all_pass = -1
        self._postfiltering_coefficent = 0.0
        self._speed_rate = 1.0
        self._addtional_half_tone = 0.0
        self._threshold = 0.5
        self._gv_spectrum = 1.0
        self._gv_log_f0 = 1.0
        self._volume = 0.0

        if prop.getProperty("openjtalk.3rdparty_dir") :
            self._conf.openjtalk(prop.getProperty("openjtalk.3rdparty_dir"))

        if prop.getProperty("openjtalk.top_dir") :
            self._conf.openjtalk_top(prop.getProperty("openjtalk.top_dir"))

        if prop.getProperty("openjtalk.sox_dir") :
            self._conf.sox_top(prop.getProperty("openjtalk.sox_dir"))

        openjtalk_bin=prop.getProperty("openjtalk.bin")
        if not openjtalk_bin : openjtalk_bin = self._conf._openjtalk_bin

        if prop.getProperty("openjtalk.phonemodel_male_ja") :
            self._conf._openjtalk_phonemodel_male_ja=prop.getProperty("openjtalk.phonemodel_male_ja")

        if prop.getProperty("openjtalk.phonemodel_female_ja") :
            self._conf._openjtalk_phonemodel_female_ja=prop.getProperty("openjtalk.phonemodel_female_ja")

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
        if self._sampling_rate > 0:
            cmdarg.extend(["-s", str(self._sampling_rate)])

        #   all-pass constant 
        if self._all_pass >= 0.0 and self._all_pass <= 1.0:
            cmdarg.extend(["-a", str(self._all_pass)])

        #   postfiltering coefficient  
        if self._postfiltering_coefficent >= 0.0 and self._postfiltering_coefficent <= 1.0:
            cmdarg.extend(["-b", str(self._postfiltering_coefficent)])

        #
        #
        #  speech speed rate
        if self._speed_rate > 0:
            cmdarg.extend(["-r", str(self._speed_rate)])

        #  additional half-tone
        cmdarg.extend(["-fm", str(self._addtional_half_tone)])

        #   voiced/unvoiced threshold
        if self._threshold >= 0.0 and self._threshold <= 1.0:
            cmdarg.extend(["-u", str(self._threshold)])

        #  weight of GV for spectrum
        if self._gv_spectrum >= 0.0:
            cmdarg.extend(["-jm", str(self._gv_spectrum)])

        #  weight of GV for log F0
        if self._gv_log_f0 >= 0.0:
            cmdarg.extend(["-jf", str(self._gv_log_f0)])

        #  volume (dB) 
        cmdarg.extend(["-g", str(self._volume)])


        #
        # dictionary directory
        cmdarg.extend(["-x", self._conf._openjtalk_dicfile_ja])
        #
        # filename of output wav audio and filename of output trace information
        cmdarg.extend(["-ow", wavfile, "-ot", logfile])
        #
        # text file(input)
        cmdarg.append(textfile)

        print ' '.join(cmdarg)
        # run OpenJTalk
        #    String ---> Wav data
        p = subprocess.Popen(cmdarg)
        p.wait()

        # convert samplerate
        # normally openjtalk outputs 48000Hz sound.
        wavfile2 = self.gettempname()
        cmdarg = [self._conf._sox_bin, "-t", "wav", wavfile, "-r", str(samplerate), "-t", "wav", wavfile2]
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
    #  set cachesize
    #
    def set_cachesize(self, n):
        self._cachesize = n

    #
    #  set params
    #
    def set_params(self, rtc):
        self._sampling_rate = int(rtc._sampling_rate[0])
        self._all_pass = float(rtc._all_pass[0])
        self._postfiltering_coefficent = float(rtc._postfiltering_coefficent[0])
        self._speed_rate = float(rtc._speed_rate[0])
        self._addtional_half_tone = float(rtc._addtional_half_tone[0])
        self._threshold = float(rtc._threshold[0])
        self._gv_spectrum = float(rtc._gv_spectrum[0])
        self._gv_log_f0 = float(rtc._gv_log_f0[0])
        self._volume = float(rtc._volume[0])
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
                     "conf.default.cachesize", "1",
                     "conf.__widget__.cachesize", "text",
                     "conf.__type__.cachesize", "int",
                     "conf.default.sampling_rate", "0",
                     "conf.__widget__.samplig_rate", "text",
                     "conf.__type__.samplig_rate", "int",
                     "conf.default.all_pass", "-1.0",
                     "conf.__widget__.all_pass", "text",
                     "conf.__type__.all_pass", "float",
                     "conf.default.postfiltering_coefficent", "0.0",
                     "conf.__widget__.postfiltering_coefficent", "text",
                     "conf.__type__.postfiltering_coefficent", "float",
                     "conf.default.speed_rate", "1.0",
                     "conf.__widget__.speed_rate", "text",
                     "conf.__type__.speed_rate", "float",
                     "conf.default.half_tone", "0.0",
                     "conf.__widget__.half_tone", "text",
                     "conf.__type__.half_tone", "float",
                     "conf.default.voice_unvoice_threshold", "0.5",
                     "conf.__widget__.voice_unvoice_threshold", "text",
                     "conf.__type__.voice_unvoice_threshold", "float",
                     "conf.default.gv_spectrum", "1.0",
                     "conf.__widget__.gv_spectrum", "text",
                     "conf.__type__.gv_spectrum", "float",
                     "conf.default.gv_log_f0", "1.0",
                     "conf.__widget__.gv_log_f0", "text",
                     "conf.__type__.gv_log_f0", "float",
                     "conf.default.volume", "0.0",
                     "conf.__widget__.volume", "text",
                     "conf.__type__.volume", "float",
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

        self._cachesize=[1]
        self.bindParameter("cachesize", self._cachesize, "1")

        self._sampling_rate=[0]
        self.bindParameter("sampling_rate", self._sampling_rate, "0")
        self._all_pass = [-1.0]
        self.bindParameter("all_pass", self._all_pass, "-1.0")

        self._postfiltering_coefficent = [0.0]
        self.bindParameter("postfiltering_coefficent", self._postfiltering_coefficent, "0.0")

        self._speed_rate=[1.0]
        self.bindParameter("speed_rate", self._speed_rate, "1.0")

        self._addtional_half_tone = [0.0,]
        self.bindParameter("half_tone", self._addtional_half_tone, "0.0")

        self._threshold = [0.5,]
        self.bindParameter("voice_unvoice_threshold", self._threshold, "0.5")

        self._gv_spectrum = [1.0,]
        self.bindParameter("gv_spectrum", self._gv_spectrum, "1.0")

        self._gv_log_f0 = [1.0,]
        self.bindParameter("gv_log_f0", self._gv_log_f0, "1.0")

        self._volume = [0.0]
        self.bindParameter("volume", self._volume, "0.0")


        self._wrap = OpenJTalkWrap(self._properties)
        self._logger.RTC_INFO("This component depends on following softwares and datas:")
        self._logger.RTC_INFO('')
        for c in self._wrap._copyrights:
            for l in c.strip('\n').split('\n'):
                self._logger.RTC_INFO('  '+l)
            self._logger.RTC_INFO('')
        return RTC.RTC_OK
    #
    #
    #
    def onActivated(self, ec_id):
        self._wrap.set_params(self)
        self._wrap.set_cachesize(int(self._cachesize[0]))

        VoiceSynthComponentBase.onActivated(self, ec_id)
        return RTC.RTC_OK
    #
    #  OnData (callback function)
    #
    def onData(self, name, data):
        self._wrap.set_params(self)

        VoiceSynthComponentBase.onData(self, name, data)
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
