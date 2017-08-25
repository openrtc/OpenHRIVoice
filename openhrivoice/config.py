#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''configuration manager for OpenHRIVoice

Copyright (C) 2010
    Yosuke Matsusaka
    Intelligent Systems Research Institute,
    National Institute of Advanced Industrial Science and Technology (AIST),
    Japan
    All rights reserved.
Licensed under the Eclipse Public License -v 1.0 (EPL)
http://www.opensource.org/licenses/eclipse-1.0.txt
'''

import sys
import os
import socket
import platform
import time
import struct
import traceback
import locale
import codecs
import tempfile
import optparse
from glob import glob
from openhrivoice.__init__ import __version__
from openhrivoice import utils

class config():
    def __init__(self):
        self._platform = platform.system()

        if self._platform != "Windows":
		my_platform_list =  platform.platform().split("-")
		ubuntu_osname = my_platform_list[len(my_platform_list)-1]

        if hasattr(sys, "frozen"):
            self._basedir = os.path.dirname(unicode(sys.executable, sys.getfilesystemencoding()))
        else:
            self._basedir = os.path.dirname(__file__)
        self._homedir = os.path.expanduser('~')
        self._configdir = os.path.join(self._homedir, '.openhri')
        if os.path.exists(self._configdir) == False:
            os.makedirs(self._configdir)
#
#
#
        self.openjtalk(os.path.join(self._basedir, "3rdparty") )

    def openjtalk(self, basedir):
        if self._platform == "Windows":
            self._openjtalk_dir = os.path.join(basedir, "open_jtalk-1.10")
            self._openjtalk_bin = os.path.join(self._openjtalk_dir, "bin", "open_jtalk.exe")
            self._openjtalk_phonemodel_male_ja =  os.path.join(self._openjtalk_dir, "share", "hts_voice_nitech_jp_atr503_m001-1.05", "nitech_jp_atr503_m001.htsvoice")
            self._openjtalk_phonemodel_female_ja =  os.path.join(self._openjtalk_dir,"share", "mei", "mei_normal.htsvoice")
            self._openjtalk_dicfile_ja = os.path.join(self._openjtalk_dir, "dic")

        else:
            #harumi 2015_01_14 change with 3rdparty setting
            if ubuntu_osname == "precise":
                self._openjtalk_phonemodel_male_ja = "/usr/local/share/hts-voice/nitech-jp-atr503-m001/nitech_jp_atr503_m001.htsvoice"
            else:
                self._openjtalk_phonemodel_male_ja = "/usr/share/hts-voice/nitech-jp-atr503-m001/nitech_jp_atr503_m001.htsvoice"
                
                #self._openjtalk_dicfile_ja = "/usr/local/share/open_jtalk/dic/utf-8"


            self._openjtalk_dicfile_ja = "/var/lib/mecab/dic/open-jtalk/naist-jdic"
            self._openjtalk_phonemodel_female_ja = "/usr/local/lib/mmdagent/voice/mei_normal"
            self._openjtalk_bin = "open_jtalk"

        if self._platform == "Windows":
            self._soxdir = os.path.join(basedir, "sox-14.4.2")
            self._sox_bin = os.path.join(self._soxdir, "sox.exe")
        else:
            self._sox_bin = "sox"


