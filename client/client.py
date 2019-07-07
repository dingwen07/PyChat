"""
This is the client side of PyChat
This is the sender part of the client
"""

import socket
import json

DEFAULT_PORT = 233
clientCredentialFile = 'credential.json'


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
    if answer == 'Y' or answer == 'y':
        return 1
    else:
        return 0


# Ask the user about the server they need to connect to
s = socket.socket()
host = input('Input server name: ')
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
    clientCredential_recv = s.recv(2048).decode()
    clientCredential = clientCredential_recv.split(',')
    new_data = {'id': clientCredential[0], 'code': clientCredential[1]}
    # Dump credential to local cache file
    with open(clientCredentialFile, 'w') as dump_f:
        json.dump(new_data, dump_f)
    print('Please save credential below to authenticate receiver...')
    print('ID:')
    print(clientCredential[0])
    print('Access Code:')
    print(clientCredential[1])

except ConnectionRefusedError:
    print('Unable to connect ' + "'" + host + "'.")
    exit()

print('')
# Create a loop to send messages to the server
while True:
    try:
        send_data = input(">>>")
        send_fmt = send_data.lower()
        if send_data == '':
            continue
        elif send_fmt[0] == '#' and send_fmt[1] != '#':
            send_fmt2 = send_fmt[1:]
            if send_fmt2 == 'exit':
                if confirm('Exit client') == 1:
                    s.send('##EXIT'.encode())
                    s.close()
                    break
                else:
                    print('CLIENT: Operation canceled.')
                    print()
                    continue
            elif send_fmt2 == 'recv':
                print(s.recv(4096).decode())
                print()
            else:
                print('CLIENT: COMMAND NOT FOUND')
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

    except ConnectionResetError:
        print('Server disconnected.')
        s.close()
        break
