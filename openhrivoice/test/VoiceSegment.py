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
    CB_DOCUMENT = 1
    CB_LOGWAVE = 2
    
    #
    #  Constructor
    #
    def __init__(self, language='jp', rtc=''):
        threading.Thread.__init__(self)
        self._config = config()
        self._platform = platform.system()


    #
    #  get unused communication port
 
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
            ### output voice segment to file
        except:
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
#  JuliusRTC 
#
VoiceSegmentRTC_spec = ["implementation_id", "VoideSegmentRTC",
                  "type_name",         "VoiceSegmentRTC",
                  "description",       __doc__.encode('UTF-8'),
                  "version",           __version__,
                  "vendor",            "AIST",
                  "category",          "communication",
                  "activity_type",     "DataFlowComponent",
                  "max_instance",      "10",
                  "language",          "Python",
                  "lang_type",         "script",
                  "conf.default.language", "japanese",
                  "conf.__descirption__.language", _("Specify target language.").encode('UTF-8'),
                  "conf.__widget__.language", "radio",
                  "conf.__constraints__.language", "(japanese, english, german)",
                  "conf.default.phonemodel", "male",
                  "conf.__descirption__.phonemodel", _("Specify acoustic model (fixed to male)").encode('UTF-8'),
                  "conf.__widget__.phonemodel", "radio",
                  "conf.__constraints__.phonemodel", "(male)",
                  "conf.default.voiceactivitydetection", "internal",
                  "conf.__descirption__.voiceactivitydetection", _("Specify voice activity detection trigger (fixed to internal).").encode('UTF-8'),
                  "conf.__widget__.voiceactivitydetection", "radio",
                  "conf.__constraints__.voiceactivitydetection", "(internal)",
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
        # create inport for active grammar
        self._grammardata = RTC.TimedString(RTC.Time(0,0), "")
        self._grammarport = OpenRTM_aist.InPort("activegrammar", self._grammardata)
        self._grammarport.appendProperty('description', _('Grammar ID to be activated.').encode('UTF-8'))
        self._grammarport.addConnectorDataListener(OpenRTM_aist.ConnectorDataListenerType.ON_BUFFER_WRITE,
                                                   DataListener("activegrammar", self, RTC.TimedString))
        self.registerInPort(self._grammarport._name, self._grammarport)

        #
        # create outport for status
        self._statusdata = RTC.TimedString(RTC.Time(0,0), "")
        self._statusport = OpenRTM_aist.OutPort("status", self._statusdata)
        self._statusport.appendProperty('description',
                                        _('Status of the recognizer (one of "LISTEN [accepting speech]", "STARTREC [start recognition process]", "ENDREC [end recognition process]", "REJECTED [rejected speech input]")').encode('UTF-8'))
        self.registerOutPort(self._statusport._name, self._statusport)

        #
        # create outport for result
        self._outdata = RTC.TimedString(RTC.Time(0,0), "")
        self._outport = OpenRTM_aist.OutPort("result", self._outdata)
        self._outport.appendProperty('description', _('Recognition result in XML format.').encode('UTF-8'))
        self.registerOutPort(self._outport._name, self._outport)

        #
        # create outport for log
        self._logdata = RTC.TimedOctetSeq(RTC.Time(0,0), None)
        self._logport = OpenRTM_aist.OutPort("log", self._logdata)
        self._logport.appendProperty('description', _('Log of audio data.').encode('UTF-8'))
        self.registerOutPort(self._logport._name, self._logport)

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
        if self._j:
            self._j.terminate()
            self._j.join()
            self._j = None
        return RTC.RTC_OK

    #
    #  OnActivate
    #
    def onActivated(self, ec_id):
        OpenRTM_aist.DataFlowComponentBase.onActivated(self, ec_id)
        if self._mode == 'dictation' :
            self._lang = 'ja'
        else:
            self._lang = self._srgs._lang
        self._j = JuliusWrap(self._lang, self)
        self._j.start()
        self._j.setcallback(self.onResult)

        while self._j._gotinput == False:
            time.sleep(0.1)

        if self._j._mode == 'dictation' :
            self._logger.RTC_INFO("run with dictation mode")
        else:
            for r in self._srgs._rules.keys():
                gram = self._srgs.toJulius(r)
                if gram == "":
                    return RTC.RTC_ERROR
                self._logger.RTC_INFO("register grammar: %s" % (r,))
                print gram
                self._j.addgrammar(gram, r)
            self._j.switchgrammar(self._srgs._rootrule)

        return RTC.RTC_OK

    #
    #  OnDeactivate
    #
    def onDeactivate(self, ec_id):
        OpenRTM_aist.DataFlowComponentBase.onDeactivate(self, ec_id)
        if self._j:
            self._j.terminate()
            self._j.join()
            self._j = None
        return RTC.RTC_OK

    #
    #  OnData (Callback from DataListener)
    #
    def onData(self, name, data):
        if self._j:
            if name == "data":
                self._j.write(data.data)
            elif name == "activegrammar":
                self._j.switchgrammar(data.data)

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
        if type == JuliusWrap.CB_DOCUMENT:
            if data.input:
                d=data.input
                self._logger.RTC_INFO(d['status'])
                self._statusdata.data = str(d['status'])
                self._statusport.write()
            elif data.rejected:
                d=data.rejected
                self._logger.RTC_INFO('rejected')
                self._statusdata.data = 'rejected'
                self._statusport.write()
            elif data.recogout:
                d = data.recogout
                doc = Document()
                listentext = doc.createElement("listenText")
                doc.appendChild(listentext)
                for s in d.findAll('shypo'):
                    hypo = doc.createElement("data")
                    score = 0
                    count = 0
                    text = []
                    for w in s.findAll('whypo'):
                        if not w['word'] or  w['word'][0] == '<':
                            continue
                        whypo = doc.createElement("word")
                        whypo.setAttribute("text", w['word'])
                        whypo.setAttribute("score", w['cm'])
                        hypo.appendChild(whypo)
                        text.append(w['word'])
                        score += float(w['cm'])
                        count += 1
                    if count == 0:
                        score = 0
                    else:
                        score = score / count
                    hypo.setAttribute("rank", s['rank'])
                    hypo.setAttribute("score", str(score))
                    hypo.setAttribute("likelihood", s['score'])
                    hypo.setAttribute("text", " ".join(text))
                    self._logger.RTC_INFO("#%s: %s (%s)" % (s['rank'], " ".join(text), str(score)))
                    listentext.appendChild(hypo)
                data = doc.toxml(encoding="utf-8")
                #self._logger.RTC_INFO(data.decode('utf-8', 'backslashreplace'))
                self._outdata.data = data
                self._outport.write()

        elif type == JuliusWrap.CB_LOGWAVE:
            t = os.stat(data).st_ctime
            tf = t - int(t)
            self._logdata.tm = RTC.Time(int(t - tf), int(tf * 1000000000))
            try:
                wf = wave.open(data, 'rb')
                self._logdata.data = wf.readframes(wf.getnframes())
                wf.close()
                os.remove(data)
                self._logport.write()
            except:
                pass

    #
    #  Set Grammer
    #
    def setgrammar(self, srgs):
        self._srgs = srgs

    #
    #  Set Grammer
    #
    def setgrammarfile(self, gram, rebuid=False):
        self._grammer = gram
        print "compiling grammar: %s" % (gram,)
        self._srgs = SRGS(gram, self._properties, rebuid)
        print "done"

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

        parser = utils.MyParser(version=__version__, usage="%prog [srgsfile]",
                                description=__doc__)
        utils.addmanageropts(parser)
        parser.add_option('-g', '--gui', dest='guimode', action="store_true",
                          default=False,
                          help=_('show file open dialog in GUI'))

        parser.add_option('-D', '--dictation', dest='dictation_mode', action="store_true",
                          default=False,
                          help=_('run with dictation mode'))

        parser.add_option('-r', '--rebuild-lexicon', dest='rebuild_lexicon', action="store_true",
                          default=False,
                          help=_('rebuild lexicon'))
        try:
            opts, args = parser.parse_args()
        except optparse.OptionError, e:
            print >>sys.stderr, 'OptionError:', e
            sys.exit(1)

        if opts.guimode == True:
            sel = utils.askopenfilenames(title="select W3C-SRGS grammar files")
            if sel is not None:
                args.extend(sel)
    
        if opts.dictation_mode == False and len(args) == 0:
            parser.error("wrong number of arguments")
            sys.exit(1)
            
        if opts.dictation_mode == True:
          args.extend(['dictation'])

        self._grammars = args
        self._comp = {}
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
  
        for a in self._grammars:
            self._comp[a] = manager.createComponent("VoiceSegmentRTC?exec_cxt.periodic.rate=1")

#
#  Main
#
if __name__=='__main__':
    manager = VoiceSegmentRTCManager()
    manager.start()

