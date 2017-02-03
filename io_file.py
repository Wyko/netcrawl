from datetime import datetime
from os.path import isfile
from global_vars import TIME_FORMAT, DB_PATH


import os
import pickle

index_path = DB_PATH + 'index.db'
neighborhood_path = DB_PATH + 'neighborhood.db' 
pending_path = DB_PATH + 'pending.db'
failed_path = DB_PATH + 'failed.db'
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
    
    log('# Writing %s to file using pickle' % filename, proc='write_device')
    
    if not os.path.exists(path):
        os.makedirs(path)
    
    # Save the network_device to file
    pickle.dump(device, open( path + filename, "wb" ) )
    
    #update_neighborhood(device, path + filename)
    


def load_neighborhood():
    """Returns the index."""
    
    log('# Start populating the neighborhood', proc='load_neighborhood')
    
    if not os.path.exists(DB_PATH):
        log('# Database path not found. Creating directory.', proc='load_neighborhood')
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
    
    if len(index) >= 1: 
        log('# Finished loading neighborhood. {} entries found.'.format(len(index)), proc='load_neighborhood')
    else: 
        log('# Finished. No previous entries found. Neighborhood empty.', proc='load_neighborhood')
    return index

    
def update_neighborhood(neighborhood):
    log('# Starting update.', proc='update_neighborhood')
    
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH)
    
    with open(index_path, 'w') as outfile:
        for entry in neighborhood:

            output = '{:16},{:30},{}'.format(
                str(entry['ip']).replace(',', ';'),
                str(entry['name']).replace(',', ';'),
                str(entry['updated'].replace(',', ';'))
                )
            outfile.write('\n' + output)
    
    log('# Finished updating the neighborhood.', proc='update_neighborhood')


def backup_config(raw_config):
    pass


def update_pending_devices(device_list):
    
    log('# Starting write.', proc='update_pending_devices')
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH)
    
    # Open the pending devices list, overwriting anything in it.
    with open(pending_path, 'w') as outfile:
        for (i) in device_list:
            outfile.write('\n{:15}, {:15}, {}'.format(i['ip'], i['netmiko_platform'], i['name']))
    
    log('# Finished writing devices to file.', proc='update_pending_devices')





def log_failed_device(msg='', device_ip='', error='', cdp_name='',  proc=''):
    """Logs a failed device.
    
    Args:
        device_ip (string): The IP address of the device.
        
    Optional Args:
        msg (string): The message to write.
        
    Returns:
        Boolean: True if write was successful, False otherwise.
    """ 

    log(msg, device_ip, proc=proc)
       
    output = '{:19}, {:15}, {:30.29}, {}, {}'.format(
            datetime.now().strftime(TIME_FORMAT),
            device_ip,
            cdp_name,
            msg.replace(',', ';'),
            str(error).replace(',', ';')
            )
    
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH)
    
    # Open the error log
    f = open(failed_path,'a')
    
    if f and not f.closed:
        f.write(output + '\n')
        f.close()
        return True
    
    else: return False    



def log(msg, device_ip='', print_out=True, proc=''):
    """Writes a message to the log.
    
    Args:
        msg (string): The message to write.
        
    Optional Args:
        device_ip (string): The IP address of the device.
        print_out (Boolean): If True, copies the message to console
        
    Returns:
        Boolean: True if write was successful, False otherwise.
    """ 
    
    if proc:
        output = '{}, {:<25}, {:45}, {}'.format(
                    datetime.now().strftime(TIME_FORMAT),
                    proc,
                    msg.replace(',', ';'),
                    device_ip
                    )
        
    else:
        output = '{}, {:45}, {}'.format(
                    datetime.now().strftime(TIME_FORMAT),
                    msg.replace(',', ';'),
                    device_ip
                    )
                
    if print_out: print('{:<25.25}: {}'.format(proc, msg))
    
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH)
    
    # Open the error log
    f = open(DB_PATH + 'log.txt','a')
    
    if f and not f.closed:
        f.write(output + '\n')
        f.close()
        return True
    
    else: return False
    