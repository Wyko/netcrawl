from io_file import log_failed_device
from cisco import get_device
from util import log
from global_vars import MAIN_DB_PATH, RUN_PATH, DEVICE_DB_PATH
import sys, argparse, textwrap, os, util, io_sql
    

def normal_run(ip= None, netmiko_platform= 'cisco_ios', **kwargs):
    log('Starting Normal Run', proc= 'main.normal_run', v= util.H)
    
    # Load the databases
    vlist = io_sql.visited_db(MAIN_DB_PATH, **kwargs)
    nlist = io_sql.neighbor_db(MAIN_DB_PATH, **kwargs)
    dlist = io_sql.device_db(DEVICE_DB_PATH, **kwargs)
    
    # Add the seed device
    nlist.add_device_d(ip= ip, netmiko_platform= netmiko_platform)
    
    # Process each device in the pending list
    while nlist.count_pending() > 0:
        
        # Get the next device from the pending list
        device_d = nlist.get_next()
        if not device_d:
            log('No device returned.', proc= 'main.normal_run', v= util.C)
            break
        
        # Skip devices which have already been processed
        # This happens when multiple devices see the same neighbor
        if vlist.ip_exists(device_d['ip']): 
            log('- Device {1} at {0} has already been processed. Skipping.'.format(device_d['ip'],device_d['name']), proc='normal_run', v= util.N)
            nlist.set_processed(device_d['id'])
            continue

        log('---- Processing {name} at {ip} || {pending} devices pending ----'.format(
            ip= device_d['ip'], name= device_d['name'], pending= nlist.count_pending()), 
            proc='main.normal_run', v= util.H)
    
        try: device = get_device(device_d['ip'], 
                                device_d['netmiko_platform'],
                                name = device_d['name'])
        except Exception as e:
            # Add the device to the list of visited devices
            log(msg= 'Failed to start cli connection to {0}'.format(device_d['ip']), 
                ip= device_d['ip'], 
                error= e,
                proc= 'main.normal_run',
                v= util.C)
            
            vlist.add_device_d(device_d)
            nlist.set_processed(device_d['id'])
            continue
        
        if device.failed:
            # Add the device to the list of visited devices
            log(msg= 'Failed connection to {} due to: {}'.format(device_d['ip'], device.failed_msg), 
                ip= device_d['ip'], 
                proc= 'main.normal_run',
                v= util.C)
            
            vlist.add_device_d(device_d)
            nlist.set_processed(device_d['id'])
            
            # Add the failed device to the list
            dlist.add_device_nd(device)
            continue
        
        # Set the device as processed
        log('Successfully processed {}'.format(device.device_name), 
            proc='process_pending_list', v= util.NORMAL)
        nlist.set_processed(device_d['id'])
         
        # Save the device to disk 
        device.save_config()
        
        # Save the device's neighbors to the database
        nlist.add_device_neighbors(device)
        
        # Add the device to the visited list
        vlist.add_device_nd(device)
        
        # Save the device to the device database
        dlist.add_device_nd(device)

    
    log('Normal run complete. {} devices pending.'.
            format(nlist.count_pending()), proc ='main.normal_run', v= util.H)



def single_run(ip, platform):
    log('Processing connection to {}'.format(ip), proc='main.single_run', v= util.H)
    
    # Process the device
    try: device = get_device(ip, platform)
    except Exception as e:
        # Add the device to the list of failed and processed devices
        log_failed_device(
            msg= 'Failed to start cli connection to {0}'.format(ip), 
            ip= ip, 
            error= e,
            proc= 'single_run'
            )
        return False
    
    dlist = io_sql.device_db(DEVICE_DB_PATH)
    dlist.add_device_nd(device)
    dlist.db.close()
    # Output the device info to console
    print('\n' + str(device) + '\n')
    print(device.neighbor_table())
     
    return True



def parse_cli():
    parser = argparse.ArgumentParser(
        prog= 'NetCrawl',
        formatter_class= argparse.RawTextHelpFormatter,
        description='''
This package will process a specified host and pull information from it. If desired, it can then crawl the device's neighbors recursively and continue the process.''')
    
    parser.add_argument(
        '-v',
        type= int,
        dest= 'v',
        default= util.HIGH,
        choices= range(0, 5),
        metavar= 'LEVEL',
        help= textwrap.dedent(
            '''\
            Verbosity level. Logs with less importance than 
            the global verbosity level will not be processed.
              1: Critical alerts
              2: Non-critical alerts 
              3: High level info
              4: Common info
              5: Debug level info (All info)''')
        )
    
    parser.add_argument(
        '-p',
        dest= 'platform',
        metavar= 'PLATFORM',
        help= 'The Netmiko platform for the device',
        default = 'cisco_ios'
        )

    parser.add_argument(
        '-s',
        '--scan',
        action="store_true",
        dest= 'recursive',
        help= 'Recursively scan neighbors for info',
        default = False
        )
    
    parser.add_argument(
        '-r',
        '--resume',
        action="store_true",
        dest= 'resume',
        help= 'Resume the last scan, if one was interrupted midway. Omitting '+
            'this argument is not the same as using -c; Previous database '+
            'entries are maintained. Scan starts with the seed device.',
        default = False
        )
    
    parser.add_argument(
        '-c',
        '--clean',
        action="store_true",
        dest= 'clean',
        help= 'Ignore results of previous runs. Delete all existing database ' +
              'entries and start with a clean database.',
        default = False
        )
    
    parser.add_argument(
        'host',
        action='store',
        help= 'Hostname or IP address of the starting device'
        )
    
    
    args = parser.parse_args()
    
    if (not args.host):
        parser.error('Host not specified')
     
    return args


    
if __name__ == "__main__":
        
    # Parse CLI arguments
    if len(sys.argv[1:]) > 0: 
        args = parse_cli()
        
        # Set verbosity level for logging
        util.VERBOSITY = args.v
        
        # Create the directory to host the logs and other files
        if not os.path.exists(RUN_PATH):
            os.makedirs(RUN_PATH)
        
        log('##### Starting Run #####', proc= 'main.__main__', v= util.H)
         
        if args.recursive: 
            normal_run(
                ip= args.host, 
                netmiko_platform= args.platform, 
                resume= args.resume,
                clean= args.clean,
                )
         
        else: 
            single_run(ip= args.host, platform= args.platform)
     
    else:
        print('No arguments passed. Host is required.')
     
     
    log('##### Run Complete #####', proc= 'main.__main__', v= util.H)
     
    
    
    