import cv2
import numpy as np
import random

def crop_object(image, obj_meta):
    scale_w = 0.25
    scale_h = 0.25
    h, w, c = image.shape
    rect_params = obj_meta.rect_params
    top = int(rect_params.top)
    left = int(rect_params.left)
    width = int(rect_params.width)
    height = int(rect_params.height)

    top = max(0, int(top - height*scale_h/2))
    left = max(0, int(left - width*scale_w/2))
    width = int(width * (1+scale_w))
    height = int(height * (1+scale_h))

    crop_img = image[top:min(top+height, h), left:min(left+width, w)]
	
    return crop_img

def plot_box(image, obj_meta, l_color, label):
    rect_params = obj_meta.rect_params
    top = int(rect_params.top)
    left = int(rect_params.left)
    width = int(rect_params.width)
    height = int(rect_params.height)

    # print('face w={}  h={}'.format(width, height))

    len_h = int(0.1 * height)
    len_w = int(0.1 * width)
    x1 = int(left)
    y1 = int(top)
    x2 = int(left + width)
    y2 = int(top + height)

    # l_color = (0, 255, 0)

    line_tn = 2
    cv2.line(image, (x1, y1), (x1 + len_w, y1), l_color, line_tn)
    cv2.line(image, (x1, y1), (x1, y1 + len_h), l_color, line_tn)
    cv2.line(image, (x2, y2), (x2 - len_w, y2), l_color, line_tn)
    cv2.line(image, (x2, y2), (x2, y2 - len_h), l_color, line_tn)
    cv2.line(image, (x1, y2), (x1 + len_w, y2), l_color, line_tn)
    cv2.line(image, (x1, y2), (x1, y2 - len_h), l_color, line_tn)
    cv2.line(image, (x2, y1), (x2 - len_w, y1), l_color, line_tn)
    cv2.line(image, (x2, y1), (x2, y1 + len_h), l_color, line_tn)

    cv2.putText(image, label, (x1, int(y1 - 0.05 * height)), cv2.FONT_HERSHEY_COMPLEX, 1, l_color, 2)

    return image
def draw_text(image, text, color, pos):
    cv2.putText(image, text, pos, cv2.FONT_HERSHEY_COMPLEX, 1, color, 2)
    return image
def plot_box_grad(image, obj_meta, l_color, label):
    rect_params = obj_meta.rect_params
    top = int(rect_params.top)
    left = int(rect_params.left)
    width = int(rect_params.width)
    height = int(rect_params.height)

    # print('face w={}  h={}'.format(width, height))

    len_h = int(0.3 * height)
    len_w = int(0.3 * width)
    x1 = int(left)
    y1 = int(top)
    x2 = int(left + width)
    y2 = int(top + height)

    # l_color = (0, 255, 0)

    line_tn = 2
    cv2.line(image, (x1, y1), (x1 + len_w, y1), l_color, line_tn)
    cv2.line(image, (x1, y1), (x1, y1 + len_h), l_color, line_tn)
    cv2.line(image, (x2, y2), (x2 - len_w, y2), l_color, line_tn)
    cv2.line(image, (x2, y2), (x2, y2 - len_h), l_color, line_tn)
    cv2.line(image, (x1, y2), (x1 + len_w, y2), l_color, line_tn)
    cv2.line(image, (x1, y2), (x1, y2 - len_h), l_color, line_tn)
    cv2.line(image, (x2, y1), (x2 - len_w, y1), l_color, line_tn)
    cv2.line(image, (x2, y1), (x2, y1 + len_h), l_color, line_tn)

    cv2.putText(image, label, (x1, int(y1 - 0.05 * height)), cv2.FONT_HERSHEY_COMPLEX, 1, l_color, 2)

    return image

def random_color():
    rgbl=[random.randint(0,255),random.randint(0,255),random.randint(0,255)]
    return tuple(rgbl)

def draw_roi(image, ROI):
    cv2.rectangle(image, (ROI[0], ROI[1]), (ROI[0] + ROI[2], ROI[1] + ROI[3]), (0,0,255), 2)

def draw_polygon(image, points, color=random_color()):
    cv_points = np.array(points, np.int32)
    cv2.polylines(image, [cv_points], True, color, 2)

def is_inside_rect(x1, y1, x2, y2, px, py):
    return (x1 < px < x2) and (y1 < py < y2)

def is_in_roi(obj_meta, ROI):
    rect_params = obj_meta.rect_params
    x1 = int(rect_params.left)
    y1 = int(rect_params.top)
    x2 = int(x1 + rect_params.width)
    y2 = int(y1 + rect_params.height)

    tl_ = is_inside_rect(ROI[0], ROI[1], ROI[0] + ROI[2], ROI[1] + ROI[3], x1, y1)
    br_ = is_inside_rect(ROI[0], ROI[1], ROI[0] + ROI[2], ROI[1] + ROI[3], x2, y2)

    return tl_ & br_

def is_point_in_polygon(polygon, point):
    contours = np.array(polygon, np.int32)
    dst = cv2.pointPolygonTest(contours, point, True)
    # print(result)
    if dst > 0: 
        return True
    else:
        return False

def letterbox(image, size = (720, 1280, 4)):
    ih, iw, ic = image.shape
    h, w, c = size
    scale = min(w / iw, h / ih)
    nw = int(iw * scale)
    nh = int(ih * scale)
    image = cv2.resize(image, (nw, nh))
    
    new_image = np.zeros(size, np.uint8)
    new_image[(h - nh) // 2:(h - nh) // 2 + ih, (w - nw) // 2:(w - nw) // 2 + iw, :] = image
    # new_image.paste(image, ((w - nw) // 2, (h - nh) // 2))
    return new_image

import time
def current_milli_time():
    return round(time.time() * 1000)

import os
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
# Get the directory of script
dir_arr = os.path.realpath(__file__).split('/')
dir_arr = dir_arr[:-1]
DIR=''
BACKUP_COUNT = 10
for dir in dir_arr:
    DIR = DIR + dir + '/'
def init_logger():
    dir = DIR + 'logs'
    if not os.path.exists(dir):
        os.makedirs(dir)

    formatter = logging.Formatter('%(asctime)s _ %(name)s _ %(levelname)s _ %(message)s')
    logger = logging.getLogger('LOG')
    logger.setLevel(logging.DEBUG)
    
    # handler = RotatingFileHandler(dir + '/fim_log.log', maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT)
    handler = TimedRotatingFileHandler(dir + '/fim_log.log', when='m', interval=15, backupCount=BACKUP_COUNT, 
                                        encoding=None, delay=False, atTime=None)
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger

logger = init_logger()

def get_logger():
    return logger
