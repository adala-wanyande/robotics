import picar_4wd as fc
import sys
import tty
import termios
import asyncio
import time

power_val = 20
key = 'status'
movement_history = []  # List to store movements along with their durations
duration_history = []
last_key_time = time.time()  # Initialize with the current time
print("If you want to quit. Please press q")

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

async def sleep_for_duration(duration):
    await asyncio.sleep(duration)

def return_to_home():
    global movement_history
    global duration_history
    #print(movement_history)
    duration_history.pop(0)
    
    fc.turn_right(power_val)
    asyncio.run(sleep_for_duration(1.6)) 
    print("Lenght of movement_history: ", movement_history)
    print("Lenght of duration_history: ", duration_history)
    
    for i in reversed(range(len(movement_history))):
        command = movement_history[i]
        duration = duration_history[i]
        start = time.time()
        if command == 'w':
            print("Forward: ", duration)
            fc.forward(power_val)
        elif command == 's':
            print("Backward")
            fc.backward(power_val)
        elif command == 'a':
            print("Right")
            duration = duration - 0.085
            fc.turn_right(power_val)
        elif command == 'd':
            print("Left")
            duration = duration + 0.085
            fc.turn_left(power_val)
        asyncio.run(sleep_for_duration(duration)) # Use the stored duration for each move
        end = time.time()-start
        print("END: ", end)
    movement_history.clear()
    fc.stop()
    


def Keyborad_control():
    global last_key_time
    
    while True:
        global power_val
        key=readkey()
        
        current_time = time.time()
        duration = current_time - last_key_time  # Calculate duration since last key press
        last_key_time = current_time  # Update last_key_time for the next press
        
        if key in ['w', 's', 'a', 'd']:  # Log the movement with its duration
            movement_history.append(key)
            duration_history.append(duration)
        
        print("DURATION: ", duration)
        if key=='w':
            fc.forward(power_val)
            print("F: ", duration)
        elif key=='a':
            fc.turn_left(power_val)
        elif key=='s':
            fc.backward(power_val)
        elif key=='d':
            fc.turn_right(power_val)
        elif key=='q':
            duration_history.append(duration)
            print("Returning to home position")
            return_to_home()
            break
        else:
            fc.stop() 
            break 
            
        
             
if __name__ == '__main__':
    Keyborad_control()
