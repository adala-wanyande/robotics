#!/usr/bin/env python3

import cv2
import numpy as np
import time
from picamera2 import Picamera2
import picar_4wd as fc  # SunFounder motor library

print("Starting Autonomous Visual Follower (SSH Mode)...")

# ==========================================
# 1. VISION SYSTEM SETUP
# ==========================================
# Background Subtractor for finding the Unknown Object
# history=500, varThreshold=50, detectShadows=False
backSub = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50, detectShadows=False)
kernel_5 = np.ones((5,5), np.uint8)

def detect_unknown_object(img, state, time_left):
    """
    Finds the moving object. 
    During CALIBRATING, it learns the empty room.
    During TRACKING, it locks onto the new unknown object.
    """
    # Downscale for speed (160x120)
    resize_img = cv2.resize(img, (160, 120), interpolation=cv2.INTER_LINEAR)
    
    if state == "CALIBRATING":
        # learningRate=0.05: Learn the background (room, lighting, fixed obstacles)
        mask = backSub.apply(resize_img, learningRate=0.05)
        
        cv2.putText(img, f"CALIBRATING BACKGROUND... {int(time_left)}s", 
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
        cv2.putText(img, "DO NOT PLACE OBJECT YET", 
                    (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        return img, None, None

    elif state == "TRACKING":
        # learningRate=0.0: Freeze background. Track the new object!
        mask = backSub.apply(resize_img, learningRate=0.0)
        
        # Clean up camera noise
        morphologyEx_img = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_5, iterations=1)
        
        # Find contours
        _tuple = cv2.findContours(morphologyEx_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = _tuple[1] if len(_tuple) == 3 else _tuple[0]
        
        if len(contours) > 0:
            # Assume the LARGEST moving blob is our target
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # Ignore tiny noise artifacts
            if w >= 8 and h >= 8:
                # Map coordinates back to 640x480 resolution
                x, y, w, h = x * 4, y * 4, w * 4, h * 4
                
                # --- THE CRITICAL METRICS ---
                x_center = x + (w // 2)  # For Steering
                y_bottom = y + h         # For Distance
                
                # Draw visual feedback
                cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.circle(img, (x_center, y_bottom), 8, (255, 0, 0), -1)
                
                return img, x_center, y_bottom
                
        cv2.putText(img, "SEARCHING FOR TARGET...", 
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        return img, None, None

# ==========================================
# 2. MAIN CONTROL LOOP
# ==========================================
try:
    with Picamera2() as camera:
        print("Initializing Camera...")
        camera.preview_configuration.main.size = (640, 480)
        camera.preview_configuration.main.format = "RGB888"
        camera.preview_configuration.align()
        camera.configure("preview")
        camera.start()
        
        # Settings
        CALIBRATION_TIME = 50 # 50 seconds to calibrate, leaving 10s to place object
        start_time = time.time()
        
        # Following/Servoing Constants
        CENTER_X = 320
        TARGET_Y = 350    # The Y-pixel representing "Constant Distance"
        X_DEADZONE = 60   # Tolerance for steering
        Y_DEADZONE = 40   # Tolerance for distance
        BASE_SPEED = 30   # Power sent to motors
        
        print("Camera running. Starting calibration phase.")
        print("Check 'current_view.jpg' in VS Code to see what the robot sees.")
        
        while True:
            img = camera.capture_array()
            
            # Check timers
            elapsed_time = time.time() - start_time
            time_left = CALIBRATION_TIME - elapsed_time
            
            if time_left > 0:
                state = "CALIBRATING"
            else:
                state = "TRACKING"
                
            # Process Vision
            img, x_center, y_bottom = detect_unknown_object(img, state, time_left)
            
            # ==========================================
            # 3. MOTOR DRIVING LOGIC (VISUAL SERVOING)
            # ==========================================
            if state == "TRACKING":
                if x_center is not None and y_bottom is not None:
                    
                    # PRIORITY 1: STEERING (Center the object on the X axis)
                    if x_center < (CENTER_X - X_DEADZONE):
                        fc.turn_left(BASE_SPEED)
                        cv2.putText(img, "MOTOR: TURN LEFT", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 255), 2)
                        
                    elif x_center > (CENTER_X + X_DEADZONE):
                        fc.turn_right(BASE_SPEED)
                        cv2.putText(img, "MOTOR: TURN RIGHT", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 255), 2)
                        
                    else:
                        # PRIORITY 2: DISTANCE (Target is centered, now fix the Y axis distance)
                        if y_bottom < (TARGET_Y - Y_DEADZONE):
                            fc.forward(BASE_SPEED) # Too high up screen -> Too far away -> Drive Forward
                            cv2.putText(img, "MOTOR: FORWARD", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 255), 2)
                            
                        elif y_bottom > (TARGET_Y + Y_DEADZONE):
                            fc.backward(BASE_SPEED) # Too low down screen -> Too close -> Drive Backward
                            cv2.putText(img, "MOTOR: BACKWARD", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 255), 2)
                            
                        else:
                            fc.stop() # Centered AND perfect distance
                            cv2.putText(img, "MOTOR: STOPPED (PERFECT DISTANCE)", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                else:
                    # Object lost or missing
                    fc.stop()
            else:
                # Still calibrating, don't move
                fc.stop()

            # Save frame for remote viewing (Convert RGB to BGR for accurate colors in OpenCV)
            img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            cv2.imwrite("current_view.jpg", img_bgr)
            
            # Small delay to prevent CPU overheating and allow image saving
            time.sleep(0.05)

except KeyboardInterrupt:
    print("\nProgram stopped by user.")

finally:
    # CRITICAL SAFETY FEATURE: 
    # Ensure motors stop if the script crashes or is exited via Ctrl+C
    print("Stopping motors and cleaning up...")
    fc.stop()