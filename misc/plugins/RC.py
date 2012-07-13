#
# RC.py -- Remote Control plugin for Ginga fits viewer
# 
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Thu Jul 12 16:02:49 HST 2012
#]
#
# Copyright (c) 2011-2012, Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
The RC plugin implements a remote control interface for the Ginga FITS
viewer.
"""
import GingaPlugin
import AstroImage

import numpy
import SimpleXMLRPCServer
import binascii

class RC(GingaPlugin.GlobalPlugin):

    def __init__(self, fv):
        # superclass defines some variables for us, like logger
        super(RC, self).__init__(fv)

        # What port to listen for requests
        self.port = 9000
        # If blank, listens on all interfaces
        self.host = ''

        self.ev_quit = fv.ev_quit

    def initialize(self, container):
        # NO GUI
        pass
    
    def start(self):
        self.robj = GingaWrapper(self.fv, self.logger)
        
        self.server = SimpleXMLRPCServer.SimpleXMLRPCServer((self.host,
                                                             self.port))
        self.server.register_instance(self.robj)
        self.fv.nongui_do(self.monitor_shutdown)
        self.fv.nongui_do(self.server.serve_forever, poll_interval=0.1)
        
    def stop(self):
        self.server.shutdown()

    def monitor_shutdown(self):
        # the thread running this method waits until the entire viewer
        # is exiting and then shuts down the XML-RPC server which is
        # running in a different thread
        self.ev_quit.wait()
        self.server.shutdown()

    def __str__(self):
        return 'rc'

    
class GingaWrapper(object):

    def __init__(self, fv, logger):
        self.fv = fv
        self.logger = logger

    def display_fitsbuf(self, fitsname, chname, data, width, height, na_type,
                        header, metadata):
        """Display a FITS image buffer.  Parameters:
        _fitsname_: name of the file
        _chname_: channel to display the data
        _data_: ascii encoded numpy containing image data
        _width_, _height_: image dimensions in pixels
        _na_type_: numpy data type (currently ignored)
        _header_: fits file header as a dictionary
        _metadata_: metadata about image to attach to image
        """

        # Unpack the data
        try:
            # Decode binary data
            data = binascii.a2b_base64(data)

            na_type = numpy.float32
            data = numpy.fromstring(data, dtype=na_type)
            data.byteswap(True)
            data = data.reshape((height, width))
            self.logger.debug("Received data: width=%d height=%d" % (
                width, height))

        except Exception, e:
            # Some kind of error unpacking the data
            errmsg = "Error creating image data for '%s': %s" % (
                fitsname, str(e))
            self.logger.error(errmsg)
            raise GingaPlugin.PluginError(errmsg)

        # Create image container
        image = AstroImage.AstroImage(data, metadata=metadata,
                                      wcsclass=wcs.BareBonesWCS)
        image.set(name=fitsname)
        image.update_keywords(header)
        
        # Enqueue image to display datasrc
        self.fv.gui_do(self.fv.add_image, fitsname, image,
                            chname=chname)
        return 0

    def add_channel(self, chname):
        """Create a new channel with name (chname).
        """
        self.fv.gui_do(self.fv.add_channel, chname)
        return 0

    def display_fitsfile(self, chname, fitspath, dowait):
        """Load (fitspath) into channel (chname).  If (dowait) is True
        then wait for the file to be loaded before returning (synchronous).
        """
        self.fv.load_file(fitspath, chname=chname, wait=dowait)
        return 0

    def cut_levels(self, chname, loval, hival):
        """Cut levels on channel (chname) with (loval) and (hival).
        """
        chinfo = self.fv.get_channelInfo(chname)
        self.fv.gui_do(chinfo.fitsimage.cut_levels, float(loval), float(hival))
        return 0

    def autocuts(self, chname):
        """Auto cut levels on channel (chname).
        """
        chinfo = self.fv.get_channelInfo(chname)
        self.fv.gui_do(chinfo.fitsimage.auto_levels)
        return 0

    def zoom(self, chname, zoomlevel):
        """Set zoom level on channel (chname) to (zoomlevel).
        """
        chinfo = self.fv.get_channelInfo(chname)
        self.fv.gui_do(chinfo.fitsimage.zoom_to, int(zoomlevel))
        return 0

    def zoom_fit(self, chname):
        """Zoom to fit on channel (chname).
        """
        chinfo = self.fv.get_channelInfo(chname)
        self.fv.gui_do(chinfo.fitsimage.zoom_fit)
        return 0

    def transform(self, chname, flipx, flipy, swapxy):
        """Transforms on channel (chname).  (flipx), (flipy) and
        (swapxy) are boolean values which determine the transform.
        """
        chinfo = self.fv.get_channelInfo(chname)
        self.fv.gui_do(chinfo.fitsimage.transform,
                       bool(int(flipx)), bool(int(flipy)), bool(int(swapxy)))
        return 0

    
#END
                                
