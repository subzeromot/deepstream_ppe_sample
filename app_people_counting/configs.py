VERSION_INFO = 'Version 1.0.0 \
                Update time: 2 Mar 2022 16:55:46'

# Camera
CAMID = "test"

# DEEPSTREAM CONFIG
PGIE_CONFIG = '../models/Primary_Detector/config_infer_primary.txt' 
TRACK_CONFIG = '../config_ds_5.1/tracker_config.txt'

LIVE_AGES_MIN = 5    # unit: frame --> numb of frames this object existed 
MISS_AGES_MAX = 30    # unit: frame --> numb of frames this object disappear
MIN_INTRUSION_AGE = 5 # unit: frame

LINE_IN = [[2, 520], [1576, 1076]]
LINE_OUT = [[1738, 910], [202, 430]]
# LINE_IN = [[530, 441], [1344, 599]]
# LINE_OUT = [[622, 358], [1355, 501]]

#Streammux
STREAMMUX_W = 1920
STREAMMUX_H = 1080

# DÍPLAY SETTING
TILED_OUTPUT_WIDTH=1920
TILED_OUTPUT_HEIGHT=1080

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