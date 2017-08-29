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
                    ],
        "options": {
            "py2exe": {
                "includes": ["xml.etree.ElementTree", "lxml._elementpath", "OpenRTM_aist", "RTC"],
                "dll_excludes": ["USP10.dll", "NSI.dll", "MSIMG32.dll", 
                                 "DNSAPI.dll", "ierutil.dll", "powrprof.dll",
                                  "msimg32.dll", "mpr.dll", "urlmon.dll", "dnsapi.dll",
                                  "OLEAUT32.dll", "USER32.dll", "IMM32.dll", "SHELL32.dll",
                                  "OLE32.dll", "SHLWAPI.dll", "MSVCR100.dll", "COMCTL32.dll",
                                  "ADVAPI32.dll", "msvcrt.dll", "WS2_32.dll", "WINSPOOL.drv",
                                  "GDI32.dll", "KERNEL32.dll", "COMDLG32.dll", "gdiplus.dll",
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
      author='Yosuke Matsusaka',
      author_email='yosuke.matsusaka@aist.go.jp',
      url='http://openrtc.org/',
      license='EPL',
      data_files = [],
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
      """,
      **extra
      )
