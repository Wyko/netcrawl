from datetime import datetime
from global_vars import TIME_FORMAT
from io_file import write_device, load_visited, load_pending, save_config
from io_file import update_pending_list, update_visited, log_failed_device
from time import sleep
from cisco import get_device
from uti import log
from device_classes import network_device
import uti, sys, argparse
from email.policy import default
    

# This list of Dicts store the devices we haven't visited yet
pending_list_d = []

# List of Dicts (defined in add_to_visited) containing devices we visited
visited_list_d = []

# This is the list of ips of failed devices
failed_list_ips = []

def process_pending_list():

    global pending_list_d, visited_list_d, failed_list_ips

    new_devices = [] # The list of network_device objects containing found neighbors
    processed_devices_d = [] # The list of dicts containing all processed devices
    
    # Process each device in the pending list
    for i, device_d in enumerate(pending_list_d):
        log('---------------------------------------------', v= uti.H)
        log('Processing pending device {} of {}'.format(str(i+1), len(pending_list_d)), proc ='process_pending_list', v= uti.H)
        log('Processing connection to {1} at {0}'.format(device_d['ip'], device_d['name']), proc='process_pending_list', v= uti.H)
        
        # Skip devices which have already been processed
        # This happens when multiple devices see the same neighbor
        if in_visited(device_d['ip']) or any(device_d['ip'] == x for x in processed_devices_d): 
            log('Device {1} at {0} has already been processed. Skipping.'.format(device_d['ip'],device_d['name']), proc='process_pending_list', v= uti.N)
            processed_devices_d.append(device_d)
            continue
        
        device = network_device()
        try: device = get_device(device_d['ip'], 
                                 device_d['netmiko_platform'],
                                 name = device_d['name'])
        except Exception as e:
            # Add the device to the list of failed and processed devices
            log_failed_device(
                msg= 'Failed to start cli connection to {0}'.format(device_d['ip']), 
                ip= device_d['ip'], 
                error= e,
                proc= 'process_pending_list'
                )
            failed_list_ips.append(device_d['ip'])
            processed_devices_d.append(device_d)
            continue
        
        log('Successfully processed %s' % device.device_name, proc='process_pending_list', v= uti.NORMAL)
        
        # Save the device to disk and add all known IP's to the index
        write_device(device)
        save_config(device)
        add_to_visited(device)
        
        # Add the processed device to the list of completed devices
        processed_devices_d.append(device_d)
        
        # Populate the new neighbor list with all newly found neighbor dict entries
        new_devices.extend(get_new_neighbors(device))
        
    
    # Remove processed devices from pending devices
    pending_list_d = [x for x in pending_list_d if x not in processed_devices_d]
#     for x in processed_devices_d:
#         for y in pending_list_d:
#             if x['ip'] == y['ip']: 
#                 pending_list_d.remove(x)
#                 log('Processed device {} removed from pending.'.format(x['name']), proc = 'process_pending_list', v= uti.D)
#                 break
     
    # Add the newly found devices to the pending list    
    pending_list_d.extend(new_devices)

    # Save the pending devices list to disk
    update_pending_list(pending_list_d)
        
    log('Loop completed. %s new neighbors found' % str(len(new_devices)), proc='process_pending_list', v= uti.H)
            


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
            log('Neighbor %s:%s rejected due to platform.' % (
                neighbor['ip'], 
                neighbor['system_platform']), 
                proc='process_pending_list',
                print_out=False,
                v= uti.ALERT
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
    global pending_list_d
    for x in pending_list_d:
        if ip == x['ip']: 
            log('{} already pending.'.format(ip), proc='in_pending', v= uti.D)
            return True
    return False
    

def in_failed_list(ip):
    global failed_list_ips
    if ip in failed_list_ips: 
        log('{} previously failed.'.format(ip), proc='in_failed_list', v= uti.D)
        return True
    else: 
        return False 


def in_visited(ip):
    global visited_list_d
    for x in visited_list_d:
        if ip == x['ip']: 
            log('{} already visited.'.format(ip), proc='in_visited', v= uti.D)
            return True
    
    log('{} not in visited list.'.format(ip), proc='in_visited', v= uti.D)
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
        3. Add each entry to visited_list_d to keep the list in memory
    """
    
    log('Adding device {} to the visited list'.format(device.device_name), proc='add_to_visited', v= uti.D)
    
    # Get the IP's from the device 
    ip_list = device.get_ips()
    log('This device has {} ip(s)'.format(len(ip_list)), proc='add_to_visited', v= uti.N)
    ip_list = [ii for n,ii in enumerate(ip_list) if ii not in ip_list[:n]]
    
    counter = 0
        
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
            
            global visited_list_d
            visited_list_d.append(entry)
            update_visited(entry)
            log('Adding {} to visited list'.format(entry), print_out=False, proc='add_to_visited', v= uti.D)
            counter +=1
            
        else: 
            log('{1} at {0} was already visited. Skipping.'.format(ip, device.device_name), proc='add_to_visited', v= uti.D)
            continue
            
    log('Added {} ips to the visited list'.format(counter), proc='add_to_visited', v= uti.N)


def normal_run(ip= '10.1.120.1', platform= 'cisco_ios'):
   
    global pending_list_d, visited_list_d, failed_list_ips
    
    # Populate the index
    visited_list_d.extend(load_visited())
    pending_list_d.extend(load_pending())
    
    if not pending_list_d:
        pending_list_d = [{
            'ip': '10.30.9.40', 
             'netmiko_platform': 'cisco_ios',
             'name': ''
             }]
    
    while True:
        process_pending_list()
        if not pending_list_d: break
        sleep(1)   


def single_run(ip, platform):
    log('Processing connection to {}'.format(ip), proc='single_run', v= uti.H)
    try: device = get_device(ip, platform)
    except Exception as e:
        # Add the device to the list of failed and processed devices
        log_failed_device(
            msg= 'Failed to start cli connection to {0}'.format(ip), 
            ip= ip, 
            error= e,
            proc= 'single_run'
            )
    else:
        print('\n' + str(device) + '\n')
        print(device.neighbor_table())
    



def parse_cli():
    parser = argparse.ArgumentParser(description='''
This package will process a seed device and pull information from it. 
If desired, it will then crawl the device's neighbors recursively and continue the process.''')
    
    parser.add_argument(
        '-v',
        '--verbose',
        type= int,
        dest= 'v',
        default= uti.HIGH,
        choices= range(0, 5),
        metavar= 'LEVEL',
        help= '''Verbosity level. Logs with less importance than the global verbosity level will not be processed.
 1: Critical alerts, 2: Non-critical alerts, 3: High level info, 4: Common info, 5: Debug level info.'''
        )
    
    parser.add_argument(
        '-p',
        '--platform',
        dest= 'platform',
        metavar= 'PLATFORM',
        help= 'The Netmiko platform for the device',
        default = 'cisco_ios'
        )

    parser.add_argument(
        '-c',
        '--crawl',
        action="store_true",
        dest= 'crawl',
        help= 'Recursively scan neighbors for info',
        default = False
        )
    
    parser.add_argument(
        'host',
        action='store',
        help= 'Hostname or IP address of the starting device'
        )
    
    
    args = parser.parse_args()
    
    if (not args.host) or (not uti.is_ip(args.host)):
        parser.error('Expected IP address as seed device.')
     
    return args


    
if __name__ == "__main__":

    # Parse CLI arguments
    if len(sys.argv[1:]) > 0: 
        args = parse_cli()
        
        # Set verbosity level for logging
        uti.VERBOSITY = args.v
        
        if args.crawl: normal_run(ip= args.host, platform= args.platform)
        else: single_run(ip= args.host, platform= args.platform)
    
    
    
    #normal_run()
    
    
    
    
    