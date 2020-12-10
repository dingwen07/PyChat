"""
This is the client side of PyChat
This is the sender part of the client
"""

import os
import json
import socket
import time
import hashlib
import struct

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

current_milli_time = lambda: int(round(time.time() * 1000))

if not os.path.exists('./MESSAGE_DUMP/'):
    os.mkdir('./MESSAGE_DUMP')

# Ask the user about the server they need to connect to
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
use_nickname = confirm('Use a nickname')
nickname = ''
if use_nickname:
    nickname = input('Input your nickname: ')
client_info['nickname'] = nickname

# Try to connect to the server
try:
    s = socket.socket()
    s.connect((host, port))
    server_data = json.loads(s.recv(1024).decode())
    print(server_data)
    s.send(json.dumps(client_info).encode())
    if server_data['appid'] != client_info['appid']:
        print('Not a PyChat Server!')
        raise()

    client_session_data = json.loads(s.recv(1024).decode())

    try:
        if not client_session_data['success']:
            print('Server rejected connection.')
            raise()
        client_credential = client_session_data['credential']
    except Exception:
        print('Connection not successful.')
        s.close()
        input()
        exit()

    new_data = {
        'server': host, 
        'port': server_data['portrcv'] - 1, 
        'id': client_credential['id'], 
        'code': client_credential['code']}
    # Dump credential to local cache file
    with open(CLIENT_CREDENTIAL_FILE, 'w') as dump_file:
        json.dump(new_data, dump_file)
    print('Please save credential below to authenticate receiver...')
    print('ID:')
    print(client_credential['id'])
    print('Access Code:')
    print(client_credential['code'])

except Exception:
    print('Unable to connect ' + "'" + host + "'.")
    s.close()
    exit()

print('')
# Create a loop to send messages to the server
while True:
    try:
        send_data = input(">>>")
        header = {}
        header['time'] = current_milli_time()
        if send_data == '':
            continue
        elif len(send_data) > 1 and send_data[0] == '#' and send_data[1] != '#':
            send_fmt = send_data[1:].lower()
            if send_fmt == 'exit':
                if confirm('Exit client'):
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
        header['size'] = len(send_data.encode())
        header['sha256'] = hashlib.sha256(send_data.encode()).hexdigest()
        s.send(json.dumps(header).encode())
        header_size = s.recv(1024).decode()
        s.send(send_data.encode())

        # Get echo header
        echo_header_byte = s.recv(1024).decode()
        echo_header = json.loads(echo_header_byte)
        s.send(str(len(echo_header)).encode())
        reply = s.recv(echo_header['size']).decode()
        '''
        If the message returned from the server does not match the one sent,
         print the message returned by the server.
        '''
        if reply != send_data:
            if echo_header['size'] > 10240:
                message_dump_file = './MESSAGE_DUMP/MESSAGE_DUMP_' + str(echo_header['message_id']) + '_' + str(current_milli_time()) + '.txt'
                with open(message_dump_file, 'w') as dump_file:
                    dump_file.write(reply)
                print('Receved message too long, dumped to ' + message_dump_file)
            else:
                print(reply)
            print()

    except (BrokenPipeError, ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError):
        print('Server disconnected.')
        s.close()
        break
