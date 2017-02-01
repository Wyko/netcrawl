from datetime import datetime
from cisco import get_device

from io_file import log, log_failed_device
from io_file import write_device
from io_file import load_index
from io_file import update_index

from time import sleep
from os.path import isfile
from global_vars import TIME_FORMAT 

import global_vars
import os



# This array store the devices we haven't visited yet
pending_devices = [('10.1.199.26', 'cisco_ios')]

# This is the index of devices we have visited
index = ''
 
    

def load_pending_devices():
    
    # The list containing found devices
    new_devices = []
    
    # Process each device in the pending list
    for i, (ip, platform) in enumerate(pending_devices):
        print('# ------------')
        log('# load_pending_devices: Processing %s' % ip)
        
        try: 
            device = get_device(ip, platform)
        except Exception as e:
            log_failed_device('! load_pending_devices: Failed to get device %s due to error: %s' % (ip, str(e)), ip, e)
            pending_devices.pop(i)
            raise
            continue
        
        # Remove the offending device
        if not device: 
            log('# load_pending_devices: No device found: %s' % ip)
            pending_devices.pop(i)
            continue
        
        log('# load_pending_devices: Found %s' % device.device_name)
        
        write_device(device)
        add_to_index(device)

        
        # Populate the pending devices with unknown devices
        for neighbor in device.neighbors:           
            if not is_platform_allowed(neighbor['netmiko_platform']): 
                log('# Neighbor %s:%s rejected due to platform.' % (neighbor['ip'], neighbor['system_platform'])) 
                continue
            
            if not in_index([neighbor['ip']]):
                new_devices.append((neighbor['ip'], neighbor['netmiko_platform']))
        
        # Remove the processed device from the list
        pending_devices.pop(i)
    
    pending_devices.extend(new_devices)
    log('# load_pending_devices: Loop completed. %s new IP\'s found' % str(len(new_devices)))
            


def is_platform_allowed(platform):
    # List of desirable platforms
    platform_list = [
        'cisco_ios',
        'cisco_nxos'
        ]
    
    if platform in platform_list: 
        return True
    else:
        return False


def in_index(ip_list):
    """Checks if the given Network Device is in the index.
    
    Args:
        index (string): The full index.
        ip_list (list): A list of one or more ip addresses
    
    Returns:
        Integer: The line number of the index entry of a matched device
        Boolean: False if the device is not in the index
    """
    
    # If the IP list is empty:
    if not ip_list: return False
    
    # Check every entry in the index to see if an IP matches.
    for i, entry in enumerate(index):
        if entry['ip'] in ip_list:
            return i
    
    return False


    

def add_to_index(device):
    # Get the interface IP's from the device 
    ip_list = device.get_ips()
    
    # For each IP in the list, check if it's already in the index
    for ip in ip_list:
        
        # If it's not in the index, add it
        if not in_index([ip]):
            entry = {
                'ip': ip,
                'serial': device.first_serial(),
                'updated': datetime.now().strftime(TIME_FORMAT)
                } 
            index.append(entry)
        
        else: 
            log('? %s already in index.' % ip)
            
    
    
if __name__ == "__main__":
    log('# ----- Starting new run -----')
       
    # Populate the index
    global index
    index = load_index()
    
    while True:
        load_pending_devices()
        update_index(index)
        
        if not pending_devices: break
        sleep(1)   
    
    
    
    log('# ----- Finishing run -----')