#!/usr/bin/python3
import sys
import struct
import wrapper
import threading
import time
from wrapper import recv_from_any_link, send_to_link, get_switch_mac, get_interface_name


def parse_ethernet_header(data):
    # Unpack the header fields from the byte array
    #dest_mac, src_mac, ethertype = struct.unpack('!6s6sH', data[:14])
    dest_mac = data[0:6]
    src_mac = data[6:12]
    
    # Extract ethertype. Under 802.1Q, this may be the bytes from the VLAN TAG
    ether_type = (data[12] << 8) + data[13]

    vlan_id = -1
    # Check for VLAN tag (0x8100 in network byte order is b'\x81\x00')
    if ether_type == 0x8200:
        vlan_tci = int.from_bytes(data[14:16], byteorder='big')
        vlan_id = vlan_tci & 0x0FFF  # extract the 12-bit VLAN ID
        ether_type = (data[16] << 8) + data[17]

    return dest_mac, src_mac, ether_type, vlan_id

def create_vlan_tag(vlan_id):
    # 0x8100 for the Ethertype for 802.1Q
    # vlan_id & 0x0FFF ensures that only the last 12 bits are used
    return struct.pack('!H', 0x8200) + struct.pack('!H', vlan_id & 0x0FFF)

def construct_and_send_bdpu(sender_mac, root_bridge_ID, sender_bridge_ID, sender_path_cost, interface):
    bdpu = b'\x01\x80\xC2\x00\x00\x00' + sender_mac
    bdpu = bdpu + struct.pack('!I', root_bridge_ID) + struct.pack('!I', sender_path_cost) + struct.pack('!I', sender_bridge_ID)
    send_to_link(interface, bdpu, len(bdpu))

def send_bdpu_every_sec(sender_mac, root_bridge_ID, own_bridge_ID, interfaces, interface_vlan_map):
    while True:
        # TODO Send BDPU every second if necessary
        if root_bridge_ID == own_bridge_ID:
            for interface in interfaces:
                if interface_vlan_map[interface] == 99:
                    construct_and_send_bdpu(sender_mac, own_bridge_ID, own_bridge_ID, 0, interface)
        time.sleep(1)

    

def is_unicast_mac(mac_address):
    mac_address = mac_address.lower().replace(':', '')

    first_byte = int(mac_address[:2], 16)
    is_unicast = (first_byte & 1) == 0

    return is_unicast


def return_interface_idx(interface):
    for i in range(0, 4):
        if get_interface_name(i) == interface:
            return i

def read_config_file(filename):
    interface_vlan = {}
    priority = 0
    with open(filename) as f:
        first_line = True  
        for line in f:
            if first_line:
                first_line = False
                priority = int(line.strip())
                continue
            line = line.strip()
            if line:
                interface, vlan = line.split()
                if (vlan == 'T'):
                    interface_vlan[return_interface_idx(interface)] = 99
                else:
                    interface_vlan[return_interface_idx(interface)] = int(vlan)
    return priority, interface_vlan


def handle_BDPU_received(receiver_mac, data, opened_ports, own_bridge_ID, root_bridge_ID, root_path_cost, interface_received_from, interface_vlan_map):

    sender_root_bridge_ID, sender_path_cost, sender_bridge_ID = struct.unpack('!III', data)

    if sender_root_bridge_ID < root_bridge_ID:
    
        root_bridge_ID = sender_root_bridge_ID  
        root_path_cost = sender_path_cost + 10
        root_port = interface_received_from

        for port in interface_vlan_map.keys():
            if interface_vlan_map[port] == 99:
                opened_ports[port] = 0
        opened_ports[root_port] = 1

        if opened_ports[root_port] == 0:
            opened_ports[root_port] = 1

        for interface in interface_vlan_map.keys():
            if interface_vlan_map[interface] == 99 and interface != interface_received_from:
                construct_and_send_bdpu(receiver_mac, root_bridge_ID, own_bridge_ID, root_path_cost, root_port)

    elif sender_root_bridge_ID == root_bridge_ID:
        if opened_ports[interface_received_from] != 0  and sender_path_cost + 10 < root_path_cost:
            root_path_cost = sender_path_cost + 10

        elif opened_ports[interface_received_from] == 0:  
            if sender_path_cost > root_path_cost:
                if opened_ports[interface_received_from] == 0:
                    opened_ports[interface_received_from] = 1

    elif sender_bridge_ID == own_bridge_ID:
        opened_ports[interface_received_from] = 0
    
    else:
        return root_bridge_ID, root_path_cost
    
    if own_bridge_ID == root_bridge_ID:
        for port in interface_vlan_map.keys():
            if interface_vlan_map[port] == 99:
                opened_ports[port] = 1

    copy_root_bridge_ID = root_bridge_ID
    copy_root_path_cost = root_path_cost

    return copy_root_bridge_ID, copy_root_path_cost

        

def main():
    # init returns the max interface number. Our interfaces
    # are 0, 1, 2, ..., init_ret value + 1
    switch_id = sys.argv[1]

    num_interfaces = wrapper.init(sys.argv[2:])
    interfaces = range(0, num_interfaces)

    if (switch_id == "0"):
        priority, interface_vlan_map = read_config_file("configs/switch0.cfg")
        opened_ports = {}
        for port in interface_vlan_map.keys(): # set all ports opened
            opened_ports[port] = 1
    elif (switch_id == "1"):
        priority, interface_vlan_map = read_config_file("configs/switch1.cfg")
        opened_ports = {}
        for port in interface_vlan_map.keys(): # set all ports opened
            opened_ports[port] = 1
    elif (switch_id == "2"):
        priority, interface_vlan_map = read_config_file("configs/switch2.cfg")
        opened_ports = {}
        for port in interface_vlan_map.keys(): # set all ports opened
            opened_ports[port] = 1

    Table = {}  

    own_bridge_ID = priority
    root_bridge_ID = priority
    root_path_cost = 0

    sender_mac = get_switch_mac()
    # Create and start a new thread that deals with sending BDPU
    t = threading.Thread(target=send_bdpu_every_sec, args=(sender_mac, root_bridge_ID, own_bridge_ID, interfaces, interface_vlan_map))
    t.start()


    while True:
        # Note that data is of type bytes([...]).
        # b1 = bytes([72, 101, 108, 108, 111])  # "Hello"
        # b2 = bytes([32, 87, 111, 114, 108, 100])  # " World"
        # b3 = b1[0:2] + b[3:4].
        interface, data, length = recv_from_any_link()

        dest_mac, src_mac, ethertype, vlan_id = parse_ethernet_header(data)

        if (data[0:6] == b'\x01\x80\xC2\x00\x00\x00'): # received frame is BPDU
            new_root_bridge_ID, new_root_path_cost = handle_BDPU_received(get_switch_mac(), data[12:24], opened_ports, own_bridge_ID, root_bridge_ID, root_path_cost, interface, interface_vlan_map)
            root_bridge_ID = new_root_bridge_ID
            root_path_cost = new_root_path_cost
            continue

        # Print the MAC src and MAC dst in human readable format
        dest_mac = ':'.join(f'{b:02x}' for b in dest_mac)
        src_mac = ':'.join(f'{b:02x}' for b in src_mac)

        # Note. Adding a VLAN tag can be as easy as
        # tagged_frame = data[0:12] + create_vlan_tag(10) + data[12:]


        # TODO: Implement forwarding with learning
        # TODO: Implement VLAN support
        # TODO: Implement STP support
        Table[src_mac] = interface

        if (vlan_id == -1):  # received without vlan tag

            if is_unicast_mac(dest_mac):
                if dest_mac in Table:
                    if opened_ports[interface] != 0:
                        if interface_vlan_map[Table[dest_mac]] == interface_vlan_map[interface] and interface_vlan_map[Table[dest_mac]] != 99 and opened_ports[Table[dest_mac]] == 1: # trimit fara vlan tag
                            send_to_link(Table[dest_mac], data, length)
                        elif interface_vlan_map[Table[dest_mac]] == 99 and opened_ports[Table[dest_mac]] == 1:  # send further with vlan tag
                            new_data = data[0:12] + create_vlan_tag(interface_vlan_map[interface]) + data[12:]
                            send_to_link(Table[dest_mac], new_data, length + 4)
                    
                else:
                    for o in interfaces: 
                        if o == interface and opened_ports[o] == 0:
                            break
                        if o != interface:
                            if interface_vlan_map[o] == interface_vlan_map[interface] and interface_vlan_map[o] != 99 and opened_ports[o] == 1: # trimit fara vlan tag
                                send_to_link(o, data, length)
                            elif interface_vlan_map[o] == 99 and opened_ports[o] == 1:  # send further with vlan tag
                                new_data = data[0:12] + create_vlan_tag(interface_vlan_map[interface]) + data[12:]
                                send_to_link(o, new_data, length + 4)
                         
            else:
                for o in interfaces:
                    if o == interface and opened_ports[o] == 0:
                            break
                    if o != interface:
                        if interface_vlan_map[o] == interface_vlan_map[interface] and interface_vlan_map[o] != 99 and opened_ports[o] == 1:  # trimit fara vlan tag
                            send_to_link(o, data, length)
                        elif interface_vlan_map[o] == 99 and opened_ports[o] == 1:  # send further with vlan tag
                            new_data = data[0:12] + create_vlan_tag(interface_vlan_map[interface]) + data[12:]
                            send_to_link(o, new_data, length + 4)
                
            
        else: # am primit cu vlan tag
            if is_unicast_mac(dest_mac):
                if dest_mac in Table:
                    if opened_ports[interface] != 0:
                        
                        if interface_vlan_map[Table[dest_mac]] == vlan_id and interface_vlan_map[Table[dest_mac]] != 99 and opened_ports[Table[dest_mac]] == 1: # trimit fara vlan tag
                            new_data = data[0:12] + data[16:]
                            send_to_link(Table[dest_mac], new_data, length - 4)
                        elif interface_vlan_map[Table[dest_mac]] == 99 and opened_ports[Table[dest_mac]] == 1: # send further with vlan tag
                            send_to_link(Table[dest_mac], data, length)
                
                else:
                    for o in interfaces:
                        if o == interface and opened_ports[o] == 0:
                            break
                        if o != interface:
                            if interface_vlan_map[o] == vlan_id and interface_vlan_map[o] != 99 and opened_ports[o] == 1:  # send further without vlan tag
                                new_data = data[0:12] + data[16:]
                                send_to_link(o, new_data, length - 4)
                            elif interface_vlan_map[o] == 99 and opened_ports[o] == 1:  # send further with vlan tag
                                send_to_link(o, data, length)
                   
            else:
                for o in interfaces:
                    if o == interface and opened_ports[o] == 0:
                        break
                    if o != interface:
                        if interface_vlan_map[o] == vlan_id and interface_vlan_map[o] != 99 and opened_ports[o] == 1:  # send further without vlan tag
                            new_data = data[0:12] + data[16:]
                            send_to_link(o, new_data, length - 4)
                        elif interface_vlan_map[o] == 99 and opened_ports[o] == 1:  # send further with vlan tag
                            send_to_link(o, data, length)
                 

        # data is of type bytes.
        # send_to_link(i, data, length)

if __name__ == "__main__":
    main()
