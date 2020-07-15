"""
This is the server side of PyChat

Requirements: {
    root user privilege (Linux)
    python3

    files:
        ./config.json
            example:
                {
                    "Port": 233,
                    "Auth": false,
                    "AllowAdminCommands": true,
                    "AllowNickname": true,
                    "MessageLogFile": "./message-log.json",
                    "CredentialFolder": "./credentials/",
                    "WelcomeMessage": "Welcome to PyChat Server!"
                }
}

Run:
    python3 server.py
"""


import hashlib
import json
import multiprocessing
import os
import random
import socket
import sqlite3
import time

try:
    from holder import Holder
except ImportError:
    from .holder import Holder

CONFIG_FILE = './config.json'
DATABASE_FILE = './server.db'
HOST = socket.gethostname()

current_milli_time = lambda: int(round(time.time() * 1000))

# Detect db
if not os.path.exists(DATABASE_FILE):
    print('Creating database...')
    db = sqlite3.connect(DATABASE_FILE)
    db_cursor = db.cursor()
    db_cursor.execute('''CREATE TABLE "clients" (
                            "id"	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                            "address"	TEXT,
                            "name"	TEXT,
                            "code"	TEXT,
                            "valid"	INTEGER,
                            "meta"	TEXT
                            );''')
    db_cursor.execute('''CREATE TABLE "messages" (
                            "id"	INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                            "client"	INTEGER NOT NULL,
                            "time"  INTEGER NOT NULL,
                            "content"	TEXT,
                            "meta"	TEXT,
                            FOREIGN KEY("client") REFERENCES "clients"("id")
                            );''')
    db_cursor.execute('''CREATE TABLE "rules" (
                            "id"	INTEGER NOT NULL UNIQUE,
                            "type"	INTEGER NOT NULL,
                            "rule"	TEXT NOT NULL,
                            "meta"	TEXT,
                            "comments"	TEXT,
                            PRIMARY KEY("id" AUTOINCREMENT)
                            );''')
    db_cursor.execute('''CREATE  TRIGGER auto_set_valid AFTER UPDATE OF "valid" ON "clients" WHEN new.id==0
                            BEGIN
                                UPDATE "clients" SET valid=1 WHERE id=new.id;
                            END;''')
    db_cursor.execute('''CREATE TRIGGER auto_set_name AFTER UPDATE OF "name" ON "clients" WHEN new.id==0
                            BEGIN
                                UPDATE "clients" SET "name"="<SERVER>" WHERE id=new.id;
                            END''')
    db_cursor.execute('''INSERT INTO "main"."clients" ("id", "address", "name", "code", "valid") VALUES ('0', '0.0.0.0', '<SERVER>', '', '1');''')

    db.commit()

else:
    db = sqlite3.connect(DATABASE_FILE)
    db_cursor = db.cursor()

# Detect and create default config file
if not os.path.exists(CONFIG_FILE):
    print('Creating config file...')
    with open(CONFIG_FILE, 'w') as dump_file:
        dump_data = {
            "Port": 233,
            "Auth": False,
            "AllowAdminCommands": True,
            "AllowNickname": True,
            "MessageLogFile": "./message-log.json",
            "CredentialFolder": "./credentials/",
            "WelcomeMessage": "Welcome to PyChat Server!"
        }
        json.dump(dump_data, dump_file)
# Load config from file
with open(CONFIG_FILE, 'r') as load_file:
    load_conf = json.load(load_file)
port = load_conf['Port']
rx_port = port + 1
AllowAdminCommands = load_conf['AllowAdminCommands']
AllowNickname = load_conf['AllowNickname']
WelcomeMessage = load_conf['WelcomeMessage']


def sender_main(cnn, addr):
    """sender communication

    This method is used to communicate with the sender (client)
    
    Args:
        :param cnn: socket object, for socket communication
        :param addr: tuple, store the client address

    Returns:
        Method returns an integer

        Normal exit returns 0
    """

    global AllowAdminCommands
    global AllowNickname
    message_counter = 0
    client_address = str(addr)
    nickname = ''
    print(client_address + ' Connected')

    # Receive nickname from the client
    use_nickname = False
    if AllowNickname:
        cnn.send('NICK'.encode())
        request = cnn.recv(1024).decode()
        if request == 'NICK_ON':
            use_nickname = True
            print(client_address + ' use_nickname=' + str(use_nickname))
            nickname = cnn.recv(1024).decode()
            nickname = nickname.strip('#').strip('<').strip('>').strip(':')
            print(client_address + ' nickname=' + nickname)
        else:
            print(client_address + ' use_nickname=' + str(use_nickname))
    else:
        cnn.send('NICK_REJECTED'.encode())

    # Generate a credential to authenticate the receiver
    try:
        db_cursor.execute('''INSERT INTO "main"."clients"("address","name","code","valid") VALUES (NULL,NULL,NULL,1);''')
    except Exception:
        cnn.send('ERROR,ERROR'.encode())
        cnn.close()
        exit()
    client_id = db_cursor.lastrowid
    client_credential_pre = str(time.time()) + str(client_id) + str(random.randint(100000, 655360))
    client_credential = hashlib.sha512(client_credential_pre.encode()).hexdigest()
    client_credential_send = str(client_id) + ',' + client_credential
    print(client_address + ' ' + str(client_credential_send.split(',')))
    # Send the credential to the sender
    cnn.send(client_credential_send.encode())
    # Dump the credential to db
    db_cursor.execute('''
                        UPDATE "main"."clients"
                        SET "address"=?, "name"=?, "code"=?
                        WHERE "_rowid_"=?;
                        ''', (addr[0]+','+str(addr[1]), nickname, client_credential, client_id))
    message_time = current_milli_time()
    if use_nickname:
        client_alias = nickname
    else:
        client_alias = str(addr)
    message_content = client_alias + ' ' + 'Connected'
    db_cursor.execute('''
                        INSERT INTO "main"."messages"
                        ("client", "time", "content")
                        VALUES (?, ?, ?);''', (0, message_time, message_content))
    db.commit()

    # Create a loop to receive and process messages
    while True:
        try:
            # Receive message
            request = cnn.recv(4096).decode()
            print(client_address + ': ' + request)
            time.sleep(0.1)

            # Validate credentials
            try:
                load_credential = db_cursor.execute('''SELECT "id", "code", "valid", "meta", "name"
                                                        FROM "main"."clients"
                                                        WHERE "id" = ?''', (client_id,)).fetchall()[0]
                if not (load_credential[2]):
                    print(client_address + ' Rejected (Invalid Credential)')
                    cnn.send('Invalid Credential'.encode())
                    cnn.close()
                    return 1
            except:
                print(client_address + ' Rejected (Invalid Credential)')
                cnn.send('##Invalid Credential'.encode())
                cnn.close()
                return 1

            # Check meta
            if load_credential[3] is not None:
                load_meta_data = json.loads(load_credential[3])
                if 'mute' in load_meta_data and load_meta_data['mute'] > time.time():
                    remain_mute_time = int(load_meta_data['mute'] - time.time())
                    time.sleep(0.9)
                    cnn.send('YOU ARE NOT ALLOWED TO SEND MESSAGES IN {} SECONDS'.format(str(remain_mute_time)).encode())
                    continue

            # Update nickname
            nickname = load_credential[4]

            # Detect if the received message is an instruction to the server
            if len(request.strip()) > 2 and request[0] == '#':
                # Send message
                message_time = current_milli_time()
                message_content = request
                meta_data = json.dumps({'nosend': True})
                try:
                    db_cursor.execute('''
                                        INSERT INTO "main"."messages"
                                        ("client", "time", "content", "meta")
                                        VALUES (?, ?, ?, ?);''', (client_id, message_time, message_content, meta_data))
                except Exception:
                    cnn.send('SERVER NOT AVAILABLE, PLEASE TRY AGAIN LATER'.encode())
                    continue
                db.commit()
                if request[0:2] == '##' and request[2] != '#':
                    # Session command
                    request_cmd_session_fmt = request.lower()[2:].strip()
                    user_cmd = ' '.join(filter(lambda x: x, request_cmd_session_fmt.split(' '))).split(' ')
                    if user_cmd[0] == 'exit':
                        print(client_address + ' Disconnected')
                        db_cursor.execute('''UPDATE "main"."clients" SET "valid"=0 WHERE "_rowid_"=?;''', (client_id,))
                        db.commit()
                        cnn.close()
                        return 0
                    elif user_cmd[0] == 'welcome':
                        cnn.send(WelcomeMessage.encode())
                    elif len(user_cmd) > 1 and user_cmd[0] == 'nick':
                        if user_cmd[1] == 'get':
                            if use_nickname:
                                cnn.send(nickname.encode())
                            else:
                                cnn.send('#NICKNAME NOT SET#'.encode())
                        elif len(user_cmd) > 2 and user_cmd[1] == 'set':
                            new_nickname = request[request.lower().find(user_cmd[2]):][0:len(user_cmd[2])]
                            new_nickname = new_nickname.strip('#').strip('<').strip('>').strip(':')
                            db_cursor.execute('''UPDATE "main"."clients" SET "name"=? WHERE "_rowid_"=?;''', (new_nickname, client_id,))
                            message_time = current_milli_time()
                            if use_nickname:
                                client_alias = nickname
                            else:
                                client_alias = str(addr)
                            message_content = client_alias + ' ==> ' + new_nickname
                            db_cursor.execute('''
                                                INSERT INTO "main"."messages"
                                                ("client", "time", "content")
                                                VALUES (?, ?, ?);''', (0, message_time, message_content))
                            db.commit()
                            use_nickname = nickname
                            cnn.send('NICKNAME SET'.encode())
                        else:
                            cnn.send('INVALID COMMAND'.encode())
                    elif len(user_cmd) > 2 and user_cmd[0] == 'dm':
                        meta_data = json.dumps({'to': user_cmd[1], 'dm': True})
                        message_time = current_milli_time()
                        message_content = user_cmd[2]
                        try:
                            db_cursor.execute('''
                                                INSERT INTO "main"."messages"
                                                ("client", "time", "content", "meta")
                                                VALUES (?, ?, ?, ?);''', (client_id, message_time, message_content, meta_data))
                            cnn.send('MESSAGE SENT'.encode())
                        except Exception:
                            cnn.send('SERVER NOT AVAILABLE, PLEASE TRY AGAIN LATER'.encode())
                            continue
                        db.commit()
                    elif user_cmd[0] == 'su' and (len(user_cmd) > 2 or (len(user_cmd) > 1 and client_id == 0)):
                        try:
                            new_uid = int(user_cmd[1])
                            load_credential = db_cursor.execute('''SELECT "id", "code"
                                                                    FROM "main"."clients"
                                                                    WHERE "id" = ?''', (new_uid,)).fetchall()[0]
                            if client_id == 0 or (user_cmd[2] == load_credential[1]):
                                if new_uid == 0:
                                    AllowAdminCommands = True
                                    AllowNickname = True
                                meta_data = json.dumps({'to': '#'+str(client_id),
                                                         'su': True,
                                                         'id': new_uid
                                                         })
                                try:
                                    message_time = current_milli_time()
                                    message_content = '#SU'
                                    db_cursor.execute('''
                                                        INSERT INTO "main"."messages"
                                                        ("client", "time", "content", "meta")
                                                        VALUES (?, ?, ?, ?);''',
                                                      (client_id, message_time, message_content, meta_data))
                                    db_cursor.execute('''UPDATE "main"."clients" SET "address"=? WHERE "_rowid_"=?;''',
                                                      (addr[0]+','+str(addr[1]), new_uid))
                                except Exception:
                                    cnn.send('SERVER NOT AVAILABLE, PLEASE TRY AGAIN LATER'.encode())
                                    continue
                                db.commit()
                                load_credential = db_cursor.execute('''SELECT "id", "name"
                                                                                        FROM "main"."clients"
                                                                                        WHERE "id" = ?''',
                                                                    (new_uid,)).fetchall()[0]
                                client_id = new_uid
                                use_nickname = load_credential[1] is not None
                                cnn.send('Welcome!'.encode())
                                continue
                            else:
                                cnn.send('SU FAILURE!'.encode())
                                continue
                        except Exception:
                            cnn.send('CLIENT NOT FOUND'.encode())
                    else:
                        cnn.send('INVALID COMMAND'.encode())
                    continue

                elif len(request.strip()) > 3 and request[0:3] == '###':
                    # Server command
                    if not AllowAdminCommands:
                        cnn.send('INVALID COMMAND'.encode())
                        continue
                    request_cmd_server_fmt = request.lower()[3:].strip()
                    user_cmd = ' '.join(filter(lambda x: x, request_cmd_server_fmt.split(' '))).split(' ')
                    print('SERVER COMMAND')
                    print(user_cmd)
                    if len(user_cmd) > 2 and user_cmd[0] == 'pause':
                        try:
                            pause_time = int(user_cmd[1])
                            resume_time = int(user_cmd[2])
                        except Exception:
                            cnn.send('INVALID COMMAND'.encode())
                            continue
                        message_time = current_milli_time()
                        if resume_time > 0:
                            message_content = 'THE SERVER WILL PAUSE AFTER {} SECONDS AND WILL REMAIN UNAVAILABLE FOR {} SECONDS'.format(pause_time, resume_time)
                        else:
                            message_content = 'THE SERVER WILL PAUSE AFTER {} SECONDS AND WILL REMAIN UNAVAILABLE UNTIL IT IS RESUMED'.format(pause_time)
                        db_cursor.execute('''
                                            INSERT INTO "main"."messages"
                                            ("client", "time", "content")
                                            VALUES (?, ?, ?);''', (0, message_time, message_content))
                        db.commit()
                        time.sleep(pause_time)
                        message_time = current_milli_time()
                        message_content = 'SERVER PAUSED'.format(pause_time, resume_time)
                        db_cursor.execute('''
                                            INSERT INTO "main"."messages"
                                            ("client", "time", "content")
                                            VALUES (?, ?, ?);''', (0, message_time, message_content))
                        db.commit()
                        db_cursor.execute('''UPDATE "main"."clients" SET "valid"=1 WHERE "_rowid_"=?;''', (client_id,))
                        print('SERVER PAUSED')
                        if resume_time > 0:
                            time.sleep(resume_time)
                        else:
                            while request != 'resume':
                                cnn.send('SERVER PAUSED, SEND "RESUME" TO RESUME'.encode())
                                try:
                                    request = cnn.recv(4096).decode().lower()
                                except Exception:
                                    print(client_address + ' Disconnected (Unexpected)')
                                    while True:
                                        print('WARN: SERVICE TERMINATED!')
                                        message_time = current_milli_time()
                                        message_content = 'SERVICE TERMINATED, YOU MAY DISCONNECT NOW'.format(pause_time, resume_time)
                                        db_cursor.execute('''
                                                            INSERT INTO "main"."messages"
                                                            ("client", "time", "content")
                                                            VALUES (?, ?, ?);''', (0, message_time, message_content))
                                        db.commit()
                                        db_cursor.execute('''UPDATE "main"."clients" SET "valid"=1 WHERE "_rowid_"=?;''', (client_id,))
                                        time.sleep(60)
                        db.commit()
                        message_time = current_milli_time()
                        message_content = 'SERVER RESUMED'.format(pause_time, resume_time)
                        db_cursor.execute('''
                                            INSERT INTO "main"."messages"
                                            ("client", "time", "content")
                                            VALUES (?, ?, ?);''', (0, message_time, message_content))
                        db.commit()
                        print('SERVER RESUMED')
                        cnn.send('SERVER RESUMED'.encode())
                        continue
                    elif user_cmd[0] == 'kick' and len(user_cmd) > 1:
                        target_client_id = user_cmd[1]
                        print(target_client_id)
                        try:
                            db_cursor.execute('''UPDATE "main"."clients" SET "valid"=0 WHERE "_rowid_"=?;''', (target_client_id,))
                            db.commit()
                            cnn.send('KICKED'.encode())
                        except Exception:
                            cnn.send('CLIENT NOT FOUND'.encode())
                        continue
                    elif user_cmd[0] == 'mute' and len(user_cmd) > 2:
                        target_client_id = user_cmd[1]
                        try:
                            mute_time = int(user_cmd[2])
                            meta_data = json.dumps({'mute': time.time()+mute_time})
                            try:
                                db_cursor.execute('''UPDATE "main"."clients" SET "meta"=? WHERE "_rowid_"=?;''',
                                                  (meta_data, target_client_id,))
                                db.commit()
                                cnn.send('MUTE'.encode())
                            except Exception:
                                cnn.send('CLIENT NOT FOUND'.encode())
                            continue
                        except Exception:
                            cnn.send('INVALID COMMAND'.encode())
                            continue
                    elif user_cmd[0] == 'unmute' and len(user_cmd) > 1:
                        target_client_id = user_cmd[1]
                        meta_data = json.dumps({'mute': time.time()})
                        try:
                            db_cursor.execute('''UPDATE "main"."clients" SET "meta"=? WHERE "_rowid_"=?;''',
                                              (meta_data, target_client_id,))
                            db.commit()
                            cnn.send('UNMUTE'.encode())
                        except Exception:
                            cnn.send('CLIENT NOT FOUND'.encode())
                    elif len(user_cmd) > 2 and user_cmd[0] == 'get':
                        if user_cmd[1] == 'id':
                            target_name = user_cmd[2]
                            target_style = '%' + target_name + '%'
                            target_list = db_cursor.execute('''SELECT "id", "address", "name"
                                                                FROM "clients"
                                                                WHERE "valid" = 1 AND ("address" LIKE ? OR "name" LIKE ?);
                                                            ''', (target_style, target_style)).fetchall()
                            target_str = 'RES:\n'
                            for item in target_list:
                                target_str = target_str + str(item) + '\n'
                            cnn.send(target_str.strip('\n').encode())
                            continue
                        elif user_cmd[1] == 'cdt':
                            try:
                                target_client_id = int(user_cmd[2])
                                if target_client_id == 0:
                                    cnn.send('OPERATION NOT ALLOWED'.encode())
                                    continue
                                load_credential = db_cursor.execute('''SELECT "id", "code"
                                                                        FROM "main"."clients"
                                                                        WHERE "id" = ?''',
                                                                    (target_client_id,)).fetchall()[0]
                                target_str = 'ID:\n' + str(load_credential[0]) + '\nAccess Code:\n' + load_credential[1]
                                cnn.send(target_str.encode())
                                continue
                            except Exception:
                                cnn.send('INVALID COMMAND'.encode())
                                continue
                        else:
                            cnn.send('INVALID COMMAND'.encode())
                    elif len(user_cmd) > 2 and user_cmd[0] == 'block':
                        pass
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

            # Send message
            message_time = current_milli_time()
            message_content = request
            try:
                db_cursor.execute('''
                                    INSERT INTO "main"."messages"
                                    ("client", "time", "content")
                                    VALUES (?, ?, ?);''', (client_id, message_time, message_content))
                db.commit()
            except Exception as e:
                db.rollback()
                cnn.send('SERVER NOT AVAILABLE, PLEASE TRY AGAIN LATER'.encode())
                continue


            # The received message is returned to the client receiver to help the client confirm that the message has
            # been delivered.
            cnn.send(request.encode())


        except (BrokenPipeError, ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError):
            print(client_address + ' Disconnected (Unexpected)')
            db_cursor.execute('''UPDATE "main"."clients" SET "valid"=0 WHERE "_rowid_"=?;''', (client_id,))
            db.commit()
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
        :param rxcnn: socket object, for socket communication
        :param addr: tuple, store the client address

    Returns:
        Method returns an integer

        Normal exit returns 0
        Validation fails returns 1
    """

    client_address = str(addr)

    print(client_address + ' RX Connected')
    # Receive credential from the client
    rxcnn.send('UNBLOCK'.encode())
    client_id = rxcnn.recv(1024).decode()
    rxcnn.send(client_id.encode())
    client_credential = rxcnn.recv(1024).decode()
    rxcnn.send(client_credential.encode())

    # Validate credentials
    try:
        load_credential = db_cursor.execute('''SELECT "id", "address", "code", "valid"
                                                FROM "main"."clients"
                                                WHERE "id" = ?''', (client_id,)).fetchall()[0]
        if not ((load_credential[2] == client_credential) and load_credential[3] and (
                load_credential[1].split(',')[0] == addr[0])):
            db_cursor.execute('''UPDATE "main"."clients" SET "valid"=0 WHERE "_rowid_"=?;''', (client_id,))
            db.commit()
            print(client_address + ' RX Rejected (Invalid Credential)')
            rxcnn.send('Invalid Credential'.encode())
            rxcnn.close()
            return 1
    except:
        print(client_address + ' RX Rejected (Invalid Credential)')
        rxcnn.send('Invalid Credential'.encode())
        rxcnn.close()
        return 1

    # Send welcome message
    rxcnn.send(WelcomeMessage.encode())

    # Create a loop to send messages
    try:
        message = db_cursor.execute('''SELECT "id", "client", "time", "content"
                                FROM messages ORDER BY id DESC LIMIT 1;''').fetchall()[0]
        temp_message_id = message[0]
        message_id = temp_message_id
    except:
        temp_message_id = 0
        message_id = temp_message_id
    while True:
        try:
            # Wait until a new message is detected
            while temp_message_id == message_id:
                time.sleep(0.05)
                message = db_cursor.execute('''SELECT "id", "client", "time", "content", "meta"
                                                FROM messages ORDER BY id DESC LIMIT 1;''').fetchall()[0]
                message_id = message[0]
            temp_message_id = message_id
            client = db_cursor.execute('''SELECT "id", "address", "name"
                                            FROM clients WHERE "id"=?;''', (message[1],)).fetchall()[0]
            # Validate credentials
            try:
                load_credential = db_cursor.execute('''SELECT "id", "address", "code", "valid", "name"
                                                        FROM "main"."clients"
                                                        WHERE "id" = ?''', (client_id,)).fetchall()[0]
                if not ((load_credential[2] == client_credential) and load_credential[3] and (
                        load_credential[1].split(',')[0] == addr[0])):
                    print(client_address + ' RX Rejected (Invalid Credential)')
                    rxcnn.send('Invalid Credential'.encode())
                    rxcnn.close()
                    return 1
            except:
                print(client_address + ' RX Rejected (Invalid Credential)')
                rxcnn.send('Invalid Credential'.encode())
                rxcnn.close()
                return 1

            # Send message
            message_content = message[3]
            if message[4] is not None:
                load_meta = json.loads(message[4])
                if 'to' in load_meta and (str(load_meta['to']) in ['#'+str(client_id), str(load_credential[4]).lower()] or str(message[1]) == client_id):
                    if 'dm' in load_meta and load_meta['dm'] == True:
                        if message_content == '#':
                            continue
                        if client[2] == "":
                            client_alias = str((client[1].split(',')[0], int(client[1].split(',')[1])))
                        else:
                            client_alias = client[2]
                        message_send = '<DM> ' + client_alias + ': ' + message_content
                        rxcnn.send(message_send.encode())
                        print('Local==>' + client_address + ' RX Send: ' + message_send)
                    elif 'su' in load_meta:
                        client_id = load_meta['id']
                        load_credential = db_cursor.execute('''SELECT "id", "address", "code", "valid", "name"
                                                                                FROM "main"."clients"
                                                                                WHERE "id" = ?''',
                                                            (client_id,)).fetchall()[0]
                        client_credential = load_credential[2]
                    else:
                        continue
                else:
                    continue
            else:
                if message_content == '#':
                    continue
                if client[2] == "":
                    client_alias = str((client[1].split(',')[0], int(client[1].split(',')[1])))
                else:
                    client_alias = client[2]
                message_send = client_alias + ': ' + message_content
                rxcnn.send(message_send.encode())
                print('Local==>' + client_address + ' RX Send: ' + message_send)

        except (BrokenPipeError, ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError):
            print(client_address + ' RX Disconnected (Unexpected)')
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
    print('Invalidating credentials...')
    db_cursor.execute('''UPDATE "clients" SET "valid" = 0;''')
    client_credential_pre = str(time.time()) + str(0) + str(random.randint(100000, 655360))
    client_credential = hashlib.sha512(client_credential_pre.encode()).hexdigest()
    db_cursor.execute('''UPDATE "main"."clients" SET "code"=?, "valid"=1 WHERE "_rowid_"=?;''', (client_credential, 0))
    print('SU Access Code:')
    print(client_credential)
    db.commit()

    # Create an object for establishing socket communication
    rxm = multiprocessing.Process(target=receiver_launcher, args=())
    rxm.start()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, port))
    s.listen(5)

    sender_holder = Holder(0.2, 4, 0.2, 0.1)

    print('Server started!')

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
            # sender_holder.evoke()

        except (BrokenPipeError, ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError):
            pass
        except Exception as e:
            print(e)
            continue
