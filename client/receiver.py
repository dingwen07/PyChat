"""
This is the client side of PyChat
This is the receiver part of the client
"""

import sys
import socket
import json

try:
    from mylibs import *
except ImportError:
    from .mylibs import *


DEFAULT_PORT = 233
CLIENT_CREDENTIAL_FILE = 'credential.json'

client_info = {
    'host': socket.gethostname(),
    'appid': 1
}

s = socket.socket()

# Try to load credential from cache
client_id = ''
credential_code = ''
try:
    with open(CLIENT_CREDENTIAL_FILE, 'r') as load_f:
        load_credential = json.load(load_f)
    host = load_credential['server']
    port = load_credential['port']
    client_id = load_credential['id']
    credential_code = load_credential['code']
except:
    pass
finally:
    # If a cached credential found, ask if user want use it
    if client_id == '' or not confirm('Use cached credential', True):
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
        client_id = int(input('ID: '))
        credential_code = input('Access Code: ')
    rx_port = port + 1

print()

# Send credential to server
try:
    s.connect((host, rx_port))
    server_data = json.loads(s.recv(1024).decode())
    client_info['id'] = client_id
    client_info['code'] = credential_code
    s.send(json.dumps(client_info).encode())
    if server_data['appid'] != client_info['appid']:
        print('Not a PyChat Server!')
        exit()
except ConnectionRefusedError:
    print('Unable to connect ' + "'" + host + "'.")
    exit()

# Create a loop to continuously receive messages from the server
while True:
    try:
        rx_header_byte = s.recv(1024).decode()
        echo_header = json.loads(rx_header_byte)
        s.send(str(len(echo_header)).encode())
        rx_data = s.recv(echo_header['size']).decode()
        if rx_data == '':
            s.send('RX ACTIVE'.encode())
            continue
        print(rx_data)
    except (BrokenPipeError, ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError):
        print('Server disconnected.')
        s.close()
        break
    except Exception as e:
        print(e)
        break
