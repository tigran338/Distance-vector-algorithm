
import sys

max_int32 = 2 ** 31 - 1
myid = None
servers = None
row_table = None
dv_table = {}
edgesid = {}


def read_topology(file_path):
    global myid, servers, row_table, dv_table, max_int32
    with open(file_path, 'r') as file:
        num_servers = int(file.readline().strip())
        num_edges = int(file.readline().strip())

        servers = {}
        for _ in range(num_servers):
            server_id, ip, port = file.readline().strip().split()
            servers[int(server_id)] = {'ip': ip, 'port': int(port)}

        # Initialize dv_table with 'inf' for all cells except the current server

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
    
    
    
    

if __name__ == "__main__":
    # Read topology from file and store in servers and edges
    read_topology('topology.txt')

    # Display the topology
    display_dv_table()

    while True:
        neighbor_id = int(input("Enter neighbor_id: "))
        num_servers = len(servers)
        neighborTable = {}
        for i in range(num_servers):
            server_id, cost = map(int, input(f"Enter server ID and cost for neighbor {neighbor_id}: ").split())
            neighborTable[server_id] = cost
        update_dv_table(neighbor_id, neighborTable)
        display_dv_table()