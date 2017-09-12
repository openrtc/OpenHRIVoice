#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Julius speech recognition component

Copyright (C) 2010
    Yosuke Matsusaka
    Intelligent Systems Research Institute,
    National Institute of Advanced Industrial Science and Technology (AIST),
    Japan
    All rights reserved.

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
from glob import glob
#from BeautifulSoup import BeautifulSoup
from lxml import *
from bs4 import BeautifulSoup
from xml.dom.minidom import Document
from openhrivoice.JuliusRTC.parsesrgs import *
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

__doc__ = _('Julius (English and Japanese) speech recognition component.')

'''
Dictation-kit
main.jconf:
  -d model/lang_m/bccwj.60k.bingram  # 単語2-gram,3-gramファイル(バイナリ形式）
  -v model/lang_m/bccwj.60k.htkdic   # 単語辞書ファイル
  -b 1500                            # 第1パスのビーム幅（ノード数
  -b2 100                            # 第2パスの仮説数ビームの幅（仮説数）
  -s 500                             # 第2パスの最大スタック数 (仮説数)
  -m 10000                           # 第2パスの仮説オーバフローのしきい値
  -n 30                              # 第2パスで見つける文の数（文数）
  -output 1                          # 第2パスで見つかった文のうち出力する数 （文数）
  -zmeanframe                        # フレーム単位のDC成分除去を行う (HTKと同処理)
  -rejectshort 800                   # 指定ミリ秒以下の長さの入力を棄却する
  
am-gmm.jconf
  -h model/phone_m/jnas-tri-3k16-gid.binhmm    # 音響HMM定義ファイル
  -hlist model/phone_m/logicalTri-3k16-gid.bin # 論理的に出現しうる triphone -> 定義されている triphoneの対応を指定した「HMMListファイル」
  -lmp  10 0  # 言語重みと挿入ペナルティ: 第1パス(2-gram)
  -lmp2 10 0  # 言語重みと挿入ペナルティ: 第2パス(3-gram)


'''

#
#  Julius Wrappper
#
class JuliusWrap(threading.Thread):
    CB_DOCUMENT = 1
    CB_LOGWAVE = 2
    
    #
    #  Constructor
    #
    def __init__(self, language='jp', rtc=''):
        threading.Thread.__init__(self)
        self._config = config()
        self._running = False
        self._platform = platform.system()
        self._gotinput = False
        self._lang = language
        self._memsize = "large"
        #self._memsize = "medium"
        self._logdir = tempfile.mkdtemp()
        self._callbacks = []
        self._grammars = {}
        self._firstgrammar = True
        self._activegrammars = {}
        self._prevdata = ''

        self._jconf_file = ""

        self._mode = 'grammar'
        #self._jcode = 'euc_jp'
        self._jcode = 'utf-8'

        self._modulesocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._audiosocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        if rtc :
            self._mode = rtc._mode
            prop = rtc._properties
            if prop.getProperty("julius.3rdparty_dir") :
                self._config.julius(prop.getProperty("julius.3rdparty_dir"))

            if prop.getProperty("julius.runkit_dir") :
                self._config.julius_runkit(prop.getProperty("julius.runkit_dir"))
            if prop.getProperty("julius.voxforge_dir") :
                self._config.julius_voxforge(prop.getProperty("julius.voxforge_dir"))

            if os.path.isfile(rtc._jconf_file[0]) :
                self._jconf_file = rtc._jconf_file[0]

        self._cmdline = []
        self._cmdline.append(self._config._julius_bin)

        ###########################################################
        #  Opntion Setting
        #
        ###########################################################
        if self._mode == 'dictation' :
            # dictation-kit-v4.4(GMM版デフォルトパラメータ）ただし、outputを5に変更
            self._cmdline.extend(['-d',     self._config._julius_bingram_ja])
            self._cmdline.extend(['-v',     self._config._julius_htkdic_ja])
            self._cmdline.extend(['-h',     self._config._julius_hmm_ja])
            self._cmdline.extend(['-hlist', self._config._julius_hlist_ja])
            self._cmdline.extend(["-b", "1500", "-b2", "100", "-s", "500" ,"-m", "10000"])
            self._cmdline.extend(["-n", "30", "-output", "5", "-zmeanframe", "-rejectshort" ,"800", "-lmp", '10' ,'0', '-lmp2', '10', '0'])
        else:
            #
            #  Japanese
            if self._lang in ('ja', 'jp'):
                self._cmdline.extend(['-h',  self._config._julius_hmm_ja])
                self._cmdline.extend(['-hlist', self._config._julius_hlist_ja])
                self._cmdline.extend(["-dfa", os.path.join(self._config._basedir, "JuliusRTC", "dummy.dfa")])
                self._cmdline.extend(["-v" , os.path.join(self._config._basedir, "JuliusRTC", "dummy.dict")])
                self._cmdline.extend(["-sb", "80.0"])
            #
            #  Germany
            elif self._lang == 'de':
                self._cmdline.extend(['-h',  self._config._julius_hmm_de])
                self._cmdline.extend(['-hlist', self._config._julius_hlist_de])
                self._cmdline.extend(["-dfa", os.path.join(self._config._basedir, "JuliusRTC", "dummy-en.dfa")])
                self._cmdline.extend(["-v", os.path.join(self._config._basedir, "JuliusRTC", "dummy-en.dict")])
                self._cmdline.extend(["-sb", "160.0"])
            #
            #  English
            else:
                self._cmdline.extend(['-h',  self._config._julius_hmm_en])
                self._cmdline.extend(['-hlist', self._config._julius_hlist_en])
                self._cmdline.extend(["-dfa", os.path.join(self._config._basedir, "JuliusRTC", "dummy-en.dfa")])
                self._cmdline.extend(["-v", os.path.join(self._config._basedir, "JuliusRTC", "dummy-en.dict")])
                self._cmdline.extend(["-sb", "160.0"])
    
            if self._memsize == "large":
                self._cmdline.extend(["-b", "-1", "-b2", "120", "-s", "1000" ,"-m", "2000"])
            else:
                self._cmdline.extend(["-b", "-1", "-b2", "80", "-s", "500" ,"-m", "1000"])
    
            self._cmdline.extend(["-n", "5", "-output", "5"])
            self._cmdline.extend(["-rejectshort", "200"])
            self._cmdline.extend(["-penalty1", "5.0", "-penalty2", "20.0"]) # (文法使用時) 第1,2パス用の単語挿入ペナルティ

        self._cmdline.extend(["-pausesegment"])         # レベル・零交差による音声区間検出の強制ON
        self._cmdline.extend(["-nostrip"])              # ゼロ続きの無効な入力部の除去をOFFにする
        self._cmdline.extend(["-spmodel", "sp"])        # ショートポーズ音響モデルの名前
        self._cmdline.extend(["-iwcd1", "max"])         # 第1パスの単語間トライフォン計算法を指定する．(同じコンテキストのトライフォン集合の全尤度の最大値を近似尤度として用いる)
        self._cmdline.extend(["-gprune", "safe"])       # safe pruning 上位N個が確実に求まる．正確．
        self._cmdline.extend(["-forcedict"])            # エラー単語を無視して続行する
        self._cmdline.extend(["-record", self._logdir]) # 認識した音声データを連続したファイルに自動保存
        self._cmdline.extend(["-smpFreq", "16000"])     # サンプリング周波数(Hz)


        self._audioport = self.getunusedport()
        self._cmdline.extend(["-input", "adinnet",  "-adport",  str(self._audioport)]) # 入力の設定（adinport使用)

        if self._jconf_file :
            self._cmdline.extend(["-C", self._jconf_file]) # overwrite parameters by jconf file.

        self._moduleport = self.getunusedport()
        self._cmdline.extend(["-module", str(self._moduleport)])                       # module mode

        #self._cmdline.extend(["-nolog"])               # ログ出力を禁止

        #####################################################

        print "command line: %s" % " ".join(self._cmdline)
        print self._cmdline

        self._running = True
        self._p = subprocess.Popen(self._cmdline)
        print "connecting to ports"
        for retry in range(0, 10):
            try:
                self._modulesocket.connect(("localhost", self._moduleport))
            except socket.error:
                time.sleep(1)
                continue
            break
        for retry in range(0, 10):
            try:
                self._audiosocket.connect(("localhost", self._audioport))
            except socket.error:
                time.sleep(1)
                continue
            break
        self._modulesocket.sendall("INPUTONCHANGE TERMINATE\n")
        print "JuliusWrap started"

    #
    #  get unused communication port
    #
    def getunusedport(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('localhost', 0))
        addr, port = s.getsockname()
        s.close()
        return port

    #
    #  Terminate (Call on Finished)
    #
    def terminate(self):
        print 'JuliusWrap: terminate'
        self._running = False
        self._audiosocket.close()
        self._modulesocket.close()
        self._p.terminate()
        return 0

    #
    #   Write to audio data
    #
    def write(self, data):
        try:
            self._audiosocket.send(struct.pack("i", len(data)))
            self._audiosocket.sendall(data)
        except socket.error:
            try:
                self._audiosocket.connect(("localhost", self._audioport))
            except:
                pass
        return 0

    #
    #  Run
    #
    def run(self):
        while self._running:
            for f in glob(os.path.join(self._logdir, "*.wav")):
                for c in self._callbacks:
                    c(self.CB_LOGWAVE, f)
            try:
                self._modulesocket.settimeout(1)
                data = self._prevdata + unicode(self._modulesocket.recv(1024*10),  self._jcode)
            except socket.timeout:
                continue
            except socket.error:
                print 'socket error'
                break

            self._gotinput = True
            ds = data.split(".\n")
            self._prevdata = ds[-1]
            ds = ds[0:-1]
            for d in ds:
                try:
                  dx = BeautifulSoup(d, "lxml")
                  for c in self._callbacks:
                      c(self.CB_DOCUMENT, dx)
                except:
                  import traceback
                  traceback.print_exc()
                  pass

        print 'JuliusWrap: exit from event loop'

    #
    #   Add grammer to Julius Server
    #
    def addgrammar(self, data, name):
        if self._firstgrammar == True:
            self._modulesocket.sendall("CHANGEGRAM %s\n" % (name,))
            self._firstgrammar = False
        else:
            self._modulesocket.sendall("ADDGRAM %s\n" % (name,))
        self._modulesocket.sendall(data.encode(self._jcode, 'backslashreplace'))
        self._grammars[name] = len(self._grammars)
        self._activegrammars[name] = True
        time.sleep(0.1)

    #
    #  Activate current grammer
    #
    def activategrammar(self, name):
        try:
            gid = self._grammars[name]
        except KeyError:
            print "[error] unknown grammar: %s" % (name,)
            return
        print "ACTIVATEGRAM %s" % (name,)
        self._modulesocket.sendall("ACTIVATEGRAM\n%s\n" % (name,))
        self._activegrammars[name] = True
        time.sleep(0.1)

    #
    #  Deactivate current grammer
    #
    def deactivategrammar(self, name):
        try:
            gid = self._grammars[name]
        except KeyError:
            print "[error] unknown grammar: %s" % (name,)
            return
        print "DEACTIVATEGRAM %s" % (name,)
        self._modulesocket.sendall("DEACTIVATEGRAM\n%s\n" % (name,))
        del self._activegrammars[name]
        time.sleep(0.1)

    #
    #  Synchronize grammer
    #
    def syncgrammar(self):
        self._modulesocket.sendall("SYNCGRAM\n")

    #
    #  Switch grammer
    #
    def switchgrammar(self, name):
        self.activategrammar(name)
        for g in self._activegrammars.keys():
            if g != name:
                self.deactivategrammar(g)

    #
    #  Set callback function
    #
    def setcallback(self, func):
        self._callbacks.append(func)

#
#  JuliusRTC 
#
JuliusRTC_spec = ["implementation_id", "JuliusRTC",
                  "type_name",         "JuliusRTC",
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
                  "conf.default.jconf_file", "main.jconf",
                  "conf.__widget__.jconf_file", "text",

                  ""]
#
#  DataListener class for JuliusRTC
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
#  JuliusRTC Class
#
class JuliusRTC(OpenRTM_aist.DataFlowComponentBase):
    #
    #  Constructor
    #
    def __init__(self, manager):
        OpenRTM_aist.DataFlowComponentBase.__init__(self, manager)
        self._lang = 'en'
        self._srgs = None
        self._j = None
        self._mode = 'grammar'
        self._config = config()

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
        self._logger.RTC_INFO("Copyright (C) 2010-2011 Yosuke Matsusaka")
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


        self._jconf_file=["main.jconf"]
        self.bindParameter("jconf_file", self._jconf_file, "main.jconf")

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
#  JuliusRTCManager Class
#
class JuliusRTCManager:
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


        self._rebuid_lexicon=opts.rebuild_lexicon

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
        profile = OpenRTM_aist.Properties(defaults_str = JuliusRTC_spec)
        manager.registerFactory(profile, JuliusRTC, OpenRTM_aist.Delete)
  
        for a in self._grammars:
            self._comp[a] = manager.createComponent("JuliusRTC?exec_cxt.periodic.rate=1")
            if a == 'dictation':
                self._comp[a]._mode='dictation'
            else:
                self._comp[a].setgrammarfile(a, self._rebuid_lexicon)

#
#  Main
#
if __name__=='__main__':
    manager = JuliusRTCManager()
    manager.start()

