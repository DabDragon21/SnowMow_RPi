from joystick_pub import *
import paho.mqtt.publish as publish
import paho.mqtt.client as client

broker_ip = "10.83.0.146"
topic = "heading"
latest_heading = None

def load_calibration():
    global max_corner, max_distance_value
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
            max_corner = tuple(data.get("max_corner", (0, 0)))
            max_distance_value = data.get("max_distance_value", 0.0)
        print(f"Calibration loaded: {data}")
    else:
        print("No saved calibration")

# acceses last stored calibrated path

# follow last calibrated path
# let's say max_corner = (8, 8) --> travel lines in x dir
# so....

def on_connect2(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(topic)
    else:
        print(f"Connection failed: {rc}")

def on_message2(client, userdata, msg):
    global latest_heading
    try:
        latest_heading = float(msg.payload.decode())
    except ValueError:
        print("Invalid datatype: ", msg.payload)

client = mqtt.Client()
client.on_connect = on_connect2
client.on_message = on_message2
client.connect(broker_ip, 1883, 60)
client.loop_start()

def find_path():
    #global max_corner, max_distance_value
    x = abs(max_corner[0]*12) #width in inches
    y = abs(max_corner[1]*12) #length in inches
    time_x = x * 10 * math.pi #sec to travel x
    lines_x = math.ceil(y/15) #15inches per x line --> div by 15 --> num of x lines
    #forward for time_x, then turn, then repeat lines_x 
    #turn L or R? see if max_y > end of x1, turn left, else turn right
    #this logic done on ESP32 bc we dont have x pos?
    #nah so send the motor run time from the ESP32, use that + heading to estimate position
    #then return to max_y vs y0 to decide turn logic  

    publish.single("lines", f"{time_x}", hostname=broker_ip)
    publish.single("turns", f"{lines_x}", hostname=broker_ip)
    publish.single("state", "trace", hostname=broker_ip)

load_calibration()