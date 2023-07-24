VERSION_INFO = 'Version 1.0.0 \
                Update time: 2 Mar 2022 16:55:46'

# Camera
CAMID = "ss"

# DEEPSTREAM CONFIG
PGIE_CONFIG = '../models/yolov5_person_cm01_416px/config_infer_primary.txt'
TRACK_CONFIG = '../config_ds_5.1/tracker_config.txt'

LIVE_AGES_MIN = 15    # unit: frame --> numb of frames this object existed 
MISS_AGES_MAX = 15    # unit: frame --> numb of frames this object disappear
# SIMILARITY_SCORE_THRESH = 0.75

# ROI: [x,y,w,h]
ROI = [430, 0, 420, 720]

# Streammux SETTING
STREAM_W = 1280
STREAM_H = 720

VIDEO_CROP_L = ROI[0]
VIDEO_CROP_R = STREAM_W - (ROI[0] + ROI[2]) 
VIDEO_CROP_T = ROI[1]
VIDEO_CROP_B = STREAM_H - (ROI[1] + ROI[3])

#LOGGING
MAX_BYTES = 100000
TIME_CHECK_INTERVAL = 30    #seconds

#LOGO COORDINATION
COOR_X = ROI[0] + 5
COOR_Y = 5

#MINIO
MINIO_HOST='fs.nexteyevision.com'
MINIO_ACCESS='camera-team'
MINIO_SECRET='c@me3a-team'
MINIO_BUCKET_IMAGE='camera-team'

#Kafka
KAFKA_ADDRESS = '18.139.72.29:30002'
KAFKA_TOPIC = 'nexteye.events'

#SINK Overlay position
SINK_OVERLAY_x = 0
SINK_OVERLAY_y = 0
SINK_OVERLAY_w = ROI[2]
SINK_OVERLAY_h = ROI[3]