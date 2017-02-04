from datetime import datetime
from global_vars import TIME_FORMAT
from io_file import write_device, load_visited, update_neighborhood
from io_file import update_pending_list, write_visited_device
from time import sleep
from cisco import get_device
from utility import log
    

# This array store the devices we haven't visited yet
pending_list = [{'ip': '10.1.120.1', 
                 'netmiko_platform': 'cisco_ios', 
                 'name': ''
                 }]

visited_list = [] # This is the index of devices we have visited
failed_list = [] # This is the list of failed devices

def process_pending_list():

    global pending_list, visited_list, failed_list

    new_devices = [] # The list containing found devices
    processed_devices = [] # The list containing all processed devices
    
    # Process each device in the pending list
    for i, pending_device in enumerate(pending_list):
        log('---------------------------------------------')
        log('# Processing pending device {} of {}'.format(str(i+1), len(pending_list)), proc ='process_pending_list')
        log('# Processing connection to {1} at {0}'.format(pending_device['ip'], pending_device['name']), proc='process_pending_list')
        
        # Skip devices which have already been processed
        # This happens when multiple devices see the same neighbor
        if pending_device in processed_devices: 
            log('? Device {1} at {0} has already been processed. Skipping.'.format(pending_device['ip'],pending_device['name']), proc='process_pending_list')
            continue
        
        try: device = get_device(pending_device['ip'], 
                                 pending_device['netmiko_platform'],
                                 name = pending_device['name'])
        except:
            # Add the device to the list of failed and processed devices
            failed_list.append(pending_device['ip'])
            processed_devices.append(pending_list[i])
            continue
        
        log('# Found %s' % device.device_name, proc='process_pending_list')
        
        # Save the device to disk and add all known IP's to the index
        write_device(device)
        add_to_visited(device)
        
        # Add the processed device to the list of completed devices
        processed_devices.append(pending_list[i])
        
        # Populate the new neighbor list with all newly found neighbors
        new_devices.extend(get_new_neighbors(device))
        
    
    # Remove processed devices from pending devices
    pending_list = [x for x in pending_list if x not in processed_devices]
#     for x in processed_devices:
#         if x in pending_list: 
#             pending_list.remove(x)
#             log('? Processed device {} removed from pending.'.format(x['name']), proc = 'process_pending_list')
     
    # Add the newly found devices to the pending list    
    pending_list.extend(new_devices)

    # Save the pending devices list to disk
    update_pending_list(pending_list)
        
    log('# Loop completed. %s new neighbors found' % str(len(new_devices)), proc='process_pending_list')
            


def get_new_neighbors(device):
    """Given a network_device object, iterate all its neighbors and:
        1. Skip if is has an invalid netmiko platform
        2. Skip if it is a known device
        3. Return the newly discovered neighbors
    
    Args:
        device (network_device)
    
    Returns:
        List of Dicts: List of neighbors as defined in cdp.parse_neighbor
    """
    
    new_neighbors = []
    
    for neighbor in device.neighbors:           
        # Throw out all of the devices whose platform is not recognized  
        if not is_platform_allowed(neighbor['netmiko_platform']): 
            log('? Neighbor %s:%s rejected due to platform.' % (
                neighbor['ip'], 
                neighbor['system_platform']), 
                proc='process_pending_list',
                print_out=False
                ) 
            continue
        
        # Check if the ip is a known address.
        # If not, add it to the list of ips to check
        if (not in_visited([neighbor['ip']]) and 
            not in_failed_list(neighbor['ip']) and
            not in_pending(neighbor['ip'])
            ):
            new_neighbors.append(neighbor)
            
    return new_neighbors


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
    global pending_list
    for x in pending_list:
        if ip == x['ip']: 
            log('# {} already pending.'.format(ip), proc='in_pending')
            return True
    return False
    

def in_failed_list(ip):
    global failed_list
    if ip in failed_list: 
        log('# {} previously failed.'.format(ip), proc='in_failed_list')
        return True
    else: 
        return False 


def in_visited(ip):
    global visited_list
    for x in visited_list:
        if ip == x['ip']: 
            return True
    return False
    

def add_to_visited(device):
    """Given a network_device object:
        1. Create a dict for each ip address in the device, in the format: 
        entry = {
                'ip': 
                'name': 
                'serial': 
                'updated':
                }
        2. Save each entry to visited.db
        3. Add each entry to visited_list to keep the list in memory
    """
    
    log('# Adding device {} to the visited list'.format(device.device_name), proc='add_to_visited')
    
    # Get the IP's from the device 
    ip_list = device.get_ips()
    log('# This device has {} ip(\'s)'.format(len(ip_list)), proc='add_to_visited')
        
    # For each IP in the list, check if it's already in the index
    for ip in ip_list:
        
        # If the ip is not already in visited.db, add it
        if not in_visited(ip):
            entry = {
                'ip': ip,
                'name': device.device_name,
                'serial': device.first_serial(),
                'updated': datetime.now().strftime(TIME_FORMAT)
                } 
            
            global visited_list
            visited_list.append(entry)
            write_visited_device(entry)
            log('# Adding {} to visited list'.format(entry), print_out=False, proc='add_to_visited')
            
        else: 
            log('? {1} at {0} was already visited. Skipping.'.format(ip, device.device_name), proc='add_to_visited')
            continue
            



    
if __name__ == "__main__":
    log('# ----- Starting new run -----', proc = 'main')
       
    # Populate the index
    index = load_visited()
    
    while True:
        process_pending_list()
        if not pending_list: break
        sleep(1)   

    
    log('# ----- Finishing run -----', proc = 'main')