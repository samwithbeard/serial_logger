import serial
import time

serial_settings = {
    "115200": {"baudrate": 9600, "timeout": 1, "parity": 'N'},
    "9600": {"baudrate": 115200, "timeout": 0.5, "parity": 'N'},
    "57600": {"baudrate": 57600, "timeout": 0.5, "parity": 'N'},
    "38400": {"baudrate": 38400, "timeout": 0.5, "parity": 'N'},
    "19200": {"baudrate": 19200, "timeout": 0.5, "parity": 'N'},
}

com_port = 'COM5'

for baud_rate, settings in serial_settings.items():
    try:
        ser = serial.Serial(port=com_port, **settings)
        print("Serial connection established with settings:")
        print(f"Baudrate: {settings['baudrate']}")
        print(f"Timeout: {settings['timeout']}")
        print(f"Parity: {settings['parity']}")
        
        while True:
            command = input("Enter command (or 'exit' to quit): ")
            if command.lower() == "exit":
                break
            
            ser.write(command.encode() + b'\n')
            response = ser.readline()
            print("Received response:", response.decode().strip())
        
        ser.close()
        print("Serial connection closed.")
        
        break
    
    except Exception as e:
        print(f"Failed to establish serial connection with settings: {settings}")
        print(f"Error: {str(e)}")
        time.sleep(1)

else:
    print("Failed to establish serial connection with all settings.")
