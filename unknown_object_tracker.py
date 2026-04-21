#!/usr/bin/env python3

import cv2
from picamera2 import Picamera2
import numpy as np
import time

print("Starting Unknown Object Tracker (SSH Mode)...")

# 1. Initialize the Background Subtractor
# history=500 (remembers last 500 frames)
# varThreshold=50 (higher = less sensitive to camera noise)
# detectShadows=False (Ignore shadows to keep the bounding box accurate)
backSub = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50, detectShadows=False)

# 2. Setup Noise Filter
kernel_5 = np.ones((5,5), np.uint8)

def detect_unknown_object(img, state, time_left):
    """
    Processes the image to find the unknown object based on the current state.
    """
    # Downscale for massive speed boost (matches original code logic)
    resize_img = cv2.resize(img, (160, 120), interpolation=cv2.INTER_LINEAR)
    
    if state == "CALIBRATING":
        # learningRate=0.05 makes the algorithm learn the static room, lighting, and fixed obstacles
        mask = backSub.apply(resize_img, learningRate=0.05)
        
        # Add visual feedback so you know what the robot is doing
        cv2.putText(img, f"CALIBRATING BACKGROUND... {int(time_left)}s left", 
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
        cv2.putText(img, "DO NOT PLACE OBJECT YET", 
                    (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        return img, None, None

    elif state == "TRACKING":
        # learningRate=0.0 FREEZES the background model. 
        # Anything new entering the frame (our unknown object) is instantly detected.
        mask = backSub.apply(resize_img, learningRate=0.0)
        
        # Clean up camera noise (dust, slight lighting changes)
        morphologyEx_img = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_5, iterations=1)
        
        # Find moving contours
        _tuple = cv2.findContours(morphologyEx_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = _tuple[1] if len(_tuple) == 3 else _tuple[0] # Fallback for different OpenCV versions
        
        if len(contours) > 0:
            # Assume the LARGEST moving object is our target
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # Filter out tiny noise (w >= 8, h >= 8 on the small image)
            if w >= 8 and h >= 8:
                # Multiply by 4 to map back to the original 640x480 resolution
                x, y, w, h = x * 4, y * 4, w * 4, h * 4
                
                # Calculate our Steering and Distance metrics
                x_center = x + (w // 2)
                y_bottom = y + h
                
                # Draw the bounding box and the tracking point
                cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.circle(img, (x_center, y_bottom), 8, (255, 0, 0), -1)
                
                cv2.putText(img, f"TARGET FOUND! X:{x_center} Y:{y_bottom}", 
                            (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                
                return img, x_center, y_bottom
        
        cv2.putText(img, "SEARCHING FOR TARGET...", 
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        return img, None, None

# --- Main Camera Loop ---
try:
    with Picamera2() as camera:
        print("Initializing Camera...")
        camera.preview_configuration.main.size = (640, 480)
        camera.preview_configuration.main.format = "RGB888"
        camera.preview_configuration.align()
        camera.configure("preview")
        camera.start()
        
        # Challenge rules say: "Your robot has at most 1 minute to capture and process"
        # We will use 50 seconds to be safe and give you 10 seconds to put the object down.
        CALIBRATION_TIME = 50 
        start_time = time.time()
        
        print("Camera running. Starting 50-second background calibration...")
        print("Check 'current_view.jpg' in VS Code to see what the robot sees.")
        
        while True:
            # 1. Grab frame
            img = camera.capture_array()
            
            # 2. Check the clock
            elapsed_time = time.time() - start_time
            time_left = CALIBRATION_TIME - elapsed_time
            
            if time_left > 0:
                state = "CALIBRATING"
            else:
                state = "TRACKING"
                
            # 3. Process the frame
            img, x_center, y_bottom = detect_unknown_object(img, state, time_left)
            
            # 4. Mock Motor Control (Just printing for now)
            if state == "TRACKING" and x_center is not None:
                # This is where we will eventually plug in `fc.forward()` etc.
                print(f"[MOTOR COMMAND] Steer towards X: {x_center}, Keep distance based on Y: {y_bottom}")
            
            # 5. Save the output image quietly so you can view it over SSH
            # We overwrite the same file every frame to save disk space
            cv2.imwrite("current_view.jpg", cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
            
            # Tiny sleep to prevent maxing out the Pi's CPU while saving images
            time.sleep(0.05) 

except KeyboardInterrupt:
    print("\nProgram stopped by user (Ctrl+C).")
finally:
    print('Quitting... Cleaning up camera.')
    # camera.close() is handled by the 'with' statement automatically