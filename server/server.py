"""
This is the server side of PyChat

Requirements: {
    root user privilege (Linux)
    python3
    directory: ./credentials
    files: 
        ./config.json
            example: 
                {
                    "Port": 233,
                    "Auth": false,
                    "AllowNickname": true,
                    "MessageLogFile": "./message-log.json",
                    "CredentialFolder": "./credentials/",
                    "WelcomeMessage": "Welcome to PyChat Server!"
                }
        ./message-log.json
            example: 
                {"Message": []}
}

Run:
    python3 server.py
"""

import datetime
import hashlib
import json
import multiprocessing
import os
import random
import socket
import time

CONFIG_FILE = './config.json'
HOST = socket.gethostname()

# Detect and create default config file
if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, 'w') as dump_file:
        dump_data = {
            "Port": 233,
            "Auth": False,
            "AllowNickname": True,
            "MessageLogFile": "./message-log.json",
            "CredentialFolder": "./credentials/",
            "WelcomeMessage": "Welcome to PyChat Server!"
        }
        json.dump(dump_data, dump_file)
# Load config from file
with open(CONFIG_FILE, 'r') as load_file:
    load_conf = json.load(load_file)
port = load_conf["Port"]
rx_port = port + 1
AllowNickname = load_conf["AllowNickname"]
MessageLogFile = load_conf["MessageLogFile"]
CredentialFolder = load_conf["CredentialFolder"]
WelcomeMessage = load_conf["WelcomeMessage"]
# Detect and create default message log file and credential folder
if not os.path.exists(MessageLogFile):
    with open(MessageLogFile, 'w') as dump_file:
        dump_data = {"Message": []}
        json.dump(dump_data, dump_file)
if not os.path.exists(CredentialFolder):
    os.makedirs(CredentialFolder)

def sender_main(cnn, addr):
    """sender communication

    This method is used to communicate with the sender (client)
    
    Args:
        cnn: socket object, for socket communication
        addr: tuple, store the client address

    Returns:
        Method returns an integer

        Normal exit returns 0
    """

    message_counter = 0
    client_address = str(addr)
    nickname = ''
    print(client_address + ' Connected')

    # Receive  nickname from the client
    use_nickname = False
    if load_conf["AllowNickname"]:
        cnn.send('NICK'.encode())
        request = cnn.recv(1024).decode()
        if request == 'NICK_ON':
            use_nickname = True
            print(client_address + ' Nickname status=' + str(use_nickname))
            nickname = cnn.recv(1024).decode()
            print(client_address + ' Nickname=' + str(nickname))
        else:
            print(client_address + ' Nickname status=' + str(use_nickname))
    else:
        cnn.send('NICK_REJECTED'.encode())

    # Generate a credential to authenticate the receiver
    client_id = hashlib.sha256(client_address.encode()).hexdigest()
    client_credential_pre = str(datetime.datetime.now()) + client_address + str(random.randint(100000, 655360))
    client_credential = hashlib.sha512(client_credential_pre.encode()).hexdigest()
    client_credential_send = client_id + ',' + client_credential
    print(client_address + ' ' + str(client_credential_send.split(',')))
    # Send the credential to the sender
    cnn.send(client_credential_send.encode())
    # Dump the credential to local file
    dump_data = {
        'id': client_id,
        'address': addr,
        'name': nickname,
        'code': client_credential,
        'valid': True
    }
    with open(CredentialFolder + client_id + ".json", 'w') as dump_file:
        json.dump(dump_data, dump_file)

    # Create a loop to receive and process messages
    while True:
        try:
            # Receive message
            request = cnn.recv(4096).decode()

            # Generate message ID
            message_time = str(datetime.datetime.now())
            message_counter = message_counter + 1
            message_content = request
            message_id_pre = message_time + client_address + str(message_counter) + message_content
            message_id = hashlib.sha256(message_id_pre.encode()).hexdigest()

            # Validate credentials
            try:
                with open(CredentialFolder + client_id + ".json", 'r') as load_file:
                    load_credential = json.load(load_file)
                if not (load_credential['valid']):
                    print(str(addr) + ' Rejected (Invalid Credential)')
                    cnn.send('Invalid Credential'.encode())
                    cnn.close()
                    return 1
            except:
                print(str(addr) + ' Rejected (Invalid Credential)')
                cnn.send('##Invalid Credential'.encode())
                cnn.close()
                return 1

            # Detect if the received message is an instruction to the server
            if len(request.strip()) > 2:
                if request[0:2] == '##' and request[2] != '#':
                    # Session command
                    request_cmd_session_fmt = request.lower()[2:].strip()
                    if request_cmd_session_fmt == 'exit':
                        print(client_address + ' Disconnected')
                        with open(CredentialFolder + client_id + ".json", 'r') as load_file:
                            load_credential = json.load(load_file)
                        load_credential['valid'] = False
                        with open(CredentialFolder + client_id + ".json", 'w') as dump_file:
                            json.dump(load_credential, dump_file)
                        cnn.close()
                        return 0
                    elif request_cmd_session_fmt == 'welcome':
                        cnn.send(WelcomeMessage.encode())
                    elif request_cmd_session_fmt[0:4] == 'nick' and request_cmd_session_fmt[4] == ' ':
                        if request_cmd_session_fmt[5:] == 'get':
                            if use_nickname:
                                cnn.send(nickname.encode())
                            else:
                                cnn.send('NICKNAME NOT SET'.encode())
                        elif request_cmd_session_fmt[5:8] == 'set' and len(request_cmd_session_fmt) > 9:
                            use_nickname = True
                            nickname = request_cmd_session_fmt[9:]()
                            cnn.send('NICKNAME SET'.encode())
                        else:
                            cnn.send('INVALID COMMAND'.encode())
                    else:
                        cnn.send('INVALID COMMAND'.encode())
                    continue
                elif len(request.strip()) > 3 and request[0:3] == '###':
                    # Server command
                    request_cmd_server_fmt = request.lower()[3:].strip()
                    print('SERVER COMMAND')
                    if request_cmd_server_fmt == 'exit':
                        os._exit(0)
                    elif request_cmd_server_fmt[0:4] == 'kick' and len(request_cmd_server_fmt) > 4 and \
                            request_cmd_server_fmt[4] == ' ':
                        target_client_id = request_cmd_server_fmt[5:]
                        print(target_client_id)
                        try:
                            with open(CredentialFolder + target_client_id + ".json", 'r') as load_file:
                                load_target_credential = json.load(load_file)
                            load_target_credential['valid'] = False
                            with open(CredentialFolder + target_client_id + ".json", 'w') as dump_file:
                                json.dump(load_target_credential, dump_file)
                            cnn.send('KICKED'.encode())
                        except Exception:
                            cnn.send('CLIENT NOT FOUND'.encode())
                    elif request_cmd_server_fmt[0:3] == 'get' and len(request_cmd_server_fmt) > 3 and \
                            request_cmd_server_fmt[3] == ' ':
                        if request_cmd_server_fmt[4:6] == 'id' and len(request_cmd_server_fmt) > 7 and \
                                request_cmd_server_fmt[6] == ' ':
                            target_name = request_cmd_server_fmt[7:]
                            target_list = []
                            credential_path = './credentials'
                            credential_files = os.listdir(credential_path)
                            for file_name in credential_files:
                                if not os.path.isdir(file_name):
                                    with open(CredentialFolder + file_name, 'r') as load_file:
                                        load_credential = json.load(load_file)
                                    if (target_name == '*' or target_name == load_credential['code'] or target_name ==
                                        load_credential['address'][0] or target_name == str(
                                                    load_credential['address'][1]) or target_name in load_credential[
                                            'name'].lower()) and load_credential['valid']:
                                        target_list.append([load_credential['id'],
                                                            (load_credential['address'][0],
                                                             load_credential['address'][1]),
                                                            load_credential['name']])
                            cnn.send(str(target_list).encode())
                        else:
                            cnn.send('INVALID COMMAND'.encode())
                    else:
                        cnn.send('INVALID COMMAND'.encode())
                    continue

            '''
            If the client is disconnected, the server may receive an empty message indefinitely.
            If an empty message is received, a message is sent to the client receiver to confirm if that client is still alive.
            '''
            if request == '':
                time.sleep(0.5)
                cnn.send('ACTIVE'.encode())
                continue

            print(client_address + ': ' + request)

            # The received message is returned to the client receiver to help the client confirm that the message has
            # been delivered. 
            cnn.send(request.encode())

            # Determine the value of "client_name" depending on whether a nickname is used
            if use_nickname:
                client_name = nickname
            else:
                client_name = client_address

            '''
            Dump the message to a local temporary file.
            Let the process responsible for communicating with the client receiver read.
            '''
            with open("./temp.json", 'w') as dump_file:
                dump_data = {
                    "message_id": message_id,
                    "message_time": message_time,
                    "client_id": client_id,
                    "client_address": addr,
                    "client_name": client_name,
                    "message_content": message_content
                }
                json.dump(dump_data, dump_file)

            # Dump the message to log file
            messageInList = [message_id, message_time, client_id, addr, client_name, message_content]
            with open(MessageLogFile, 'r') as load_file:
                load_log = json.load(load_file)
            dump_log = load_log
            dump_log["Message"].append(messageInList)
            with open(MessageLogFile, 'w') as dump_file:
                json.dump(dump_log, dump_file)

        except (BrokenPipeError, ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError):
            print(client_address + ' Disconnected (Unexpected)')
            with open(CredentialFolder + client_id + ".json", 'r') as load_file:
                load_credential = json.load(load_file)
            load_credential['valid'] = False
            with open(CredentialFolder + client_id + ".json", 'w') as dump_file:
                json.dump(load_credential, dump_file)
            cnn.close()
            return 0
        except Exception as e:
            print(e)
            continue


def receiver_launcher():
    """receiver launcher

    This method is used to create a child process that communicates with the receiver (client)
    """

    rxs = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    rxs.bind((HOST, rx_port))
    rxs.listen(5)

    while True:
        try:
            # Listening port, waiting for connection (for receivers)
            rxcnn, addr = rxs.accept()
            m = multiprocessing.Process(target=receiver_main, args=(
                rxcnn,
                addr,
            ))
            # Enable daemon
            m.daemon = True
            # Initiate a subprocess
            m.start()

        except (BrokenPipeError, ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError):
            pass
        except Exception as e:
            print(e)
            continue


def receiver_main(rxcnn, addr):
    """receiver communication

    This method is used to communicate with the receiver (client)

    Args:
        rxcnn: socket object, for socket communication
        addr: tuple, store the client address

    Returns:
        Method returns an integer

        Normal exit returns 0
        Validation fails returns 1
    """

    print(str(addr) + ' RX Connected')
    # Receive credential from the client
    rxcnn.send('UNBLOCK'.encode())
    client_id = rxcnn.recv(1024).decode()
    rxcnn.send(client_id.encode())
    client_credential = rxcnn.recv(1024).decode()
    rxcnn.send(client_credential.encode())

    # Validate credentials
    try:
        with open(CredentialFolder + client_id + ".json", 'r') as load_file:
            load_credential = json.load(load_file)
        if not ((load_credential['code'] == client_credential) and load_credential['valid'] and (
                load_credential['address'][0] == addr[0])):
            print(str(addr) + ' RX Rejected (Invalid Credential)')
            rxcnn.send('Invalid Credential'.encode())
            rxcnn.close()
            return 1
    except:
        print(str(addr) + ' RX Rejected (Invalid Credential)')
        rxcnn.send('Invalid Credential'.encode())
        rxcnn.close()
        return 1

    # Send welcome message
    rxcnn.send(WelcomeMessage.encode())

    # Create a loop to send messages
    while True:
        try:
            # Wait until a new message is detected
            with open("./temp.json", 'r') as load_file:
                load_msg = json.load(load_file)
            temp_message_id = load_msg['message_id']
            message_id = temp_message_id
            while temp_message_id == message_id:
                time.sleep(0.1)
                with open("./temp.json", 'r') as load_file:
                    load_msg = json.load(load_file)
                message_id = load_msg['message_id']

            # Validate credentials
            try:
                with open(CredentialFolder + client_id + ".json", 'r') as load_file:
                    load_credential = json.load(load_file)
                if not ((load_credential['code'] == client_credential) and load_credential['valid'] and (
                        load_credential['address'][0] == addr[0])):
                    print(str(addr) + ' RX Rejected (Invalid Credential)')
                    rxcnn.send('Invalid Credential'.encode())
                    rxcnn.close()
                    return 1
            except:
                print(str(addr) + ' RX Rejected (Invalid Credential)')
                rxcnn.send('Invalid Credential'.encode())
                rxcnn.close()
                return 1

            # Send message
            messageSend = load_msg['client_name'] + ': ' + load_msg['message_content']
            rxcnn.send(messageSend.encode())
            print('Local==>' + str(addr) + ' RX Send: ' + messageSend)

        except (BrokenPipeError, ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError):
            print(str(addr) + ' RX Disconnected (Unexpected)')
            rxcnn.close()
            return 0

        except Exception as e:
            print(e)
            continue


if __name__ == '__main__':
    '''main

    This is where the program starts
    '''

    print(load_conf)

    # Invalidate all credentials
    credential_path = './credentials'
    credential_files = os.listdir(credential_path)
    for file_name in credential_files:
        if not os.path.isdir(file_name):
            with open(CredentialFolder + file_name, 'r') as load_file:
                credential = json.load(load_file)
            credential['valid'] = False
            with open(CredentialFolder + file_name, 'w') as dump_file:
                json.dump(credential, dump_file)

    # Create an object for establishing socket communication
    rxm = multiprocessing.Process(target=receiver_launcher, args=())
    rxm.start()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, port))
    s.listen(5)

    while True:
        try:
            # Listening port, waiting for connection
            cnn, addr = s.accept()
            m = multiprocessing.Process(target=sender_main, args=(
                cnn,
                addr,
            ))
            # Enable daemon
            m.daemon = True
            # Initiate a subprocess
            m.start()

        except (BrokenPipeError, ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError):
            pass
        except Exception as e:
            print(e)
            continue
