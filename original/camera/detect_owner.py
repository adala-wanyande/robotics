#!/usr/bin/env python3

print('Please run under desktop environment (eg: vnc) to display the image window')

import cv2
from picamera2 import Picamera2
import time
import picar_4wd as fc

face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

def detect_owner(img, allow_movement):
    resize_img = cv2.resize(img, (320,240), interpolation=cv2.INTER_LINEAR)         # In order to reduce the amount of calculation, resize the image to 320 x 240 size
    gray = cv2.cvtColor(resize_img, cv2.COLOR_BGR2GRAY)    # Convert to grayscale
    faces = face_cascade.detectMultiScale(gray, 1.3, 2)    # Detect faces on grayscale images
    face_num = len(faces)   # Number of detected faces
    if face_num  > 0 and allow_movement:

        # The robot will consider only the first face that it sees.
        (x,y,w,h) = faces[0]

        x = x*2   # Because the image is reduced to one-half of the original size, the x, y, w, and h must be multiplied by 2.
        y = y*2
        w = w*2
        h = h*2
        cv2.rectangle(img,(x,y),(x+w,y+h),(255,0,0),2)  # Draw a rectangle on the face

        # The robot is moving in the owner's direction
        face_center_x = x + w / 2
        frame_center_x = img.shape[1] / 2
        if face_center_x < frame_center_x - 50:  # Face is on the left
            fc.turn_left(10)
        elif face_center_x > frame_center_x + 50:  # Face is on the right
            fc.turn_right(10)
        else:  # Face is in the center
            fc.forward(10)

    if allow_movement == False: fc.stop()

    return img


start_time = time.time()

with Picamera2() as camera:
    print("Start detecting the owner")

    camera.preview_configuration.main.size = (640,480)
    camera.preview_configuration.main.format = "RGB888"
    camera.preview_configuration.align()
    camera.configure("preview")
    camera.start()

    allow_movement = True  # Initially allow movement

    while True:

        current_time = time.time()
        if current_time - start_time > 20:
            allow_movement = False  # Disable movement after 20 seconds

        # parameter movment_allowed can be modified further by using vocal commands

        img = camera.capture_array()
        img =  detect_owner(img, allow_movement)
        cv2.imshow("video", img)  #OpenCV image show


        k = cv2.waitKey(1) & 0xFF
        # 27 is the ESC key, which means that if you press the ESC key to exit
        if k == 27:
            fc.stop()
            break

    print('quit ...')
    cv2.destroyAllWindows()
    camera.close()