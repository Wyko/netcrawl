from datetime import datetime
from os.path import isfile
from global_vars import DB_PATH, TIME_FORMAT
from utility import log

import os
import pickle

visited_path = DB_PATH + 'visited.db'
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
    
    
def log_failed_device(msg='', ip='', error='', cdp_name='',  proc=''):
    """Logs a failed device.
    
    Args:
        ip (string): The IP address of the device.
        
    Optional Args:
        msg (string): The message to write.
        
    Returns:
        Boolean: True if write was successful, False otherwise.
    """ 

    log(msg, ip, proc=proc)
       
    output = '{:19}, {:15}, {:30.29}, {}, {}'.format(
            datetime.now().strftime(TIME_FORMAT),
            ip,
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


def write_visited_device(visited_entry):
    """Appends a visited device to visited.db
    
    Args:
        visited_entry (dict): The visited device entry as defined in main.add_to_visited
        
    Returns:
        Boolean: True if write was successful, False otherwise.
    """ 
       
    output = '{ip:15}, {name}, {serial}, {updated}'.format(
            updated= datetime.now().strftime(TIME_FORMAT),
            ip= visited_entry['ip'],
            name= visited_entry['name'],
            serial= visited_entry['serial'],
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


def load_visited():
    """Returns a list of dicts containing all the devices we've visited."""
    
    log('# Start populating visted devices', proc='load_visited')
    
    if not os.path.exists(DB_PATH):
        log('# Database path not found. Creating directory.', proc='load_visited')
        os.makedirs(DB_PATH)

    visited_devices = []
    
    # Check if the file exists
    if isfile(visited_path):
        
        # Open visited.db
        with open(visited_path, 'r') as infile:
            for line in infile:
                
                #Check if the line is empty 
                line = line.strip()
                if not line: continue
                
                # Split each entry into a nice little dict object.
                line = line.split(',')
                line = [x.strip for x in line]
                
                entry = {
                    'ip': line[0],
                    'name': line[1],
                    'serial': line[2],
                    'updated': line[3],
                    } 
                
                visited_devices.append(entry)
    
    if len(visited_devices) >= 1: 
        log('# Finished loading visited devices. {} entries found.'.format(len(visited_devices)), proc='load_visited')
    else: 
        log('# Finished. No previous entries found.', proc='load_visited')
        
    return visited_devices

    
def update_neighborhood(neighborhood):
    log('# Starting update.', proc='update_neighborhood')
    
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH)
    
    with open(neighborhood_path, 'w') as outfile:
        for entry in neighborhood:

            output = '{:16},{:30},{}'.format(
                str(entry['ip']).replace(',', ';'),
                str(entry['name']).replace(',', ';'),
                str(entry['updated'].replace(',', ';'))
                )
            outfile.write('\n' + output)
    
    log('# Finished updating the neighborhood.', proc='update_neighborhood')


def in_neighborhood(ip):
    """Checks if the given ip address has been seen as a neighbor device.
    
    Args:
        ip (string): An ip addresses
    
    Returns:
        Boolean: False if the device is not in the index
    """
    
    # Check if the file exists
    if isfile(neighborhood_path):
        with open(neighborhood_path, 'r') as infile:
            for line in infile:
                line = line.split

    # Check every entry in the neighborhood to see if an IP matches.
            
    return False


def backup_config(raw_config):
    pass


def update_pending_list(device_list):
    
    log('# Starting write.', proc='update_pending_list')
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH)
    
    # Open the pending devices list, overwriting anything in it.
    with open(pending_path, 'w') as outfile:
        for (i) in device_list:
            outfile.write('\n{:15}, {:15}, {}'.format(i['ip'], i['netmiko_platform'], i['name']))
    
    log('# Finished writing devices to file.', proc='update_pending_list')

    