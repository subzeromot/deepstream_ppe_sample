VERSION_INFO = 'Version 1.0.0 \
                Update time: 2 Mar 2022 16:55:46'

# Camera
CAMID = "6245112195c877ec434099ec"

# DEEPSTREAM CONFIG
PGIE_CONFIG = '../models/yolov5_fm_320px/config_infer_primary.txt'
TRACK_CONFIG = '../config_ds_5.1/tracker_config.txt'

LIVE_AGES_MIN = 5    # unit: frame --> numb of frames this object existed 
MISS_AGES_MAX = 15    # unit: frame --> numb of frames this object disappear
SIMILARITY_SCORE_THRESH = 0.75

# ROI: [x,y,w,h]
ROI = [0, 0, 1280, 720]

# DÍPLAY SETTING
DISPLAY_W = 1280
DISPLAY_H = 720

#LOGGING
MAX_BYTES = 100000
BACKUP_COUNT = 10
TIME_CHECK_INTERVAL = 30    #seconds

#LOGO COORDINATION
COOR_X = 435
COOR_Y = 5

#MINIO
MINIO_HOST='fs.nexteyevision.com'
MINIO_ACCESS='camera-team'
MINIO_SECRET='c@me3a-team'
MINIO_BUCKET_IMAGE='camera-team'

#Kafka
KAFKA_ADDRESS = '18.139.72.29:30002'
KAFKA_TOPIC = 'nexteye.events'