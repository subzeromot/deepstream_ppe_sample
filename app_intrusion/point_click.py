# importing the module
import cv2
import numpy as np
import random

video_url = "rtsp://admin:123456aA@10.35.31.50:554/Streaming/Channels/101"
points=[]
config_points=[]
roi_numb = 0

def random_color():
    rgbl=[random.randint(0,255),random.randint(0,255),random.randint(0,255)]
    return tuple(rgbl)

def click_event(event, x, y, flags, params):
    # checking for left mouse clicks
    global roi_numb, points
    if event == cv2.EVENT_LBUTTONDOWN:
        c_x = x
        c_y = y
        # c_x = int(x * 1920/1136)
        # c_y = int(y * 1080/630)
        # print("x:", x, "  ", c_x, "      y:",y,"  ", c_y)
        cv2.circle(img,(x,y), 3, (0,0,255), -1)
  
        config_points.append(c_x)
        config_points.append(c_y)
        points.append([x,y])
  
        # displaying the coordinates
        # on the image window
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(img, str(x) + ',' +
                    str(y), (x,y), font,
                    0.5, (255, 0, 0), 1)
        cv2.imshow('image', img)
  
    # # checking for right mouse clicks     
    if event==cv2.EVENT_RBUTTONDOWN:
        # print list points for config
        print("ROI {0}: {1}".format(roi_numb,config_points))
        
        # draw polygon
        cv_points = np.array(points, np.int32)
        cv_points = cv_points.reshape((-1,1,2))
        color = random_color()
        cv2.polylines(img, [cv_points], True, color, 2)
        
        # reset list data
        config_points.clear()
        points.clear()
            
        roi_numb = roi_numb + 1
        cv2.imshow('image', img)

# driver function
if __name__=="__main__":
  
    # reading the image
    # img = cv2.imread('/home/dannv5nxt/Downloads/Video_input/ROI_6/ROI6.PNG', 1)
    
    # read video
    cap = cv2.VideoCapture(video_url)
    if not cap.isOpened():
        print("Cannot open video {}".format(video_url))
        exit()
    ret, img = cap.read()


    # displaying the image
    cv2.imshow('image', img)
  
    # setting mouse hadler for the image
    # and calling the click_event() function
    cv2.setMouseCallback('image', click_event)
  
    # wait for a key to be pressed to exit
    cv2.waitKey(0)
  
    # close the window
    cv2.destroyAllWindows()
