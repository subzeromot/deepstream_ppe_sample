import code
import sys
import os
import gi
import configparser
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
from common.is_aarch_64 import is_aarch64
from common.bus_call import bus_call
from threading import Thread, Lock, main_thread

import pyds
import time
import cv2
import sys
import numpy as np
import glob
import os
import math

from configs import *
from utils import plot_box, draw_roi, is_in_roi, plot_box_grad, crop_object
import track_manager as tracker

OSD_PROCESS_MODE= 0
OSD_DISPLAY_TEXT= 1

CLASS_PGIE = ['Person', 'Person_Hat', 'Person_Vest', 'Person_Hat_Vest']

# Get the directory of script
dir_arr = os.path.realpath(__file__).split('/')
dir_arr = dir_arr[:-1]
DIR=''
for dir in dir_arr:
    DIR = DIR + dir + '/'
print("Script path:", DIR)

class App:
    def __init__(self) -> None:
        self.logo_ROI = [[10, 5], [536, 43]]
        h, w = self.logo_ROI[1][1] - self.logo_ROI[0][1], self.logo_ROI[1][0] - 435  #43-5, 536 - 435
        self.logo = cv2.imread(DIR + '/../resources/logo.jpg')
        self.mask = cv2.imread(DIR + '/../resources/mask.jpg')
        self.mask = cv2.cvtColor(self.mask, cv2.COLOR_RGB2GRAY)
        self.mask = cv2.resize(self.mask, (w, h))
        self.logo = cv2.resize(self.logo, (w, h))

        self.track_manager = tracker.TrackManager()
        self.track_manager.start()
    
    def osd_sink_pad_buffer_probe(self, pad,info,u_data):
        
        frame_number=0

        gst_buffer = info.get_buffer()
        if not gst_buffer:
            return

        # Retrieve batch metadata from the gst_buffer
        # Note that pyds.gst_buffer_get_nvds_batch_meta() expects the
        # C address of gst_buffer as input, which is obtained with hash(gst_buffer)
        batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
        l_frame = batch_meta.frame_meta_list
        
        while l_frame is not None:
            try:
                # Note that l_frame.data needs a cast to pyds.NvDsFrameMeta
                # The casting is done by pyds.NvDsFrameMeta.cast()
                # The casting also keeps ownership of the underlying memory
                # in the C code, so the Python garbage collector will leave
                # it alone.
                frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
            except StopIteration:
                break

            frame_number=frame_meta.frame_num
            l_obj=frame_meta.obj_meta_list

            # Add Logo
            n_frame_c = pyds.get_nvds_buf_surface(hash(gst_buffer), frame_meta.batch_id)
            org_frame = n_frame_c.copy()

            img_crop = n_frame_c[self.logo_ROI[0][1]: self.logo_ROI[1][1], self.logo_ROI[0][0]: self.logo_ROI[1][0]]
            img_crop = cv2.cvtColor(img_crop, cv2.COLOR_RGBA2BGR)
            img_crop[np.where(self.mask == 255)] = self.logo[np.where(self.mask == 255)]
            img_crop = cv2.cvtColor(img_crop, cv2.COLOR_RGB2BGRA)
            n_frame_c[self.logo_ROI[0][1]: self.logo_ROI[1][1], self.logo_ROI[0][0]: self.logo_ROI[1][0]] = img_crop

            while l_obj is not None:
                try:
                    # Casting l_obj.data to pyds.NvDsObjectMeta
                    obj_meta=pyds.NvDsObjectMeta.cast(l_obj.data)
                except StopIteration:
                    break

                check_in_roi = is_in_roi(obj_meta, ROI)
                track_id = obj_meta.object_id
                class_id = obj_meta.class_id

                has_request_cm02 = False
                status = ''

                box_color = (255,0,0)
                # Check CM02 violation
                cm02_violate = False
                has_request_cm02, live_ages = self.track_manager.has_request_violate(track_id)
                label = str(track_id) + '_' + CLASS_PGIE[class_id]
                if class_id == 0:
                    status = 'Mis hat, vest'
                    cm02_violate = True
                if class_id == 1:
                    status = 'Mis vest'
                    cm02_violate = True
                if class_id == 2:
                    status = 'Mis hat'
                    cm02_violate = True
                if class_id == 3:
                    status = ''
                    box_color = (0,255,0)
                    cm02_violate = False

                # TODO:
                # If:
                #   - check_in_roi == True
                #   - cm02_violate == True and track_id is not request cm02 yet 
                # Then: 
                #   - crop image
                #   - save image into minio
                #   - send message to API
                n_frame = pyds.get_nvds_buf_surface(hash(gst_buffer), frame_meta.batch_id)
                if check_in_roi:
                    if (cm02_violate and not has_request_cm02 and live_ages > LIVE_AGES_MIN):
                        img_crop = crop_object(org_frame, obj_meta)
                        # convert python array into numpy array format in the copy mode.
                        img_crop = np.array(img_crop, copy=True, order='C')
                        # convert the array into cv2 default color format
                        img_crop = cv2.cvtColor(img_crop, cv2.COLOR_RGBA2BGRA)

                        data_request = tracker.DataRequest(track_id, img_crop, status, cm02_violate)
                        self.track_manager.add_data_request(data_request)
                    
                ## Hide OSD box
                rect_params = obj_meta.rect_params
                rect_params.border_width = 0
                txt_params = obj_meta.text_params
                txt_params.font_params.font_size = 0    # hide text

                ## Draw frame
                n_frame = plot_box_grad(n_frame, obj_meta, box_color, label)

                n_frame = draw_roi(n_frame, ROI)

                try: 
                    l_obj=l_obj.next
                except StopIteration:
                    break

            try:
                l_frame=l_frame.next
            except StopIteration:
                break
                
        return Gst.PadProbeReturn.OK	

    def cb_newpad(self, decodebin, decoder_src_pad,data):
        print("In cb_newpad\n")
        caps=decoder_src_pad.get_current_caps()
        gststruct=caps.get_structure(0)
        gstname=gststruct.get_name()
        source_bin=data
        features=caps.get_features(0)

        # Need to check if the pad created by the decodebin is for video and not
        # audio.
        print("gstname=",gstname)
        if(gstname.find("video")!=-1):
            # Link the decodebin pad only if decodebin has picked nvidia
            # decoder plugin nvdec_*. We do this by checking if the pad caps contain
            # NVMM memory features.
            print("features=",features)
            if features.contains("memory:NVMM"):
                # Get the source bin ghost pad
                bin_ghost_pad=source_bin.get_static_pad("src")
                if not bin_ghost_pad.set_target(decoder_src_pad):
                    sys.stderr.write("Failed to link decoder src pad to source bin ghost pad\n")
            else:
                sys.stderr.write(" Error: Decodebin did not pick nvidia decoder plugin.\n")

    def decodebin_child_added(self, child_proxy,Object,name,user_data):
        print("Decodebin child added:", name, "\n")
        if(name.find("decodebin") != -1):
            Object.connect("child-added",self.decodebin_child_added,user_data)

        if "source" in name:
            Object.set_property("drop-on-latency", True)

    def create_source_bin(self, index,uri):
        print("Creating source bin")

        # Create a source GstBin to abstract this bin's content from the rest of the
        # pipeline
        bin_name="source-bin-%02d" %index
        print(bin_name)
        nbin=Gst.Bin.new(bin_name)
        if not nbin:
            sys.stderr.write(" Unable to create source bin \n")

        # Source element for reading from the uri.
        # We will use decodebin and let it figure out the container format of the
        # stream and the codec and plug the appropriate demux and decode plugins.
        uri_decode_bin=Gst.ElementFactory.make("uridecodebin", "uri-decode-bin")
        if not uri_decode_bin:
            sys.stderr.write(" Unable to create uri decode bin \n")
        # We set the input uri to the source element
        uri_decode_bin.set_property("uri",uri)
        # Connect to the "pad-added" signal of the decodebin which generates a
        # callback once a new pad for raw data has beed created by the decodebin
        uri_decode_bin.connect("pad-added",self.cb_newpad,nbin)
        uri_decode_bin.connect("child-added",self.decodebin_child_added,nbin)

        # We need to create a ghost pad for the source bin which will act as a proxy
        # for the video decoder src pad. The ghost pad will not have a target right
        # now. Once the decode bin creates the video decoder and generates the
        # cb_newpad callback, we will set the ghost pad target to the video decoder
        # src pad.
        Gst.Bin.add(nbin,uri_decode_bin)
        bin_pad=nbin.add_pad(Gst.GhostPad.new_no_target("src",Gst.PadDirection.SRC))
        if not bin_pad:
            sys.stderr.write(" Failed to add ghost pad in source bin \n")
            return None
        return nbin

    def gst_pipeline(self, args):
        # Check input arguments
        if len(args) < 2:
            sys.stderr.write("usage: %s <uri1> [uri2] ... [uriN]\n" % args[0])
            sys.exit(1)

        number_sources=len(args)-1

        # Standard GStreamer initialization
        GObject.threads_init()
        Gst.init(None)

        # ***** Create gstreamer elements ******/
        # Create Pipeline
        print("Creating Pipeline \n ")
        pipeline = Gst.Pipeline()
        if not pipeline:
            sys.stderr.write(" Unable to create Pipeline \n")

        # Create nvstreammux
        print("Creating streamux \n ")
        streammux = Gst.ElementFactory.make("nvstreammux", "Stream-muxer")
        if not streammux:
            sys.stderr.write(" Unable to create NvStreamMux \n")
        pipeline.add(streammux)
        streammux.set_property('live-source', 1)
        streammux.set_property('width', DISPLAY_W)
        streammux.set_property('height', DISPLAY_H)
        streammux.set_property('batch-size', 1)
        streammux.set_property('batched-push-timeout', 4000000)

        # Create sources bin
        for i in range(number_sources):
            print("Creating source_bin ",i," \n ")
            uri_name=args[i+1]
            if uri_name.find("rtsp://") == 0 :
                is_live = True
            source_bin=self.create_source_bin(i, uri_name)
            if not source_bin:
                sys.stderr.write("Unable to create source bin \n")
            pipeline.add(source_bin)
            padname="sink_%u" %i
            sinkpad= streammux.get_request_pad(padname) 
            if not sinkpad:
                sys.stderr.write("Unable to create sink pad bin \n")
            srcpad=source_bin.get_static_pad("src")
            if not srcpad:
                sys.stderr.write("Unable to create src pad bin \n")
            srcpad.link(sinkpad)

        # Create queue
        queue1=Gst.ElementFactory.make("queue","queue1")
        queue2=Gst.ElementFactory.make("queue","queue2")
        queue3=Gst.ElementFactory.make("queue","queue3")
        queue4=Gst.ElementFactory.make("queue","queue4")
        pipeline.add(queue1)
        pipeline.add(queue2)
        pipeline.add(queue3)
        pipeline.add(queue4)

        # Create PGIE 
        print("Creating Pgie \n ")
        pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
        if not pgie:
            sys.stderr.write(" Unable to create pgie \n")
        pgie.set_property('config-file-path', PGIE_CONFIG)
        pipeline.add(pgie)

        # Add tracker
        print("Creating tracker \n ")
        tracker = Gst.ElementFactory.make("nvtracker", "tracker")
        if not tracker:
            sys.stderr.write(" Unable to create tracker \n")
        pipeline.add(tracker)
        config = configparser.ConfigParser()
        config.read(DIR + TRACK_CONFIG)
        config.sections()
        for key in config['tracker']:
            if key == 'tracker-width' :
                tracker_width = config.getint('tracker', key)
                tracker.set_property('tracker-width', tracker_width)
            if key == 'tracker-height' :
                tracker_height = config.getint('tracker', key)
                tracker.set_property('tracker-height', tracker_height)
            if key == 'gpu-id' :
                tracker_gpu_id = config.getint('tracker', key)
                tracker.set_property('gpu_id', tracker_gpu_id)
            if key == 'll-lib-file' :
                tracker_ll_lib_file = config.get('tracker', key)
                tracker.set_property('ll-lib-file', tracker_ll_lib_file)
            if key == 'll-config-file' :
                tracker_ll_config_file = config.get('tracker', key)
                tracker.set_property('ll-config-file', tracker_ll_config_file)
            if key == 'enable-batch-process' :
                tracker_enable_batch_process = config.getint('tracker', key)
                tracker.set_property('enable_batch_process', tracker_enable_batch_process)
            if key == 'enable-past-frame' :
                tracker_enable_past_frame = config.getint('tracker', key)
                tracker.set_property('enable_past_frame', tracker_enable_past_frame)

        # Create video convert
        print("Creating nvvidconv \n ")
        nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "convertor")
        if not nvvidconv:
            sys.stderr.write(" Unable to create nvvidconv \n")
        pipeline.add(nvvidconv)
        
        # Create OSD
        print("Creating nvosd \n ")
        nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")
        if not nvosd:
            sys.stderr.write(" Unable to create nvosd \n")
        nvosd.set_property('process-mode',OSD_PROCESS_MODE)
        nvosd.set_property('display-text',OSD_DISPLAY_TEXT)
        pipeline.add(nvosd)

        # Video convert
        nvvidconv1 = Gst.ElementFactory.make("nvvideoconvert", "convertor_before_crop")
        pipeline.add(nvvidconv1)

        # Create video crop
        videocrop = Gst.ElementFactory.make("videocrop", "videocrop0")
        videocrop.set_property('left', 0)
        videocrop.set_property('right', 0)
        videocrop.set_property('top', 0)
        videocrop.set_property('bottom', 0)
        pipeline.add(videocrop)

        # Create cap filter
        caps_crop = Gst.ElementFactory.make("capsfilter", "caps_crop")
        if not caps_crop:
            sys.stderr.write(" Unable to create caps_crop \n")
        caps_crop.set_property('caps', Gst.Caps.from_string("video/x-raw(memory:NVMM),width=1280,height=720"))
        pipeline.add(caps_crop)

        nvvidconv2 = Gst.ElementFactory.make("nvvideoconvert", "convertor_after_crop")
        if not nvvidconv2:
            sys.stderr.write(" Unable to create nvvidconv2 \n")
        pipeline.add(nvvidconv2)

        # Create sink
        print("Creating Sink \n")
        sink = Gst.ElementFactory.make("nvoverlaysink", "nvvideo-renderer")
        if not sink:
            sys.stderr.write(" Unable to create sink \n")
        pipeline.add(sink)
        sink.set_property("qos",0)
        sink.set_property("async", 0)
        
        




        # Link elements
        print("Linking elements in the Pipeline \n")
        streammux.link(queue1)
        queue1.link(pgie)
        pgie.link(tracker)
        tracker.link(nvvidconv)
        nvvidconv.link(queue4)
        queue4.link(nvosd)
        nvosd.link(nvvidconv1)
        nvvidconv1.link(videocrop)
        videocrop.link(nvvidconv2)
        nvvidconv2.link(caps_crop)
        caps_crop.link(sink)





        # create an event loop and feed gstreamer bus mesages to it
        loop = GObject.MainLoop()
        bus = pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect ("message", bus_call, loop)

        osdsinkpad = nvosd.get_static_pad("sink")
        if not osdsinkpad:
            sys.stderr.write(" Unable to get sink pad of nvosd \n")
        osdsinkpad.add_probe(Gst.PadProbeType.BUFFER, self.osd_sink_pad_buffer_probe, 0)

        # List the sources
        print("Now playing...")
        for i, source in enumerate(args):
            if (i != 0):
                print(i, ": ", source)

        print("Starting pipeline \n")
        # start play back and listed to events		
        pipeline.set_state(Gst.State.PLAYING)
        try:
            loop.run()
        except:
            pass
        # cleanup
        print("Exiting app\n")
        pipeline.set_state(Gst.State.NULL)

if __name__ == '__main__':
    app = App()
    sys.exit(app.gst_pipeline(sys.argv))

