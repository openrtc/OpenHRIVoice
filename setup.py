#!/usr/bin/env python

from setuptools import setup, find_packages
from setuptools.command.build_ext import build_ext
import sys, os
from glob import glob
from openhrivoice.__init__ import __version__

cmd_classes = {}
try:
    from DistUtilsExtra.command import *
    cmd_classes.update({"build": build_extra.build_extra,
                        "build_i18n" :  build_i18n.build_i18n})
except ImportError:
    pass

try:
    import py2exe
    sys.path.append("openhrivoice2.20")
except ImportError:
    pass

data_files = []

if sys.platform == "win32":
    # py2exe options
    extra = {
        "console": [
                    "openhrivoice/OpenJTalkRTC/OpenJTalkRTC.py",
                    "openhrivoice/JuliusRTC/JuliusRTC.py",
                    "openhrivoice/JuliusCliRTC/JuliusCli.py",
                    "openhrivoice/FestivalRTC/FestivalRTC.py",
                    "openhrivoice/GoogleSpeechRecogRTC/GoogleSpeechRecogRTC.py",
                    "openhrivoice/RecaiusSpeechRecogRTC/RecaiusSpeechRecogRTC.py",
                    "openhrivoice/RecaiusTalkRTC/RecaiusTalkRTC.py",
                    "openhrivoice/XSLTRTC/XSLTRTC.py",
                    "openhrivoice/MARYRTC/MARYRTC.py",
                    ],
        "options": {
            "py2exe": {
                "includes": ["xml.etree.ElementTree", "lxml._elementpath", "OpenRTM_aist", "RTC",
                              "cairo", "pango", "pangocairo",
                             "atk", "gobject", "gio", "glib", "gtk", "gtksourceview2"],
                "dll_excludes": ["USP10.dll", "NSI.dll", "MSIMG32.dll", 
                                 "DNSAPI.dll", "ierutil.dll", "powrprof.dll",
                                  "msimg32.dll", "mpr.dll", "urlmon.dll", "dnsapi.dll",
                                  "OLEAUT32.dll", "USER32.dll", "IMM32.dll", "SHELL32.dll",
                                  "OLE32.dll", "SHLWAPI.dll", "MSVCR100.dll", "COMCTL32.dll",
                                  "ADVAPI32.dll", "msvcrt.dll", "WS2_32.dll", "WINSPOOL.drv",
                                  "GDI32.dll", "KERNEL32.dll", "COMDLG32.dll", "gdiplus.dll",
                                  "libxml2-2.dll", "gtksourceview2.pyd",
                                ],
            }
        }
        }
else:
    extra = {}

setup(name='openhrivoice',
      cmdclass=cmd_classes,
      version=__version__,
      description="Voice components for OpenRTM (part of OpenHRI softwares)",
      long_description="""Voice components for OpenRTM (part of OpenHRI softwares).""",
      classifiers=[],
      keywords='',
      author='Yosuke Matsusaka and Isao Hara',
      author_email='isao-hara@aist.go.jp',
      url='http://www.intsys.org/_openrtc/ja/HRI/index.html',
      license='EPL',
      data_files = [('/usr/share/openhrivoice2.30',
                    ['util/setup_3rdparty_1204.sh',
                     'util/setup_3rdparty_1404.sh',
		     'util/dictation_kit.sh','util/func_setup.sh',
		     'util/mmdagent_example.sh',
		     'util/uninstall_3rdparty.sh',
		     'util/hts_voice.sh',
		     'util/open_jtalk_dic_utf_8.sh']),
		    ('/usr/share/openhrivoice2.30/lice_dir',
		    ['util/lice_dir/hts_voice_copyright.txt',
		     'util/lice_dir/mmdagent_mei_copyright.txt',
		     'util/lice_dir/julius_copyright_utf8.txt',
		     'util/lice_dir/utf_8_copyright.txt'])],
      packages=find_packages(exclude=['ez_setup', 'doc', 'examples', 'tests']),
      include_package_data=True,
      package_data={'openhrivoice': ['*.dfa', '*.dict', '*.xsd']},
      zip_safe=False,
      install_requires=[
        # -*- Extra requirements: -*-
        ],
      entry_points="""
      [console_scripts]
      openjtalkrtc = openhrivoice.OpenJTalkRTC.OpenJTalkRTC:main
      juliusrtc = openhrivoice.JuliusRTC.JuliusRTC:main
      juliusclirtc = openhrivoice.JuliusCliRTC.JuliusCli:main
      festivalrtc = openhrivoice.FestivalRTC.FestivalRTC:main
      googlespeechrecogrtc = openhrivoice.GoogleSpeechRecogRTC.GoogleSpeechRecogRTC:main
      recaiusspeechrecogrtc = openhrivoice.RecaiusSpeechRecogRTC.RecaiusSpeechRecogRTC:main
      recaiustalkrtc = openhrivoice.RecaiusTalkRTC.RecaiusTalkRTC:main
      xlstrtc = openhrivoice.XSLTRTC.XSLTRTC:main
      maryrtc = openhrivoice.MARYRTC.MARYRTC:main
      """,
      **extra
      )
