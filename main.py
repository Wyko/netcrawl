from datetime import datetime
from cisco import get_device

from io_file import log, log_failed_device, write_device
from io_file import load_index, update_index, update_pending_devices 
from time import sleep
from global_vars import TIME_FORMAT 



# This array store the devices we haven't visited yet
pending_devices = [('10.1.120.1', 'cisco_ios')]

# This is the index of devices we have visited
index = ''

# This is the list of failed devices
failed_devices = []
    

def process_pending_devices():
    
    # The list containing found devices
    new_devices = []
    
    # Process each device in the pending list
    for i, (ip, platform) in enumerate(pending_devices):
        log('# -------------------------------------------')
        log('# process_pending_devices: Processing %s' % ip)
        
        try: device = get_device(ip, platform)
        except Exception as e:
            failed_devices.append(ip)
            log_failed_device('! process_pending_devices: Failed to get %s' % (ip), ip, e)
            pending_devices.pop(i)
            continue
        
        # Remove the offending device
        if not device: 
            log('! process_pending_devices: No device found with ip %s' % ip)
            pending_devices.pop(i)
            continue
        
        log('# process_pending_devices: Found %s' % device.device_name)
        
        # Save the device to disk and add all known IP's to the index
        write_device(device)
        add_to_index(device)
        
        # Populate the pending devices list with all of the newly 
        # found, previously unknown devices
        for neighbor in device.neighbors:           
            
            # Throw out all of the devices whose platform is not recognized  
            if not is_platform_allowed(neighbor['netmiko_platform']): 
                log('? process_pending_devices: Neighbor %s:%s rejected due to platform.' % (neighbor['ip'], neighbor['system_platform'])) 
                continue
            
            # Check if the device a known device.
            # If not, add it to the list of devices to check
            if (not in_index([neighbor['ip']]) and 
                not in_failed_list(neighbor['ip']) and
                not (neighbor['ip'], neighbor['netmiko_platform']) in new_devices
                ):
                new_devices.append((neighbor['ip'], neighbor['netmiko_platform']))
        
        # Remove the processed device from the list
        pending_devices.pop(i)
        
        # Save the pending devices list to disk
        update_pending_devices(pending_devices) 
    
    pending_devices.extend(new_devices)
    log('# process_pending_devices: Loop completed. %s new IP\'s found' % str(len(new_devices)))
            


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


def in_failed_list(ip):
    if ip in failed_devices: 
        log('# in_failed_list: {} previously failed.'.format(ip))
        return True
    else: 
        return False 
    

def add_to_index(device):
    log('# add_to_index: Starting on device {}'.format(device.device_name))
    
    # Get the interface IP's from the device 
    ip_list = device.get_ips()
    
    # For each IP in the list, check if it's already in the index
    for ip in ip_list:
        
        # If it's not in the index, add it
        if not in_index([ip]):
            entry = {
                'ip': ip,
                'name': device.device_name,
                'updated': datetime.now().strftime(TIME_FORMAT)
                } 
            index.append(entry)
            log('# add_to_index: Adding {}'.format(entry), print_out=False)
            
        else: 
            log('? %s already in index.' % ip)
            
    
    
if __name__ == "__main__":
    log('# ----- Starting new run -----')
       
    # Populate the index
    global index
    index = load_index()
    
    while True:
        process_pending_devices()
        update_index(index)
        
        if not pending_devices: break
        sleep(1)   
    
    
    
    log('# ----- Finishing run -----')