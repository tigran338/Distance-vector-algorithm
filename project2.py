import sys
import socket
import threading
import sys
import time

# Server connected variables
connections = {}

# Distance vector Algoritm variables
max_int32 = 2 ** 31 - 1
myid = None
servers = None
row_table = None
dv_table = {}



# Distance vector Algoritm variables paert
#______________________________________________________________________________________
def read_topology(file_path):
    global myid, servers, row_table, dv_table, max_int32
    with open(file_path, 'r') as file:
        num_servers = int(file.readline().strip())
        num_edges = int(file.readline().strip())

        servers = {}
        for _ in range(num_servers):
            server_id, ip, port = file.readline().strip().split()
            servers[int(server_id)] = {'ip': ip, 'port': int(port)}


        neighbor = set()
        row_table = set()
        # Update dv_table with costs from the file for the current server
        for _ in range(num_edges):
            server_id, neighbor_id, cost = map(int, file.readline().strip().split())
            
            neighbor.update([(server_id, neighbor_id, cost)])
            row_table.add(server_id)
            row_table.add(neighbor_id)
            myid = server_id

        for i in row_table:
            dv_table[i] = {}
            for key in servers.keys():
                dv_table[i][key] = max_int32

        for server_id, neighbor_id, cost in neighbor:
            dv_table[server_id][neighbor_id] = cost
        
        dv_table[myid][myid] = 0
            
def display_dv_table():
    global myid, servers, dv_table, max_int32

    print(f"\nDistance Vector Table for Server ID {myid}:")
    header = "   |" + "|".join([f"{server_id:5}" for server_id in servers])
    separator = "----+" + "+".join(["-----"] * len(servers))
    print(header)
    print(separator)

    for server_id in servers:
        if server_id in dv_table:
            row = f"{server_id:3} |"
            for neighbor_id in dv_table[server_id].keys():
                cost = dv_table[server_id][neighbor_id]
                if cost == max_int32:
                    cost_str = " inf "
                else:
                    cost_str = f"{cost:5}"
                row += cost_str.replace('-', ' - ') + "|"
            print(row)
            print(separator)
        

def update_dv_table(neighbor_id:int, neighborTable:dict):
    # Fill up the neigbor id row in dv_table
    for server_id, cost in neighborTable.items():
        dv_table[neighbor_id][server_id] = cost

    
    for server_id in servers:
        dv_table[myid][server_id] = min(dv_table[myid][server_id], dv_table[myid][neighbor_id] + dv_table[neighbor_id][server_id])

    display_dv_table()
    
    

def step():
    global myid, servers, connections
    for connection_id in connections:
        message = f"TABLE {myid}"
        for server_id, cost in dv_table[myid].items():
            message += f" {server_id}:{cost}"
        send_message(connection_id, message)
        print(f"Sent distance vector row to server {connection_id}")




#SERVER PART
#______________________________________________________________________________________
def accept_connections():
    global servers, connections
    port = servers[myid]['port']
    ip = servers[myid]['ip']
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((ip, port))
    server_socket.listen(5)
    print(f"Server started and listening on port {port}")
    while True:
        client_socket, client_address = server_socket.accept()

        # Find the server ID associated with the incoming connection
        for server_id, server_info in servers.items():
            # Compare IP and port of the connected client and the server info
            print(f"ip {client_address[0]} port {client_address[1]}")
            if server_info['ip'] == client_address[0] and server_info['port'] == client_address[1]:
                connections[server_id] = (client_socket, client_address)
                break

        print(f"New connection from {client_address}")
        client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address, None))
        client_thread.start()

def handle_client(client_socket, client_address, server_id):
    if not server_id:
        data = client_socket.recv(1024)
        server_id = int(data.strip())

    connections[server_id] = (client_socket, client_address)
    print(f"Connected to server {server_id}")
    while True:
        data = client_socket.recv(1024)
        if data:
            message = data.decode()
            if message.startswith("TABLE"):
                message_parts = message.split(" ")
                sender_id = int(message_parts[1])
                neighbor_table = {}
                for table_entry in message_parts[2:]:
                    server_id, cost = map(int, table_entry.split(":"))
                    neighbor_table[server_id] = cost
                update_dv_table(sender_id, neighbor_table)
            else:
                print(f"Received message from {client_address}: {message}")
            display_connections()
        

def send_message(connection_id, message):
    connection = connections[connection_id]
    connection[0].sendall(message.encode())
    print(f"message sent to: {connection_id}")

def connect_to(address, port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((address, port))
    server_id = None

    # Find server ID based on the address and port
    for key, value in servers.items():
        if value['ip'] == address and value['port'] == port:
            server_id = key
            break

    # If the server ID is found, update the connections dictionary
    if server_id:
        print(f"Connected to {address}:{port}")
        client_thread = threading.Thread(target=handle_client, args=(client_socket, (address, port), server_id))
        client_thread.start()
        send_message(server_id, str(myid))
    else:
        print("Could not find server ID for given address and port")


def connect_to_neighbors():
    
    for neighbor_id in row_table:
        try:
            if myid != neighbor_id:
                connect_to(servers[neighbor_id]['ip'] , servers[neighbor_id]['port'])
                print(str(neighbor_id))
        except:
            print(f"Was no able to connect to {neighbor_id} server") 



#Debug
def display_connections():
    print("Current connections:")
    for server_id, connection_info in connections.items():
        print(f"Server ID: {server_id} - Address: {connection_info[1]}")
              

#Main part
if __name__ == "__main__":
    # Read topology from file and store in servers and edges
    read_topology('topology.txt')

    # Display the topology
    display_dv_table()
    connect_to_neighbors()

    accept_thread = threading.Thread(target=accept_connections, daemon=True)
    accept_thread.start()

    while True:
        command = input("Enter command: ")

        if command == 'step':
            step()
            '''
        elif command.split(' ')[0] == 'update':
            try:
                dv_table[int(command.split(' ')[1])][int(command.split(' ')[2])] = int(command.split(' ')[3]) 
            except:
                print("Wrong input")



    
    while True:
        neighbor_id = int(input("Enter neighbor_id: "))
        num_servers = len(servers)
        neighborTable = {}
        for i in range(num_servers):
            server_id, cost = map(int, input(f"Enter server ID and cost for neighbor {neighbor_id}: ").split())
            neighborTable[server_id] = cost
        update_dv_table(neighbor_id, neighborTable)
        display_dv_table()
    '''