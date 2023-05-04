from ast import Delete
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
topology = None
packet_count = 0
is_initialize_dv_table = False


# NetworkTopology input
#_____________________________________________________________________________________
class NetworkTopology:
    def __init__(self, servers, neighbors):
        self.servers = set(servers)
        self.neighbors = set(neighbors)




def update_topology(add_element):
    global topology, myid, servers, connections
    # Check if the second element exists in the set

    if add_element in topology.neighbors:
        return
    
    existing_element = None
    for e in topology.neighbors:
        if e.split(' ')[1] == add_element.split(' ')[1]:
            existing_element = e
            break

    # If the second element exists, remove it from the set
    if existing_element:
        topology.neighbors.remove(existing_element)

    # Add the new element to the set
    topology.neighbors.add(add_element)

    for connection_id in connections:
        message = f"Update {add_element}"
        send_message(connection_id, message)
        print(f"Sent Update to server {connection_id}")



# Distance vector Algoritm variables paert
#______________________________________________________________________________________
def initialize_dv_table():
    global myid, servers, row_table, dv_table, max_int32, topology, is_initialize_dv_table
    
    while is_initialize_dv_table:
        pass
    
    is_initialize_dv_table = True

    dv_table={}

    servers = {}
    for line in topology.servers:
        server_id, ip, port = line.strip().split()
        servers[int(server_id)] = {'ip': ip, 'port': int(port)}


    neighbor = set()
    row_table = set()
    # Update dv_table with costs from the file for the current server

    for line in topology.neighbors:
        server_id, neighbor_id, cost = map(int, line.strip().split())
        
        neighbor.update([(server_id, neighbor_id, cost)])
        row_table.add(server_id)
        row_table.add(neighbor_id)
        

    for i in row_table:
        dv_table[i] = {}
        for key in servers.keys():
            dv_table[i][key] = max_int32

    for server_id, neighbor_id, cost in neighbor:
        dv_table[server_id][neighbor_id] = cost
    
    #display_dv_table()

    if myid in row_table:
        dv_table[myid][myid] = 0

    is_initialize_dv_table = False
        
            
def display_dv_table():
    global myid, servers, dv_table, max_int32

    print(f"\nDistance Vector Table for Server ID {myid}:")
    header = "   |" + "|".join([f"{server_id:5}" for server_id in sorted(servers)])
    separator = "----+" + "+".join(["-----"] * len(servers))
    print(header)
    print(separator)

    for server_id in sorted(servers):
        if server_id in dv_table:
            row = f"{server_id:3} |"
            for neighbor_id in sorted(dv_table[server_id].keys()):
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

    
    
    

def step():
    global myid, servers, connections
    message = f"TABLE {myid}"
    for server_id, cost in dv_table[myid].items():
        message += f" {server_id}:{cost}"
    
    for connection_id in connections:
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
    server_socket.listen(10)
    
    print(f"Server started and listening on port {port}")
    while True:
        client_socket, client_address = server_socket.accept()

        # Find the server ID associated with the incoming connection
        for server_id, server_info in servers.items():
            # Compare IP and port of the connected client and the server info
            #print(f"ip {client_address[0]} port {client_address[1]}")
            if server_info['ip'] == client_address[0] and server_info['port'] == client_address[1]:
                connections[server_id] = (client_socket, client_address)
                break

        print(f"New connection from {client_address}")
        client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address, None))
        client_thread.start()

def handle_client(client_socket, client_address, server_id):
    global packet_count,connections, topology
    
    
    if not server_id:
        data = client_socket.recv(1024)
        server_id = int(data.strip())
    
    connections[server_id] = (client_socket, client_address)
    try:
        print(f"Connected to server {server_id}")
        while True:
            
            data = client_socket.recv(1024)
            


            if data:
                message = data.decode()
                if message.startswith("TABLE"):
                    packet_count+=1
                    message_parts = message.split(" ")
                    sender_id = int(message_parts[1])
                    neighbor_table = {}
                    for table_entry in message_parts[2:]:
                        server_id, cost = map(int, table_entry.split(":"))
                        neighbor_table[server_id] = cost
                    update_dv_table(sender_id, neighbor_table)
                elif message.startswith("Update"):
                    link_1, link_2 = map(int, message.split()[1:3])
                    if (message.split()[3] == 'inf'):
                        cost = max_int32
                    else:
                        cost = int(message.split()[3])
                    if int(link_1) == int(myid):
                        update_topology(f"{link_1} {link_2} {cost}")
                    elif int(link_2) == int(myid):
                        update_topology(f"{link_2} {link_1} {cost}")
                    #print(topology.neighbors)
                    initialize_dv_table()
                elif message.startswith("Disable"):
                    del connections[int(server_id)]
                    
                    print(f"Connection with {server_id} lost.")
                    existing_element =  None

                    for line in topology.neighbors:
                        link_1, link_2 = map(int, line.strip().split(' ')[0:2])
                        if server_id == link_1 or server_id == link_2:
                            existing_element = line
                            break
                    if existing_element:
                        topology.neighbors.remove(existing_element)
                    
                    initialize_dv_table()


                    ignore_id = [int(myid), int(server_id)]
                    message = str(myid) + " " + str(server_id) + " " + " ".join(str(id) for id in connections)

                    for connection_id in connections.keys():
                        if connection_id not in ignore_id:
                            try:
                                send_message(connection_id, message)
                                print(f"Sent Reset to server {connection_id}") 
                            except ConnectionResetError:
                                print(f"ConnectionResetError: Connection to server {connection_id} was forcibly closed by the remote host.")
                    return

                elif message.startswith("Reset"):
                    initialize_dv_table()
                    ignore_id = [int(num) for num in message.strip().split()[1:]]
                    message = message + " " + str(myid) + " " + str(server_id) + " " + " ".join(str(id) for id in connections)

                    for connection_id in connections.keys():
                        if connection_id not in ignore_id:
                            try:
                                send_message(connection_id, message)
                                print(f"Sent Reset to server {connection_id}") 
                            except ConnectionResetError:
                                print(f"ConnectionResetError: Connection to server {connection_id} was forcibly closed by the remote host.")
                            
                             
                else:
                    print(f"Received message from {client_address}: {message}")
                #display_connections()
    except:
        if server_id in connections.keys():
            #print(f"Before delete {connections}")
            del connections[int(server_id)]
            #print(f"After delete {connections}")
            print(f"Connection with {server_id} lost (not handle).")
            existing_element =  None
            for line in topology.neighbors:
                link_1, link_2 = map(int, line.strip().split(' ')[0:2])
                if server_id == link_1 or server_id == link_2:
                    existing_element = line
                    break
            if existing_element:
                topology.neighbors.remove(existing_element)
                
                initialize_dv_table()
                '''
                message = " ".join(str(id) for id in connections)
                message = "Reset " + str(myid)
                for connection_id in connections:
                    send_message(connection_id, message)
                    print(f"Sent Reset to server {connection_id}")
                '''
        

        

def send_message(server_id, message):
    
    global connections
    connection = connections[server_id]
    connection[0].sendall(message.encode())
    #print(f"message sent to: {server_id}")
    return

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
        connections[server_id] = (client_socket, (address, port))
    else:
        print("Could not find server ID for given address and port")


def connect_to_neighbors():
    
    for neighbor_id in row_table:
        try:
            if myid != neighbor_id:
                connect_to(servers[neighbor_id]['ip'] , servers[neighbor_id]['port'])
                #print(str(neighbor_id))
        except:
            print(f"Was no able to connect to {neighbor_id} server") 



#Debug
def display_connections():
    print("Current connections:")
    for server_id, connection_info in connections.items():
        print(f"Server ID: {server_id} - Address: {connection_info[1]}")
              


#closes a specific connection id, sends "Close Connection" message to the connection to remove it
def terminate_connection(connection_id):
    global connections, topology

    send_message(connection_id,"Disable")

    connection = connections[connection_id]
    connection[0].close()
    del connections[connection_id]
    print(f"Connection with {connection_id} terminated.")
    existing_element =  None
    for line in topology.neighbors:
        link_1, link_2 = map(int, line.strip().split(' ')[0:2])
        if connection_id == link_1 or connection_id == link_2:
            existing_element = line
            break
    
    if existing_element:
        topology.neighbors.remove(existing_element)
        initialize_dv_table()

        
        # for connection_id in connections:
        #     message = f"Update -1 -1 -1"
        #     send_message(connection_id, message)
        #     print(f"Sent Reset to server {connection_id}")
        time.sleep(1)
        message = "Reset " +  str(myid) + " " + str(connection_id)+ " "  + " ".join(str(id) for id in connections)
        initialize_dv_table()
        
        for connection_id in connections.keys():
            try:
                send_message(connection_id, message)
                print(f"Sent Reset to server {connection_id}")
            except ConnectionResetError:
                print(f"ConnectionResetError: Connection to server {connection_id} was forcibly closed by the remote host.")
                
                



#Main part
if __name__ == "__main__":

    
    while True:
        command = input("Enter command: ")

        if command == 'step':
            step()
        elif command == 'display':
            display_dv_table()
        elif command.startswith('server -t'):
            topology = NetworkTopology([],[])
            filename = command.split(' ')[-1]  # get the last part of the string (the filename)
            with open(filename) as file:
                num_servers = int(file.readline().strip())
                num_edges = int(file.readline().strip())

                for _ in range(num_servers):
                    topology.servers.add(file.readline().strip())

                for _ in range(num_edges):
                    s = file.readline().strip()
                    topology.neighbors.add(s)
                    myid = int(s.split(' ')[0])
            
            #print(topology.servers)
            #print(topology.neighbors)
            initialize_dv_table()
            display_dv_table()
            connect_to_neighbors()
            #print(row_table)
            accept_thread = threading.Thread(target=accept_connections, daemon=True)
            accept_thread.start()
        elif command == 'packets':
            print(f"Total packets received: {packet_count}")
        elif command.split(' ')[0] == 'update':
            link_1, link_2 = map(int, command.split()[1:3])
            if (command.split()[3] == 'inf'):
                cost = max_int32
            else:
                cost = int(command.split()[3])
            
            if int(link_1) == int(myid):
                update_topology(f"{link_1} {link_2} {cost}")
            elif int(link_2) == int(myid):
                update_topology(f"{link_2} {link_1} {cost}")
            #print(topology.neighbors)
            initialize_dv_table()
        elif command.startswith("disable"):
            server_id = int(command.split(' ')[1])
            
            print(row_table)
            if int(server_id) not in row_table and int(server_id) == int(myid):
                print("The neigbor not found")
                continue
            
            terminate_connection(server_id)
        elif command.startswith("crash"):
            del_connections = list(connections.keys())[:]

            for id in del_connections:
                terminate_connection(id)
            
            break


       







