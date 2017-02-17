from datetime import datetime
from os.path import isfile
from global_vars import RUN_PATH, TIME_FORMAT, TIME_FORMAT_FILE
from util import log

import os, pickle
import util


def write_device(device, path='', update=True, error_code=''):
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
    
    log('Writing %s to file using pickle' % filename, proc='write_device', v= util.N)
    
    if not os.path.exists(path):
        os.makedirs(path)
    
    # Save the network_device to file
    pickle.dump(device, open( path + filename, "wb" ) )



    
def log_failed_device(msg, ip='', error='', name='',  proc=''):
    """Logs a failed device.
    
    Args:
        msg (string): The message to write.
        
    Optional Args:
        ip (string): The IP address of the device.
        error (Exception): The exception raised to cause the device to fail
        name (string): The hostname of the device, if known
        proc (string): The procedure name that failed. 
        
    Returns:
        Boolean: True if write was successful, False otherwise.
    """ 

    log(msg + ' - Error: ' + str(error), ip= ip, proc= proc, v= util.C)
       
    output = '{:19}, {:15}, {:30.29}, {}, {}'.format(
            datetime.now().strftime(TIME_FORMAT),
            ip,
            name,
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


def update_visited(_list):
    """Appends a list of visited devices to visited.db
    
    Args:
        _list (List): Visited device entries as defined in main.add_to_visited
        
    Returns:
        Boolean: True if write was successful, False otherwise.
    """ 
    
    if  type(_list) != list: _list= [_list]
    output = ''
    
    for visited_entry in _list:
        output += '{updated}, {ip:15}, {name}, {serial}\n'.format(
                updated= datetime.now().strftime(TIME_FORMAT),
                ip= visited_entry['ip'],
                name= visited_entry['name'],
                serial= visited_entry['serial'],
                )
    
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH)
    
    # Open the error log
    f = open(visited_path,'a')
    
    if f and not f.closed:
        f.write(output + '\n')
        f.close()
        return True
    
    else: return False  


def load_pending():
    """Returns a list of dicts containing all the pending devices."""
    
    log('Start populating pending devices', proc='load_pending', v= util.N)
    
    if not os.path.exists(DB_PATH):
        log('Database path not found. Creating directory.', proc='load_visited', v= util.N)
        os.makedirs(DB_PATH)

    _devices = []
    
    # Check if the file exists
    if isfile(pending_path):
        
        # Open visited.db
        with open(pending_path, 'r') as infile:
            for line in infile:
                
                #Check if the line is empty 
                line = line.strip()
                if not line: continue
                
                # Split each entry into a nice little dict object.
                line = line.split(',')
                line = [x.strip() for x in line]
                
                entry = {
                    'ip': line[0],
                    'netmiko_platform': line[1],
                    'name': line[2],
                    } 
                
                _devices.append(entry)
    
    if len(_devices) >= 1: 
        log('Finished loading pending devices. {} entries found.'.format(len(_devices)), proc='load_pending', v= util.N)
    else: 
        log('Finished. No previous entries found.', proc='load_pending', v= util.N)
        
    return _devices


def load_visited():
    """Returns a list of dicts containing all the devices we've visited."""
    
    log('Start populating visted devices', proc='load_visited', v= util.N)
    
    if not os.path.exists(DB_PATH):
        log('Database path not found. Creating directory.', proc='load_visited', v= util.N)
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
                line = [x.strip() for x in line]
                
                entry = {
                    'updated': line[0],
                    'ip': line[1],
                    'name': line[2],
                    'serial': line[3],
                    }
                
                visited_devices.append(entry)
    
    if len(visited_devices) >= 1: 
        log('Finished loading visited devices. {} entries found.'.format(len(visited_devices)), proc='load_visited', v= util.N)
    else: 
        log('Finished. No previous entries found.', proc='load_visited', v= util.N)
        
    return visited_devices


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
    
    log('Starting write. {} devices remain in pending list.'.format(len(device_list)), proc='update_pending_list', v= util.N)
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH)
    
    # Open the pending devices list, overwriting anything in it.
    with open(pending_path, 'w') as outfile:
        for (i) in device_list:
            outfile.write('\n{:15}, {:15}, {}'.format(i['ip'], i['netmiko_platform'], i['name']))
    
    log('Finished writing pending device list to file.', proc='update_pending_list', v= util.N)

    