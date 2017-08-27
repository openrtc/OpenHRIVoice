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

        self._lexicondb = os.path.join(self._configdir, 'lexcon.db')

        self.julius(os.path.join(self._basedir, "3rdparty") )
        self.openjtalk(os.path.join(self._basedir, "3rdparty") )
        self.festival(os.path.join(self._basedir, "3rdparty") )

    #
    #  For Julius
    #
    def julius(self, basedir):
        if self._platform == "Windows":
            self._julius_runkitdir = os.path.join(basedir, "dictation-kit-v4.4")
            self._julius_voxforgedir = os.path.join(basedir, "Julius_AcousticModels_16kHz-16bit_MFCC_O_D_(0_1_1-build726)")

            self._julius_bin = os.path.join(self._julius_runkitdir, "bin", "windows", "julius.exe")

            self._julius_hmm_en = os.path.join(self._julius_voxforgedir, "hmmdefs")
            self._julius_hlist_en = os.path.join(self._julius_voxforgedir, "tiedlist")
            self._julius_dict_en = os.path.join(self._julius_voxforgedir, "dict")

        else:
	    self._julius_runkitdir = "/usr/local/share/julius-runkit"
            if ubuntu_osname == "precise":
                self._julius_dict_en = "/usr/share/doc/julius-voxforge/dict.gz"
            else:
                self._julius_dict_en = "/usr/share/julius-voxforge/acoustic/dict"
            self._julius_voxforgedir = "/usr/share/julius-voxforge"
            self._julius_voxforgedir_de = "/usr/share/julius-voxforge-de"
	    self._julius_bin = "/usr/bin/julius"
            self._julius_hmm_en = os.path.join(self._julius_voxforgedir, "acoustic", "hmmdefs")
            self._julius_hlist_en = os.path.join(self._julius_voxforgedir, "acoustic", "tiedlist")
            self._julius_hmm_de = os.path.join(self._julius_voxforgedir_de, "acoustic", "hmmdefs")
            self._julius_hlist_de = os.path.join(self._julius_voxforgedir_de, "acoustic", "tiedlist")

        self._julius_hmm_ja   = os.path.join(self._julius_runkitdir, "model", "phone_m", "jnas-tri-3k16-gid.binhmm")
        self._julius_hlist_ja = os.path.join(self._julius_runkitdir, "model", "phone_m", "logicalTri-3k16-gid.bin")
        self._julius_ngram_ja = os.path.join(self._julius_runkitdir, "model", "lang_m", "bccwj.60k.bingram")
        #self._julius_dict_ja  = os.path.join(self._julius_runkitdir, "model", "lang_m", "bccwj.60k.htkdic")
        self._julius_dict_ja  = os.path.join(self._julius_runkitdir, "model", "lang_m", "web.60k.htkdic")
    #
    #   For OpenJTalk
    #
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

            self.sox(basedir)

    #
    #  For SOX
    #
    def sox(self, basedir):
        if self._platform == "Windows":
            self._soxdir = os.path.join(basedir, "sox-14.4.2")
            self._sox_bin = os.path.join(self._soxdir, "sox.exe")
        else:
            self._sox_bin = "sox"

    #
    #  For Festival
    #
    def festival(self, basedir):
        if self._platform == "Windows":
            #harumi 2014_12_04 change with a change in the folder structure of festival.
            #self._festivaldir = os.path.join(basedir, "festival-1.96.03-win", "festival")
            self._festivaldir = os.path.join(basedir, "festival")

            self._festival_bin = os.path.join(self._festivaldir, "festival.exe")
            self._festival_opt = ["--libdir", os.path.join(self._festivaldir, "lib")]
        else:
            self._festival_bin = "festival"
            self._festival_opt = []
