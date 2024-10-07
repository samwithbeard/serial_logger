#!/usr/bin/env python3

import hashlib
import serial
import time
import paho.mqtt.client as mqtt
import os
import logging
from configparser import ConfigParser
import traceback
import ssl
import uuid

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



def print_file_md5():
    file_path = __file__
    with open(file_path, 'rb') as file:
        md5_hash = hashlib.md5()
        while chunk := file.read(4096):
            md5_hash.update(chunk)
    print(f"MD5 hash of file '{file_path}': {md5_hash.hexdigest()}")
print_file_md5()

# read Configuration parameter
config = ConfigParser()
config_path = os.path.join(os.path.dirname(__file__), '/config/config.ini')
print(config_path)
config.read(config_path)


mqtt_user_id = config.get('credentials', 'mqtt_username')
mqtt_password = config.get('credentials', 'mqtt_password')
mqtt_broker_intern = config.get('credentials', 'mqtt_broker_intern')
mqtt_broker_outside = config.get('credentials', 'mqtt_broker_outside')
# MQTT Configuration

# Generiere eine zufällige UUID
my_uuid = uuid.uuid1()
#uic range 94856500666 - 94856500669        
#uuid       
UIC_VehicleID="94856500666"
#mqtt_broker_intern = "mqtt-fzge-int.sbb.ch"   #mqtte-fzge-int.sbb.ch:8885 
#mqtt_broker_outside = "mqtte-fzge-int.sbb.ch"   #mqtte-fzge-int.sbb.ch:8885 
mqtt_port_outside = 8885               #8885
mqtt_port_intern = 8883
mqtt_topic_publish = UIC_VehicleID+"/ETCS"
mqtt_topic_subscribe = "+/ETCS/#"
mqtt_client_id_fahrzeug = UIC_VehicleID+"-ETCS-inte" #<uic>-ETCS-inte
mqtt_topic_test_publish=mqtt_topic_publish+"/test"
mqtt_client_id_intern = "s-ETCS-consumer-inte-"+str(my_uuid) #s-ETCS-consumer-inte-<uuid>
mqtt_user_id="ETCS_PoC-inte"
mqtt_pem_file_intern = "/home/pi/serial_logger/config/SBB-CL-B-Issuing-CA.pem"
mqtt_pem_file_outside = "/home/pi/serial_logger/config/SwissSign RSA TLS DV ICA 2022 - 1.pem" #C:\Users\u242381\OneDrive - SBB\Dokumente\visual code\repos\serial logger
#name       #port       #datei                                  #valid
#SBB signed	8883, 8886	SBB-CL-B-Issuing-CA.pem	                27.09.2027
#SwissSign	8885, 8887	SwissSign RSA TLS DV ICA 2022 - 1.pem	29.06.2036
intern=False


def check_pem_file(pem_file):
    try:
        context = ssl.create_default_context()
        context.load_verify_locations(cafile=pem_file)
        return True
    except ssl.SSLError as e:
        print(f"Error loading PEM file: {str(e)}")
        return False

is_valid = check_pem_file(mqtt_pem_file_outside)
if is_valid:
    print(mqtt_pem_file_outside+" PEM file is valid!")

is_valid = check_pem_file(mqtt_pem_file_intern)

if is_valid:
    print(mqtt_pem_file_intern+" PEM file is valid!")

def on_connect(client, userdata, flags, rc):
    print("Connection Return code:", rc)
    if rc == 0:
        print("Connected to MQTT broker successfully.")
        client.subscribe(mqtt_topic_subscribe)
    elif rc == 1:
        print("Connection refused: incorrect protocol version.")
    elif rc == 2:
        print("Connection refused: invalid client identifier.")
    elif rc == 3:
        print("Connection refused: server unavailable.")
    elif rc == 4:
        print("Connection refused: bad username or password.")
    elif rc == 5:
        print("Connection refused: not authorized.")
    else:
        print("Connection refused: unknown reason. Return code:", rc)    
    

def on_publish(client, userdata, mid):
    print("Nachricht erfolgreich veröffentlicht")

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("Unerwartete Trennung vom MQTT-Broker "+str(rc))

def on_message(client, userdata, msg):
    print("Neue Nachricht empfangen: " + msg.topic + " " + str(msg.payload))
try:
    if intern:
        client = mqtt.Client(client_id=mqtt_client_id_intern)    
    else :
        client = mqtt.Client(client_id=mqtt_client_id_fahrzeug)    
except: 
    print("mqtt connection failed")

# MQTT-Broker mit TLS-Verbindung konfigurieren
if intern:
    client.tls_set(ca_certs=mqtt_pem_file_intern, certfile=None, keyfile=None, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)    
else :
    client.tls_set(ca_certs=mqtt_pem_file_outside, certfile=None, keyfile=None, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)

client.username_pw_set(username=mqtt_user_id, password=mqtt_password)
client.on_connect = on_connect
client.on_publish = on_publish
client.on_disconnect = on_disconnect
client.on_message = on_message
timeout=60
if intern:
    client.connect(mqtt_broker_intern, mqtt_port_intern, timeout)
else:
    client.connect(mqtt_broker_outside, mqtt_port_outside, timeout)
client.loop_start()
# Testnachricht senden
client.publish(mqtt_topic_publish, str(my_uuid)+" started")
# serial configuration
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
    message=("logger CPU temp "+str(int(temp)))
    client.publish(mqtt_topic_publish, message)
    print(f"Current CPU temperature: {temp}°C")
    if temp > 80.0:  # Threshold for warning
        print("Warning: CPU temperature is too high! wait..")
        while temp > 82.0:
            temp = log_temperature()
            client.publish("logger CPU too high, having a break..",mqtt_topic_test_publish)
            time.sleep(1)  # Log every 10 seconds
            client.publish("..continue",mqtt_topic_test_publish)



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
                            client.publish(str(UIC_VehicleID)+" speed: "+str(rad_speed),mqtt_topic_test_publish)                     
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
