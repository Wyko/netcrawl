from datetime import datetime
from os.path import isfile
import os
import global_vars

# Define the timestamp format
TIME_FORMAT = '%Y-%m-%d %H:%M:%S'



def load_index():
    """Returns the index."""
    
    index_path = global_vars.DB_PATH + 'index.db'
    index = []
    
    # Check if the file exists
    if isfile(index_path):
        # Open the error log
        with open(index_path, 'r') as infile:
            for line in infile:
                # Split each index entry into a nice little dict object.
                line = line.rstrip('\n')
                line = line.split('[,]')
                entry = {
                    'ip': line[0],
                    'serial': line[1],
                    'updated': line[2]
                    } 
                
                index.append(entry)
    return index
    

def in_index(index, device):
    """Checks if the given Network Device is in the index.
    
    Args:
        index (string): The full index.
        device (network_device): The device to find.
    
    Returns:
        # String: The filepath of the network_device entry
        Integer: The line number of the index entry of a matched device
        Boolean: False if the device is not in the index
    """
    
    ip_list = device.get_ips()
    
    # If the IP list is empty:
    if not ip_list: return False
    
    # Check every entry in the index to see if an IP matches.
    for i, entry in enumerate(index):
        if entry['ip'] in ip_list:
            return i
    
    return False


def log(msg, device_ip='', device_serial=''):
    """Writes a message to the log.
    
    Args:
        msg (string): The message to write.
        
    Optional Args:
        device_ip (string): The IP address of the device.
        device_serial (string): The unique serial of the device.
        
    Returns:
        Boolean: True if write was successful, False otherwise.
    """ 
    
    output = '[,]'.join([datetime.now().strftime(TIME_FORMAT),
                         msg, 
                         device_ip, 
                         device_serial
                         ])
    
    print(msg)
    
    if not os.path.exists(global_vars.DB_PATH):
        os.makedirs(global_vars.DB_PATH)
    
    # Open the error log
    f = open(global_vars.DB_PATH + 'log.txt','a')
    
    if f and not f.closed:
        f.write(output + '\n')
        f.close()
        return True
    
    else: return False
    