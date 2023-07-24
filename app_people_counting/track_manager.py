from array import array
from ast import Bytes
import code
from threading import Thread, Lock, main_thread
import os
import numpy as np
from numpy.linalg import norm
import cv2
import json
import time
from enum import Enum
from configs import *
from utils import current_milli_time

from minio import Minio
from minio.error import S3Error
import sys
from kafka import KafkaProducer
import logging

# logger = logging.getLogger('kafka')
# logger.addHandler(logging.StreamHandler(sys.stdout))
# logger.setLevel(logging.DEBUG)
def json_serializer(data):
    return json.dumps(data).encode('utf-8')

def ccw(p1,p2,p3):
    return (p3[1]-p1[1]) * (p2[0]-p1[0]) > (p2[1]-p1[1]) * (p3[0]-p1[0])

# Return true if line segments AB and CD intersect
def is_intersect(p1,p2,p3,p4):
    return ccw(p1,p3,p4) != ccw(p2,p3,p4) and ccw(p1,p2,p3) != ccw(p1,p2,p4)

def io_checking(p1, p2, line_1, line_2):
    is_pass_line_1 = is_intersect(p1, p2, line_1[0], line_1[1])
    is_pass_line_2 = is_intersect(p1, p2, line_2[0], line_2[1])
    if is_pass_line_1 & is_pass_line_2:
        d1 = norm(np.cross(np.array(line_1[0]) - np.array(p1), np.array(p1)-np.array(line_1[1])))/norm(np.array(line_1[0])-np.array(p1))
        d2 = norm(np.cross(np.array(line_2[0]) - np.array(p1), np.array(p1)-np.array(line_2[1])))/norm(np.array(line_2[0])-np.array(p1))
        print("========== d1={}      d1={}".format(d1, d2))
        if d1 < d2:
            return 'in'
        else:
            return 'out'
    return None

class DataTrack:
    track_id: int
    pos: []
    start_p: []
    ages: int
    live_ages: int
    need_warning: bool
    def __init__(self, track_id, pos):
        self.track_id = track_id
        self.start_p = pos

        self.ages = 0
        self.live_ages = 0

class DataRequest():
    track_id: int
    image: np.ndarray
    status: str
    violate: bool
    box: array
    def __init__(self, track_id, image, status, box, violate) -> None:
        self.track_id = track_id
        self.image = image
        self.status = status
        self.violate = violate
        self.box = box

class TrackManager(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.lock = Lock()

        self.data_track = {}
        self.q_request = []

        self.minio_client = Minio(MINIO_HOST, MINIO_ACCESS, MINIO_SECRET, secure=False)
        self.kafka_producer = KafkaProducer(bootstrap_servers=KAFKA_ADDRESS,
                                            value_serializer=json_serializer)

        self.running = True

    def remove_dead_tracklet(self, track_ids, max_ages = MISS_AGES_MAX):
        del_tracks = []
        for d in self.data_track:
            # update live ages
            if d in track_ids:
                self.data_track[d].ages = 0
                self.data_track[d].live_ages += 1
            else:
                self.data_track[d].ages += 1
                if self.data_track[d].ages > max_ages:
                    del_tracks.append(d)
        # remove track cached if not live
        for d in del_tracks:
            self.data_track.pop(d)

    def update(self, track_id, point):
        io_result = ""
        if track_id in self.data_track:
            # TODO: check pass line
            start_p = self.data_track[track_id].start_p
            io_result = io_checking(start_p, point, LINE_OUT, LINE_IN)
            if not io_result is None:
                self.data_track[track_id].start_p = point
                print("track id {} startp={} curP={}  ==> result={}".format(track_id, start_p, point, io_result))
                return io_result
        else:
            # Create new object
            self.data_track[track_id] = DataTrack(track_id, point)

        self.remove_dead_tracklet({track_id})

        return io_result

    def add_data_request(self, data_request):
        self.lock.acquire()
        if data_request.track_id in self.data_track:
            if data_request.violate:
                self.data_track[data_request.track_id].need_warning = False

        self.q_request.append(data_request)
        self.lock.release()

    def terminate(self):
        self.running = False
    
    def upload_image(self, image, bucket):
        found = self.minio_client.bucket_exists(bucket)
        if not found:
            self.minio_client.make_bucket(bucket_name=bucket)
        tmp_file_path = 'tmp.jpg'
        h,w,c = image.shape
        ratio = h/720
        resize_dim = (int(w/ratio) , 720)
        image = cv2.resize(image, resize_dim, interpolation = cv2.INTER_AREA)
        # print(image.shape)
        cv2.imwrite(tmp_file_path, image)

        minio_file = CAMID + '/' + CAMID + '_' + str(current_milli_time()) + '.jpg'
        self.minio_client.fput_object(bucket_name=bucket, object_name=minio_file, file_path=tmp_file_path)
        
        return 'https://' + MINIO_HOST + '/' + MINIO_BUCKET_IMAGE + '/' + minio_file

    def run(self):
        while True:
            if not self.running or not main_thread().isAlive():
                break
            time.sleep(0.01)
            if len(self.q_request) == 0:
                continue
            
            self.lock.acquire()
            data = self.q_request.pop(0)
            self.lock.release()

            # Save minio
            # url_minio = self.upload_image(data.image, bucket=MINIO_BUCKET_IMAGE)
            #
            # # Push server
            # event_type = ''
            # if data.violate:
            #     event_type = 'SM02'
            #
            # message = {
            #     'camera_id': CAMID,
            #     'camera_ip': '',
            #     'image_url': url_minio,
            #     'processed_image_url': url_minio,
            #     'frame_id': 1,
            #     'track_id': data.track_id,
            #     'event_time': current_milli_time(),
            #     'boxes': [data.box], # [[x1, y1, x2, y2], [x1, y1, x2, y2]]
            #     'is_violation': True,
            #     'event_type': event_type,
            #     'description': data.status,
            #     'display_events': ['SM02']
            # }
            #
            # self.kafka_producer.send(KAFKA_TOPIC, message)
            # print('Send kafka', message)
            
