import json
import socket
import sys
import time
import threading
import tkinter as tk

DEFAULT_PORT = 233
CLIENT_CREDENTIAL_FILE = 'credential.json'

def connect_btn(host, port, event=None):
    connect(host, port)

def connect_win_back(connect_win):
    connect_win.destroy()
    root_win.deiconify()

def connect(host, port):
    root_win.withdraw()
    connect_win = tk.Tk()
    connect_win.geometry('400x250')
    connect_win.title('PyChat Client - Connecting')
    var_cnn_msg = tk.StringVar(connect_win)
    info_lbl = tk.Message(connect_win, width=200, textvariable=var_cnn_msg)
    info_lbl.pack(side='top', anchor='nw', padx=5, pady=5)
    connect_win.update()
    cnn_msg = 'Connecting...\n'
    var_cnn_msg.set(cnn_msg)
    connect_win.update()
    try:
        s = socket.socket()
        s.connect((host, port))
        cnn_msg += 'Connected.\n'
        var_cnn_msg.set(cnn_msg)
        connect_win.update()
        nkr = s.recv(1024).decode()
        cnn_msg += 'Exchange info...\n'
        var_cnn_msg.set(cnn_msg)
        connect_win.update()
        if nkr == 'NICK':
            s.send('NICK_OFF'.encode())
        client_credential_recv = s.recv(2048).decode()
        client_credential = client_credential_recv.split(',')

        cnn_msg += 'Receiver connecting...\n'
        var_cnn_msg.set(cnn_msg)
        connect_win.update()
        r = socket.socket()
        r.connect((host, port + 1))
        cnn_msg += 'Receiver connected.\n'
        var_cnn_msg.set(cnn_msg)
        connect_win.update()
        cnn_msg += 'Exchange receiver info...\n'
        var_cnn_msg.set(cnn_msg)
        connect_win.update()
        r.recv(1024)
        r.send(client_credential[0].encode())
        r.recv(1024)
        r.send(client_credential[1].encode())
        r.recv(1024)
        cnn_msg += 'Connection finished.\n'
        var_cnn_msg.set(cnn_msg)
        connect_win.update()
        t = threading.Thread(target=main, args=(host, s, r,))
        t.daemon = True
        t.start()
        connect_win.destroy()
    except:
        cnn_msg += 'Failed to connect...\n'
        var_cnn_msg.set(cnn_msg)
        win_close_btm = tk.Button(connect_win, text='Close', command=lambda: connect_win_back(connect_win))
        win_close_btm.pack(side='top', anchor='nw', padx=10)
        connect_win.update()

def sender_task(s, msg_box, msg_ent, send_btm):
    sender_thread = threading.Thread(target=sender, args=(s, msg_box, msg_ent, send_btm))
    sender_thread.start()

def sender(s, msg_box, msg_ent, send_btm):
    send_btm.config(state='disabled')
    message = msg_ent.get(1.0, 'end').strip('\n')
    msg_ent.delete(1.0, 'end')
    try:
        if message == '':
            return 0
        else:
            s.send(message.encode())
            reply = s.recv(8092).decode()
            if reply != message:
                if reply.find('\n') == -1:
                    msg_box.config(state='normal')
                    msg_box.insert('end', reply)
                    msg_box.insert('end', '\n')
                    msg_box.yview('end')
                    msg_box.config(state='disabled')
                else:
                    msg_box.config(state='normal')
                    for replyln in reply.split('\n'):
                        msg_box.insert('end', replyln)
                        msg_box.insert('end', '\n')
                        msg_box.yview('end')
                    msg_box.config(state='disabled')
    except Exception as e:
        msg_ent.insert('end', e)
    finally:
        send_btm.config(state='normal')
        sys.exit()

def recever(s, msg_box):
    while True:
        try:
            rx_data = s.recv(4096).decode()
            if rx_data == '':
                s.send('RX ACTIVE'.encode())
                continue
            elif rx_data.find('\n') == -1:
                msg_box.config(state='normal')
                msg_box.insert('end', rx_data)
                msg_box.insert('end', '\n')
                msg_box.config(state='disabled')
                msg_box.yview('end')
            else:
                msg_split = rx_data.split(':', 1)
                sender = msg_split[0]
                msg = msg_split[1].strip(' ')
                msg_box.config(state='normal')
                for msgln in msg.split('\n'):
                    msg_box.insert('end', sender + ': ' + msgln)
                    msg_box.insert('end', '\n')
                    msg_box.yview('end')
                msg_box.config(state='disabled')
        except (BrokenPipeError, ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError):
            print('Server disconnected.')
            s.close()
            break


def main(host, s, r):
    main_win = tk.Tk()
    main_win.title('PyChat Client - {}'.format(host))
    # msg_box = tk.Listbox(main_win,font=('Arial',10), width=50)
    msg_box = tk.Text(main_win, font=('Arial',10), wrap='word', state='disabled', height=10, width=50)
    msg_box.pack(side='left', expand=True, fill='both')
    msg_box_sb = tk.Scrollbar(main_win, orient="vertical")
    msg_box_sb.config(command=msg_box.yview)
    msg_box_sb.pack(side='left', fill='y')
    msg_box.config(yscrollcommand=msg_box_sb.set)
    msg_ent = tk.Text(main_win, show=None, font=('Arial', 10), height=4, width=25)
    msg_ent.pack(side='top', expand=True, fill='both')
    main_win.bind('<Return>', lambda event=None: send_btm.invoke())
    main_win.bind('<Shift-Return>', lambda event=None: msg_ent.insert('end', ''))

    send_btm = tk.Button(main_win, text='Send', command=lambda: sender_task(s, msg_box, msg_ent, send_btm))
    send_btm.pack(side='bottom', pady=10)

    recever_thread = threading.Thread(target=recever, args=(r, msg_box,))
    # recever_thread.daemon = True
    recever_thread.start()

    main_win.update()
    main_win.minsize(main_win.winfo_width(), main_win.winfo_height())
    main_win.mainloop()
    root_win.destroy()


if __name__ == "__main__":
    root_win = tk.Tk()
    root_win.title('PyChat Client')
    #root_win.geometry('300x200')
    pychat_lbl = tk.Label(root_win, text='PyChat Client', font=('Arial', 24))
    pychat_lbl.pack(fill='both', expand=True, padx=40, pady=10)

    host_ent_frame = tk.Frame(root_win)
    host_ent_lbl = tk.Label(host_ent_frame, text='Server', font=('Arial', 12))
    var_host = tk.StringVar(value=socket.gethostname())
    host_ent = tk.Entry(host_ent_frame, show=None, font=('Consolas', 12), textvariable=var_host)
    host_ent_lbl.pack(side='left', fill='x', expand=False, padx=5, pady=5)
    host_ent.pack(side='right', fill='x', expand=False, padx=5, pady=5)
    host_ent_frame.pack(fill='both')

    port_ent_frame = tk.Frame(root_win)
    port_ent_lbl = tk.Label(port_ent_frame, text='Port', font=('Arial', 12))
    var_port = tk.StringVar(value=str(DEFAULT_PORT))
    port_ent = tk.Entry(port_ent_frame, show=None, font=('Arial', 12), textvariable=var_port)
    port_ent_lbl.pack(side='left', fill='x', expand=False, padx=5, pady=5)
    port_ent.pack(side='right', fill='x', expand=False, padx=5, pady=5)
    port_ent_frame.pack(fill='both')

    connect_btm = tk.Button(root_win, text='Connect', command=lambda: connect_btn(var_host.get(), int(var_port.get())))
    connect_btm.pack(expand=False, pady=10)

    root_win.bind('<Return>', lambda event=None: connect_btm.invoke())
    root_win.resizable(width=False, height=False)
    root_win.mainloop()

    sys.exit()
