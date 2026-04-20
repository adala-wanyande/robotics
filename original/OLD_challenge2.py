import sys
import tty
import termios
import asyncio
import time
import cv2
from picamera2 import Picamera2
import numpy as np
import picar_4wd as fc

power_val = 10
movement_history = []  # List to store movements along with their durations
duration_history = []
last_key_time = time.time()
left_images = []
right_images = []
print("If you want to quit, please press 'q'.")


def initialize_camera():
    camera = Picamera2()
    camera.preview_configuration.main.size = (640, 480)
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
    global reference_image
    # Capture an image from the camera
    reference_image = camera.capture_array()
    # Optionally, you can save the reference image to disk for future use
    cv2.imwrite("reference_image.jpg", reference_image)

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
    lower_red1 = np.array([0, 120, 70])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 120, 70])
    upper_red2 = np.array([180, 255, 255])
    
    global left_images
    global right_images
    
    print("Searching for red object...")
    found_object = False
    startRotation = time.time()
    
    # Save image before rotation to find the object 
    fc.stop()
    time.sleep(1)
    reference_image_rotation = save_reference_image(camera)
    
    # Red object detection starts here
    while not found_object:
        # Turn right slowly
        fc.turn_right(power_val)
        time.sleep(0.1) # Adjust turning time for more granular control
        fc.stop()
        
        # Capture image and check for red object
        img = camera.capture_array()
        found_object = detect_object(img)
    
    s = time.time()
    # Rotate more to fix the angle camera issue
    fc.turn_right(power_val)
    time.sleep(0.15)
    e = time.time()
    print("Duration: ", e-s)
    endRotation = time.time() - startRotation
    
        
    print("Red object detected, moving towards object...")
    
    # Initialize variables for tracking red color coverage
    total_pixels = img.shape[0] * img.shape[1]
    target_coverage = 0.1 # Target coverage for red color in the image
    current_coverage = 0.0
    
    # Move forward until target coverage of red color is reached
    startMoving = time.time()
    while current_coverage < target_coverage:
        fc.forward(power_val)
        # Capture image anc check for red object
        img = camera.capture_array()
        
        # Calculate current coverage of red color in the image
        red_pixels = cv2.countNonZero(cv2.inRange(cv2.cvtColor(img, cv2.COLOR_BGR2HSV), lower_red1,
        upper_red1))
        red_pixels += cv2.countNonZero(cv2.inRange(cv2.cvtColor(img, cv2.COLOR_BGR2HSV), lower_red2,
        upper_red2))
        print("red pixels: ", red_pixels)
            
        #print("red pixels shape: ", red_pixels.shape)
        
        current_coverage = red_pixels / total_pixels
        print("current_coverage: ", current_coverage)
        if current_coverage > 0.1:
            print("BREAKING: ", current_coverage)
            fc.forward(power_val)
            time.sleep(0.4)
            break
    endMoving = time.time() - startMoving
    
    # Stop when target coverage is reached or red object is lost
    fc.stop()
    
    print("Object touched, returning to home...")
    
    # Redo last actions to get to object (rotation + forward movement)
    print("Backward movement for :", endMoving)
    print("Rotation to left for: ", endRotation)
    # Move backward for the same amount of time that robot moved forward before
    fc.backward(power_val)
    time.sleep(endMoving)
    
    # Turn left until robot arrives in the same position as before
    threshold = 30
    print("Turning...")
    while True:
        fc.turn_left(1)
        current_image = camera.capture_array()
        
        #fc.stop()
        #current_image = camera.capture_array()
        
        #fc.turn_left(1)
        

        # Compare images
        difference = cv2.absdiff(current_image, reference_image_rotation)
        mean_difference = difference.mean()
        
        print("MEAN DIFFERENCE: ", mean_difference)
        # Check if alignment is achieved (adjust threshold as needed)
        if mean_difference < threshold:
            break  # Stop rotationddd

    # Optionally, display the current image or difference for debugging
    #cv2.imshow("Current Image", current_image)
    #cv2.waitKey(1)
    cv2.imwrite("current_image.jpg", current_image)

    #fc.turn_left(power_val)
    #time.sleep(endRotation) # - 0.18
    print("Rotation finished.")
    

    global movement_history
    global duration_history
    #print(movement_history)
    duration_history.pop(0)
    
    #fc.turn_right(power_val)
    #asyncio.run(sleep_for_duration(1.6)) 
    print("Lenght of movement_history: ", movement_history)
    print("Lenght of duration_history: ", duration_history)
    
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
            now_image = save_reference_image(camera)
            print("Right")
            #duration = duration + 0.05
            #fc.turn_right(power_val)
            while True:
                fc.turn_right(1)
                now_image = camera.capture_array()
                
                #fc.stop()
                #current_image = camera.capture_array()
                
                #fc.turn_left(1)
               
                
                # Compare images
                difference = cv2.absdiff(now_image, left_images[-1])
                mean_difference = difference.mean()
                
                print("MEAN DIFFERENCE: ", mean_difference)
                # Check if alignment is achieved (adjust threshold as needed)
                if mean_difference < threshold:
                    cv2.imwrite("current_image.jpg", now_image)
                    break
            left_images.pop()
        elif command == 'd':
            now_image = save_reference_image(camera)
            print("Left")
            #duration = duration + 0.05
            #fc.turn_right(power_val)
            while True:
                fc.turn_left(1)
                now_image = camera.capture_array()
                
                #fc.stop()
                #current_image = camera.capture_array()
                
                #fc.turn_left(1)

                # Compare images
                difference = cv2.absdiff(now_image, right_images[-1])
                mean_difference = difference.mean()
                
                print("MEAN DIFFERENCE: ", mean_difference)
                # Check if alignment is achieved (adjust threshold as needed)
                if mean_difference < threshold:
                    cv2.imwrite("current_image.jpg", now_image)
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
