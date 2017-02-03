from datetime import datetime
from cisco import get_device

from io_file import log, log_failed_device, write_device
from io_file import load_neighborhood, update_neighborhood, update_pending_devices 
from time import sleep
from global_vars import TIME_FORMAT 
from concurrent.futures._base import PENDING



# This array store the devices we haven't visited yet
pending_devices = [{'ip': '10.1.103.3', 
                   'netmiko_platform': 'cisco_ios', 
                   'name': ''}]

# This is the index of devices we have visited
index = ''

# This is the list of failed devices
failed_devices = []
    

def process_pending_devices():
    
    # The list containing found devices
    new_devices = []
    
    # This list contains all the devices already processed
    processed_devices = []
    
    # Process each device in the pending list
    for i, pending_device in enumerate(pending_devices):
        log('---------------------------------------------')
        log('# Processing pending device {} of {}'.format(str(i+1), len(pending_devices)), proc ='process_pending_devices')
        log('# Processing connection to {1} at {0}'.format(pending_device['ip'], pending_device['name']), proc='process_pending_devices')
        
        # Skip devices which have already been processed
        # This happens when multiple devices see the same neighbor
        if pending_device in processed_devices: 
            log('? Device {1} at {0} has already been processed. Skipping.'.format(
                pending_device['ip'], 
                pending_device['name']), 
                proc='process_pending_devices')
            continue
        
        
        try: device = get_device(pending_device['ip'], 
                                 pending_device['netmiko_platform'])
        except Exception as e:
            failed_devices.append(pending_device['ip'])
            log_failed_device('! Failed connection to {1} at {0}'.format(
                pending_device['ip'], 
                pending_device['name']), 
                pending_device['ip'], 
                e, 
                cdp_name=pending_device['name'],
                proc= 'process_pending_devices')
            
            processed_devices.append(pending_devices[i])
            continue
        
        # Remove the offending device
        if not device: 
            failed_devices.append(pending_device['ip'])
            log_failed_device('! Connected but returned nothing: {1} at {0}'.format(
                pending_device['ip'], 
                pending_device['name']), 
                pending_device['ip'], 
                cdp_name=pending_device['name'],
                proc='process_pending_devices')
            
            processed_devices.append(pending_devices[i])
            continue
        
        log('# Found %s' % device.device_name, proc='process_pending_devices')
        
        # Save the device to disk and add all known IP's to the index
        write_device(device)
        add_to_neighborhood(device)
        
        # Populate the pending devices list with all of the newly 
        # found, previously unknown devices
        for neighbor in device.neighbors:           
            
            # Throw out all of the devices whose platform is not recognized  
            if not is_platform_allowed(neighbor['netmiko_platform']): 
                log('? Neighbor %s:%s rejected due to platform.' % (
                    neighbor['ip'], 
                    neighbor['system_platform']), 
                    proc='process_pending_devices',
                    print_out=False
                    ) 
                continue
            
            # Check if the device is a known device.
            # If not, add it to the list of devices to check
            if (not in_neighborhood([neighbor['ip']]) and 
                not in_failed_list(neighbor['ip']) and
                not in_pending(neighbor['ip'])
                ):
                new_devices.append(neighbor)
        
        
        # Add the processed device to the list of completed devices
        processed_devices.append(pending_devices[i])
        
        # Save the pending devices list to disk
        update_pending_devices(pending_devices)
        update_neighborhood(index) 
    
    
    for x in processed_devices:
        if x in pending_devices: 
            pending_devices.remove(x)
            log('? Processed device {} removed from pending.'.
                format(x['name']),
                proc = 'process_pending_devices'
                )
        
    pending_devices 
    pending_devices.extend(new_devices)
    log('# Loop completed. %s new neighbors found' % str(len(new_devices)), proc='process_pending_devices')
            


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


def in_pending(ip):
    for pending_device in pending_devices:
        if ip == pending_device['ip']: 
            log('# {} already pending.'.format(ip), proc='in_pending')
            return True
        
    return False
    


def in_neighborhood(ip_list):
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


def in_failed_list(ip):
    if ip in failed_devices: 
        log('# {} previously failed.'.format(ip), proc='in_failed_list')
        return True
    else: 
        return False 
    
    

def add_to_neighborhood(device):
    log('# Adding device {} to the neighborhood'.format(device.device_name), proc='add_to_neighborhood')
    
    # Get the interface IP's from the device 
    ip_list = device.get_ips()
    log('# This device has {} ip(\'s)'.format(len(ip_list)), proc='add_to_neighborhood')
        
    # For each IP in the list, check if it's already in the index
    for ip in ip_list:
        
        # If it's not in the index, add it
        if not in_neighborhood([ip]):
            entry = {
                'ip': ip,
                'name': device.device_name,
                'updated': datetime.now().strftime(TIME_FORMAT)
                } 
            index.append(entry)
            log('# Adding {} to neighborhood'.format(entry), print_out=False, proc='add_to_neighborhood')
            
        else: 
            log('? %s already in the neighborhood.' % ip, proc='add_to_neighborhood')
            
    
    
if __name__ == "__main__":
    log('# ----- Starting new run -----', proc = 'main')
       
    # Populate the index
    index = load_neighborhood()
    
    while True:
        process_pending_devices()
        if not pending_devices: break
        sleep(1)   

    
    log('# ----- Finishing run -----', proc = 'main')