#!/bin/bash

# Navigate to the project directory
cd /mnt/c/Users/sethv/Desktop/project || exit

# Start the Python web app in the background
python3 WebApp.py &

# Wait a few seconds for the server to start (adjust if needed)
sleep 3

# Open the web page in the default Windows browser
cmd.exe /c start http://127.0.0.1:5000

