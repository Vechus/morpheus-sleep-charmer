import socket
import time
import threading

HOST = ''                 # Symbolic name meaning all available interfaces
PORT = 50002              # Arbitrary non-privileged port

temp_optimal = '25'
hum_optimal = '50'
co2_optimal = '700'

def newConnection(socket, addr):
    while(True):
        try:
            data = conn.recv(1024)
            if not data: break
            print(data.decode("utf-8"))
            if data.decode("utf-8") == 'SEND MEMES':
                conn.sendall(temp_optimal.encode('ascii'))
                time.sleep(1)
                conn.sendall(hum_optimal.encode('ascii'))
                time.sleep(1)
                conn.sendall(co2_optimal.encode('ascii'))
            if data.decode("utf-8") == 'LT':
                # Low Temperature
                print("LT")
                conn.sendall("ok".encode('ascii'))
            if data.decode("utf-8") == 'HT':
                # High Temperature
                print("HT")
                conn.sendall("ok".encode('ascii'))
            if data.decode("utf-8") == 'LH':
                # Low Humidity
                print("LH")
                conn.sendall("ok".encode('ascii'))
            if data.decode("utf-8") == 'HH':
                # High Humidity
                print("HH")
                conn.sendall("ok".encode('ascii'))
            if data.decode("utf-8") == 'HC':
                # High Carbon
                print("HC")
                conn.sendall("ok".encode('ascii'))
            if data.decode("utf-8") == 'TO':
                # High Carbon
                print("TO")
                conn.sendall("ok".encode('ascii'))
            if data.decode("utf-8") == 'HO':
                # High Carbon
                print("HO")
                conn.sendall("ok".encode('ascii'))
            if data.decode("utf-8") == 'CO':
                # High Carbon
                print("CO")
                conn.sendall("ok".encode('ascii'))

        except socket.timeout:
            print("Timeout con " + addr + ", STACCA STACCA STACCAAAHAHHHAAHH")

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen(1)
    while(True):
        conn, addr = s.accept()
        t = threading.Thread(target=newConnection, args=(conn,addr), name="Thread")
        t.start()
    #Note it's (addr,) not (addr) because second parameter is a tuple
    #Edit: (c,addr)
    #that's how you pass arguments to functions when creating new threads using thread module.
    s.close()