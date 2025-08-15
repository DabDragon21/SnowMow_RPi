#!/usr/bin/env python3
#------------------------------------------------------
#
#		This is a program for JoystickPS2 Module.
#
#		This program depend on PCF8591 ADC chip. Follow 
#	the instruction book to connect the module and 
#	ADC0832 to your Raspberry Pi.
#
#------------------------------------------------------
import PCF8591 as ADC 
import time
import math
import RPi.GPIO as GPIO

system_on = False
press_start_time = None
toggle_time = 2.0

def setup():
	ADC.setup(0x48)					# Setup PCF8591
	global state
setup()

def direction():	#get joystick result
	state = [None, 'up', 'down', 'left', 'right', 'pressed', 'on', 'off']
	i = 0
	if ADC.read(0) <= 30:
		i = 3		#up
	if ADC.read(0) >= 225:
		i = 4		#down

	if ADC.read(1) >= 225:
		i = 2		#left
	if ADC.read(1) <= 30:
		i = 1		#right

	if ADC.read(2) <= 30:
		i = 5		# Button pressed

	if ADC.read(0) - 125 < 15 and ADC.read(0) - 125 > -15	and ADC.read(1) - 125 < 15 and ADC.read(1) - 125 > -15 and ADC.read(2) == 255:
		#i = 0
		pass
	
	return state[i]

def check_button():
    global system_on, press_start_time
    btn_val = ADC.read(2)
    if btn_val <= 30:
        if press_start_time is None:
            press_start_time = time.time()
        elif time.time() - press_start_time >= toggle_time:
            system_on = not system_on
            press_start_time = float('inf')
    else:
        press_start_time = None
    
    return"ON" if system_on else "OFF"

def loop():
	last_status = ''
	last_mode = None
	while True:
		mode = check_button()
		if mode and mode != last_mode:
			print(f"System: {mode}")
			last_mode = mode
		tmp = direction()
		if tmp and tmp != last_status and tmp != "pressed":
			print(f"Direction: {tmp}")
			last_status = tmp
		time.sleep(0.2)
		
def destroy():
	GPIO.cleanup()
	pass

if __name__ == '__main__':		# Program start from here
	setup()
	try:
		loop()
	except KeyboardInterrupt:  	# When 'Ctrl+C' is pressed, the child program destroy() will be  executed.
		destroy()
