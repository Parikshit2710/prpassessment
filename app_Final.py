import sqlite3
import eventlet
import json
from threading import Thread
import socket
from flask import Flask, render_template
from flask_mqtt import Mqtt
from flask_socketio import SocketIO
from flask_bootstrap import Bootstrap
from flask_mail import Mail, Message

eventlet.monkey_patch()

app = Flask(_name_)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['MQTT_BROKER_URL'] = 'broker.hivemq.com'
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_CLEAN_SESSION'] = True
app.config['MQTT_USERNAME'] = ''
app.config['MQTT_PASSWORD'] = ''
app.config['MQTT_KEEPALIVE'] = 5
app.config['MQTT_TLS_ENABLED'] = False
app.config['MQTT_LAST_WILL_TOPIC'] = 'home/lastwill'
app.config['MQTT_LAST_WILL_MESSAGE'] = 'bye'
app.config['MQTT_LAST_WILL_QOS'] = 2

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = "patassessment2710@gmail.com"
app.config['MAIL_PASSWORD'] = "patassessment27105394"
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

app.config.from_object(_name_)

mqtt = Mqtt(app)
socketio = SocketIO(app)
bootstrap = Bootstrap(app)
mail = Mail(app)

# TCP connection
TCP_IP = '192.168.50.213'  # Replace with Raspberry Pi IP address
TCP_PORT = 8080  # TCP port for TCP communication
tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
tcp_socket.bind((TCP_IP, TCP_PORT))
tcp_socket.listen(4)

# UDP connection
UDP_IP = '192.168.50.213'  # Replace with Raspberry Pi IP address
UDP_PORT = 5005  # UDP port for UDP communication
udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_socket.bind((UDP_IP, UDP_PORT))

temperature_counter = 0
temp_readings = []
light_readings = []
light_counter = 0

conn = sqlite3.connect('Sensordata.db')
cursor = conn.cursor()

# Create the Sensordata table if it doesn't exist
cursor.execute('''CREATE TABLE IF NOT EXISTS Sensordata
                  (id INTEGER PRIMARY KEY AUTOINCREMENT,
                   temperature REAL,
                   light_intensity REAL,
                   timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
conn.commit()


@app.route('/')
def index():
    return render_template('index.html')


@mqtt.on_connect()
def handle_mqtt_connect(client, userdata, flags, rc):
    mqtt.subscribe('topic/temp_request_20648424')
    mqtt.subscribe('topic/light_request_20648424')


@socketio.on('publish')
def handle_publish(json_str):
    if json.loads(json_str)['topic'] == 'topic/temp_request_20648424':
        # Query the latest 10 temperature readings from database
        cursor.execute("SELECT temperature FROM Sensordata ORDER BY timestamp DESC LIMIT 10")
        rows = cursor.fetchall()

        # Extract the temperature values from the rows
        temperature_readings = [row[0] for row in rows]

        # Convert the temperature readings to JSON
        json_data = json.dumps(temperature_readings)

        # Publish the JSON data via MQTT
        mqtt.publish("topic/temp_reply_20648424", json_data)

        # Subscribe to the reply topic to receive the response from the Raspberry Pi
        mqtt.subscribe("topic/temp_reply_20648424")

    elif json.loads(json_str)['topic'] == "topic/light_request_20648424":
        # Query the latest 10 light sensor readings from the local database
        cursor.execute("SELECT light_intensity FROM Sensordata ORDER BY timestamp DESC LIMIT 10")
        rows = cursor.fetchall()

        # Extract the light values from the rows
        light_readings = [row[0] for row in rows]

        # Convert the light sensor readings to JSON
        json_data = json.dumps(light_readings)

        # Publish the JSON data via MQTT
        mqtt.publish("topic/light_reply_20648424", json_data)

        # Subscribe to the reply topic to receive the response from the Raspberry Pi
        mqtt.subscribe("topic/light_reply_20648424")


@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    global temperature_counter
    global light_counter
    data = dict(
        topic=message.topic,
        payload=message.payload.decode(),
        qos=message.qos,
    )
    socketio.emit('mqtt_message', data=data)
    value = data['payload']
    sensor = message.topic

    if message.topic.startswith('topic/temp_reply_20648424'):
        temperature_counter += 1
        # Checking the count and sending email if it's 50
        if temperature_counter == 50:
            # Send email notification
            max_temp = max(temp_readings)
            min_temp = min(temp_readings)
            avg_temp = sum(temp_readings) / len(temp_readings)

            msg = Message('Temperature Readings Notification',
                          sender='patassessment2710@gmail.com',
                          recipients=['20648424@students.latrobe.edu.au'])
            msg.body = f"Max Temperature: {max_temp}\n" \
                       f"Min Temperature: {min_temp}\n" \
                       f"Average Temperature: {avg_temp}"
            mail.send(msg)

            # Reset the counter and clear temperature readings
            temperature_counter = 0
            temp_readings.clear()

    elif message.topic.startswith('topic/light_reply_20648424'):
        light_counter += 1
        # Checking the count and sending email if it's 50
        if light_counter == 50:
            # Send email notification
            max_light = max(light_readings)
            min_light = min(light_readings)
            avg_light = sum(light_readings) / len(light_readings)

            msg = Message('Light Sensor Readings Notification',
                          sender='patassessment2710@gmail.com',
                          recipients=['20648424@students.latrobe.edu.au'])
            msg.body = f"Max Light Sensor Value: {max_light}\n" \
                       f"Min Light Sensor Value: {min_light}\n" \
                       f"Average Light: {avg_light}"
            mail.send(msg)

            # Reset the counter and clear light readings
            light_counter = 0
            light_readings.clear()


def handle_tcp_client(tcp_conn):
    while True:
        data = tcp_conn.recv(1024)
        try:
            received_data = json.loads(data)
            if 'Temp' in received_data:
                temperature = received_data['Temp']
                print('Received temperature:', temperature)
                if -40 <= temperature <= 85:
                    cursor.execute("INSERT INTO Sensordata (temperature) VALUES (?)", (temperature,))
                    # Commit the changes
                    conn.commit()
                else:
                    print("Abnormal Pico temperature reading. Discarding...")
            else:
                print('No temperature data found in received message')
        except json.JSONDecodeError:
            print('Invalid JSON data received')


def handle_udp_client():
    while True:
        message_recv, (udp_ip, udp_port) = udp_socket.recvfrom(1024)
        try:
            received_data = json.loads(message_recv)
            if 'Light' in received_data:
                light_intensity = received_data['Light']
                print('Received light intensity:', light_intensity)
                if 0 <= light_intensity <= 100:
                    cursor.execute("INSERT INTO Sensordata (light_intensity) VALUES (?)", (light_intensity,))
                    # Commit the changes
                    conn.commit()
                else:
                    print("Abnormal light sensor reading. Discarding...")
            else:
                print('No light intensity data found in received message')
        except json.JSONDecodeError:
            print('Invalid JSON data received')


def start_background_threads():
    tcp_thread = Thread(target=start_tcp_server)
    udp_thread = Thread(target=start_udp_server)

    tcp_thread.start()
    udp_thread.start()


def start_tcp_server():
    while True:
        tcp_conn, addr = tcp_socket.accept()
        tcp_thread = Thread(target=handle_tcp_client, args=(tcp_conn,))
        tcp_thread.start()


def start_udp_server():
    while True:
        handle_udp_client()


if _name_ == '_main_':
    start_background_threads()
    socketio.run(app, host='0.0.0.0', port=5000)