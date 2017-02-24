from gvars import MAIN_DB_PATH, RUN_PATH, DEVICE_DB_PATH
from ssh_dispatcher import ConnectHandler
from util import log

import sys, argparse, textwrap, os, util, io_sql, gvars
    

def normal_run(ip, netmiko_platform, **kwargs):
    log('Starting Normal Run', proc= 'main.normal_run', v= util.H)
    
    # Load the databases
    vlist = io_sql.visited_db(MAIN_DB_PATH, **kwargs)
    nlist = io_sql.neighbor_db(MAIN_DB_PATH, **kwargs)
    dlist = io_sql.device_db(DEVICE_DB_PATH, **kwargs)
    
    # Add the seed device
    nlist.add_device_d(ip= ip, netmiko_platform= netmiko_platform)
    
    # While there are pending neighbors, process each one
    while nlist.count_pending() > 0:
        
        # Get the next device from the pending list
        device = nlist.get_next()
        if not device:
            log('No device returned.', proc= 'main.normal_run', v= util.C)
            break
        
        # Skip devices which have already been processed
        if (kwargs.get('skip_named_duplicates', False) and 
            vlist.ip_name_exists(device.ip, device.device_name)):
            visited= True           
        elif vlist.ip_exists(device.ip): 
            visited= True
        else: visited= False
        
        if visited:
            log('- Device {1} at {0} has already been processed. Skipping.'.format(device.ip, device.device_name), proc='normal_run', v= util.N)
            nlist.set_processed(device.device_id)
            continue

        log('---- Processing {name} at {ip} || {pending} devices pending ----'.format(
            ip= device.ip, name= device.device_name, pending= nlist.count_pending()), 
            proc='main.normal_run', v= util.H)
        
        # Poll the device
        try: device.process_device()
        except Exception as e:
            device.alert('Connection to {} failed: {}'.format(device.ip, str(e)), proc= 'main.normal_run')
            if not gvars.SUPPRESS_ERRORS: raise
        
        # Record the device as being processed and save it
        nlist.set_processed(device.device_id)
        vlist.add_device_nd(device)
        dlist.add_device_nd(device)
        
        if device.failed: continue

        else:
            log('Successfully processed {}'.format(device.device_name), 
                proc='process_pending_list', v= util.NORMAL)
         
            # Save the device to disl and it's neighbors to the db 
            device.save_config()
            nlist.add_device_neighbors(device)
    
    log('Normal run complete. {} devices pending.'.
            format(nlist.count_pending()), proc ='main.normal_run', v= util.H)



def scan_range():
    pass


def single_run(ip, netmiko_platform, **kwargs):
    log('Processing connection to {}'.format(ip), proc='main.single_run', v= util.H)
    
    device = ConnectHandler(ip= ip, netmiko_platform= netmiko_platform)
    
    # Process the device
    
    try: device.process_device()
    except Exception as e:
        device.alert(msg= 'Connection to {} failed: {}'.format(device.ip, str(e)), proc= 'main.single_run')
        if not gvars.SUPPRESS_ERRORS: raise
        
    # Save the device
    dlist = io_sql.device_db(DEVICE_DB_PATH, **kwargs)
    dlist.add_device_nd(device)
    dlist.db.close()
    
    # Output the device info to console
    print('\n' + str(device) + '\n')
    print(device.neighbor_table())



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
            'entries are maintained. Scan starts with the seed device. All '+
            'neighbor entries marked pending are reset.',
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
        '-sd',
        '--skip-named_duplicates',
        action="store_true",
        dest= 'skip_named_duplicates',
        help= 'If a CDP entry has the same host name as a previously visited device,'
        ' ignore it.',
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
            single_run(
                ip= args.host, 
                netmiko_platform= args.platform,
                resume= args.resume,
                clean= args.clean,
                )
     
    else:
        print('No arguments passed. Host is required.')
     
     
    log('##### Run Complete #####', proc= 'main.__main__', v= util.H)
     
    
    
    