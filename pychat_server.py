import socket
import select
from Crypto.Cipher import DES3
from Crypto import Random
import sys
import pickle

READ_BUFFER = 128

class Main_server:
    userName_pswd = {}
    userName_port = {}
    groupName_members = {}
    userName_groups = {}
    groupName_nonce = {}

def sendMessage(message, port):
    client_socket = socket.socket()
    client_socket.connect(("127.0.0.1", port))
    client_socket.send(message.encode())
    # data = client_socket.recv(READ_BUFFER).decode()
    # print('Received from server: ' + data)
    client_socket.close()
    # return data

def handle_command(conn, data):
    if len(data) > 0:
        print("from connected user: " + str(data))
        command = data.split()[0]
        if command.lower() == 'signup':
            Main_server.userName_pswd[data.split()[1]] = data.split()[2]
            Main_server.userName_port[data.split()[1]] = int(data.split()[3])
            data = "Successfully signed up"
            conn.send(data.encode())
        elif command.lower() == 'signin':
            if data.split()[1] in Main_server.userName_pswd:
                if Main_server.userName_pswd[data.split()[1]] == data.split()[2]:
                    Main_server.userName = data.split()[1]
                    data = "True"
                else:
                    data = "False"
            else:
                data = 'False'
            conn.send(data.encode())
        elif command.lower() == 'send' or command.lower() == "send_file":
            #print("Received send")
            if data.split()[1] in Main_server.userName_port:
                #print("User found")
                data = str(Main_server.userName_port[data.split()[1]])
            conn.send(data.encode())
        elif command.lower() == 'create':
            nonce = Random.new().read(24)
            #print(sys.getsizeof(nonce))
            members = [data.split()[-1]]
            Main_server.groupName_members[data.split()[1]] = members
            Main_server.groupName_nonce[data.split()[1]] = str(nonce)
            #print(Main_server.groupName_members)
            if data.split()[-1] in Main_server.userName_groups:
                Main_server.userName_groups[data.split()[-1]].append(data.split()[1])
            else:
                groups = [data.split()[1]]
                Main_server.userName_groups[data.split()[-1]] = groups
            #print(Main_server.userName_groups)
            #print(str(nonce))
            data = str(nonce)
            conn.send(data.encode())
        elif command.lower() == 'join':
            if data.split()[1] in Main_server.groupName_members:
                #print("Group exists")
                Main_server.groupName_members[data.split()[1]].append(data.split()[-1])
                if data.split()[-1] in Main_server.userName_groups:
                    Main_server.userName_groups[data.split()[-1]].append(data.split()[1])
                else:
                    groups = [data.split()[1]]
                    Main_server.userName_groups[data.split()[-1]] = groups
                #print(Main_server.groupName_members)
                #print(Main_server.userName_groups)
            else:
                print("Group does not exist")
            data = Main_server.groupName_nonce[data.split()[1]]
            conn.send(data.encode())
        elif command.lower() == 'send_group' or 'send_group_file':
            if data.split()[1] in Main_server.groupName_members:

                ## sending details to all clients.
                list_of_ports = []
                
                for member in Main_server.groupName_members[data.split()[1]]:
                    if member in Main_server.userName_port:
                        if member != data.split()[-1]:
                            #sendMessage(data, Main_server.userName_port[member])
                            list_of_ports.append(Main_server.userName_port[member])
                    else:
                        print("Member port mapping not present on server")
                
                conn.send(pickle.dumps(list_of_ports))
                ## sending encrypted data to all clients.
                '''
                data = conn.recv(READ_BUFFER)
                for member in Main_server.groupName_members[group_name]:
                    if member in Main_server.userName_port:
                        if member != group_member:
                            sendEncryptedMessage(data, Main_server.userName_port[member])
                    else:
                        print("Member port mapping not present on server")

            else:
                print("Group does not exist")
                '''
        elif command.lower() == 'list':
            message_to_send = ""
            for group in Main_server.userName_groups[data.split()[-1]]:
                message_to_send += group + " " + str(len(Main_server.groupName_members[group])) + "\n"
            data = message_to_send
            conn.send(data.encode())
            
def server_program():

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("127.0.0.1", 1234))
    
    server_socket.listen(5)
    sockets_list = [server_socket]
    
    while True:
        read_sockets, _, exception_sockets = select.select(sockets_list, [], sockets_list)
        for notified_socket in read_sockets:
            if notified_socket == server_socket:
                conn, address = server_socket.accept()
                print("Connection from User: " + str(address))
                data = conn.recv(64).decode()
                handle_command(conn, data)
            else:
                data = conn.recv(64).decode()
                handle_command(conn, data)

    for notified_socket in exception_sockets:
        sockets_list.remove(notified_socket)
        del clients[notified_socket]

    conn.close()

if __name__ == '__main__':
    server_program()