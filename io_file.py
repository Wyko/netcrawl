from datetime import datetime
from os.path import isfile
from global_vars import TIME_FORMAT, DB_PATH


import os
import pickle

index_path = DB_PATH + 'index.db'
pending_path = DB_PATH + 'pending.db'
device_path = DB_PATH + 'dev/'


def write_device(device, path=device_path, update=True, error_code=''):
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
    
    log('# write_device: Writing %s to file using pickle' % filename)
    
    if not os.path.exists(path):
        os.makedirs(path)
    
    # Save the network_device to file
    pickle.dump(device, open( path + filename, "wb" ) )
    
    #update_index(device, path + filename)
    


def load_index():
    """Returns the index."""
    
    log('# load_index: Loading index')
    
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
                if line == '': continue
                line = line.split(',')
                entry = {
                    'ip': line[0].strip(),
                    'name': line[1].strip(),
                    'updated': line[2].strip()
                    } 
                
                index.append(entry)
    return index

    
def update_index(index):
    log('# update_index: Starting write.')
    
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH)
    
    with open(index_path, 'w') as outfile:
        for entry in index:

            output = '{:15},{:30},{}'.format(
                str(entry['ip']).replace(',', ';'),
                str(entry['name']).replace(',', ';'),
                str(entry['updated'].replace(',', ';'))
                )
            outfile.write('\n' + output)
    
    log('# update_index: Finished writing index.')


def backup_config(raw_config):
    pass


def update_pending_devices(device_list):
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH)
    
    # Open the pending devices list, overwriting anything in it.
    with open(pending_path, 'w') as outfile:
        for (ip, platform) in device_list:
            outfile.write('\n{:15}, {}'.format(ip,platform))
    
    log('# update_pending_devices: Writing devices to file.')





def log_failed_device(msg='', device_ip='', error=''):
    """Logs a failed device.
    
    Args:
        device_ip (string): The IP address of the device.
        
    Optional Args:
        msg (string): The message to write.
        
    Returns:
        Boolean: True if write was successful, False otherwise.
    """ 

    log(msg, device_ip)
       
    output = '{:19}, {:15}, {}, {}'.format(
            datetime.now().strftime(TIME_FORMAT),
            device_ip,
            msg.replace(',', ';'),
            str(error).replace(',', ';')
            )
    
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH)
    
    # Open the error log
    f = open(DB_PATH + 'failed.txt','a')
    
    if f and not f.closed:
        f.write(output + '\n')
        f.close()
        return True
    
    else: return False    



def log(msg, device_ip='', print_out=True):
    """Writes a message to the log.
    
    Args:
        msg (string): The message to write.
        
    Optional Args:
        device_ip (string): The IP address of the device.
        
    Returns:
        Boolean: True if write was successful, False otherwise.
    """ 
    
    
    output = '{:19}, {:15}, {}'.format(
                datetime.now().strftime(TIME_FORMAT),
                device_ip,
                msg.replace(',', ';'))
                
    if print_out: print(msg)
    
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH)
    
    # Open the error log
    f = open(DB_PATH + 'log.txt','a')
    
    if f and not f.closed:
        f.write(output + '\n')
        f.close()
        return True
    
    else: return False
    