import sys
import tty
import termios
import asyncio
import time
import cv2
from picamera2 import Picamera2
import numpy as np
import picar_4wd as fc

power_val = 5
movement_history = []  # List to store movements along with their durations
duration_history = []
last_key_time = time.time()
print("If you want to quit, please press 'q'.")
left_images = []
right_images = []


def initialize_camera():
    camera = Picamera2()
    # 1536 x 864
    # 640 x 480
    camera.preview_configuration.main.size = (1536, 864)
    camera.preview_configuration.main.format = "RGB888"
    camera.preview_configuration.align()
    camera.configure("preview")
    camera.start()
    return camera


def readchar():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch


def readkey(getchar_fn=None):
    getchar = getchar_fn or readchar
    c1 = getchar()
    if ord(c1) != 0x1b:
        return c1
    c2 = getchar()
    if ord(c2) != 0x5b:
        return c1
    c3 = getchar()
    return chr(0x10 + ord(c3) - 65)
    
def save_reference_image(camera):
    print("image_Counter")
    #global reference_image
    # Capture an image from the camera
    reference_image = camera.capture_array()
    # Optionally, you can save the reference image to disk for future use
    cv2.imwrite("reference_image.jpg", reference_image)
    return reference_image

async def sleep_for_duration(duration):
    await asyncio.sleep(duration)

def detect_object(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower_red1 = np.array([0, 120, 70])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 120, 70])
    upper_red2 = np.array([180, 255, 255])

    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = cv2.bitwise_or(mask1, mask2)

    # Check if there is a significant amount of red
    if cv2.countNonZero(mask) > 500:
        return True
    return False


def return_to_home(camera):
    global movement_history
    global duration_history
    global left_images
    global right_images

    threshold = 25
    duration_history.pop(0)

    print("Length of movement_history: ", movement_history)
    print("Length of duration_history: ", duration_history)
    
    for i in reversed(range(len(movement_history))):
        command = movement_history[i]
        duration = duration_history[i]
        start = time.time()
        if command == 'w':
            print("Backward: ", duration)
            fc.backward(power_val)
            asyncio.run(sleep_for_duration(duration)) # Use the stored duration for each move
        elif command == 's':
            print("Forward")
            fc.forward(power_val)
            asyncio.run(sleep_for_duration(duration)) # Use the stored duration for each move
        elif command == 'a':
            print("Right")
            while True:
                #fc.stop()
                #asyncio.run(sleep_for_duration(0.005))  # Adjust the duration as needed
                current_image = camera.capture_array()
                fc.turn_right(power_val)
                
                #fc.turn_left(1)
                reference_image = left_images[-1]
                
                # Compare images
                difference = cv2.absdiff(current_image, reference_image)
                mean_difference = difference.mean()
                
                print("MEAN DIFFERENCE: ", mean_difference)
                # Check if alignment is achieved (adjust threshold as needed)
                if mean_difference < threshold:
                    cv2.imwrite("current_image.jpg", current_image)
                    break
            left_images.pop()
                
        elif command == 'd':
            #current_image = save_reference_image(camera)
            print("Left")
            #duration = duration + 0.05
            #fc.turn_right(power_val)
            counter = 0
            while True:
                #fc.stop()
                #asyncio.run(sleep_for_duration(0.005))
                current_image = camera.capture_array()
                fc.turn_left(power_val)
                
                #fc.turn_left(1)
                reference_image = right_images[-1]
                
                # Compare images
                difference = cv2.absdiff(current_image, reference_image)
                mean_difference = difference.mean()
                
                print("MEAN DIFFERENCE: ", mean_difference)
                counter += 1
                
                # Check if alignment is achieved (adjust threshold as needed)
                if mean_difference < threshold:
                    cv2.imwrite("current_image.jpg", current_image)
                    break
            right_images.pop()
        end = time.time()-start
        print("END: ", end) 
    movement_history.clear()
    fc.stop()


def keyboard_control():
    global last_key_time
    camera = initialize_camera()

    try:
        while True:
            key = readkey()
            current_time = time.time()
            duration = current_time - last_key_time
            last_key_time = current_time

            if key in ['w', 's', 'a', 'd']:
                movement_history.append(key)
                duration_history.append(duration)

            if key == 'w':
                fc.forward(power_val)
            elif key == 'a':
                reference_image = save_reference_image(camera)
                left_images.append(reference_image)
                fc.turn_left(power_val)
            elif key == 's':
                fc.backward(power_val)
            elif key == 'd':
                reference_image = save_reference_image(camera)
                right_images.append(reference_image)
                fc.turn_right(power_val)
            elif key == 'q':
                duration_history.append(duration)
                print("Returning to home position")
                return_to_home(camera)
                break
            else:
                fc.stop()
                break
    finally:
        camera.stop()


if __name__ == '__main__':
    keyboard_control()
