#!/usr/bin/env python3

print('Please run under desktop environment (eg: vnc) to display the image window')

import cv2
from picamera2 import Picamera2
import time

face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml') 

def human_face_detect(img):
    resize_img = cv2.resize(img, (320,240), interpolation=cv2.INTER_LINEAR)         # In order to reduce the amount of calculation, resize the image to 320 x 240 size
    gray = cv2.cvtColor(resize_img, cv2.COLOR_BGR2GRAY)    # Convert to grayscale
    faces = face_cascade.detectMultiScale(gray, 1.3, 2)    # Detect faces on grayscale images
    face_num = len(faces)   # Number of detected faces
    if face_num  > 0:
        for (x,y,w,h) in faces:
            
            x = x*2   # Because the image is reduced to one-half of the original size, the x, y, w, and h must be multiplied by 2.
            y = y*2
            w = w*2
            h = h*2
            cv2.rectangle(img,(x,y),(x+w,y+h),(255,0,0),2)  # Draw a rectangle on the face
    
    return img


with Picamera2() as camera:
    print("start human face detect")

    camera.preview_configuration.main.size = (640,480)
    camera.preview_configuration.main.format = "RGB888"
    camera.preview_configuration.align()
    camera.configure("preview")
    camera.start()

    while True:
        img = camera.capture_array()
        img =  human_face_detect(img) 
        cv2.imshow("video", img)  #OpenCV image show
    
        k = cv2.waitKey(1) & 0xFF
        # 27 is the ESC key, which means that if you press the ESC key to exit
        if k == 27:
            break

    print('quit ...') 
    cv2.destroyAllWindows()
    camera.close()  
     
