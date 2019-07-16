"""
This is the client side of PyChat
This is the receiver part of the client
"""

import sys
import socket
import json

sys.path.append("client/")
from mylibs import *

DEFAULT_PORT = 233
CLIENT_CREDENTIAL_FILE = 'credential.json'

s = socket.socket()

# Try to load credential from cache
credential_id = ''
credential_code = ''
try:
    with open(CLIENT_CREDENTIAL_FILE, 'r') as load_f:
        load_credential = json.load(load_f)
    host = load_credential['server']
    port = load_credential['port']
    credential_id = load_credential['id']
    credential_code = load_credential['code']
except:
    pass
finally:
    # If a cached credential found, ask if user want use it
    if credential_id == '' or not confirm('Use cached credential'):
        # Ask the user about the server they need to connect to
        host = input('Input server name: ').strip()
        if host == '':
            print('Use localhost...')
            host = socket.gethostname()
        port = input('Input port: ')
        if port == '':
            print('Use default port...')
            port = DEFAULT_PORT
        else:
            port = int(port)
        credential_id = input('ID: ')
        credential_code = input('Access Code: ')
    rx_port = port + 1

print()

# Send credential to server
try:
    s.connect((host, rx_port))
    s.recv(1024)
    s.send(credential_id.encode())
    s.recv(1024)
    s.send(credential_code.encode())
    s.recv(1024)
except ConnectionRefusedError:
    print('Unable to connect ' + "'" + host + "'.")
    exit()

# Create a loop to continuously receive messages from the server
while True:
    try:
        rx_data = s.recv(4096).decode()
        if rx_data == '':
            s.send('RX ACTIVE'.encode())
            continue
        print(rx_data)
    except (BrokenPipeError, ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError):
        print('Server disconnected.')
        s.close()
        break
