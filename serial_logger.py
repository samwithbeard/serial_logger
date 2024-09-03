#!/usr/bin/env python3

from gpiozero import Button ,LED
import serial
import time
import paho.mqtt.client as mqtt
import os
import logging
from configparser import ConfigParser
logging.basicConfig(filename='/home/pi/serial_logger.log', level=logging.DEBUG)

# MQTT Configuration
#MQTT_BROKER = '192.168.1.119'  # Replace with your MQTT broker address
MQTT_PORT = 1883 #5672 #1883  # Default port for MQTT
MQTT_TOPIC_DATA = "logger/data"
MQTT_TOPIC_DEBUG = "logger/debug"

config = ConfigParser()
config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
print(config_path)
config.read(config_path)

usern = config.get('credentials', 'db_username')
passw = config.get('credentials', 'db_password')
MQTT_BROKER = config.get('credentials', 'MQTT_BROKER')

if usern and passw and MQTT_BROKER:
    print("Successfully retrieved credentials")
else:
    print("Failed to retrieve credentials")
rpm1=0
rpm2=0


ser = serial.Serial('/dev/serial0', 115200, timeout=1)
print("serial connection opened")

def log_temperature():
    res = os.popen('vcgencmd measure_temp').readline()
    temp = float(res.replace("temp=", "").replace("'C\n", ""))
    return temp

def temp_check():
    temp = log_temperature()
    send_message("raspi CPU temp "+str(int(temp)),MQTT_TOPIC_DEBUG)
    print(f"Current CPU temperature: {temp}°C")
    if temp > 80.0:  # Threshold for warning
        print("Warning: CPU temperature is too high! wait..")
        while temp > 82.0:
            temp = log_temperature()
            send_message("raspi CPU too high, having a break..",MQTT_TOPIC_DEBUG)
            time.sleep(1)  # Log every 10 seconds
            send_message("..continue",MQTT_TOPIC_DEBUG)


# Callback when connecting to the MQTT broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
        # Subscribe to the topic once connected
        client.subscribe(MQTT_TOPIC_DATA)
        client.subscribe(MQTT_TOPIC_DEBUG)
    else:
        print("Failed to connect, return code %d\n", rc)

# Callback for when a message is received
def on_message(client, userdata, msg):
    print(f"Received message: '{msg.payload.decode()}' on topic '{msg.topic}'")


try:
    # Create an MQTT client instance
    client = mqtt.Client()
    print("mqtt initialized")
    # Set the username and password
    client.username_pw_set(usern, passw)

    # Assign the on_connect and on_message callbacks
    client.on_connect = on_connect
    client.on_message = on_message

    # Connect to the MQTT broker
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    # Start the MQTT client loop in a separate thread
    client.loop_start()
    print("mqtt running")
except:
    print("mqtt not available")

def send_message(message="activated",TOPIC=MQTT_TOPIC_DATA):
        client.publish(TOPIC, message)
        print(f"Published message: '{message}' to topic: '{TOPIC}'")


# Setup GPIO pins
#GPIO.setmode(GPIO.BCM)
sensor1_pin = 20
sensor2_pin = 21
buzz_button_pin=5
led1_pin=6
#GPIO.setup(sensor1_pin, GPIO.IN)
#GPIO.setup(sensor2_pin, GPIO.IN)
#GPIO.setup(buzz_button_pin, GPIO.IN)
#GPIO.setup(led1_pin, GPIO.OUT)
#GPIO.output(led1_pin, GPIO.HIGH)

sensor1 = Button(sensor1_pin)
sensor2 = Button(sensor2_pin)
BUZZ_button = Button(buzz_button_pin, bounce_time = 0.2)
led = LED(led1_pin)
led.on()
# Variables to count pulses
count1 = 0
count2 = 0

# Callback functions to count pulses
def pulse1(channel):
    global count1
    led.on()
    count1 += 1
    print("rpm "+str(int(rpm1))+" "+int(rpm1/100)*"0")
    send_message("rpm "+str(int(rpm1))+" "+int(rpm1/100)*"0",MQTT_TOPIC_DATA)

def pulse2(channel):
    global count2
    led.on()
    count2 += 1
    print("rpm "+str(int(rpm2))+" "+int(rpm2/100)*"0")
    send_message("rpm "+str(int(rpm2))+" "+int(rpm2/100)*"0",MQTT_TOPIC_DATA)

def buzzz(channel):
    print("BUZZZ"+str(channel))
    led.on()
    send_message("BUZZZ button pressed",MQTT_TOPIC_DATA)
    time.sleep(1)  # Log every 10 seconds

# Add event detection for the sensors
# Attach the callbacks to the button
sensor1.when_pressed = pulse1
sensor2.when_pressed = pulse2
BUZZ_button.when_pressed = buzzz


# Function to calculate RPM
def calculate_rpm(count, interval):
    return (count / interval) * 60

try:
    led.off()
    print("waiting for serial messages..")
    while True:
        temp_check()
        with open('data\\serial_log.txt', 'a') as log_file:
            while True:
                line = ser.readline().decode('utf-8').strip()
                if line:
                    led.on()
                    print(line)
                    send_message(line)
                    led.off()
                    #log_file.write(line + '\n')

        

except KeyboardInterrupt:
    logging.error('Error occurred', exc_info=True)
    print("Measurement stopped by user")

finally:
    print("bye..")
