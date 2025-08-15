import os, json, time, threading, math
from flask import Flask, render_template, request, jsonify, abort
import paho.mqtt.client as mqtt

# ---------------- CONFIG ----------------
ADMIN_PASSWORD = "demo123"   # Change to secure password
SAVE_FOLDER = "paths"
os.makedirs(SAVE_FOLDER, exist_ok=True)

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
current_direction = None
direction_start_time = None
direction_totals = {"up":0.0,"down":0.0,"left":0.0,"right":0.0}
net_forward = 0.0

# ---------------- MQTT ----------------
def on_connect(client, userdata, flags, rc):
    print("MQTT connected with code", rc)
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    global latest_heading
    try: latest_heading = float(msg.payload.decode())
    except: pass

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(broker_ip, 1883, 60)
threading.Thread(target=mqtt_client.loop_forever, daemon=True).start()

# ---------------- HELPERS ----------------
def save_path():
    filename = f"{SAVE_FOLDER}/path_{int(time.time())}.json"
    data = {"positions": positions}
    with open(filename, "w") as f: json.dump(data, f)
    return filename

def list_paths(): return sorted(os.listdir(SAVE_FOLDER), reverse=True)
def rename_path(old_name,new_name):
    old_path = os.path.join(SAVE_FOLDER, old_name)
    new_path = os.path.join(SAVE_FOLDER, new_name)
    if os.path.exists(old_path): os.rename(old_path,new_path); return True
    return False

# ---------------- ROUTES ----------------
@app.route('/')
def index(): return render_template("index.html")

def check_admin():
    password = request.form.get('password')
    if password != ADMIN_PASSWORD: abort(403)

@app.route('/toggle_calibration', methods=['POST'])
def toggle_calibration():
    check_admin()
    global calibration_mode
    calibration_mode = not calibration_mode
    return jsonify(calibration_mode=calibration_mode)

@app.route('/toggle_trace', methods=['POST'])
def toggle_trace():
    check_admin()
    global trace_mode
    trace_mode = not trace_mode
    return jsonify(trace_mode=trace_mode)

@app.route('/save_path', methods=['POST'])
def save_current_path():
    check_admin()
    filename = save_path()
    return jsonify(filename=filename)

@app.route('/paths')
def get_paths(): return jsonify(list_paths())

@app.route('/rename_path', methods=['POST'])
def rename_existing_path():
    check_admin()
    old_name = request.form.get('old_name')
    new_name = request.form.get('new_name')
    success = rename_path(old_name,new_name)
    return jsonify(success=success)

@app.route('/position')
def get_position(): return jsonify({"x":x1,"y":y1})

@app.route('/dimensions')
def get_dimensions(): return jsonify({"net_forward": net_forward})

# ---------------- FLASK RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
