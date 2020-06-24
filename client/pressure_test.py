"""
This is the client side of PyChat
This is the sender part of the client
"""

import datetime
import json
import multiprocessing
import socket
import time

try:
    from mylibs import *
except ImportError:
    from .mylibs import *

DEFAULT_PORT = 233
CLIENT_CREDENTIAL_FILE = 'credential.json'


def sender_start(start_receiver=False, auto_exit=False):
    s = socket.socket()
    host = socket.gethostname()
    port = DEFAULT_PORT
    rx_port = port + 1
    print('Connecting to ' + host + ':' + str(port))
    use_nickname = False
    nickname = ''

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
        # Get credential from the server
        client_credential_recv = s.recv(2048).decode()
        client_credential = client_credential_recv.split(',')
        '''
        new_data = {'server': host, 'port': port, 'id': client_credential[0], 'code': client_credential[1]}
        with open(CLIENT_CREDENTIAL_FILE, 'w') as dump_file:
            json.dump(new_data, dump_file)
        print('Please save credential below to authenticate receiver...')
        print('ID:')
        print(client_credential[0])
        print('Access Code:')
        print(client_credential[1])
        '''
        if start_receiver:
            receiver_m = multiprocessing.Process(target=receiver_start, args=(client_credential[0], client_credential[1]))
            receiver_m.daemon = True
            receiver_m.start()

    except ConnectionRefusedError:
        print('Unable to connect ' + "'" + host + "'.")
        exit()

    # Create a loop to send messages to the server
    if auto_exit:
        s.close()
        exit()
    while True:
        try:
            send_data = str(datetime.datetime.now())
            time.sleep(100)
            if send_data == '':
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


def receiver_start(credential_id, credential_code):
    s = socket.socket()
    # Try to load credential from cache
    host = socket.gethostname()
    port = DEFAULT_PORT
    rx_port = port + 1
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


if __name__ == "__main__":
    for i in range(1, 10000):
        print(i)
        sender_m = multiprocessing.Process(target=sender_start, args=(False, True,))
        # sender_m.daemon = True
        sender_m.start()
        time.sleep(0.5)
    input()
