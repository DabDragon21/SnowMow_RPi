from ultrasonic import *
import time
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt

original_heading = "forward"
SAFE_DISTANCE = 15  # cm
trace_mode = False

broker_ip = "10.83.0.146"

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker with result code {rc}")
    client.subscribe("state")  # Listen for trace toggle messages

def on_message(client, userdata, msg):
    global trace_mode
    payload = msg.payload.decode().strip().lower()
    if payload == "trace":
        trace_mode = True
        print("Trace mode ENABLED")
    else:
        trace_mode = False
        print("Trace mode DISABLED")

mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(broker_ip, 1883, 60)
mqtt_client.loop_start()

def avoid_obstacle(turn_direction):
    """
    Handles rectangle obstacle avoidance.
    turn_direction: "left" or "right" -> side to initially turn
    """
    global extra_x

    print(f"Turning {turn_direction}")
    publish.single("ultra", turn_direction, hostname=broker_ip)
    time.sleep(0.5)

    # Phase 1: Clear obstacle
    start_turn = time.time()
    opposite = "right" if turn_direction == "left" else "left"

    while distances[opposite] < SAFE_DISTANCE:
        update_distances()
        publish.single("ultra", "up1", hostname=broker_ip)
        print("Avoiding obstacle...")
        time.sleep(0.2)
    end_turn = time.time()
    time_return = end_turn - start_turn
    publish.single("time", f"{time_return:.2f}", hostname=broker_ip)

    # Phase 2: Return to original heading
    publish.single("ultra", opposite, hostname=broker_ip)
    extra_start = time.time()
    while distances[opposite] < SAFE_DISTANCE:
        update_distances()
        publish.single("ultra", "up2", hostname=broker_ip)
        time.sleep(0.2)
    extra_end = time.time()
    extra_x = extra_end - extra_start

    # Final turn to resume forward
    publish.single("ultra", opposite, hostname=broker_ip)
    publish.single("ultra", "up3" + turn_direction[0].upper(), hostname=broker_ip)
    publish.single("extra", f"{extra_x:.2f}", hostname=broker_ip)
    publish.single("state", "trace", hostname=broker_ip)
    print(f"Finished avoiding obstacle, extra_x={extra_x:.2f}")


def update_distances():
    """Update global distances dictionary"""
    global distances
    distances = {name: round(distance(pins["TRIG"], pins["ECHO"]), 2)
                 for name, pins in sensors.items()}


def navigate():
    global original_heading
    while True:
        if not trace_mode:
            time.sleep(0.1)
            continue

        update_distances()
        print(f"Distances: {distances}")

        if distances["front"] < SAFE_DISTANCE:
            publish.single("state", "ultra", hostname=broker_ip)
            publish.single("ultra", "", hostname=broker_ip)
            print("Obstacle detected ahead, saving heading")
            original_heading = "forward"

            # Decide which side to turn
            if distances["left"] > distances["right"]:
                avoid_obstacle("left")
            else:
                avoid_obstacle("right")
