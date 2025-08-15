from ultrasonic import *
import time
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
"""
If ultrasonic detects object within 15cm
    Save the horizontal coordinates
    Check coordinates: if on border, must turn into box
    If not, use side ultrasonic/rotating camera to check sides, then turn into open side:
        After turning, use side detector to continue until the object is out of turning radius:
            Turn back into original horizontal axis and keep going straight
"""


original_heading = "forward"


def navigate():
    global original_heading
    while True:
        distances = {name: round(distance(pins["TRIG"], pins["ECHO"]), 2) for name, pins in sensors.items()}
        print(f"Distances: {distances}")


        if distances["front"] < 15:
            publish.single("state", "ultra", hostname=broker_ip)
            publish.single("ultra", "", hostname=broker_ip)
            print("Obstacle detected ahead, saving heading")
            original_heading = "forward"
           
            if distances["left"] > distances["right"]:
                print("Turning left")
                publish.single("ultra", "left", hostname=broker_ip) #time left turn & add as delay in turnleft command
                time.sleep(0.5)
                start_turn1 = time.time()
                while distances["right"] < 15:
                    distances = {name: round(distance(pins["TRIG"], pins["ECHO"]), 2)
                             for name, pins in sensors.items()}
                    publish.single("ultra", "up1", hostname=broker_ip)
                    print("avoiding object")
                    time.sleep(0.2)
                end_turn1 = time.time()
                time_return = end_turn1 - start_turn1 #how long to turn back
                publish("time", f"{time_return:.2f}", hostname=broker_ip)
                publish.single("ultra", "right", hostname=broker_ip)
                extra_time_start = time.time()
                while distances["right"] < 15:
                    distances = {name: round(distance(pins["TRIG"], pins["ECHO"]), 2)
                             for name, pins in sensors.items()}
                    print("avoiding object")
                    publish.single("ultra", "up2", hostname=broker_ip)
                    time.sleep(0.2)
                extra_time_end = time.time()
                extra_x = extra_time_end - extra_time_start
                publish.single("ultra", "right", hostname=broker_ip)
                publish.single("ultra", "up3L", hostname=broker_ip)
                publish.single("extra", f"{extra_x:.2f}", hostname=broker_ip)
                #publish.single("state", "trace", hostname=broker_ip)
            else:
                print("Turning right")
                publish.single("ultra", "right", hostname=broker_ip) #turn right
                time.sleep(0.5)
                start_turn1 = time.time()
                while distances["left"] < 15:
                    distances = {name: round(distance(pins["TRIG"], pins["ECHO"]), 2)
                             for name, pins in sensors.items()}
                    print("avoiding object")
                    publish.single("ultra", "up1", hostname=broker_ip)
                    time.sleep(0.2)
                end_turn1 = time.time()
                time_return = end_turn1 - start_turn1 #time for turn 1
                publish.single("time", f"{time_return:.2f}", hostname=broker_ip)
                print("returning to original heading")
                publish.single("ultra", "left", hostname=broker_ip) # turn left
                extra_time_start = time.time()
                while distances["left"] < 15:
                    distances = {name: round(distance(pins["TRIG"], pins["ECHO"]), 2)
                             for name, pins in sensors.items()}
                    print("avoiding object")
                    publish.single("ultra", "up2", hostname=broker_ip)
                    time.sleep(0.2)
                extra_time_end = time.time()
                extra_x = extra_time_end - extra_time_start
                publish.single("ultra", "left", hostname=broker_ip)
                publish.single("ultra", "up3R", hostname=broker_ip)
                publish.single("extra", f"{extra_x:.2f}", hostname=broker_ip)
                #publish.single("state", "trace", hostname=broker_ip)
                """stay same direction until back to original x-pos
                once at x-pos, turn right and continue straight
                three topics: ultra, time, extra
                    ultra: motor direction
                    time: how long to spin --> how far to travel in each direction
                    extra: account for extra x-distance traveled by navigating around object"""
                publish.single("state", "trace", hostname=broker_ip)