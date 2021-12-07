import socket
import select
import threading
import sys
import diffie
from Crypto.Cipher import DES3
from Crypto.Util.Padding import pad
from Crypto.Util.Padding import unpad
import pickle


READ_BUFFER = 128

class User:
    username_port = {}
    groupname_nonce = {}

class ChatSender(threading.Thread):
    def __init__(self, username, roll_no, listener_port):
        threading.Thread.__init__(self)
        self.username = username
        self.roll_no = roll_no
        self.listener_port = listener_port
        self.userPort_map = {}

    def sendMessage(self, message, port):
        client_socket = socket.socket()
        client_socket.connect(("127.0.0.1", port))
        client_socket.send(message.encode())
        data = client_socket.recv(1024).decode()
        #data = pickle.loads(data)
        print('Received from server: ' + data)
        client_socket.close()
        return data

    def sendGroupMessage(self, message, port):
        client_socket = socket.socket()
        client_socket.connect(("127.0.0.1", port))
        client_socket.send(message.encode())
        data = client_socket.recv(1024)
        data = pickle.loads(data)
        #print('Received from server: ' + data)
        client_socket.close()
        return data
    
    ##########################  ENCRYPTION ############################## 

    def exchange_keys(self, port_no, roll_no, message):
        #print("key exchange and encryption at client side")
        client_socket = socket.socket()
        client_socket.connect(("127.0.0.1", port_no))
        if message.split()[0] == "send":
            message_to_send = message.split()[0:2]
            message_to_send = ' '.join(message_to_send)
            #print(message_to_send)
            client_socket.sendall(message_to_send.encode())
            client_socket.recv(1024)
        else:
            message_to_send = message.split()[0:3]
            message_to_send = ' '.join(message_to_send)
            #print(message_to_send)
            client_socket.sendall(message_to_send.encode())
            client_socket.recv(1024)

        message = message.split()[2:]
        message = ' '.join(message)
        #print(message)
        slice_object = slice(8)

        ## 1st exchange
        d1 = diffie.DiffieHellman(roll_no)
        pubkey_k1 = d1.gen_public_key()
        client_socket.send(str(pubkey_k1).encode())
        #print("sent pk1")
        shared_key1 = d1.gen_shared_key(client_socket.recv(1024).decode())
        shared_key1 = shared_key1[slice_object]
        #print("sender side :", shared_key1)

        #2nd exchange
        d2 = diffie.DiffieHellman(roll_no)
        pubkey_k2 = d2.gen_public_key()
        client_socket.send(str(pubkey_k2).encode())
        shared_key2 = d2.gen_shared_key(client_socket.recv(1024).decode())
        shared_key2 = shared_key2[slice_object]

        #3rd exchange
        d3 = diffie.DiffieHellman(roll_no)
        pubkey_k3 = d3.gen_public_key()
        client_socket.send(str(pubkey_k3).encode())
        shared_key3 = d3.gen_shared_key(client_socket.recv(1024).decode())
        shared_key3 = shared_key3[slice_object]

        final_key = shared_key1 + shared_key2 + shared_key3
        #print("type final_key", type(final_key))
        if "send" == message_to_send.split()[0]:

            cipher = DES3.new(final_key, DES3.MODE_ECB) 
            encrypted_block = cipher.encrypt(pad(message.encode(), 8))

            client_socket.sendall(encrypted_block)

            #print('Received from server: ' + data)
            #print("inside send")
            client_socket.close()
        
        elif "send_file" == message_to_send.split()[0]:

            file_name = message
            try:
                f = open(file_name,'rb')
            except:
                print("No Such File Exists")
                print("DISCONNECT")
                client_socket.close()
            
            l = f.read()
            cipher = DES3.new(final_key, DES3.MODE_ECB) 
            encrypted_block = cipher.encrypt(pad(l, 8))
      
            client_socket.sendall(encrypted_block)
            #print("REQCOMP")
            f.close()
            client_socket.close()
    
    def group_encryption(self, nonce, message, data):
        slice_object = slice(24)

        nonce = nonce[slice_object]

        if message.split()[0] == "send_group":

            cipher = DES3.new(nonce, DES3.MODE_ECB)
            
            message_to_send = " ".join(message.split()[2:])
            encrypted_block = cipher.encrypt(pad(message_to_send.encode(), 8))
            #print(data)
            for ports in data:

                client_socket = socket.socket()
                client_socket.connect(("127.0.0.1", int(ports)))

                #print(message)
                client_socket.sendall(message.encode())
                #print(encrypted_block)
                client_socket.recv(1024)
                client_socket.sendall(encrypted_block)

                client_socket.close()
        elif message.split()[0] == "send_group_file":

            files = message.split()[2]
            filename = files
            try:
                f = open(filename,'rb')
            except:
                print("No Such File Exists")
                print("DISCONNECT")
                client_socket.close()
                return
            l = f.read()
            cipher = DES3.new(nonce, DES3.MODE_ECB) 
            encrypted_block = cipher.encrypt(pad(l, 8))

            for ports in data:
                client_socket = socket.socket()
                client_socket.connect(("127.0.0.1", int(ports))) 
                
                client_socket.sendall(message.encode())

                client_socket.recv(1024)

                client_socket.sendall(encrypted_block)



        
    
    ########################## ENCRYPTION ##############################
    
    def printInstructions(self):
        print('=============== Instructions: ===================')
        print("signup <username> <password> ... {registers the user}")
        print("signin <username> <password> ... {log in}")
        print("send <username> <message> ... {sends message to user}")
        print("create <groupname> ... {creates a group}")
        print("send_group <groupname> <message> ... {sends message to group}")
        print("send_group_file <groupname> <file name> ... {sends files to group}")
        print("join <groupname> ... {join a group}")
        print("list ... {lists the groups and no. of members}")
        print('=================================================')

    def run(self):
        self.printInstructions()
        while True:
            port = 1234
            message = input('Enter command: ')
            if len(message) > 0:
                command = message.split()[0]
                if command.lower() == 'signup':
                    if len(message.split()) != 3:
                        print("Insufficient arguments")
                    else:
                        message += str(" " + str(self.listener_port))
                        data = self.sendMessage(message, port)
                elif command.lower() == 'signin':
                    data = self.sendMessage(message, port)
                    if data == "True":
                        print("Successful signin")
                    else:
                        print("Try again")   
                elif command.lower() == 'send' or command.lower() == 'send_file':
                    if message.split()[1] in User.username_port.keys():
                        new_port = User.username_port[message.split()[1]]
                    else:
                        message_split = " ".join(message.split()[0:2])
                        new_port = self.sendMessage(message_split, port)
                        User.username_port[message.split()[1]] = new_port
                    message_to_send = message.split()
                    message_to_send = ' '.join(message_to_send)

                    self.exchange_keys(int(new_port), self.roll_no, message_to_send)
                    #data = self.sendMessage(message_to_send, int(new_port))
                elif command.lower() == 'create':
                    message += str(" " + str(self.username))
                    data = self.sendMessage(message, port)
                    User.groupname_nonce[message.split()[1]] = str(data)
                    #print("nonce received", str(data))
                elif command.lower() == 'join':
                    message += str(" " + str(self.username))
                    data = self.sendMessage(message, port)
                    User.groupname_nonce[message.split()[1]] = str(data)
                elif command.lower() == 'send_group' or 'send_group_file':

                    ## sending details to server to get the members port number
                    message_to_send = message.split()
                    message_to_send = ' '.join(message_to_send[0:2])
                    message_to_send += str(" " + str(self.username))
                    data = self.sendGroupMessage(message_to_send, port)
                    
                    ## encrypting data and sending it to all the clients
                    nonce = User.groupname_nonce[message.split()[1]]
                    #message = ' '.join(message.split()[2:])
                    self.group_encryption(nonce, message, data)

                    
                    #data = self.sendMessage(message, port)
                elif command.lower() == 'list':
                    message += str(" " + str(self.username))
                    data = self.sendMessage(message, port)
                    print(data, end = '')

class ChatListener(threading.Thread):
    def __init__(self, username, roll_no, listener_port):
        threading.Thread.__init__(self)
        self.username = username
        self.roll_no = roll_no
        self.listener_port = listener_port
    ##########################E  DECRYPTION ##############################

    def exchange_keys(self, listener_port, roll_no, conn, message):

        if message.split()[0] == "send_group":
            ## expecting encrypted data from server
            slice_object = slice(24)
            
            nonce = User.groupname_nonce[message.split()[1]]
            nonce = nonce[slice_object]
            encrypted_data = conn.recv(64)
            
            cipher = DES3.new(nonce, DES3.MODE_ECB)
            decrypted_data = cipher.decrypt(encrypted_data)

            return decrypted_data.decode()

        elif message.split()[0] == "send_group_file":
            slice_object = slice(24)
            
            nonce = User.groupname_nonce[message.split()[1]]
            nonce = nonce[slice_object]

            cipher = DES3.new(nonce, DES3.MODE_ECB)

            files = message.split()[2]

            recieved_filename = "recieved_file_"+files

            with open(recieved_filename, 'wb') as f:
                    # print('file opened')
                    while True:
                #key0 = DesKey(bytes(final_key,"utf-8"))
                # print('receiving data...')
                        buffer = conn.recv(1024)
                        if len(buffer) < 1:
                            buffer+=b''
                        # print('data=%s', (data))
                        if not buffer:
                            f.close()
                            break
                        data_var = cipher.decrypt(buffer)
                        f.write(data_var)
            print("File sent")
            return "File " + files + " recieved successfully"
                


        else:
            #print("key exchange and decryption at client side")
            slice_object = slice(8)
            d1 = diffie.DiffieHellman(roll_no)
            pubkey_k1 = d1.gen_public_key()
            shared_key_k1 = d1.gen_shared_key(conn.recv(1024).decode())
            #print("recieved pk1 and generated sk1")
            shared_key_k1 = shared_key_k1[slice_object]
            #print("reciever side :", shared_key_k1)
            conn.sendall(str(pubkey_k1).encode())

            d2 = diffie.DiffieHellman(roll_no)
            pubkey_k2 = d2.gen_public_key()
            shared_key2 = d2.gen_shared_key(conn.recv(1024).decode())
            shared_key2 = shared_key2[slice_object]
            conn.sendall(str(pubkey_k2).encode())

            d3 = diffie.DiffieHellman(roll_no)
            pubkey_k3 = d3.gen_public_key()
            shared_key3 = d3.gen_shared_key(conn.recv(1024).decode())
            shared_key3 = shared_key3[slice_object]
            conn.sendall(str(pubkey_k3).encode())
            
            final_key = shared_key_k1 + shared_key2 + shared_key3

            if message.split()[0] == "send":

                cipher = DES3.new(final_key, DES3.MODE_ECB)

                
                final_ans = ""
                while True:
                    buffer = conn.recv(1024)
                    #if len(buffer) < 1:
                        #buffer+=b''
                        # print('data=%s', (data))
                    if not buffer:
                        conn.close()
                        break
                    data = cipher.decrypt(buffer)
                    final_ans = final_ans + data.decode()
                #print(final_ans)
                return final_ans
            elif message.split()[0] == "send_file":

                received_filname = "recieved_file"
                cipher = DES3.new(final_key, DES3.MODE_ECB) 
                with open(received_filname, 'wb') as f:
                    # print('file opened')
                    while True:
                #key0 = DesKey(bytes(final_key,"utf-8"))
                # print('receiving data...')
                        buffer = conn.recv(1024)
                        if len(buffer) < 1:
                            buffer+=b''
                        # print('data=%s', (data))
                        if not buffer:
                            f.close()
                            break
                        data_var = cipher.decrypt(buffer)
                        f.write(data_var)
                print("File sent")
                return "File "  + message.split()[2] + " recieved successfully"
        
            
            


        ##########################E  DECRYPTION ##############################
    def run(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(("127.0.0.1", self.listener_port))
        server_socket.listen(5)
        sockets_list = [server_socket]
        
        while True:
            read_sockets, _, exception_sockets = select.select(sockets_list, [], sockets_list)
            for notified_socket in read_sockets:
                if notified_socket == server_socket:
                    conn, address = server_socket.accept()
                    print("Connection from: " + str(address))
                    message = conn.recv(64).decode()
                    ack = "accepted"
                    conn.send(ack.encode())
                    #print(message)
                    data = self.exchange_keys(self.listener_port, self.roll_no, conn, message)
                else:
                    message = conn.recv(64).decode()
                    #print(message)
                    data = self.exchange_keys(self.listener_port, self.roll_no, conn, message)

                if len(data) > 0:
                    print("from connected user: " + str(data))
                    #conn.send(data.encode())
        
        for notified_socket in exception_sockets:
            sockets_list.remove(notified_socket)
            del clients[notified_socket]
        conn.close()

def main():
    print("WELCOME TO PYCHAT!!! Please Enter your username and rollno to verify your identity.")
    username = input('Username: ')
    roll_no = input('Roll No: ')
    print("Use the commands above mentioned in the instructions.")
    listener_port = int(sys.argv[1])
    chat_listener = ChatListener(username, roll_no, listener_port)
    chat_listener.start()

    chat_sender = ChatSender(username, roll_no, listener_port)
    chat_sender.start()

if __name__=="__main__": 
    main()