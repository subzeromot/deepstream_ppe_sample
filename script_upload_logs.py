import os
import glob
from configs import *
from upload_minio import MinioUploader
import time

from utils import get_logger, get_hostname, get_ip

logger = get_logger()

# Get the directory of script
dir_arr = os.path.realpath(__file__).split('/')
dir_arr = dir_arr[:-1]
DIR=''
for dir in dir_arr:
    DIR = DIR + dir + '/'
print("Script path:", DIR)

logfiles = []
try:
    with open(DIR + 'logs/list_logs.txt', 'a+') as file_lst_logs:
        lines = [line.rstrip() for line in file_lst_logs]
        for line in lines:
            logfiles.append(line)
except:
    pass

uploadMinio = MinioUploader(MINIO_HOST, MINIO_ACCESS, MINIO_SECRET)

hostname = get_hostname()
minio_log_folder = 'fimlog_' + hostname

ip_eth0 = ''
ip_eth1 = ''
try:
    ip_eth0 = get_ip('eth0')
except:
    pass

try:
    ip_eth1 = get_ip('eth1')
except:
    pass

if not (ip_eth0 == ''):
    minio_log_folder = minio_log_folder + '_' + ip_eth0
elif not (ip_eth1 == ''):
    minio_log_folder = minio_log_folder + '_' + ip_eth1

while True:
    time.sleep(30)

    # Upload lastest file log
    try:
        print("Minio uploading: fim_log.log")
        uploadMinio.upload(MINIO_BUCKET_LOG, minio_log_folder, DIR + 'logs/fim_log.log')
    except:
        print("Minio upload fail!")
        exit()
    
    for file in glob.glob(DIR + "logs/fim_log.log.*"):
        if not (file in logfiles):
            with open(DIR + 'logs/list_logs.txt', 'a+') as file_lst_logs:
                file_lst_logs.write(file)
                file_lst_logs.write('\n')
            logfiles.append(file)
            print("Minio uploading: {}".format(file))
            try:
                uploadMinio.upload(MINIO_BUCKET_LOG, minio_log_folder, file)
            except:
                print("Minio upload fail!")
                exit()