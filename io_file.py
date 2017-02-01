from datetime import datetime
from os.path import isfile
from global_vars import TIME_FORMAT
from global_vars import DB_PATH

import os
import pickle

index_path = DB_PATH + 'index.db'


def write_device(device, path=(DB_PATH + 'dev/'), update=True, error_code=''):
    """Write a network_device using pickle.
    
    Args:
        device (network_device): The network_device class object to write. Can
            accept both a single device or a list of devices.
        update (Boolean): If True, search for and update an existing copy
            of the device in the database. If none is found, create a new
            entry anyway.
            If False, create a new entry.
        path (string): The database directory to write to. 
        error_code (string): An optional error field to include.

    Returns:
        Boolean: True if the write was successful, False if not.

    Raises:
        OSError: If write was unsuccessful.
    """
    
    filename = device.unique_name()
    path = path + filename + '/' 
    filename = filename + '.ndv'
    
    log('# Writing %s to file using pickle' % filename)
    
    if not os.path.exists(path):
        os.makedirs(path)
    
    # Save the network_device to file
    pickle.dump(device, open( path + filename, "wb" ) )
    
    #update_index(device, path + filename)
    
    
def update_index(index):
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH)
    
    with open(index_path, 'w') as outfile:
        for entry in index:
            outfile.write(entry + '\n')
    
    log('# Writing index to file.')


def load_index():
    """Returns the index."""
    
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH)

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
    
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH)
    
    # Open the error log
    f = open(DB_PATH + 'log.txt','a')
    
    if f and not f.closed:
        f.write(output + '\n')
        f.close()
        return True
    
    else: return False
    