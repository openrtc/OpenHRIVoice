#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Google Speech Recognition component

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

import json
import urllib
import urllib2

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


__doc__ = _('Google Speech Recognition component.')


#
#  
#
class GoogleSpeechRecogWrap(object):
    
    #
    #  Constructor
    #
    def __init__(self, rtc, language='ja-JP'):
        self._config = config()
        self._platform = platform.system()
        self._callbacks = []


        self._buffer = []
        self.audio_segment = []
        self._sample_width=2
        self._frame_rate=16000
        self._channels=1
        self._min_silence=100
        self._silence_thr=-10

        self._endpoint = 'http://www.google.com/speech-api/v2/recognize'
        self._lang=language
        self._apikey = ''

        prop = rtc._properties
        if prop.getProperty("google.speech.apikey") :
            self._apikey=prop.getProperty("google.speech.apikey")

    #
    #   Write to audio data
    #
    def write(self, data):
        try:
            self._buffer.extend(data)
            if len(self._buffer) > 8000:
                audio=AudioSegment(self._buffer, sample_width=self._sample_width, channels=self._channels, frame_rate=self._frame_rate)
                chunks = detect_nonsilent(audio, min_silence_len=self._min_silence, silence_thresh=self._silence_thr)

                if chunks :
                    self.audio_segment.extend(self._buffer)
                else:
                    if self.audio_segment :
                        res = self.request_google(self.audio_segment)
                        res.pop(0)
                        if res :
                            for c in self._callbacks:
                                c(res)
                        else:
                            print "===="
                        self.audio_segment=[]
                self._buffer = []

        except:
            print traceback.format_exc()
            pass
        return 0

    #
    #  Set ApiKey
    #
    def set_apikey(self, key):
        self._apikey = key

    #
    #  Set Lang
    #
    def set_lang(self, lang):
        self._lang = lang

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
    #  Request Google Voice Recognition
    #
    def request_google(self, data):
        query_string = {'output': 'json', 'lang': self._lang, 'key': self._apikey}
        url = '{0}?{1}'.format(self._endpoint, urllib.urlencode(query_string)) 
        #voice_data = open(name, 'rb').read()
        headers = {'Content-Type': 'audio/l16; rate=16000'}
        voice_data = str(bytearray(data))
        request = urllib2.Request(url, data=voice_data, headers=headers)
        response = urllib2.urlopen(request).read()

        return response.decode('utf-8').split()


#
#  JuliusRTC 
#
GoogleSpeechRecogRTC_spec = ["implementation_id", "GoogleSpeechRecogRTC",
                  "type_name",         "GoogleSpeechRecogRTC",
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
#  GoogleSpeechRecogRTC Class
#
class GoogleSpeechRecogRTC(OpenRTM_aist.DataFlowComponentBase):
    #
    #  Constructor
    #
    def __init__(self, manager):
        OpenRTM_aist.DataFlowComponentBase.__init__(self, manager)
        self._config = config()
        self._recog = None
        self._copyrights=[]


    #
    #  OnInitialize
    #
    def onInitialize(self):
        OpenRTM_aist.DataFlowComponentBase.onInitialize(self)
        self._logger = OpenRTM_aist.Manager.instance().getLogbuf(self._properties.getProperty("instance_name"))
        self._logger.RTC_INFO("GoogleSpeechRecogRTC version " + __version__)
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

        self._recog = GoogleSpeechRecogWrap(self, 'ja-JP')
        self._recog.setcallback(self.onResult)

        return RTC.RTC_OK

    #
    #  OnFinalize
    #
    def onFinalize(self):
        OpenRTM_aist.DataFlowComponentBase.onFinalize(self)
        return RTC.RTC_OK

    #
    #  OnActivate
    #
    def onActivated(self, ec_id):
        OpenRTM_aist.DataFlowComponentBase.onActivated(self, ec_id)
        if self._recog._apikey:
            return RTC.RTC_OK
        else:
            return RTC.RTC_ERROR

    #
    #  OnDeactivate
    #
    def onDeactivate(self, ec_id):
        OpenRTM_aist.DataFlowComponentBase.onDeactivate(self, ec_id)
        return RTC.RTC_OK

    #
    #  OnData (Callback from DataListener)
    #
    def onData(self, name, data):
        if self._recog:
            if name == "data":
                self._recog.write(data.data)


    #
    #  OnExecute (Do nothing)
    #
    def onExecute(self, ec_id):
        OpenRTM_aist.DataFlowComponentBase.onExecute(self, ec_id)
        return RTC.RTC_OK

    #
    #  OnResult
    #
    def onResult(self, data):
        for line in data:
            print line
        pass


#
#  Manager Class
#
class GoogleSpeechRecogManager:
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
        profile = OpenRTM_aist.Properties(defaults_str = GoogleSpeechRecogRTC_spec)
        manager.registerFactory(profile, GoogleSpeechRecogRTC, OpenRTM_aist.Delete)

        self._comp = manager.createComponent("GoogleSpeechRecogRTC?exec_cxt.periodic.rate=1")

#
#  Main
#
if __name__=='__main__':
    manager = GoogleSpeechRecogManager()
    manager.start()

