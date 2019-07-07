"""
This is the client side of PyChat
This is the receiver part of the client
"""

import socket
import json

DEFAULT_PORT = 233
CLIENT_CREDENTIAL_FILE = 'credential.json'


def confirm(msg):
    """Get confirmation from the console

    Ask the user to confirm some operations through the console.

    Args:
        msg: String, store the message will be displayed in the console
    Returns:
        Method returns Boolean value
    """

    print(msg)
    answer = input('Do you sure? (Y/n) ')
    if answer == 'Y'or answer == 'y':
        return 1
    else:
        return 0


# Ask the user about the server they need to connect to
s = socket.socket()
host = input('Input server name: ')
if host == '':
    print('Use localhost...')
    host = socket.gethostname()
port = input('Input port: ')
if port == '':
    print('Use default port...')
    port = DEFAULT_PORT
else:
    port = int(port)
rx_port = port + 1

# Try to load credential from cache
credential_id = ''
credential_code = ''
try:
    with open(CLIENT_CREDENTIAL_FILE, 'r') as load_f:
        load_credential = json.load(load_f)
    credential_id = load_credential['id']
    credential_code = load_credential['code']
except:
    pass
finally:
    # If a cached credential found, ask if user want use it
    if credential_id != '':
        if not confirm('Use cached credential'):
            credential_id = input('ID: ')
            credential_code = input('Access Code: ')
    else:
        credential_id = input('ID: ')
        credential_code = input('Access Code: ')
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
        print(rx_data)
    except ConnectionResetError:
        print('Server disconnected.')
        s.close()
        break
