import requests
import math
import random
import json
import csv
from time import sleep
import datetime
import udatetime
import socket
import string

URL = 'https://api.hack-the-necstcamp.necst.it/'
URL_LOG = URL + 'sleep/send_room_data'
IFTTT_URL = 'https://maker.ifttt.com/trigger/'
IFTTT_KEY = '/with/key/PRIVATE_KEY'

REMOTE_HOST = 'localhost'
PORT = 50002

def generateValue(oldValue, active, growth):
    if active == True:
        newValue = oldValue + random.uniform(0, 1) / growth
        return newValue
    else:
        newValue = oldValue - random.uniform(0, 1) / growth
        return newValue

def userLogin(username, password):
    headers = {'Content-Type': 'application/json'}
    data = {'username': username, 'password': password}
    try:
        req = requests.post(URL + 'users/login', headers=headers, json=data)
        if(req.status_code == 200):
            userJWT = json.loads(req.content.decode("utf-8"))['token']
            return userJWT
        else:
            return ''
    except Exception as e:
        return ''

def sendMessageToServer(message):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((REMOTE_HOST, PORT))
        print("Connected")
        s.sendall(message.encode('ascii'))
        print("Message " + message + " sent")
        s.settimeout(2)
        serverMessage = s.recv(1024).decode("utf-8")
        s.close()
        return serverMessage


if __name__ == "__main__":
    timestamp = udatetime.to_string(udatetime.now())

    ### INITIALISE CSV
    file = open("LOG_" + timestamp + ".csv", "a+")
    writer = csv.writer(file, dialect='excel', lineterminator='\n')
    if file.tell() == 0:
        writer.writerow(["TIME", "TEMP", "HUMIDITY", "CO2"])
        file.flush()
    
    # header for API requests
    headers = {'Content-Type':'application/json'}

    ### INITIALISE CONFIG TOKEN
    with open("config.json", "r") as configFile:
        config = json.load(configFile)

    config['token'] = userLogin(config["user"], config["pwd"])

    ### Get good limits from server:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((REMOTE_HOST, PORT))
        print("Connected")
        s.sendall(b'SEND MEMES')
        print("Request boot sent")
        s.settimeout(2)
        serverMessage = []
        for i in range(3):
            serverMessage.append(s.recv(1024).decode("utf-8"))

        s.close()
    print('Received {0:} {1:} {2:}'.format(serverMessage[0], serverMessage[1], serverMessage[2]))

    temp_optimal = int(serverMessage[0])
    hum_optimal = int(serverMessage[1])
    co2_optimal = int(serverMessage[2])

    # requests.post(url=IFTTT_URL+"{Low_Temp}"+IFTTT_KEY)
    # requests.post(url=IFTTT_URL+"{High_Temp}"+IFTTT_KEY)
    # requests.post(url=IFTTT_URL+"{Low_Hum}"+IFTTT_KEY)
    # requests.post(url=IFTTT_URL+"{High_Hum}"+IFTTT_KEY)
    # requests.post(url=IFTTT_URL+"{High_CO2}"+IFTTT_KEY)
    
    temp = 25
    hum = 50
    co2 = 1000

    # Memory backlog
    backlog_record = []

    # Is the system active?
    active_system = False
    active_cycle = False

    while(True):
        print("Cycle")
        active_cycle = False
        
        timestamp = udatetime.to_string(udatetime.now())

        ### ARTIFICIAL INTELLIGENCE
        if active_system == True and not (temp_optimal - 0.5 < temp < temp_optimal + 0.5 or hum_optimal - 5 < hum < hum_optimal + 5):
            active_cycle = True

        if active_system == False:
            if temp < temp_optimal - 2:
                print("****Heating the room up****")
                requests.post(url=IFTTT_URL+"{Low_Temp}"+IFTTT_KEY)
                active_system = True
                active_cycle = True
                ## Send packet
                sendMessageToServer("LT")

            if temp > temp_optimal + 2:
                print("****Cooling the room down****")
                requests.post(url=IFTTT_URL+"{High_Temp}"+IFTTT_KEY)
                active_system = True
                active_cycle = True
                ## Send packet
                sendMessageToServer("HT")
            
            if hum < hum_optimal - 20:
                print("****Humidify the room****")
                requests.post(url=IFTTT_URL+"{Low_Hum}"+IFTTT_KEY)
                active_system = True
                active_cycle = True
                ## Send packet
                sendMessageToServer("LH")

            if hum > hum_optimal + 20:
                print("****Dehumidify the room****")
                requests.post(url=IFTTT_URL+"{High_Hum}"+IFTTT_KEY)
                active_system = True
                active_cycle = True
                ## Send packet
                sendMessageToServer("HH")

            if co2 > co2_optimal + 1500:
                print("****Ventilate the room****")
                requests.post(url=IFTTT_URL+"{High_CO2}"+IFTTT_KEY)
                active_system = True
                active_cycle = True
                ## Send Packet
                sendMessageToServer("HC")

        if active_cycle == 0:
            active_system = 0
            
        if active_system == False:
            temp = generateValue(temp, not active_system, 5)
            hum = generateValue(hum, not active_system, 2.5)
            co2 = int(generateValue(co2, active_system, 0.2))
        else:
            co2 = int(generateValue(co2, not active_system, 0.2))
            if temp < temp_optimal:
                temp = generateValue(temp, active_system, 2)
            else:
                temp = generateValue(temp, not active_system, 2)

            if hum < hum_optimal:
                hum = generateValue(hum, active_system, 1.5)
            else:
                hum = generateValue(hum, not active_system, 1.5)
        ###

        writer.writerow([timestamp, temp, hum, co2])
        file.flush()

        data = {}
        # Check if token is available
        if config['token'] == '':
            config['token'] = userLogin(config['user'], config['pwd'])
        data['input'] = {'room_id': config['room_id'], 'timestamp': timestamp, 'temperature': json.dumps(temp), 'humidity': json.dumps(hum), 'co2': json.dumps(co2)} 
        data['token'] = config['token']

        # Send data to server
        try:
            print("Sending T {0:2.2} H {1:2.2} C {2:5} at time {3:}".format(temp, hum, co2, timestamp))
            req = requests.post(url=URL_LOG, headers=headers, json=data)
            # ifttt_req = requests.post(url=IFTTT_URL+"{Event}"+IFTTT_KEY, data={'temperature': temp, 'humidity': hum, 'co2 level': co2})
            print("Request {0:3} ;".format(req.status_code))

            # Check request result
            if req.status_code != 200:
                print("Req status {}:saving THC record on backlog".format(req.status_code))
                backlog_record.append(data)
            else:
                while len(backlog_record) > 0 and requests.post(url=URL_LOG, headers=headers, json=backlog_record[0]).status_code == 200:
                    del backlog_record[0]
        except requests.exceptions.ConnectionError:
            print("Connection refused: saving THC record on backlog")
            backlog_record.append(data)
        except KeyboardInterrupt:
            file.close()
            break
        
        # Wait 30 seconds
        sleep(0.5)

