#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Utility functions

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

import sys
import os
import platform
import optparse
import time

try:
    import gettext
    _ = gettext.translation(domain='openhrivoice', localedir=os.path.dirname(__file__)+'/../share/locale').ugettext
except:
    _ = lambda s: s

#
#  Original Parser
#
class MyParser(optparse.OptionParser):
    def _add_help_option (self):
        self.add_option("-h", "--help",
                        action="help",
                        help=_("show this help message and exit"))

    def _add_version_option (self):
        self.add_option("--version",
                        action="version",
                        help=_("show program's version number and exit"))

    def format_epilog(self, formatter):
        if self.epilog is not None:
            return self.epilog
        else:
            return ''

    def exit(self, status=0, msg=None):
        if msg is not None:
            sys.stderr.write(msg)
        sys.exit(status)

    def print_usage(self, file=None):
        if file == None :
            file = sys.stdout
        file.write(self.get_usage() + '\n')

    def print_help(self, file=None):
        if file == None :
            file = sys.stdout
        file.write(self.format_help() + '\n')

    def print_version(self, file=None):
        if file == None :
            file = sys.stdout
        file.write(self.get_version() + '\n')

#
#  Selector dialog for single file reading
#
def askopenfilename(title=''):
    import gtk
    ret = None
    dialog = gtk.FileChooserDialog(action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                   buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                            gtk.STOCK_OPEN, gtk.RESPONSE_OK))
    dialog.set_default_response(gtk.RESPONSE_OK)
    response = dialog.run()
    if response == gtk.RESPONSE_OK:
        ret = dialog.get_filename()
    dialog.destroy()
    return ret
#
#  Selector dialog for multi-files reading
#
def askopenfilenames(title=''):
    import gtk
    ret = None
    dialog = gtk.FileChooserDialog(action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                   buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                            gtk.STOCK_OPEN, gtk.RESPONSE_OK))
    dialog.set_default_response(gtk.RESPONSE_OK)
    
    dialog.set_select_multiple(True)
    response = dialog.run()
    if response == gtk.RESPONSE_OK:
        ret = dialog.get_filenames()
    dialog.destroy()
    return ret
#
#  Selector dialog for saving file
#
def asksaveasfile():
    import gtk
    ret = None
    dialog = gtk.FileChooserDialog(action=gtk.FILE_CHOOSER_ACTION_SAVE,
                                   buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                            gtk.STOCK_OPEN, gtk.RESPONSE_OK))
    dialog.set_default_response(gtk.RESPONSE_OK)
    response = dialog.run()
    if response == gtk.RESPONSE_OK:
        ret = dialog.get_filename()
    dialog.destroy()
    return ret

#
#  option definition for rtm_manager
#
def addmanageropts(parser):
    parser.add_option('-a', '--manager-service', dest='managerservice', action='store_true',
                      default=False,
                      help=_('enable manager to be controlled as corba servant'))
    parser.add_option('-f', '--config-file', dest='configfile', action='store',
                      default=None,
                      help=_('specify custom configuration file'))
    parser.add_option('-o', '--option', dest='option', action='append',
                      default=None,
                      help=_('specify custom configuration parameter'))
    parser.add_option('-p', '--port', dest='port', action='store',
                      default=None,
                      help=_('specify custom corba endpoint'))
    parser.add_option('-d', '--master-mode', dest='mastermode', action='store_true',
                      default=False,
                      help=_('configure manager to be master'))
#
#  option definition for rtm_manager
#
def genmanagerargs(opt):
    args = [sys.argv[0],]
    if opt.managerservice == True:
        args.append('-a')
    if opt.configfile is not None:
        args.append('-f')
        args.append(opt.configfile)
    if opt.option is not None:
        for o in opt.option:
            args.append('-o')
            args.append(o)
    if opt.port is not None:
        args.append('-p')
        args.append(port)
    if opt.mastermode == True:
        args.append('-d')

#
#  Read file
#
def read_file_contents(fname):
  try:
    f=open(fname,'r')
    contents = f.read()
    f.close()
    return contents
  except:
    return ""
    
#
#  get current time
#
def getCurrentTime():
  if platform.system() == 'Windows':
    now = time.clock()
  else:
    now = time.time()
  return now

