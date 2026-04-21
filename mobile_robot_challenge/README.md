# Remote Connection & Testing Guide

## 1. Connect to the Robot (Terminal)
Ensure Lucas has turned the robot on and it is connected to his Wi-Fi. 

Open your Mac's **Terminal** and run your pre-configured secure SSH tunnel:
```bash
ssh robotpi
```
*Note: Do not close this terminal window! This is the active secure tunnel to the robot. If you close it, the robot loses connection.*

## 2. Connect Visual Studio Code (The "No-Lag" VNC Alternative)
We are skipping RealVNC today so you don't experience video lag. Instead, we will view the robot's files and images directly through VS Code.

1. Open **Visual Studio Code** on your Mac.
2. Click the **Remote Explorer** icon on the far left sidebar (it looks like two computer monitors).
3. In the dropdown at the top, select **SSH Targets**.
4. You should see `robotpi` in the list. Click the **folder icon with a plus sign** next to it to connect.
5. VS Code will open a new window. Click **Open Folder** and select the `/home/pi` folder (or wherever you saved your python scripts).

## 3. Transferring Your Scripts (If you haven't yet)
If your 3 scripts (`unknown_object_tracker.py`, `visual_follower.py`, `obstacle_avoidance.py`) are only on your Mac right now:
1. Simply drag and drop them from your Mac into the VS Code file explorer sidebar. 
2. They will securely upload to the robot in seconds.

## 4. How to Run the Tests
Go back to your Mac's Terminal window (where you ran `ssh robotpi`). 
Make sure your scripts have execution permissions. Run this once:
```bash
chmod +x *.py
```

**To run a test, type:**
```bash
python3 name_of_script.py
```
*(Example: `python3 unknown_object_tracker.py`)*

## 5. How to View the Robot's Camera Live
1. Start the python script in your terminal.
2. Wait for the terminal to say: *"Check 'current_view.jpg' in VS Code"*
3. Go to **VS Code**.
4. Click on the `current_view.jpg` file in the sidebar.
5. To see the next frame, just click off the image (to another file) and click back onto `current_view.jpg` to refresh it. 

## 6. How to Stop the Robot 🚨
If the robot is about to crash or the code freezes:
1. Go to your Terminal window.
2. Press **`Ctrl + C`**.
3. This forces the python script to quit. The scripts are programmed to instantly trigger `fc.stop()` so the wheels shut down safely.

***

### Quick Checklist to read to Lucas before you hit run:
- [ ] "Is the robot turned on?"
- [ ] "Is the robot propped up on a block so the wheels are in the air?"
- [ ] "Are you standing out of the camera's view so it doesn't memorize you as a wall?"
- [ ] "Do you have the target object ready in your hand?"