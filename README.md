# CrowdAnalysisSetupApp
Setup Application for CrowdAnalysis Project

# Overview
The Crowd Analysis Setup App is designed to facilitate the setup of Nvidia Xavier NX device using either a USB or WiFi wireless connection. This app ensures that the device is properly configured and connected, making it easy to run and manage the main crowd analysis server on the Nvidia Xavier NX hardware.

# Features
- Nvidia Device Setup: The app allows users to set up Nvidia devices via USB or WiFi.
- USB Connection Check: The app checks if the device is connected via USB using Nvidia's Vendor ID (VID).
- WiFi Network Connection: If the device is not already set up, users can connect to a wireless network, and the app will automatically display the IP address of the Crowd Analysis server.
- Crowd Management System: A button is provided to start the crowd management system as a service on the device if it is connected.
- Service Routine: A dedicated service routine is added for running the crowd analysis server.
- Stop Button: A stop button is included to stop the service running in the background.

# Service Configuration
To ensure the crowd analysis server runs smoothly, a systemd service has been created. Below is the configuration for crowdanalysis.service.

-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
[Unit]
Description=Crowd Analysis Flask Server
After=network.target

[Service]
User=dit
WorkingDirectory=/home/dit/kirtanSoni_master_thesis/CrowdAnalysis
ExecStart=/home/dit/kirtanSoni_master_thesis/CrowdAnalysis/.venv/bin/python /home/dit/kirtanSoni_master_thesis/CrowdAnalysis/main.py
Restart=always
Environment="PATH=/home/dit/kirtanSoni_master_thesis/CrowdAnalysis/.venv/bin"

[Install]
WantedBy=multi-user.target
-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

# How to run and use the software:
If you want to setup the code base and run it over an IDE like VScode, follow the below steps given in "How to setup the python enviornmnet", but if you want to directly start using the software then follow the steps given in "How to open the software from binary"
IMPORTANT: This software only works with Linux OS

## How to setup the python enviornmnet:
- If Linux:
    - python3 -m venv .venv
    - source .venv/bin/activate
    - pip install --upgrade pip setuptools
    - pip install -r requirements.txt
    - Run the software in IDE:
        - python3 ./app.py

## How to open the software from binary:
- If Linux:
    - Double click the ./dist/CrowdAnalysis
    - OR
    - Open a Terminal inside the CrowdAnalysisSetupApp root directory
    - Enter the following cmd:
        - ./dist/CrowdAnalysis
    - The software will open

## How to use this software:
- After opening the software, it will look for the device via USB or WiFi
- If you are setting up the device first time connect the device to the laptop with USB cable and the software will automatically detect the device.
- After detection, you can enter the desired WiFi credentials and click "Connect to WiFi" button
- If the device is connected to the WiFi it will show "successfully connected", if not make sure the credentials are right and try again.
- Once connected to the WiFi, you can disconnect the USB and the software will automatically connect to it wirelessly via WiFi.
- Now, you can start the serivce by pressing "Start Crowd Analysis Server" button and wait for confiramtion message.
- Once confirmed, use the IP address displayed, copy it and enter on any browser to connect to the Main GUI

