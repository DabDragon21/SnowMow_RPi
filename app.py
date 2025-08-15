import os, json, time, threading, math
from flask import Flask, render_template, request, jsonify, abort
import paho.mqtt.client as mqtt
import paho.mqtt.publish as publish
from joystick_PS2_test import *  # Assuming your joystick code

# ---------------- CONFIG ----------------
ADMIN_PASSWORD = "demo123"   # Change to secure password
SAVE_FOLDER = "paths"
os.makedirs(SAVE_FOLDER, exist_ok=True)

SAVE_FILE = "calibration.json"
TOPIC = "heading"
broker_ip = "10.83.0.146"  # Update to your broker IP

app = Flask(__name__)

# ---------------- STATE ----------------
latest_heading = None
x1 = 0.0
y1 = 0.0
positions = []
calibration_mode = False
trace_mode = False
servo_mode = False
current_direction = None
direction_start_time = None
direction_totals = {"up":0.0,"down":0.0,"left":0.0,"right":0.0}
net_forward = 0.0
max_corner = (0,0)
max_distance_value = 0.0

# ---------------- HELPERS ----------------
def check_admin():
    password = request.form.get('password')
    if password != ADMIN_PASSWORD: abort(403)

def set_calibration(enabled: bool):
    global calibration_mode, current_direction, direction_start_time, direction_totals, net_forward
    if calibration_mode and not enabled: 
        if current_direction in direction_totals and direction_start_time is not None:
            elapsed = time.time() - direction_start_time
            direction_totals[current_direction] += elapsed
            print(f"Calibration OFF: held {current_direction} for {elapsed:.2f}s")
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

def store_position(x, y):
    positions.append((x, y))

def max_distance():
    if not positions:
        return 0.0, (0, 0)
    max_d = 0
    max_point = (0, 0)
    for x, y in positions:
        d = math.hypot(x, y)
        if d > max_d:
            max_d = d
            max_point = (x, y)
    return max_d, max_point

def save_path():
    filename = f"{SAVE_FOLDER}/path_{int(time.time())}.json"
    data = {"positions": positions}
    with open(filename, "w") as f: json.dump(data, f)
    return filename

def list_paths(): 
    return sorted(os.listdir(SAVE_FOLDER), reverse=True)

def rename_path(old_name,new_name):
    old_path = os.path.join(SAVE_FOLDER, old_name)
    new_path = os.path.join(SAVE_FOLDER, new_name)
    if os.path.exists(old_path): os.rename(old_path,new_path)
    return os.path.exists(new_path)

# ---------------- MQTT ----------------
def on_connect(client, userdata, flags, rc):
    print("MQTT connected with code", rc)
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    global latest_heading
    try: 
        latest_heading = float(msg.payload.decode())
    except ValueError:
        print("Invalid heading data:", msg.payload)

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(broker_ip, 1883, 60)
threading.Thread(target=mqtt_client.loop_forever, daemon=True).start()

# ---------------- SENSOR PUBLISH ----------------
def sensor_pub():
    global current_direction, direction_start_time, direction_totals, net_forward
    global latest_heading, x1, y1, positions, max_distance_value, max_corner
    last_system = ''
    while True:
        system = check_button()
        if system != "ON":
            current_direction = None
            direction_start_time = None
            direction_totals = {k: 0.0 for k in direction_totals}
            time.sleep(0.3)
            continue
        if system != last_system:
            publish.single("system/right", system, hostname=broker_ip)
            publish.single("system/left", system, hostname=broker_ip)
            last_system = system
        direc = direction()
        publish.single("joystick/right", direc, hostname=broker_ip)
        publish.single("joystick/left", direc, hostname=broker_ip)
        time.sleep(0.3)

        # --- Calibration timing logic ---
        if calibration_mode:
            if direc != current_direction:
                if current_direction in direction_totals and direction_start_time is not None:
                    elapsed = time.time() - direction_start_time
                    direction_totals[current_direction] += elapsed
                    net_forward = direction_totals["up"]*2.62 - direction_totals["down"]*2.62
                    publish.single('net-forward', net_forward, hostname=broker_ip)
                if direc in direction_totals:
                    direction_start_time = time.time()
                else:
                    direction_start_time = None
                current_direction = direc
            if latest_heading is not None:
                x1 = net_forward * math.cos(latest_heading)
                y1 = net_forward * math.sin(latest_heading)
                positions.append((x1, y1))
        else:
            max_distance_value, max_corner = max_distance()
            current_direction = None
            direction_start_time = None
        save_calibration()

# ---------------- ROUTES ----------------
@app.route('/')
def index(): return render_template("index.html")

@app.route('/toggle_calibration', methods=['POST'])
def toggle_calibration_route():
    #check_admin()
    global calibration_mode
    calibration_mode = not calibration_mode
    return jsonify(calibration_mode=calibration_mode)

@app.route('/toggle_trace', methods=['POST'])
def toggle_trace_route():
    #check_admin()
    global trace_mode
    trace_mode = not trace_mode
    publish.single("state", "trace", hostname=broker_ip)
    return jsonify(trace_mode=trace_mode)

@app.route('/toggle_servo', methods=['POST'])
def toggle_servo_route():
    #check_admin()
    global servo_mode
    servo_mode = not servo_mode
    publish.single("salt", "on", hostname=broker_ip)
    return jsonify(servo_mode=servo_mode)

@app.route('/totals')
def get_totals(): return jsonify(direction_totals)

@app.route('/dimensions')
def get_dimensions(): return jsonify({"net_forward": net_forward})

@app.route('/position')
def get_position(): return jsonify({"x": x1, "y": y1})

@app.route('/max_distance')
def get_max_distance():
    if max_corner is None:
        corner = [0.0, 0.0]
    else:
        corner = [round(max_corner[0],2), round(max_corner[1],2)]
    return jsonify({
        "max_distance": round(max_distance_value, 2),
        "corner": corner
    })

@app.route('/direction')
def get_direction():
    return jsonify({
        'system': check_button(),
        'direction':  direction(),
    })

@app.route('/save_path', methods=['POST'])
def save_current_path():
    check_admin()
    filename = save_path()
    return jsonify(filename=filename)

@app.route('/paths')
def get_paths_route(): return jsonify(list_paths())

@app.route('/rename_path', methods=['POST'])
def rename_existing_path():
    check_admin()
    old_name = request.form.get('old_name')
    new_name = request.form.get('new_name')
    success = rename_path(old_name,new_name)
    return jsonify(success=success)

# ---------------- MAIN ----------------
if __name__ == "__main__":
    threading.Thread(target=sensor_pub, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)), debug=True)
