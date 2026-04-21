#!/usr/bin/env python3

import cv2
import numpy as np
import time
from picamera2 import Picamera2
import picar_4wd as fc

print("Starting Obstacle Avoidance & Follower (SSH Mode)...")

# ==========================================
# 1. VISION SYSTEM & MEMORY SETUP
# ==========================================
backSub = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50, detectShadows=False)
kernel_5 = np.ones((5,5), np.uint8)

# Memory to store where the big obstacles are
obstacles_memory = [] 

def scan_for_static_obstacles(img):
    """
    Scans the room for the 'two much bigger objects' using Edge Detection.
    Returns a list of bounding boxes [x, y, w, h] for the obstacles.
    """
    # Downscale for processing
    small_img = cv2.resize(img, (160, 120))
    gray = cv2.cvtColor(small_img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Find edges of objects in the room
    edges = cv2.Canny(blurred, 50, 150)
    dilated = cv2.dilate(edges, kernel_5, iterations=1)
    
    # Find contours
    _tuple = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = _tuple[1] if len(_tuple) == 3 else _tuple[0]
    
    found_obstacles = []
    
    # Sort contours by size (largest first) to find the "much bigger objects"
    if len(contours) > 0:
        sorted_contours = sorted(contours, key=cv2.contourArea, reverse=True)
        
        # Grab the top 2 largest stationary objects (assuming they are the obstacles)
        for c in sorted_contours[:2]: 
            if cv2.contourArea(c) > 200: # Minimum size threshold
                x, y, w, h = cv2.boundingRect(c)
                # Map back to 640x480 resolution
                found_obstacles.append([x*4, y*4, w*4, h*4])
                
    return found_obstacles

def detect_moving_target(img, learning_rate):
    """ Finds the moving unknown object. """
    resize_img = cv2.resize(img, (160, 120))
    mask = backSub.apply(resize_img, learningRate=learning_rate)
    morph = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_5, iterations=1)
    
    _tuple = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = _tuple[1] if len(_tuple) == 3 else _tuple[0]
    
    if len(contours) > 0:
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        if w >= 8 and h >= 8:
            return (x*4, y*4, w*4, h*4) # Return mapped bounding box
    return None

# ==========================================
# 2. THE OBSTACLE AVOIDANCE MATH
# ==========================================
def calculate_avoidance_steering(target_x, obstacles):
    """
    If the target_x is too close to an obstacle, push the steering X away.
    """
    steer_x = target_x
    SAFE_MARGIN = 150  # Pixels of clearance needed to not hit the box
    
    for obs in obstacles:
        obs_x, obs_y, obs_w, obs_h = obs
        obs_center = obs_x + (obs_w // 2)
        
        # Calculate how close our target path is to the obstacle's center
        distance_to_obstacle = target_x - obs_center
        
        # If the target is physically behind or dangerously close to the obstacle's X path
        if abs(distance_to_obstacle) < SAFE_MARGIN:
            
            # REPULSION LOGIC:
            if distance_to_obstacle > 0:
                # Target is slightly to the RIGHT of the obstacle.
                # Push our steering hard RIGHT to go around it.
                steer_x = target_x + (SAFE_MARGIN - distance_to_obstacle)
            else:
                # Target is slightly to the LEFT of the obstacle.
                # Push our steering hard LEFT to go around it.
                steer_x = target_x - (SAFE_MARGIN + distance_to_obstacle)
                
    # Clamp the value so it doesn't go off screen
    steer_x = max(0, min(640, steer_x))
    return int(steer_x)


# ==========================================
# 3. MAIN LOOP
# ==========================================
try:
    with Picamera2() as camera:
        camera.preview_configuration.main.size = (640, 480)
        camera.preview_configuration.main.format = "RGB888"
        camera.preview_configuration.align()
        camera.configure("preview")
        camera.start()
        
        start_time = time.time()
        
        CENTER_X = 320
        TARGET_Y = 350
        BASE_SPEED = 30
        
        while True:
            img = camera.capture_array()
            elapsed_time = time.time() - start_time
            
            # --- PHASE 1: BACKGROUND TRAINING (0 to 45s) ---
            if elapsed_time < 45:
                detect_moving_target(img, learning_rate=0.05)
                cv2.putText(img, f"TRAINING BACKGROUND... {int(45 - elapsed_time)}s", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)
            
            # --- PHASE 2: MEMORIZE OBSTACLES (45s to 50s) ---
            elif elapsed_time >= 45 and elapsed_time < 50:
                detect_moving_target(img, learning_rate=0.0) # Stop learning
                obstacles_memory = scan_for_static_obstacles(img)
                cv2.putText(img, f"MEMORIZING OBSTACLES... {int(50 - elapsed_time)}s", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                
            # --- PHASE 3: TRACK AND AVOID (50s+) ---
            else:
                # Draw the memorized obstacles in RED so we can see them
                for obs in obstacles_memory:
                    ox, oy, ow, oh = obs
                    cv2.rectangle(img, (ox, oy), (ox+ow, oy+oh), (0, 0, 255), 2)
                    cv2.putText(img, "DANGER ZONE", (ox, oy-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

                # Find the moving target
                target_box = detect_moving_target(img, learning_rate=0.0)
                
                if target_box is not None:
                    tx, ty, tw, th = target_box
                    target_x_center = tx + (tw // 2)
                    target_y_bottom = ty + th
                    
                    # Draw target in GREEN
                    cv2.rectangle(img, (tx, ty), (tx+tw, ty+th), (0, 255, 0), 2)
                    cv2.circle(img, (target_x_center, target_y_bottom), 5, (0, 255, 0), -1)
                    
                    # APPLY OBSTACLE AVOIDANCE
                    safe_steer_x = calculate_avoidance_steering(target_x_center, obstacles_memory)
                    
                    # Draw the new Safe Trajectory in YELLOW
                    cv2.circle(img, (safe_steer_x, target_y_bottom), 8, (0, 255, 255), -1)
                    cv2.line(img, (320, 480), (safe_steer_x, target_y_bottom), (0, 255, 255), 3)
                    
                    # ==========================================
                    # MOTOR CONTROL (Using safe_steer_x instead of target_x)
                    # ==========================================
                    if safe_steer_x < (CENTER_X - 60):
                        fc.turn_left(BASE_SPEED)
                        cv2.putText(img, "SWERVING LEFT", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                    elif safe_steer_x > (CENTER_X + 60):
                        fc.turn_right(BASE_SPEED)
                        cv2.putText(img, "SWERVING RIGHT", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                    else:
                        if target_y_bottom < (TARGET_Y - 40):
                            fc.forward(BASE_SPEED)
                        elif target_y_bottom > (TARGET_Y + 40):
                            fc.backward(BASE_SPEED)
                        else:
                            fc.stop()
                else:
                    fc.stop() # Target lost

            # Save frame for SSH viewing
            cv2.imwrite("current_view.jpg", cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
            time.sleep(0.05)

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    fc.stop()