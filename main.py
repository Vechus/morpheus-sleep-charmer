import json
import sys
import os
import threading
from time import perf_counter, sleep
from datetime import datetime
import requests
import udatetime
#import pmodad2
sys.path.append(os.path.realpath('../necstcamp-polar-backend/ncamp-backend-mode/'))
sys.path.append(os.path.realpath('../necstcamp-polar-backend/'))
import polar_ncamp
import RPi.GPIO as GPIO
import si7021
from SPW2430 import SPW2430
from light_sensor import GA1A12S202
import busio
import digitalio
import board
import adafruit_mcp3xxx.mcp3008 as MCP
from adafruit_mcp3xxx.analog_in import AnalogIn
#from sgp30 import Sgp30
from adafruit_sgp30 import Adafruit_SGP30 as sgp30
from smbus2 import SMBusWrapper
import csv
import socket

URL = 'https://api.hack-the-necstcamp.necst.it/'
IFTTT_URL = 'https://maker.ifttt.com/trigger/'
IFTTT_KEY = '/with/key/PRIVATE_KEY'

REMOTE_HOST = 'vechus-HP-Kubuntu.local'
PORT = 50002

def turnLed(pin, state):
    if state == True:
        GPIO.output(pin, GPIO.HIGH)
    else:
        GPIO.output(pin, GPIO.LOW)

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

# thread controlling temperature and humidity
def TH_thread(config, temp_optimal, hum_optimal):
    thsensor = si7021.si7021(1)
    
    # Memory backlog
    backlog_record = []
    # File backlog
    file = open("TH_{}.csv".format(config['room_id']),"a+", newline='', encoding = "utf-8")
    writer = csv.writer(file, dialect='excel', lineterminator='\n')
    if(file.tell() == 0):
        writer.writerow(["TIME","TEMPERATURE","HUMIDITY"])
        file.flush()
    #file.close()
    # header for API requests
    headers = {'Content-Type':'application/json'}
    # Check if token is available
    if config['token'] == '':
        config['token'] = userLogin(config['user'], config['pwd'])
    headers['token'] = config['token']
    TH_URL = URL + 'sleep/send_room_data'
    
    sys_temp_active = False
    sys_hum_active = False

    while(True):
        # Wait 30 seconds
        sleep(30)
        # Read data from sensors
        temperature = thsensor.read_temperature()
        humidity = thsensor.read_humidity()

        if sys_temp_active == False:
            if temperature < temp_optimal - 2.5:
                # Throw Low Temp -> heat up the room
                ifttt_req = requests.post(IFTTT_URL + "{LowTemp}" + IFTTT_KEY)
                sendMessageToServer("LT")
                turnLed(19, True)
                sys_temp_active = True

            if temperature > temp_optimal + 2.5:
                # Throw High Temp -> cool down the room
                ifttt_req = requests.post(IFTTT_URL + "{HighTemp}" + IFTTT_KEY)
                sendMessageToServer("HT")
                turnLed(19, True)
                sys_temp_active = True

        else:
            if temp_optimal - 1.5 < temperature < temp_optimal + 1.5:
                # Back to normal -> Shut down temp activity
                ifttt_req = requests.post(IFTTT_URL + "{ShutTemp}" + IFTTT_KEY)
                sendMessageToServer("TO")
                turnLed(19, False)
                sys_temp_active = False

        if sys_hum_active == False:
            if humidity < hum_optimal - 20:
                # Throw Low Humidity -> humidify the room
                ifttt_req = requests.post(IFTTT_URL + "{LowHumidity}" + IFTTT_KEY)
                sendMessageToServer("LH")
                turnLed(26, True)
                GPIO.output(26, GPIO.HIGH)
                sys_hum_active = True
            
            if humidity > hum_optimal + 20:
                # Throw High Humidity -> dehumidify the room
                ifttt_req = requests.post(IFTTT_URL + "{HighHumidity}" + IFTTT_KEY)
                sendMessageToServer("HH")
                turnLed(26, True)
                GPIO.output(26, GPIO.HIGH)
                sys_hum_active = False

        else:
            if hum_optimal - 20 < humidity < hum_optimal + 20:
                # Back to normal -> shut down humidity activity
                ifttt_req = requests.post(IFTTT_URL + "{ShutHumidity}" + IFTTT_KEY)
                sendMessageToServer("HO")
                turnLed(26, False)
                GPIO.output(26, GPIO.LOW)
                sys_hum_active = False
        
        ### IFTTT request
        # iftttreq = requests.post(url=IFTTT_URL + IFTTT_EVENT + IFTTT_KEY, data={'temperature': temperature, 'humidity': humidity})
        # print("****IFTTT REQUEST STATUS: " + iftttreq.status_code + " \n Temperature = " + temperature + " \n Humidity = " + humidity + "****")
        
        
        # Assemble data
        timestamp = udatetime.to_string(udatetime.now())
        data = {}
        # Check if token is available
        if config['token'] == '':
            config['token'] = userLogin(config['user'], config['pwd'])
        data['token'] = config['token']
        data['input'] = {'room_id': config['room_id'], 'timestamp': timestamp, 'temperature': json.dumps(temperature), 'humidity': json.dumps(humidity)} 
        
        # Il file csv per ora lo lasciamo fuori quindi viene fatto indipendentemente dalla connessione o meno
        #file = open("TH.csv","a", encoding = "utf-8")
        #writer = csv.writer(file)
        writer.writerow([timestamp,temperature,humidity])
        file.flush()
        #file.close()
        #file = open("TH.csv","r+", encoding = "utf-8")
        #file.read()

        # Send data to server
        try:
            print("Sending T {0:2.5} H {1:2.5} at time {2:}".format(temperature, humidity, timestamp))
            req = requests.post(url=TH_URL, headers=headers, json=data)

            # Check request result
            if req.status_code != 200:
                print("Req status {}:saving TH record on backlog".format(req.status_code))
                backlog_record.append(data)
            else:
                while len(backlog_record) > 0 and requests.post(url=TH_URL, headers=headers, json=backlog_record[0]).status_code == 200:
                    del backlog_record[0]
        except requests.exceptions.ConnectionError:
            print("Connection refused: saving TH record on backlog")
            backlog_record.append(data)
        except KeyboardInterrupt:
            file.close()
            break

def sgp_calibrate(sgp):
    print("Init baseline and store it")
    sgp.iaq_init()
    # Warm up IAQ
    for _ in range(20):
        sleep(1)
        sgp.iaq_measure()
    baseline = sgp.get_iaq_baseline()
    print("baseline {}".format(baseline))
    with open("sgpbaseline.txt", "w") as base:
        json.dump(baseline, base)
        base.close()

# Thread controlling CO2 readings
def carbon_thread(config, co2_optimal):
    # Memory backlog
    backlog_record = []
    # File backlog
    file = open("CARB_{}.csv".format(config['room_id']),"a+", newline='', encoding = "utf-8")
    writer = csv.writer(file, dialect='excel', lineterminator='\n')
    if(file.tell() == 0):
        writer.writerow(["TIME","CO2"])
        file.flush()
    #file.close()

    # header for API requests
    headers = {'Content-Type':'application/json'}
    # Check if token is available
    if config['token'] == '':
        config['token'] = userLogin(config['user'], config['pwd'])
    headers['token'] = config['token']
    CO_URL = URL + 'sleep/send_room_data'
    # Setup GPIO switch for sensor reset
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(20, GPIO.IN)

    
    
    #with SMBusWrapper(1) as bus:

    i2c_bus = busio.I2C(board.SCL, board.SDA, frequency=100000)
    sgp = sgp30(i2c_bus) #Sgp30(bus, baseline_filename = "sgpbaseline.txt")
    if(GPIO.input(20) == 1):
        sgp_calibrate(sgp)
    else:
        with open("sgpbaseline.txt", "r") as base:
            baseline = json.load(base)
            base.close()
        print("get baseline from file")
        sgp.set_iaq_baseline(baseline[0], baseline[1])
    
    #sgp.read_measurements()
    sgp.iaq_measure()
    # Warm up the sensor
    for _ in range(20):
        sleep(1)
        #sgp.read_measurements()
        sgp.iaq_measure()

    IFTTT_EVENT = '{HighCarbon}'

    sys_carbon_active = False

    while(True):
        # Wait 1 second to keep sensor active
        for _ in range(30):
            sleep(1)
            # Read data from sensors
            co2, _ = sgp.iaq_measure() #read_measurements()
            #co2 = getattr(co2, "data")[0]
        # Assemble data
        timestamp = udatetime.to_string(udatetime.now())

        # Recalibrate sensor if necessary
        tnow = datetime.now()
        tset = [datetime(tnow.year,tnow.month,tnow.day,hour=11,minute=58), datetime(tnow.year,tnow.month,tnow.day,hour=12,minute=2)]
        if((tnow>tset[0]) & (tnow>tset[1])):
            sgp_calibrate(sgp)
        
        #File csv
        #file = open("CO2.csv","a", encoding = "utf-8")
        #writer = csv.writer(file)
        writer.writerow([timestamp,co2])
        file.flush()
        #file.close()
        #file = open("CO2.csv","r+", encoding = "utf-8")
        #file.read()

        data = {}
        # Check if token is available
        if config['token'] == '':
            config['token'] = userLogin(config['user'], config['pwd'])
        data['token'] = config['token']
        data['input'] = {'room_id': config['room_id'], 'timestamp': timestamp, 'co2': json.dumps(co2)} 

        if sys_carbon_active == False:
            if co2 > co2_optimal + 1500:
                # Throw high co2 -> ventilate the room
                ifttt_req = requests.post(IFTTT_URL +IFTTT_EVENT+ IFTTT_KEY)
                sendMessageToServer("HC")
                sys_carbon_active = True
        
        else:
            if co2 < co2_optimal:
                # Back to normal -> shutdown carbon control
                sys_carbon_active = False
                ifttt_req = requests.post(IFTTT_URL + "{ShutCarbon}" + IFTTT_KEY)
                sendMessageToServer("CO")

        ### IFTTT REQUEST
        # iftttreq = requests.post(url=IFTTT_URL + IFTTT_EVENT + IFTTT_KEY, data={'CO2': json.dumps(co2)})
        # print("****IFTTT REQUEST STATUS: " + iftttreq.status_code + "\n CO2: " + co2 + "****")

        # Send data to server
        try:
            print("Sending CO2 {0:} at time {1:}".format(co2, timestamp))
            req = requests.post(url=CO_URL, headers=headers, json=data)

            # Check request result
            if req.status_code != 200:
                print("Req status {}:saving CO2 record on backlog".format(req.status_code))
                backlog_record.append(data)
            else:
                while len(backlog_record) > 0 and requests.post(url=CO_URL, headers=headers, json=backlog_record[0]).status_code == 200:
                    del backlog_record[0]
        except requests.exceptions.ConnectionError:
            print("Connection refused: saving CO2 record on backlog")
            backlog_record.append(data)
        except KeyboardInterrupt:
            file.close()
            break

# Thread to read from TSL sensor ATTENTION SENSOR NEED ADDITONAL FRONTEND TO READ DATA CORRECTLY
def light_thread(config):
    # Memory backlog
    backlog_record = []
    # File backlog
    file = open("LHT_{}.csv".format(config['room_id']),"a+", newline='', encoding = "utf-8")
    writer = csv.writer(file, dialect='excel', lineterminator='\n')
    if(file.tell() == 0):
        writer.writerow(["TIME","LIGHT"])
        file.flush()
    #file.close()

    IFTTT_EVENT = '{getLight}'

    # header for API requests
    headers = {'Content-Type':'application/json'}
    # Check if token is available
    if config['token'] == '':
        config['token'] = userLogin(config['user'], config['pwd'])
    headers['token'] = config['token']
    LH_URL = URL + 'sleep/send_room_data'
   
    # create the spi bus
    spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
    #create the chip select
    cs = digitalio.DigitalInOut(board.D5)
    mcp = MCP.MCP3008(spi, cs)
    #create an analog input channel on pin 0
    #chan = AnalogIn(mcp, MCP.P1)
    sensore = GA1A12S202(mcp)
    while(True):
        # Come misura della luce prenderei la stessa che aveva usato nel vecchio main che una media di quelle
        # ottenute in 30 secondi (fa 60 prove con uno sleep di 0.5) 
        light = 0.0
        for _ in range(60):
            light = light + sensore.read_light()
            sleep(0.5)
        light = light / 60.0
       

        ### IFTTT request
        iftttreq = requests.post(url=IFTTT_URL + IFTTT_EVENT + IFTTT_KEY, data={'value1': light})
        # print("****IFTTT REQUEST STATUS: " + iftttreq.status_code + "\n Light = " + light + "****")


        # Assemble data
        timestamp = udatetime.to_string(udatetime.now())
        # Csv file
        #file = open("light.csv","a", encoding = "utf-8")
        #writer = csv.writer(file)
        writer.writerow([timestamp,light])
        file.flush()
        #file.close()
        #file = open("light.csv","r+", encoding = "utf-8")
        #file.read()
        data = {}
        # Check if token is available
        if config['token'] == '':
            config['token'] = userLogin(config['user'], config['pwd'])
        data['token'] = config['token']
        data['input'] = {'room_id': config['room_id'], 'timestamp': timestamp, 'light': json.dumps(light)} 
        # Send data to server
        try:
            print("Sending LHT {0:4.5} at time {1:}".format(light, timestamp))
            req = requests.post(url=LH_URL, headers=headers, json=data)

            # Check request result
            if req.status_code != 200:
                print("Req status {}:saving LIGHT record on backlog".format(req.status_code))
                backlog_record.append(data)
            else:
                while len(backlog_record) > 0 and requests.post(url=LH_URL, headers=headers, json=backlog_record[0]).status_code == 200:
                    del backlog_record[0]
        except requests.exceptions.ConnectionError:
            print("Connection refused: saving LIGHT record on backlog")
            backlog_record.append(data)
        except KeyboardInterrupt:
            file.close()
            break

# Thread TEMPORARY to read noise from ADC. it sends energy on 30 seconds
def noise_thread(config):
    # Memory backlog
    backlog_record = []
    # File backlog
    file = open("NOI_{}.csv".format(config['room_id']),"a+", newline='', encoding = "utf-8")
    writer = csv.writer(file, dialect='excel', lineterminator='\n')
    if(file.tell() == 0):
        writer.writerow(["TIME","NOISE"])
        file.flush()
    #file.close()

    # header for API requests
    headers = {'Content-Type':'application/json'}
    # Check if token is available
    if config['token'] == '':
        config['token'] = userLogin(config['user'], config['pwd'])
    headers['token'] = config['token']
    NOI_URL = URL + 'sleep/send_room_data'
   
    # Init sensor
    #create the spi  bus
    spi_n = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
    #create the chip select
    cs_n = digitalio.DigitalInOut(board.D5)# non sappiamo a quale board collegarlo
    cs_n.direction = digitalio.Direction.OUTPUT
    cs_n.value = True
    #create mcp object
    mcp_n = MCP.MCP3008(spi_n, cs_n)
    #create an analog input channel
    #chan_n = AnalogIn(mcp_n, MCP.P0)#non sapppiamo a che pin collegato
    sensore_n = SPW2430(mcp_n)


    while(True):
        # Wait 30 seconds
        #sleep(30)
        noise = 0
        counter = 0
        tStart = perf_counter()
        while(perf_counter() < (tStart + 30)):
            noise = noise + sensore_n.read_noise()
            counter = counter + 1
        noise = noise / counter

        # Assemble data
        timestamp = udatetime.to_string(udatetime.now())
        # saving data inside the csv file
        #file = open("noise.csv","a", encoding = "utf-8")
        #writer = csv.writer(file)
        writer.writerow([timestamp,noise])
        file.flush()
        #file.close()
        #file = open("noise.csv","r+", encoding = "utf-8")
        #file.read() 
        
        data = {}
        # Check if token is available
        if config['token'] == '':
            config['token'] = userLogin(config['user'], config['pwd'])
        data['input'] = {'room_id': config['room_id'], 'timestamp': timestamp, 'noise': json.dumps(noise)} 
        data['token'] = config['token']
        # Send data to server
        try:
            print("Sending NOI {0:4.5} at time {1:}".format(noise, timestamp))
            req = requests.post(url=NOI_URL, headers=headers, json=data)

            # Check request result
            if req.status_code != 200:
                print("Req status {}:saving NOISE record on backlog".format(req.status_code))
                backlog_record.append(data)
            else:
                while len(backlog_record) > 0 and requests.post(url=NOI_URL, headers=headers, json=backlog_record[0]).status_code == 200:
                    del backlog_record[0]
        except requests.exceptions.ConnectionError:
            print("Connection refused: saving NOISE record on backlog")
            backlog_record.append(data)
        except KeyboardInterrupt:
            file.close()
            break

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

def getSensorAssociation(config):
    headers = {'Content-Type': 'application/json'}
    headers['authorization'] = config['token']
    S_URL = URL + 'talk/get_sensor_association'

    config['polar_id'] = {}
    for user_id in config['user_id']:
        req = requests.get(url=S_URL, headers=headers, params = {'user_id': user_id})
        if(req.status_code == 200):
            print(req.content)
            data = json.loads(str(req.content, 'utf-8'))[0]
            print(data)
            config['polar_id'][data['sensor_id']] = data['user_id']


# Main routine                       
if __name__ == "__main__":
    # Load GPIOs
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(26, GPIO.OUT)
    GPIO.setup(19, GPIO.OUT)
    GPIO.output(19, GPIO.HIGH)
    GPIO.output(26, GPIO.HIGH)
    sleep(2)
    GPIO.output(19, GPIO.LOW)
    GPIO.output(26, GPIO.LOW)

    # Load Configuration JSON
    with open("config.json", "r") as configFile:
        config = json.load(configFile)

    config['token'] = userLogin(config["user"], config["pwd"])
    #getSensorAssociation(config)
    #print(config)

    ### Get good limits from server:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((REMOTE_HOST, PORT))
        print("Connected")
        s.sendall(b'SEND MEMES')
        print("Request boot sent")
        s.settimeout(2)
        serverMessage = []
        for i in range(3):
            serverMessage.append(s.recv(10219).decode("utf-8"))

        s.close()
    print('Received {0:} {1:} {2:}'.format(serverMessage[0], serverMessage[1], serverMessage[2]))

    temp_optimal = int(serverMessage[0])
    hum_optimal = int(serverMessage[1])
    co2_optimal = int(serverMessage[2])

    # Start temperature and humidity thread
    t1 = threading.Thread(target = TH_thread, args=(config,temp_optimal,hum_optimal), name="TempHumi")

    # Start CO2 thread
    t2 = threading.Thread(target = carbon_thread, args=(config,co2_optimal), name="CO2")

    # Start Light thread
    t3 = threading.Thread(target = light_thread, args=(config,), name="LIGHT")

    # Start noise thread
    t4 = threading.Thread(target = noise_thread, args=(config,), name="NOISE")

    # Start Polar thread
    #scanner = polar_ncamp.PolarScanner()
    #t5 = threading.Thread(target = scanner.start, args=(config,), name = "POLAR") 

    t1.start()
    sleep(0.5)
    t2.start()
    sleep(0.5)
    t3.start()
    sleep(0.5)
    t4.start()
    sleep(0.5)
    #t5.start()

