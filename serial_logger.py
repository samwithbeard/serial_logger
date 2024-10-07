#!/usr/bin/env python3


import serial
import time
import paho.mqtt.client as mqtt
import os
import logging
from configparser import ConfigParser
import traceback
print("version 1")
try:
    logging.basicConfig(filename='/home/pi/serial_logger/data/serial_logger.log', level=logging.DEBUG)
except:
    logging.basicConfig(filename='serial_logger.log', level=logging.DEBUG)

class GPIOSimulator:
    def __init__(self):
        self._button_state = False
        self._led_state = False

    def button(self, pin, bounce_time=None):
        return self

    def when_pressed(self, callback):
        pass

    def led(self, pin):
        return self

    def on(self):
        self._led_state = True

    def off(self):
        self._led_state = False

    @property
    def value(self):
        return self._button_state

    @value.setter
    def value(self, state):
        self._button_state = state

try:
    from gpiozero import Button, LED
except ImportError:
    GPIO = GPIOSimulator()
    Button = GPIO.button
    LED = GPIO.led

# MQTT Configuration

# mqtt_topic_publish = "logger/data"
MQTT_TOPIC_DEBUG = "94856500666/ETCS/debug"
mqtt_port_fahrzeug = 8885
mqtt_port_intern = 8883
mqtt_topic_publish = "94856500666/ETCS/test"
mqtt_topic_subscribe = "94856500666/ETCS/#"
mqtt_client_id_fahrzeug = "94856500666-ETCS-inte"
mqtt_client_id_intern = "94856500666-ETCS-inte"
mqtt_pem_file = "C:/Users/u242381/Downloads/SwissSign RSA TLS DV ICA 2022 - 1.pem"
mqtt_pem_file_intern = "C:/Users/u242381/Downloads/SBB-CL-B-Issuing-CA.pem"

config = ConfigParser()
config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
print(config_path)
config.read(config_path)

usern = config.get('credentials', 'mqtt_username')
passw = config.get('credentials', 'mqtt_password')
MQTT_BROKER = config.get('credentials', 'mqtt_broker')

if usern and passw and MQTT_BROKER:
    print("Successfully retrieved credentials")
else:
    print("Failed to retrieve credentials")
rpm1=0
rpm2=0

try:
    ser = serial.Serial('/dev/serial0', 115200, timeout=1)
except:
    ser = serial.Serial('COM7', 115200, timeout=1)

print("serial connection opened")

def log_temperature():
    res = os.popen('vcgencmd measure_temp').readline()
    temp_str = res.replace("temp=", "").replace("'C\n", "").strip()
    try:
        temp = float(temp_str)
        return temp
    except ValueError:
        print("Invalid temperature value:", temp_str)
        return -0.1
    

def temp_check():
    temp = log_temperature()
    send_message("logger CPU temp "+str(int(temp)),MQTT_TOPIC_DEBUG)
    print(f"Current CPU temperature: {temp}°C")
    if temp > 80.0:  # Threshold for warning
        print("Warning: CPU temperature is too high! wait..")
        while temp > 82.0:
            temp = log_temperature()
            send_message("logger CPU too high, having a break..",MQTT_TOPIC_DEBUG)
            time.sleep(1)  # Log every 10 seconds
            send_message("..continue",MQTT_TOPIC_DEBUG)


# Callback when connecting to the MQTT broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
        # Subscribe to the topic once connected
        client.subscribe(mqtt_topic_publish)
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
    client.connect(MQTT_BROKER, mqtt_port_fahrzeug, 60)

    # Start the MQTT client loop in a separate thread
    client.loop_start()
    print("mqtt running")
except:
    print("mqtt not available")

def send_message(message="activated",TOPIC=mqtt_topic_publish):
        client.publish(TOPIC, message)
        print(f"Published message: '{message}' to topic: '{TOPIC}'")



# Variables to count pulses
count1 = 0
count2 = 0

def parse_ICN_line(line):
    frame={}
    parsed_frame={}
    dist=""
    time=""
    rad_speed=""
    status1=""
    error_rate=""
    #print(str(line_len))
    #print(str(sub_line[0]))
    #int(line[10:12],16)    
    splitted_line = [line[i:i+2] for i in range(0, len(line), 2)]                        
    #data=split_line(line,[split_all, "1c","1d", "1a", "ff","18"] )
    try:
        counter= str(int(splitted_line[0],16))
    except:
        counter='NAN'

    try:
        rad_speed = str(float(int(splitted_line[125] + splitted_line[126],16))/100)        
        #print("i1 "+str(int(splitted_line[126],16))+" i2 "+ str(int(splitted_line[127],16)))
    except Exception as e:
        rad_speed = 'NAN'        
        print(traceback.format_exc())
        print(e)

    try:
        dist= extract_16_bit(splitted_line,127)
        #print("i1 "+str(int(splitted_line[126],16))+" i2 "+ str(int(splitted_line[127],16)))
    except Exception as e:
        dist = 'NAN'        
        print(traceback.format_exc())
        print(e)    
   
    try:                                            
        time= float(extract_64_bit(splitted_line,11))/1000000
        #print("i1 "+str(int(splitted_line[126],16))+" i2 "+ str(int(splitted_line[127],16)))
    except Exception as e:
        time = 'NAN'   
        print(traceback.format_exc())
        print(e)
    
    try:
        status1 = str(int(splitted_line[124],16))       
        #print("i1 "+str(int(splitted_line[126],16))+" i2 "+ str(int(splitted_line[127],16)))
    except Exception as e:
        status1 = 'NAN'        
        print(traceback.format_exc())
        print(e)

    try:
        error_rate = calculate_alstom_float(splitted_line[135]+splitted_line[136])     
        #print("i1 "+str(int(splitted_line[126],16))+" i2 "+ str(int(splitted_line[127],16)))
    except Exception as e:
        error_rate = 'NAN'        
        print(traceback.format_exc())
        print(e)



    parsed_frame={
        'counter': str(counter),
        'time': str(time),
        'speed' : str(rad_speed),
        'error_rate' : str(error_rate),
        'status1': str(status1),
        'dist' : str(dist)
    }   
    frame.update(parsed_frame)   

    #print(speed)
    return frame, splitted_line, parsed_frame

def extract_16_bit(splitted_line,position):
    value = str(float(int(splitted_line[position] + splitted_line[position+1],16)))
    return value

def extract_32_bit(splitted_line,position):
    value = str(float(int(splitted_line[position] + splitted_line[position+1] + splitted_line[position+2],16)))
    return value

def extract_64_bit(splitted_line,position):
    value = str(float(int(splitted_line[position] + splitted_line[position+1] + splitted_line[position+2]+ splitted_line[position+3],16)))
    return value


def calculate_alstom_float(hex_value):
    h_exp = hex_value[:2]
    h_base = hex_value[2:]
    h_base=int(h_base,16)
    h_exp=int(h_exp,16)
    if h_exp > 125:
        result = (h_base / 255) * (10 ** -(256 - h_exp))
    else:
        result = (h_base / 255) * (10 ** h_exp)
    return result

#logpath=os.getcwd()+"/data/serial_log.txt"
logpath="serial_log_test.txt"
try:    
    print("waiting for serial messages..")
    while True:
        #temp_check()        
        #with open('data/serial_log.txt', 'a') as log_file:
        while True:
            try:
                now=time.time()
                #Odometrie:
                telegram = ser.readline().hex()#+" time "+str(now)
                telegram_header=(telegram[:4])
                
                print(telegram_header+"\t "+str(len(telegram)))
                if telegram_header == "1a6b":
                    lines=telegram.split("1b0244") #1b031b0244
                    telegram = telegram+" time "+str(now)
                    #print(frags[0][:4])
                    for line in lines:                   
                        
                        try:
                            rad_speed = str(float(int(line[125] + line[126],16))/100)        
                            #print("i1 "+str(int(splitted_line[126],16))+" i2 "+ str(int(splitted_line[127],16)))
                            #print(str(rad_speed))                       
                        except Exception as e:
                            rad_speed = 'NAN'        
                            #print("no radar_speed found")
                            print(e)
                        lineid=line[0:2]
                        parsed_values=parse_ICN_line(line)
                        print(line[0:2]+ " " +str(len(line))+" "+rad_speed)
                        
                        print()
                        #line id 1a ist ungültig
                        #0b-09 mit der länge 356 sind gültig
                elif telegram_header == "09b5":
                    #länge 346
                    c=telegram.count("0")

            except Exception as e:
                print(e)
                
            if telegram:
                #led.on()
                #print("line "+line)
                #send_message(line)
                #led.off()
                with open(logpath, 'a') as fd:
                    fd.write(f'\n{telegram}')
                #log_file.write(line + '\n')
    
        

except KeyboardInterrupt:
    logging.error('Error occurred', exc_info=True)
    print("Measurement stopped by user")

finally:
    print("bye..")
