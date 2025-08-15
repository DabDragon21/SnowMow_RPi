import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
import time
import os
import threading
from joystick_PS2_test import *
from flask import Flask, jsonify, render_template, request
import math
import json

#BROKER = "10.83.0.146"
TOPIC = "heading"
latest_heading = None
x1 = 0.0
y1 = 0.0
positions = []
max_corner = (0,0)
max_distance_value = 0.0

app = Flask(__name__)

calibration_mode = False
direction_start_time = None
current_direction = None
direction_totals = {"up": 0.0, "down": 0.0, "left": 0.0, "right": 0.0}
net_forward = 0.0 # feet?
net_rotation = 0.0 #degrees

SAVE_FILE = "calibration.json"

def set_calibration(enabled: bool):
    global calibration_mode, current_direction, direction_start_time, direction_totals, net_forward
    if calibration_mode and not enabled: 
        if current_direction in direction_totals and direction_start_time is not None:
            elapsed = time.time() - direction_start_time
            direction_totals[current_direction] += elapsed
            print(f"Calibration OFF: held {current_direction} for {elapsed:.2f}s")
            print(f"total {direction_totals[current_direction]:.2f}s")
        net_forward = direction_totals["up"]*2.62 - direction_totals["down"]*2.62
        print(f"Net forward distance: {net_forward:.2f} feet")
        current_direction = None
        direction_start_time = None
    calibration_mode = enabled
    print(f"Calibration mode set to {calibration_mode}")

def save_calibration():
    data = {
        "max_corner": max_corner,
        "max_distance_value": max_distance_value
    }
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f)
    print(f"Calibration saved: {data}")

def on_connect(client, userdata, flags, rc):
    print("MQTT connected with code", rc)
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    global latest_heading
    try:
        heading_rad = float(msg.payload.decode())
        latest_heading = heading_rad
        #print(f"Heading received: {heading_rad:.6f} rad")
    except ValueError:
        print("Invalid heading data:", msg.payload)

def store_position(x, y):
    positions.append((x, y))

def max_distance():
    if not positions:
        return 0.0, (0, 0)  # no positions yet
    max_d = 0
    max_point = (0, 0)
    for x, y in positions:
        d = math.hypot(x, y)  # sqrt(x^2 + y^2)
        if d > max_d:
            max_d = d
            max_point = (x, y)
    return max_d, max_point

@app.route('/toggle_calibration', methods=['POST'])
def toggle_calibration():
    global calibration_mode
    calibration_mode = not calibration_mode
    print(f"Calibration mode {calibration_mode}")
    return jsonify(calibration_mode=calibration_mode)

@app.route('/totals')
def get_totals():
    return jsonify(direction_totals)

@app.route('/dimensions')
def get_dimensions():
    return jsonify({"net_forward": net_forward})

@app.route('/position')
def get_position():
    return jsonify({"x": x1, "y": y1})

@app.route('/max_distance')
def get_max_distance():
    global max_distance_value, max_corner
    if max_corner is None:
        max_corner = [0.0, 0.0]
    return jsonify({
        "max_distance": round(max_distance_value, 2),
        "corner": [round(max_corner[0], 2), round(max_corner[1], 2)]
    })

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/direction')
def get_direction():
    return jsonify({
        'system': check_button(),
        'direction':  direction(),
    })

#broker_ip = "10.83.0.146"
broker_ip = "10.0.0.31"

def sensor_pub():
    global current_direction, direction_start_time, direction_totals, net_forward, latest_heading, x1, y1, positions, max_distance_value, max_corner, SAVE_FILE
    last_system = ''
    #last_direction = ''
    while True:
        system = check_button()
        #print("Publishing the switch status...")
        if system != "ON":
            current_direction = None
            direction_start_time = None
            direction_totals = {k: 0.0 for k in direction_totals}
            time.sleep(0.3)
            continue
        if system != last_system:
            publish.single("system/right", system, hostname=broker_ip)
            publish.single("system/left", system, hostname=broker_ip)
            print(f"system: {system}")
            last_system = system
        direc = direction()
        #if direc != last_direction:
        #print("Publishing the joystick direction...")
        publish.single("joystick/right", direc, hostname=broker_ip)
        publish.single("joystick/left", direc, hostname=broker_ip)
        #print("Published: ", direc)
        #last_direction = direc
        time.sleep(0.3)
        # --- Calibration timing logic ---
        if calibration_mode:
            if direc != current_direction:
                if current_direction in direction_totals and direction_start_time is not None:
                    elapsed = time.time() - direction_start_time
                    direction_totals[current_direction] += elapsed
                    print(f"Stopped {current_direction}, held for {elapsed:.2f}s "
                          f"(total {direction_totals[current_direction]:.2f}s)")
                    net_forward = direction_totals["up"]*2.62 - direction_totals["down"]*2.62
                    print(f"Net forward distance: {net_forward:.2f} feet")
                    #publish.single('net-forward', net_forward, hostname=broker_ip)
                if direc in direction_totals:
                    direction_start_time = time.time()
                else:
                    direction_start_time = None
                current_direction = direc
                publish.single('net-forward', net_forward, hostname=broker_ip)
            if latest_heading is not None:
                x1 = net_forward * math.cos(latest_heading)
                y1 = net_forward * math.sin(latest_heading)
                positions.append((x1, y1))
                print(f"Position: ({x1:.2f}, {y1:.2f})")
        else:
            max_distance_value, max_corner = max_distance()
            print(f"Max distance: {max_distance_value:.2f} at {max_corner}")
            current_direction = None
            direction_start_time = None
            #direction_totals = {k: 0.0 for k in direction_totals}
        save_calibration()

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(broker_ip, 1883, 60)

mqtt_thread = threading.Thread(target = mqtt_client.loop_forever, daemon=True)
mqtt_thread.start()

if __name__ == "__main__":
    joystick_thread = threading.Thread(target = sensor_pub, daemon=True)
    joystick_thread.start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
