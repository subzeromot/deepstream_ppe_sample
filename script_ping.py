import os
import glob
import time

from utils import get_logger, get_hostname, get_ip
import door_config as cfg

host_schindler = cfg.url_login.replace('https://', '').split(':')[0]

count = 0
while True:
    time.sleep(5)

    response = os.system("ping -c 1 " + host_schindler)

    #and then check the response...
    if response == 0:
        print (host_schindler, 'is up!')
        count = 0
    else:
        print (host_schindler, 'is down!')
        count += 1

    if count > 3:
        os.system('reboot')