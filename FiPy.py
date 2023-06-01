import machine
import socket
import time

UDP_IP = '192.168.50.213'  # Replace with Raspberry Pi IP address
UDP_PORT = 5005  # UDP port for communication

# Configure button pin
button = machine.Pin('P14', machine.Pin.IN, machine.Pin.PULL_UP)

# Create UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Function to read light sensor data
def read_light_sensor():
    # Read analog value from the light sensor
    sensor_value = light_sensor.read()

    # Map the sensor value to the desired range
    mapped_value = (sensor_value - 0) * (100 - 0) / (4095 - 0) + 0

    # Return the mapped value
    return mapped_value


if name == 'main' :
   
   while 1:    
       try:
           if button.value() == 0:
              light_reading = read_light_sensor()
              dataFrame = {'Key':'Light','Value': light_reading}
              sock.sendto(str(dataFrame).encode(), (UDP_IP, UDP_PORT))
                
              # Enter deep sleep for 30 seconds
              machine.deepsleep(30000)
                
       except Exception as ex:
              print(ex)
              sock.close()