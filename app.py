from flask import Flask, render_template, jsonify, request
import subprocess
import paramiko
import platform
import threading
import webview
import os
import json
import time
import signal

app = Flask(__name__)

# Define the Nvidia Vendor ID
NVIDIA_VID = '0955'

browser_instance = None
flask_thread = None

ssh_host = '192.168.55.1'
ssh_user = 'dit'
ssh_password = 'dit'
ip_file_path = 'ip.json'
flask_port = 5100


def check_usb_connection():
    try:
        if platform.system() == "Windows":
            result = subprocess.run(['powershell', '-Command', 'Get-WmiObject Win32_USBControllerDevice | Format-Table -Property Dependent'],
                                    stdout=subprocess.PIPE)
            output = result.stdout.decode()
            return NVIDIA_VID in output
        else:
            result = subprocess.run(['lsusb'], stdout=subprocess.PIPE)
            output = result.stdout.decode()
            return NVIDIA_VID in output
    except Exception as e:
        return False


def get_ip_address():
    try:
        with open(ip_file_path, 'r') as file:
            cur_ip = json.load(file)

        # Create an SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if not check_usb_connection():
            ssh.connect(cur_ip['ip_addr'], username=ssh_user, password=ssh_password, timeout=5)
        else:
            ssh.connect(ssh_host, username=ssh_user, password=ssh_password, timeout=5)

        # Execute the command to get IP address of wlan0
        command = "ip -4 addr show wlan0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}'"
        stdin, stdout, stderr = ssh.exec_command(command)
        ip_address = stdout.read().decode().strip()
        ssh.close()

        # Update the IP address in the file if it has changed
        if cur_ip['ip_addr'] != ip_address:
            with open(ip_file_path, 'w') as file:
                new_ip = {'ip_addr': ip_address}
                json.dump(new_ip, file)

        return ip_address if ip_address else "Unknown"
    except Exception as e:
        return "Unknown"


def is_wifi_connected(usb_status):
    try:
        # Read the current IP address from the file
        with open(ip_file_path, 'r') as file:
            cur_ip = json.load(file)

        # Create an SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if not usb_status:
            ssh.connect(cur_ip['ip_addr'], username=ssh_user, password=ssh_password, timeout=5)
        else:
            ssh.connect(ssh_host, username=ssh_user, password=ssh_password, timeout=5)

        time.sleep(2)

        # Execute the command to check WiFi connection
        command = "nmcli -t -f DEVICE,TYPE,STATE,CONNECTION device"
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode().strip()
        ssh.close()

        for line in output.split('\n'):
            parts = line.split(':')
            if len(parts) >= 4 and parts[1] == 'wifi' and parts[2] == 'connected':
                return True, parts[3]  # return connection name
        return False, ''
    except Exception as e:
        return False, ''


def execute_ssh_command(command):
    try:
        # Read the current IP address from the file
        with open(ip_file_path, 'r') as file:
            cur_ip = json.load(file)

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if not check_usb_connection():
            ssh.connect(cur_ip['ip_addr'], username=ssh_user, password=ssh_password, timeout=5)
        else:
            ssh.connect(ssh_host, username=ssh_user, password=ssh_password, timeout=5)
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        ssh.close()
        return output, error
    except Exception as e:
        return "", str(e)


def check_and_kill_port(port):
    try:
        if platform.system() == "Windows":
            result = subprocess.run(['powershell', '-Command', f'Get-Process -Id (Get-NetTCPConnection -LocalPort {port}).OwningProcess'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = result.stdout.decode().strip()
            if output:
                lines = output.split('\n')
                for line in lines[3:]:
                    if line:
                        parts = line.split()
                        pid = int(parts[-1])
                        subprocess.run(['taskkill', '/PID', str(pid), '/F'])
            print(f"Port {port} is now free.")
            time.sleep(5)
        else:
            result = subprocess.run(['lsof', '-i', f':{port}'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = result.stdout.decode().strip()
            if output:
                lines = output.split('\n')
                for line in lines[1:]:
                    if line:
                        parts = line.split()
                        pid = int(parts[1])
                        os.kill(pid, signal.SIGKILL)
                print(f"Port {port} is now free.")
                time.sleep(5)
            else:
                print(f"Port {port} is not occupied.")
    except Exception as e:
        print(f"Error checking/killing port {port}: {e}")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/get_ip', methods=['POST'])
def get_ip():
    ip_address = get_ip_address()
    return jsonify({'ip_address': ip_address})


@app.route('/connect_wifi', methods=['POST'])
def connect_wifi():
    data = request.json
    ssid = data.get('ssid')
    password = data.get('password')

    if ssid and password:
        try:
            if not check_usb_connection():
                return jsonify({'message': f"First connect the device to the host with USB."}), 500

            # Create an SSH client
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ssh_host, username=ssh_user, password=ssh_password, timeout=5)

            # Check if there is an active connection on wlan0
            wifi_status, _ = is_wifi_connected(usb_status=True)

            if wifi_status:
                # Disconnect the active connection on wlan0
                disconnect_command = f"echo {ssh_password} | sudo -S nmcli d disconnect wlan0"
                stdin, stdout, stderr = ssh.exec_command(disconnect_command)
                disconnect_output = stdout.read().decode().strip()
                disconnect_error = stderr.read().decode().strip()

                if disconnect_error:
                    return jsonify({'message': f"Failed to disconnect from current WiFi: {disconnect_error}"}), 500

            # Construct the nmcli command to connect to the new WiFi network with sudo
            connect_command = f"echo {ssh_password} | sudo -S nmcli d wifi connect '{ssid}' password '{password}'"
            stdin, stdout, stderr = ssh.exec_command(connect_command)

            # Read the output and error streams
            connect_output = stdout.read().decode().strip()
            connect_error = stderr.read().decode().strip()

            ssh.close()

            if connect_error:
                return jsonify({'message': f"Failed to connect to WiFi: {connect_error}"}), 500
            else:
                return jsonify({'message': 'Connected to WiFi successfully!', 'output': connect_output})

        except Exception as e:
            return jsonify({'message': f"Failed to connect to WiFi: {str(e)}"}), 500
    else:
        return jsonify({'message': 'Please enter both SSID and Password'}), 400


@app.route('/check_status')
def check_status():
    usb_status = check_usb_connection()
    wifi_status, wifi_name = is_wifi_connected(usb_status)
    return jsonify({'usb_connected': usb_status, 'wifi_connected': wifi_status, 'wifi_name': wifi_name})


@app.route('/start_server', methods=['POST'])
def start_server():
    start_service_command = "sudo systemctl start crowdanalysis.service"
    output, error = execute_ssh_command(start_service_command)

    # Add a delay to allow the server to start
    time.sleep(5)

    # Check if the server is running
    check_server_command = "systemctl is-active crowdanalysis.service"
    check_output, check_error = execute_ssh_command(check_server_command)

    if 'active' in check_output.strip():
        return jsonify({'message': f'Crowd Analysis Server has started, please use the above IP to access the GUI.', 'output': output})
    else:
        return jsonify({'message': "Failed to start server: The server service is not active.", 'output': check_error}), 500


@app.route('/stop_server', methods=['POST'])
def stop_server():
    stop_service_command = "sudo systemctl stop crowdanalysis.service"
    output, error = execute_ssh_command(stop_service_command)
    if error:
        return jsonify({'message': f"Failed to stop Crowd Analysis Server: {error}"}), 500
    else:
        return jsonify({'message': 'Crowd Analysis Server stopped successfully', 'output': output})


@app.route('/server_status', methods=['GET'])
def server_status():
    check_server_command = "systemctl is-active crowdanalysis.service"
    output, error = execute_ssh_command(check_server_command)
    if 'active' in output.strip() and not 'inactive' in output.strip():
        return jsonify({'status': 'running'})
    else:
        return jsonify({'status': 'stopped'})


@app.route('/shutdown', methods=['POST'])
def shutdown():
    global browser_instance
    if browser_instance:
        browser_instance.destroy()
    # Terminate the Flask server and the application
    threading.Timer(1, lambda: os._exit(0)).start()
    return jsonify({'message': 'Shutting Down...'})


def start_flask():
    app.run(debug=False, use_reloader=False, port=flask_port)


if __name__ == '__main__':
    # Making ip.json file to store device ip, Check if the file exists, if not create it with default data
    try:
        with open(ip_file_path, 'r') as file:
            data = json.load(file)
    except:
        with open(ip_file_path, 'w') as file:
            init_data = {'ip_addr': ssh_host}
            json.dump(init_data, file)

    # Check and kill the process occupying the port before starting Flask
    check_and_kill_port(flask_port)

    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=start_flask)
    flask_thread.start()

    time.sleep(2)

    # Start the webview after Flask has started
    browser_instance = webview.create_window("Crowd Analysis Sytem Setup",
                                             "http://127.0.0.1:5100", fullscreen=True)
    webview.start()
