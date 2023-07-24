from array import array
from ast import Bytes
import code
from threading import Thread, Lock, main_thread
import os
import numpy as np
import cv2
import json
import time
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

class DataTrack:
    track_id: int
    ages: int
    live_ages: int
    need_warning: bool
    violate: bool
    violate_age: int
    def __init__(self, track_id, ages):
        self.track_id = track_id
        self.ages = ages

        self.live_ages = 0
        self.need_warning = False
        self.violate = False
        self.violate_age = 0
    
    def update_violate_age(self, violate_status):
        # Change age
        if violate_status:
            self.violate_age += 1
        else:
            self.violate_age -= 1
        
        # Change status violate
        if self.violate_age >= MIN_INTRUSION_AGE:
            self.violate_age = MIN_INTRUSION_AGE
            if not self.violate:
                self.need_warning = True
            self.violate = True
        if self.violate_age <= 0:
            self.violate_age = 0
            self.violate = False

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
            if d in track_ids:
                self.data_track[d].ages = 0
                self.data_track[d].live_ages += 1
            else:
                self.data_track[d].ages += 1
                if self.data_track[d].ages > max_ages:
                    del_tracks.append(d)
        for d in del_tracks:
            self.data_track.pop(d)

    def do_need_warning(self, track_id, violate):
        need_warning = False
        violate_age = 0
        if track_id in self.data_track:
            # Update violate age
            self.data_track[track_id].update_violate_age(violate)
            need_warning = self.data_track[track_id].need_warning
            violate_age = self.data_track[track_id].violate_age
        else:
            # Create new object
            self.data_track[track_id] = DataTrack(track_id, 1)

        self.remove_dead_tracklet({track_id})

        return need_warning, violate_age

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
            url_minio = self.upload_image(data.image, bucket=MINIO_BUCKET_IMAGE)

            # Push server
            event_type = ''
            if data.violate:
                event_type = 'SM02'

            message = {
                'camera_id': CAMID,
                'camera_ip': '',
                'image_url': url_minio,
                'processed_image_url': url_minio,
                'frame_id': 1,
                'track_id': data.track_id,
                'event_time': current_milli_time(),
                'boxes': [data.box], # [[x1, y1, x2, y2], [x1, y1, x2, y2]]
                'is_violation': True,
                'event_type': event_type,
                'description': data.status,
                'display_events': ['SM02']
            }
            
            self.kafka_producer.send(KAFKA_TOPIC, message)
            print('Send kafka', message)
            
