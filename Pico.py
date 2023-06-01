
import machine
import socket
import time

TCP_IP = '192.168.50.213'  # Replace with Raspberry Pi IP address
TCP_PORT = 5005  # TCP port for communication
INTERVAL = 30  # Time interval between temperature readings in seconds

# Configure temperature sensor pin
sensor = machine.ADC(26)

def read_temperature():

    sensor_pin = machine.ADC(26)
    # Return the temperature value
    reading = sensor_pin.read_u16()  # Read the ADC value
    voltage = reading * 3.3 / 65535  # Convert ADC reading to voltage
    temperature = (voltage - 0.5) * 100  # Convert voltage to temperature in degrees Celsius
    return temperature

# Create TCP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((TCP_IP, TCP_PORT))

if __name__ == 'main' :

   while 1:    
       try:
            temperature = read_temperature()
            dataFrame = {'Key':'Temp','Value': temperature}
            sock.sendall(str(dataFrame).encode())
            time.sleep(INTERVAL)
            
            # Enter deep sleep for 30 seconds
            machine.deepsleep(30000)
       except Exception as ex:
           print(ex)
           sock.close()