#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Voice segmentation component

Copyright (C) 2017
    Isao Hara
    National Institute of Advanced Industrial Science and Technology (AIST),
    Japan
    All rights reserved.

Licensed under the Eclipse Public License -v 1.0 (EPL)
http://www.opensource.org/licenses/eclipse-1.0.txt
'''

import sys, os, socket, subprocess, signal, threading, platform
import time, struct, traceback, locale, codecs, getopt, wave, tempfile
import optparse
import traceback

import wave
from pydub import AudioSegment
from pydub.silence import *

import OpenRTM_aist
import RTC
from openhrivoice.__init__ import __version__
from openhrivoice import utils
from openhrivoice.config import config
try:
    import gettext
    _ = gettext.translation(domain='openhrivoice', localedir=os.path.dirname(__file__)+'/../share/locale').ugettext
except:
    _ = lambda s: s

__doc__ = _('Voice Segmentation component.')


#
#  
#
class VoiceSegmentWrap(threading.Thread):
    
    #
    #  Constructor
    #
    def __init__(self, language='jp', rtc=''):
        threading.Thread.__init__(self)
        self._config = config()
        self._platform = platform.system()
        self._callbacks = []
        self._buffer = []
        self.audio_segment = []
        self._sample_width=2
        self._frame_rate=16000
        self._channels=1
        self._min_slience=150
        self._silence_thr=-20

    #
    #  Terminate (Call on Finished)
    #
    def terminate(self):
        print 'Terminate'
        return 0

    #
    #   Write to audio data
    #
    def write(self, data):
        try:
            self._buffer.extend(data)
            if len(self._buffer) >= 5000:
                audio=AudioSegment(self._buffer, sample_width=self._sample_width, channels=self._channels, frame_rate=self._frame_rate)
                chunks = detect_nonsilent(audio, min_silence_len=_min_slience, silence_thresh=self._silence_thr)

                if chunks :
                    self.audio_segment.extend( self._buffer)
                else:
                    if self.audio_segment :
                        self.save_to_wav("test.wav", self.audio_segment)
                        self.audio_segment=[]
                self._buffer = []

        except:
            print traceback.format_exc()
            pass
        return 0

    #
    #  Run
    #
    def run(self):
	pass

    #
    #  Set callback function
    #
    def setcallback(self, func):
        self._callbacks.append(func)

    #
    #  Save to Wav file
    #
    def save_to_wav(self, name, data):
        wave_data = wave.open(name, 'wb')
        wave_data.setnchannels(self._channels)
        wave_data.setsampwidth(self._sample_width)
        wave_data.setframerate(self._frame_rate)
        
        wave_data.setnframes(int(len(data) / (self._sample_width * self._channels)))
        wave_data.writeframesraw(bytearray(data))
        wave_data.close()

#
#  JuliusRTC 
#
VoiceSegmentRTC_spec = ["implementation_id", "VoiceSegmentRTC",
                  "type_name",         "VoiceSegmentRTC",
                  "description",       __doc__.encode('UTF-8'),
                  "version",           __version__,
                  "vendor",            "AIST",
                  "category",          "communication",
                  "activity_type",     "DataFlowComponent",
                  "max_instance",      "1",
                  "language",          "Python",
                  "lang_type",         "script",
                  ""]
#
#  DataListener class
#
class DataListener(OpenRTM_aist.ConnectorDataListenerT):
    #
    #  Constructor
    #
    def __init__(self, name, obj, dtype):
        self._name = name
        self._obj = obj
        self._dtype = dtype
    
    #
    #  
    #
    def __call__(self, info, cdrdata):
        data = OpenRTM_aist.ConnectorDataListenerT.__call__(self, info, cdrdata, self._dtype(RTC.Time(0,0),None))
        self._obj.onData(self._name, data)

#
#  VoiceSegmentRTC Class
#
class VoiceSegmentRTC(OpenRTM_aist.DataFlowComponentBase):
    #
    #  Constructor
    #
    def __init__(self, manager):
        OpenRTM_aist.DataFlowComponentBase.__init__(self, manager)
        self._config = config()
        self._j = None

        self._copyrights = []
        self._copyrights.append( utils.read_file_contents(os.path.join( self._config._basedir, "doc", "julius_copyright.txt")))
        self._copyrights.append( utils.read_file_contents(os.path.join( self._config._basedir, "doc", "voxforge_copyright.txt")))

    #
    #  OnInitialize
    #
    def onInitialize(self):
        OpenRTM_aist.DataFlowComponentBase.onInitialize(self)
        self._logger = OpenRTM_aist.Manager.instance().getLogbuf(self._properties.getProperty("instance_name"))
        self._logger.RTC_INFO("JuliusRTC version " + __version__)
        self._logger.RTC_INFO("Copyright (C) 2017 Isao Hara")

        #
        # create inport for audio stream
        self._indata = RTC.TimedOctetSeq(RTC.Time(0,0), None)
        self._inport = OpenRTM_aist.InPort("data", self._indata)
        self._inport.appendProperty('description', _('Audio data (in packets) to be recognized.').encode('UTF-8'))
        self._inport.addConnectorDataListener(OpenRTM_aist.ConnectorDataListenerType.ON_BUFFER_WRITE,
                                              DataListener("data", self, RTC.TimedOctetSeq))
        self.registerInPort(self._inport._name, self._inport)

        #
        # create outport for result
        self._outdata = RTC.TimedString(RTC.Time(0,0), "")
        self._outport = OpenRTM_aist.OutPort("result", self._outdata)
        self._outport.appendProperty('description', _('Recognition result in XML format.').encode('UTF-8'))
        self.registerOutPort(self._outport._name, self._outport)

        self._logger.RTC_INFO("This component depends on following softwares and datas:")
        self._logger.RTC_INFO('')
        for c in self._copyrights:
            for l in c.strip('\n').split('\n'):
                self._logger.RTC_INFO('  '+l)
            self._logger.RTC_INFO('')

        return RTC.RTC_OK

    #
    #  OnFinalize
    #
    def onFinalize(self):
        OpenRTM_aist.DataFlowComponentBase.onFinalize(self)
#        if self._j:
#            self._j.terminate()
#            self._j.join()
#            self._j = None
        return RTC.RTC_OK

    #
    #  OnActivate
    #
    def onActivated(self, ec_id):
        OpenRTM_aist.DataFlowComponentBase.onActivated(self, ec_id)

        self._j = VoiceSegmentWrap('ja', self)
#        self._j.start()
#        self._j.setcallback(self.onResult)

#        while self._j._gotinput == False:
#            time.sleep(0.1)

        return RTC.RTC_OK

    #
    #  OnDeactivate
    #
    def onDeactivate(self, ec_id):
        OpenRTM_aist.DataFlowComponentBase.onDeactivate(self, ec_id)
        if self._j:
#            self._j.terminate()
#            self._j.join()
            self._j = None
        return RTC.RTC_OK

    #
    #  OnData (Callback from DataListener)
    #
    def onData(self, name, data):
        if self._j:
            if name == "data":
                self._j.write(data.data)


    #
    #  OnExecute (Do nothing)
    #
    def onExecute(self, ec_id):
        OpenRTM_aist.DataFlowComponentBase.onExecute(self, ec_id)
        return RTC.RTC_OK

    #
    #  OnResult
    #
    def onResult(self, type, data):
        print data
        pass


#
#  Manager Class
#
class VoiceSegmentRTCManager:
    #
    #  Constructor
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
    #  Start component
    #
    def start(self):
        self._manager.runManager(False)

    #
    #  Initialize rtc
    #
    def moduleInit(self, manager):
        profile = OpenRTM_aist.Properties(defaults_str = VoiceSegmentRTC_spec)
        manager.registerFactory(profile, VoiceSegmentRTC, OpenRTM_aist.Delete)

        self._comp = manager.createComponent("VoiceSegmentRTC?exec_cxt.periodic.rate=1")

#
#  Main
#
if __name__=='__main__':
    manager = VoiceSegmentRTCManager()
    manager.start()

