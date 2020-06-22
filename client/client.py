"""
This is the client side of PyChat
This is the sender part of the client
"""

import sys
import socket
import json

sys.path.append("client/")
from mylibs import *

DEFAULT_PORT = 233
CLIENT_CREDENTIAL_FILE = 'credential.json'

# Ask the user about the server they need to connect to
s = socket.socket()
host = input('Input server name: ').strip()
if host == '':
    print('Use localhost...')
    host = socket.gethostname()
print('Connecting to ', host)
port = input('Input port: ')
if port == '':
    print('Use default port...')
    port = DEFAULT_PORT
else:
    port = int(port)
rx_port = port + 1
print('Connecting to ' + host + ':' + str(port))
use_nickname = False
nickname = ''
if confirm('Use a nickname.') == 1:
    nickname = input('Input your nickname: ')
    use_nickname = True

# Try to connect to the server
try:
    s.connect((host, port))
    nkr = s.recv(1024).decode()
    if nkr == 'NICK':
        if use_nickname:
            s.send('NICK_ON'.encode())
            s.send(nickname.encode())
        else:
            s.send('NICK_OFF'.encode())
    print('')
    # Get credential from the server
    client_credential_recv = s.recv(2048).decode()
    client_credential = client_credential_recv.split(',')
    new_data = {'server': host, 'port': port, 'id': client_credential[0], 'code': client_credential[1]}
    # Dump credential to local cache file
    with open(CLIENT_CREDENTIAL_FILE, 'w') as dump_file:
        json.dump(new_data, dump_file)
    print('Please save credential below to authenticate receiver...')
    print('ID:')
    print(client_credential[0])
    print('Access Code:')
    print(client_credential[1])

except ConnectionRefusedError:
    print('Unable to connect ' + "'" + host + "'.")
    exit()

print('')
# Create a loop to send messages to the server
while True:
    try:
        send_data = input(">>>")
        if send_data == '':
            continue
        elif len(send_data) > 1 and send_data[0] == '#' and send_data[1] != '#':
            send_fmt = send_data[1:].lower()
            if send_fmt == 'exit':
                if confirm('Exit client') == 1:
                    s.send('##EXIT'.encode())
                    s.close()
                    break
                else:
                    print('CLIENT: Operation canceled.')
                    print()
                    continue
            elif send_fmt == 'recv':
                print(s.recv(4096).decode())
                print()
            else:
                print('CLIENT: INVALID COMMAND')
                print()
                continue
        s.send(send_data.encode())
        reply = s.recv(4096).decode()
        '''
        If the message returned from the server does not match the one sent,
         print the message returned by the server.
        '''
        if reply != send_data:
            print(reply)
            print()

    except (BrokenPipeError, ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError):
        print('Server disconnected.')
        s.close()
        break
