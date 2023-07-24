import code
import sys
import os
import gi
import configparser
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
from common.is_aarch_64 import is_aarch64
from common.bus_call import bus_call
from common.FPS import GETFPS
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
from utils import draw_polygon, plot_box, draw_roi, is_in_roi, plot_box_grad, crop_object, is_point_in_polygon
import track_manager as tracker
import colors as color

OSD_PROCESS_MODE= 0
OSD_DISPLAY_TEXT= 1

CLASS_PGIE = ['Person']
fps_streams={}
in_count={}
out_count={}

# Get the directory of script
dir_arr = os.path.realpath(__file__).split('/')
dir_arr = dir_arr[:-1]
DIR=''
for dir in dir_arr:
    DIR = DIR + dir + '/'
print("Script path:", DIR)

class App:
    def __init__(self) -> None:
        self.track_manager = tracker.TrackManager()
        self.track_manager.start()

    def is_obj_in_polygon(self, obj_meta, polygon):
        rect_params = obj_meta.rect_params
        x1 = int(rect_params.left)
        y1 = int(rect_params.top)
        x2 = int(x1 + rect_params.width)
        y2 = int(y1 + rect_params.height)

        foot_x = int((x1 + x2)/2)
        foot_y = y2

        is_inside = is_point_in_polygon(polygon, (foot_x, foot_y))

        return is_inside

    def tiler_src_pad_buffer_probe(self, pad,info,u_data):
        
        frame_number=0
        num_rects=0
        gst_buffer = info.get_buffer()
        if not gst_buffer:
            print("Unable to get GstBuffer ")
            return

        batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
        l_frame = batch_meta.frame_meta_list
        while l_frame is not None:
            try:
                frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
            except StopIteration:
                break

            l_obj=frame_meta.obj_meta_list

            # n_frame_c = pyds.get_nvds_buf_surface(hash(gst_buffer), frame_meta.batch_id)
            # org_frame = n_frame_c.copy()
            # org_frame = cv2.cvtColor(org_frame, cv2.COLOR_RGBA2BGRA)

            while l_obj is not None:
                try:
                    obj_meta=pyds.NvDsObjectMeta.cast(l_obj.data)
                except StopIteration:
                    break
                track_id = obj_meta.object_id
                class_id = obj_meta.class_id
                rect_params = obj_meta.rect_params

                # TODO:
                # - Check is in ROI_inside/ROI_outside
                # - Update track status in trackManager
                # - Let trackManager decide to send events
                x1 = int(rect_params.left)
                y1 = int(rect_params.top)
                x2 = int(x1 + rect_params.width)
                y2 = int(y1 + rect_params.height)
                foot_x = int((x1 + x2) / 2)
                foot_y = y2
                io_result = self.track_manager.update(track_id, [foot_x, foot_y])
                if io_result == 'in':
                    in_count["stream{0}".format(frame_meta.pad_index)] += 1
                if io_result == 'out':
                    out_count["stream{0}".format(frame_meta.pad_index)] += 1

                try:
                    l_obj=l_obj.next
                except StopIteration:
                    break

            # Draw ROI
            n_frame = pyds.get_nvds_buf_surface(hash(gst_buffer), frame_meta.batch_id)
            draw_polygon(n_frame, LINE_IN, color.GREEN)
            draw_polygon(n_frame, LINE_OUT, color.RED)
            cv2.putText(n_frame, "In count: " + str(in_count["stream{0}".format(frame_meta.pad_index)]), (100, 100), cv2.FONT_HERSHEY_COMPLEX, 1, (0,255,0), 2)
            cv2.putText(n_frame, "Out count: " + str(out_count["stream{0}".format(frame_meta.pad_index)]), (100, 200), cv2.FONT_HERSHEY_COMPLEX, 1, (255,0,0), 2)

            # Get frame rate through this probe
            fps_streams["stream{0}".format(frame_meta.pad_index)].get_fps()
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

        # if "source" in name:
        #     Object.set_property("drop-on-latency", True)

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
            sys.stderr.write("usage: %s <uri1> [uri2] ... [uriN] <folder to save frames>\n" % args[0])
            sys.exit(1)

        for i in range(0, len(args) - 1):
            fps_streams["stream{0}".format(i)] = GETFPS(i)
            in_count["stream{0}".format(i)] = 0
            out_count["stream{0}".format(i)] = 0
        number_sources = len(args) - 1

        GObject.threads_init()
        Gst.init(None)

        # Create gstreamer elements */
        # Create Pipeline element that will form a connection of other elements
        print("Creating Pipeline \n ")
        pipeline = Gst.Pipeline()
        is_live = False

        if not pipeline:
            sys.stderr.write(" Unable to create Pipeline \n")

        #****** Create Streammux ************
        print("Creating streamux \n ")
        # Create nvstreammux instance to form batches from one or more sources.
        streammux = Gst.ElementFactory.make("nvstreammux", "Stream-muxer")
        if not streammux:
            sys.stderr.write(" Unable to create NvStreamMux \n")
        streammux.set_property('width', STREAMMUX_W)
        streammux.set_property('height', STREAMMUX_H)
        streammux.set_property('batch-size', number_sources)
        streammux.set_property('batched-push-timeout', 4000000)
        pipeline.add(streammux)

        # ****** Create Sources ************
        for i in range(number_sources):
            print("Creating source_bin ", i, " \n ")
            uri_name = args[i + 1]
            if uri_name.find("rtsp://") == 0:
                is_live = True
            source_bin = self.create_source_bin(i, uri_name)
            if not source_bin:
                sys.stderr.write("Unable to create source bin \n")
            pipeline.add(source_bin)
            padname = "sink_%u" % i
            sinkpad = streammux.get_request_pad(padname)
            if not sinkpad:
                sys.stderr.write("Unable to create sink pad bin \n")
            srcpad = source_bin.get_static_pad("src")
            if not srcpad:
                sys.stderr.write("Unable to create src pad bin \n")
            srcpad.link(sinkpad)

        # ****** Create Detector ************
        print("Creating Pgie \n ")
        pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
        if not pgie:
            sys.stderr.write(" Unable to create pgie \n")
        pgie.set_property('config-file-path', PGIE_CONFIG)
        pgie_batch_size = pgie.get_property("batch-size")
        if (pgie_batch_size != number_sources):
            print("WARNING: Overriding infer-config batch-size", pgie_batch_size, " with number of sources ",
                  number_sources, " \n")
            pgie.set_property("batch-size", number_sources)

        # ****** Create tracker ************
        print("Creating tracker \n ")
        tracker = Gst.ElementFactory.make("nvtracker", "tracker")
        if not tracker:
            sys.stderr.write(" Unable to create tracker \n")
        config = configparser.ConfigParser()
        config.read(DIR + TRACK_CONFIG)
        config.sections()
        for key in config['tracker']:
            if key == 'tracker-width':
                tracker_width = config.getint('tracker', key)
                tracker.set_property('tracker-width', tracker_width)
            if key == 'tracker-height':
                tracker_height = config.getint('tracker', key)
                tracker.set_property('tracker-height', tracker_height)
            if key == 'gpu-id':
                tracker_gpu_id = config.getint('tracker', key)
                tracker.set_property('gpu_id', tracker_gpu_id)
            if key == 'll-lib-file':
                tracker_ll_lib_file = config.get('tracker', key)
                tracker.set_property('ll-lib-file', tracker_ll_lib_file)
            if key == 'll-config-file':
                tracker_ll_config_file = config.get('tracker', key)
                tracker.set_property('ll-config-file', tracker_ll_config_file)
            if key == 'enable-batch-process':
                tracker_enable_batch_process = config.getint('tracker', key)
                tracker.set_property('enable_batch_process', tracker_enable_batch_process)
            if key == 'enable-past-frame':
                tracker_enable_past_frame = config.getint('tracker', key)
                tracker.set_property('enable_past_frame', tracker_enable_past_frame)

        # ****** Create nvidia video converter ************
        print("Creating nvvidconv1 \n ")
        nvvidconv1 = Gst.ElementFactory.make("nvvideoconvert", "convertor1")
        if not nvvidconv1:
            sys.stderr.write(" Unable to create nvvidconv1 \n")

        # ****** Create video filter to convert frames to RGBA ************
        print("Creating filter1 \n ")
        caps1 = Gst.Caps.from_string("video/x-raw(memory:NVMM), format=RGBA")
        filter1 = Gst.ElementFactory.make("capsfilter", "filter1")
        if not filter1:
            sys.stderr.write(" Unable to get the caps filter1 \n")
        filter1.set_property("caps", caps1)

        # ****** Create tiler ************
        print("Creating tiler \n ")
        tiler = Gst.ElementFactory.make("nvmultistreamtiler", "nvtiler")
        if not tiler:
            sys.stderr.write(" Unable to create tiler \n")
        tiler_rows = int(math.sqrt(number_sources))
        tiler_columns = int(math.ceil((1.0 * number_sources) / tiler_rows))
        tiler.set_property("rows", tiler_rows)
        tiler.set_property("columns", tiler_columns)
        tiler.set_property("width", TILED_OUTPUT_WIDTH)
        tiler.set_property("height", TILED_OUTPUT_HEIGHT)

        # ****** Create nv video converter ************
        print("Creating nvvidconv \n ")
        nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "convertor")
        if not nvvidconv:
            sys.stderr.write(" Unable to create nvvidconv \n")

        # ****** Create OSD ************
        print("Creating nvosd \n ")
        nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")
        if not nvosd:
            sys.stderr.write(" Unable to create nvosd \n")

        # ****** Create transform ************
        if (is_aarch64()):
            print("Creating transform \n ")
            transform = Gst.ElementFactory.make("nvegltransform", "nvegl-transform")
            if not transform:
                sys.stderr.write(" Unable to create transform \n")

        # ****** Create Sink ************
        print("Creating EGLSink \n")
        sink = Gst.ElementFactory.make("nveglglessink", "nvvideo-renderer")
        if not sink:
            sys.stderr.write(" Unable to create egl sink \n")
        sink.set_property("sync", 0)
        sink.set_property("qos", 0)

        if is_live:
            print("Atleast one of the sources is live")
            streammux.set_property('live-source', 1)

        if not is_aarch64():
            # Use CUDA unified memory in the pipeline so frames
            # can be easily accessed on CPU in Python.
            mem_type = int(pyds.NVBUF_MEM_CUDA_UNIFIED)
            streammux.set_property("nvbuf-memory-type", mem_type)
            nvvidconv.set_property("nvbuf-memory-type", mem_type)
            nvvidconv1.set_property("nvbuf-memory-type", mem_type)
            tiler.set_property("nvbuf-memory-type", mem_type)

        print("Adding elements to Pipeline \n")
        pipeline.add(pgie)
        pipeline.add(tracker)
        pipeline.add(tiler)
        pipeline.add(nvvidconv)
        pipeline.add(filter1)
        pipeline.add(nvvidconv1)
        pipeline.add(nvosd)
        if is_aarch64():
            pipeline.add(transform)
        pipeline.add(sink)

        print("Linking elements in the Pipeline \n")
        streammux.link(pgie)
        pgie.link(tracker)
        tracker.link(nvvidconv1)
        nvvidconv1.link(filter1)
        filter1.link(tiler)
        tiler.link(nvvidconv)
        nvvidconv.link(nvosd)
        if is_aarch64():
            nvosd.link(transform)
            transform.link(sink)
        else:
            nvosd.link(sink)

        # create an event loop and feed gstreamer bus mesages to it
        loop = GObject.MainLoop()
        bus = pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", bus_call, loop)

        tiler_sink_pad = tiler.get_static_pad("sink")
        if not tiler_sink_pad:
            sys.stderr.write(" Unable to get src pad \n")
        else:
            tiler_sink_pad.add_probe(Gst.PadProbeType.BUFFER, self.tiler_src_pad_buffer_probe, 0)

        # List the sources
        print("Now playing...")
        for i, source in enumerate(args[:-1]):
            if i != 0:
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

