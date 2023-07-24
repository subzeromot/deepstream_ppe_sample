VERSION_INFO = 'Version 1.0.0 \
                Update time: 2 Mar 2022 16:55:46'

# Camera
CAMID = "6245112195c877ec434099ec_test"

# DEEPSTREAM CONFIG
PGIE_CONFIG = '../models/yolov5_fm_320px/config_infer_primary.txt'
TRACK_CONFIG = '../config_ds_5.1/tracker_config.txt'

LIVE_AGES_MIN = 5    # unit: frame --> numb of frames this object existed 
MISS_AGES_MAX = 15    # unit: frame --> numb of frames this object disappear
SIMILARITY_SCORE_THRESH = 0.75

# ROI: [x,y,w,h]
ROI = [400, 0, 400, 720]

# STREAMMUX
STREAMMUX_W = 1280
STREAMMUX_H = 720

# CROP
CROP_LEFT = ROI[0]
CROP_RIGHT = STREAMMUX_W - (ROI[0] + ROI[2])
CROP_TOP = ROI[1]
CROP_BOTTOM = STREAMMUX_H - (ROI[1] + ROI[3])

# DISPLAY Resolution
DISPLAY_W = STREAMMUX_W - (CROP_LEFT + CROP_RIGHT)
DISPLAY_H = STREAMMUX_H - (CROP_TOP + CROP_BOTTOM)

#LOGGING
MAX_BYTES = 100000
BACKUP_COUNT = 10
TIME_CHECK_INTERVAL = 30    #seconds

# MINIO
MINIO_HOST='fs.nexteyevision.com'
MINIO_ACCESS='camera-team'
MINIO_SECRET='c@me3a-team'
MINIO_BUCKET_IMAGE='camera-team'

# Kafka
KAFKA_ADDRESS = '18.139.72.29:30002'
KAFKA_TOPIC = 'nexteye.events'