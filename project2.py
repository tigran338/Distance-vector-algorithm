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

last_update = None
last_crash = None
# NetworkTopology input
#_____________________________________________________________________________________
class NetworkTopology:
    def __init__(self, servers, neighbors):
        self.servers = set(servers)
        self.neighbors = set(neighbors)




def update_topology(update):
    global topology, myid, servers, connections,last_update
    # Check if the second element exists in the set
    if update == last_update:
        return
    
    last_update = update

    link_1,link_2,cost = map(int, update.strip().split())
    message = f"Update {update}"
    
    if link_1 in dv_table.keys() and link_2 in dv_table.keys():
        if link_1 == int(myid):
            send_message(int(link_2), message)
        else:
            send_message(int(link_1), message)

        
        dv_table[link_1][link_2] = cost
        dv_table[link_2][link_1] = cost
        #print(f"<{message}> success")
        return
    
    #print(f"<{message}> fail because the link 1 or link 2 is not the neigbor")



    # for connection_id in connections:
    #     message = f"Update {update}"
    #     send_message(connection_id, message)
    #     print(f"Sent Update to server {connection_id}")



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

    if myid in row_table:
        dv_table[myid][myid] = 0

        
            
def display_dv_table():
    global myid, servers, dv_table, max_int32, connections

    print(f"\nDistance Vector Table for Server ID {myid}:")
    header = "   |" + "|".join([f"{server_id:5}" for server_id in sorted(servers)])
    separator = "----+" + "+".join(["-----"] * len(servers))
    print(header)
    print(separator)
    for server_id in sorted(servers):
        if server_id in dv_table:
            row = f"{server_id:3} |"
            for neighbor_id in sorted(dv_table[server_id].keys()):
                if neighbor_id in servers:
                    cost = dv_table[server_id][neighbor_id]
                    if len(dv_table.keys()) == 1 and server_id != neighbor_id:
                        cost = max_int32

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
        
def connect_to_neighbors():
    
    for neighbor_id in sorted(dv_table.keys()):
        try:
            if myid != neighbor_id:
                connect_to(servers[neighbor_id]['ip'] , servers[neighbor_id]['port'])
                #print(str(neighbor_id))
        except:
            print(f"Was no able to connect to {neighbor_id} server") 

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
        # for server_id, server_info in servers.items():
        #     if server_info['ip'] == client_address[0] and server_info['port'] == client_address[1]:
        #         connections[server_id] = (client_socket, client_address)
        #         break

        print(f"New connection from {client_address}")
        client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address, None))
        client_thread.start()

def handle_client(client_socket, client_address, server_id):
    global packet_count,connections, topology, max_int32, servers, last_crash
    
    lock = threading.Lock()
    
    if not server_id:
        data = client_socket.recv(1024)
        server_id = int(data.strip())
    
    connections[server_id] = (client_socket, client_address)
    try:
        print(f"Connected to server {server_id}")
        while True:
            
            data = client_socket.recv(1024)
            


            if data:
                with lock:
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
                        packet_count += 1
                        link_1, link_2 = map(int, message.split()[1:3])
                        if (message.split()[3] == 'inf'):
                            cost = max_int32
                        else:
                            cost = int(message.split()[3])

                        update_topology(f"{link_1} {link_2} {cost}")
                    elif message.startswith("Disable"):
                        disableid = int(message.strip().split()[1])
                        del connections[disableid]
                        del dv_table[disableid]
                        dv_table[myid][disableid] = max_int32
                        print(f"Connection with {disableid} lost.")

                        return     
                    elif message.startswith("Crash"):
                        if message != last_crash:
                            last_crash = message
                            crashid = int(message.strip().split()[1])

                            if crashid in connections.keys():
                                del connections[crashid]
                                del dv_table[crashid]
                            print(f"The server {crashid} is crash.")
                            
                            for keys in dv_table.keys():
                                dv_table[keys][crashid] = max_int32

                            dv_table[myid][crashid] = max_int32

                            
                            for connection_id in connections.keys():
                                 send_message(connection_id, message)
                            
                            if server_id == crashid:
                                return      
                    else:
                        print(f"Received message from {client_address}: {message}")
                    
    except:
        pass
            
                
        

        

def send_message(server_id, message):
    
    global connections
    connection = connections[server_id]
    connection[0].sendall(message.encode())
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



#Debug
def display_connections():
    print("Current connections:")
    for server_id, connection_info in connections.items():
        print(f"Server ID: {server_id} - Address: {connection_info[1]}")
              


#closes a specific connection id, sends "Close Connection" message to the connection to remove it
def terminate_connection(connection_id):
    global connections, topology

    send_message(connection_id,f"Disable {myid}")

    connection = connections[connection_id]
    connection[0].close()
    del connections[connection_id]
    del dv_table[connection_id]
    dv_table[myid][connection_id] = max_int32
    
    print(f"Connection with {connection_id} terminated.")
                
                
def crash():
    global connections, topology
    
    del_connections = list(connections.keys())[:]

    for id in del_connections:
        send_message(id,f"Crash {myid}")

    
    time.sleep(2)
    for id in del_connections:
        connection = connections[id]
        connection[0].close()
        del connections[id]
        del dv_table[id]
        dv_table[myid][id] = max_int32
        print(f"Connection with {id} terminated.")
    
    
    


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
            
            initialize_dv_table()
            display_dv_table()
            connect_to_neighbors()
            accept_thread = threading.Thread(target=accept_connections, daemon=True)
            accept_thread.start()
        elif command == 'packets':
            print(f"Total packets received: {packet_count}")
        elif command.startswith('update'):
            link_1, link_2 = map(int, command.split()[1:3])
            if (command.split()[3] == 'inf'):
                cost = max_int32
            else:
                cost = int(command.split()[3])
            
            update_topology(f"{link_1} {link_2} {cost}")
        elif command.startswith("disable"):
            server_id = int(command.split(' ')[1])
            
            
            if int(server_id) not in dv_table.keys() or int(server_id) == int(myid):
                print("The neigbor not found")
                continue
            
            terminate_connection(server_id)
        elif command.startswith("crash"):
            crash()
            
            break


       







