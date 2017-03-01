from gvars import MAIN_DB_PATH, RUN_PATH, DEVICE_DB_PATH
from device_dispatcher import create_instantiated_device
from util import log, getCreds

import sys, argparse, textwrap, os, util, io_sql, gvars

    

def normal_run(**kwargs):
    proc= 'main.normal_run'
    log('Starting Normal Run', proc= proc, v= util.H)
    
    # Load the databases
    vlist = io_sql.visited_db(MAIN_DB_PATH, **kwargs)
    nlist = io_sql.neighbor_db(MAIN_DB_PATH, **kwargs)
    dlist = io_sql.device_db(DEVICE_DB_PATH, **kwargs)

    # Add the seed device    
    if 'target' in kwargs:
        nlist.add_device_d(ip= kwargs['target'], 
                           netmiko_platform= kwargs.get('netmiko_platform', 'unknown')
                           )
    
    # While there are pending neighbors, process each one
    while nlist.count_pending() > 0:
        
        # Get the next device from the pending list
        device_d = nlist.get_next()
        assert device_d is not None, 'No device returned'
        
        # Skip devices which have already been processed
        if (kwargs.get('skip_named_duplicates', False) and 
            vlist.ip_name_exists(device_d.get('ip', None), device_d.get('device_name', None))):
            visited= True           
        elif vlist.ip_exists(device_d.get('ip', None)): 
            visited= True
        else: visited= False
        
        if visited:
            log('- Device {1} at {0} has already been processed. Skipping.'.format(
                device_d.get('ip', None), device_d.get('device_name', None)), 
                proc= proc, v= util.N)
            nlist.set_processed(device_d['device_id'])
            continue
        
        log('---- Processing {name} at {ip} || {pending} devices pending ----'.format(
            ip= device_d.get('ip', None), 
            name= (device_d.get('device_name') if device_d.get('device_name') is not None 
                   else '[Unknown Device]'), 
            pending= nlist.count_pending()), 
            proc= proc, v= util.H)
        
        device= _process_device(device_d)
        
        # Record the device as being processed and save it
        nlist.set_processed(device_d['id'])
        vlist.add_device_d(device_d)
        
        if device is None: continue 
            
        else: 
            # Add a successfully polled device to the database
            dlist.add_device_nd(device)

            # Save the device config and the device neighbors 
            nlist.add_device_neighbors(device)
            device.save_config()
            
            log('Successfully processed {}'.format(device.device_name), 
                proc= proc, v= util.H)
    
    log('Normal run complete. {} devices pending.'.
            format(nlist.count_pending()), proc= proc, v= util.H)


def _process_device(device_d):
    
    # Create an inherited device class object
    try: device= create_instantiated_device(**device_d)
    except TypeError as e:
        log('Device could not be instantiated.', error= e, v= util.A, proc= proc) 
        return None
        
    # Poll the device
    try: device.process_device()
    except Exception as e:
        log('Connection to {} failed: {}'.format(device.ip, str(e)), proc= proc, v=util.C)
        return None
    
    return device


def scan_range(_target= '10.20.254.15', **kwargs):
    '''Ping each host in a given range one at a time. When a live host
    is found, add it to the pending hosts list and run the normal_scan
    method.''' 
    proc= 'main.scan_range'
     
    import nmap, json
    
    log('Starting host scan on target ' + _target, proc= proc, v=util.H)
    
    nm= nmap.PortScanner()
    vlist = io_sql.visited_db(MAIN_DB_PATH, **kwargs)
    nlist = io_sql.neighbor_db(MAIN_DB_PATH, **kwargs)
    
    # Use NMAP's nice target specification feature
    # to get a list of all the hosts to scan
    hosts= nm.listscan(_target)
    
    for h in hosts:
        
        # Skip hosts we've already discovered
        if vlist.ip_exists(h) or nlist.ip_exists(h): 
            log(h + ' already visited, skipping.', v=util.D, proc= proc)
            continue
        
        # Scan the host
        nm.scan(h, '22, 23', '-sV -T5')
        
        # Continue loop if the host is down
        if not nm.has_host(h): 
            log(h + ' is down', v=util.D, proc= proc)
            continue
        else:
            log(h + ' is ' + nm[h].state(), v=util.D, proc= proc)
        
        # Add newly discovered devices to the database
        if (
            (nm[h].has_tcp(22) and nm[h].tcp(22).get('state') == 'open') or
            (nm[h].has_tcp(23) and nm[h].tcp(23).get('state') == 'open')
            ):
            nlist.add_device_d({
                            'netmiko_platform': 'unknown',
                            'raw_cdp': json.dumps(nm[h], sort_keys=True, indent=4),
                            'ip': h,
                            })
            log('Found: {}, Port 22: {}, Port 23: {}'.format(h, 
                         nm[h].tcp(22).get('state', 'Unknown'),
                         nm[h].tcp(23).get('state', 'Unknown')),
                         proc= proc, v=util.N)
        
    log('Finished scanning hosts', proc= proc, v= util.H)

def single_run(ip, netmiko_platform, **kwargs):
    proc= 'main.single_run'
    
    log('Processing connection to {}'.format(ip), proc= proc, v= util.H)
    
    device = create_instantiated_device(ip= ip, netmiko_platform= netmiko_platform)
    
    # Process the device
    try: device.process_device()
    except Exception as e:
        device.alert(msg= 'Connection to {} failed: {}'.format(device.ip, str(e)), proc= proc)
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
    
    polling = parser.add_argument_group('Options')
    scanning = parser.add_argument_group('Scan Type')
    scantype= scanning.add_mutually_exclusive_group()
    target= parser.add_argument_group('Target Specification')
    
    polling.add_argument(
        '-v',
        type= int,
        dest= 'v',
        default= util.NORMAL,
        choices= range(7),
        metavar= 'LEVEL',
        help= textwrap.dedent(
            '''\
            Verbosity level. Logs with less importance than 
                the global verbosity level will not be processed.
                1: Critical alerts
                2: Non-critical alerts 
                3: High level info
                4: Normal level
                5: Informational level
                6: Debug level info (All info)''')
        )
    

    polling.add_argument(
        '-r',
        '--resume',
        action="store_true",
        dest= 'resume',
        help= textwrap.dedent(
        '''\
        Resume the last scan, if one was interrupted midway. Omitting
            this argument is not the same as using -c; Previous database
            entries are maintained. Scan starts with the seed device. All
            neighbor entries marked pending are reset.
        '''),
        default = False
        )
    
    polling.add_argument(
        '-c',
        '--clean',
        action="store_true",
        dest= 'clean',
        help= 'Delete all existing database entries and rebuild the databases.',
        default = False
        )
    
    polling.add_argument(
        '-sd',
        '--skip-named-duplicates',
        action="store_true",
        dest= 'skip_named_duplicates',
        help= 'If a CDP entry has the same host name as a previously visited device,'
        ' ignore it.',
        default = False
        )
    
    scantype.add_argument(
        '-sR',
        '--recursive',
        action="store_true",
        dest= 'recursive',
        help= textwrap.dedent(
        '''\
        Recursively scan neighbors for info. --target is not required,
            but if it is supplied then the device will be added as a 
            scan target. Target will accept a single IP or hostname.
        '''),
        default = True
        )
    
    scantype.add_argument(
        '-sS',
        '--single',
        action="store_true",
        dest= 'recursive',
        help= textwrap.dedent(
        '''\
        Scan one seed device for info. --target is required.
            Target will accept a single IP or hostname.
        '''),
        default = False
        )
    
    scantype.add_argument(
        '-sN',
        '--scan-network',
        action="store_true",
        dest= 'network_scan',
        help= textwrap.dedent(
        '''\
        Performs an NMAP scan against a specified target. 
            --target is required. Target will accept a 
            Nmap-compatible target identifier. Examples:
            10.1.1.1
            192.168.0-255.1
        '''),
        )
    
    target.add_argument(
        '-t',
        '--target',
        action='store',
        dest='host',
        metavar= 'TARGET',
        help= 'Hostname or IP address of the starting device'
        )
    
    target.add_argument(
        '-p',
        dest= 'platform',
        metavar= 'PLATFORM',
        help= 'The Netmiko platform for the device',
        default = 'Unknown'
        )
    
    args = parser.parse_args()
    
#     if (not args.host):
#         parser.error('Host not specified')
     
    return args


    
if __name__ == "__main__":
    proc= 'main.__main__'
    
#     scan_range()
    # Parse CLI arguments
    if len(sys.argv[1:]) > 0: 
        args = parse_cli()
          
        # Set verbosity level for logging
        util.VERBOSITY = args.v
          
        # Create the directory to host the logs and other files
        if not os.path.exists(RUN_PATH):
            os.makedirs(RUN_PATH)
          
        if args.network_scan:
            if args.host: 
                log('##### Starting Scan #####', proc= proc, v= util.H)
                scan_range(args.host,
                           clean= args.clean)
                log('##### Scan Complete #####', proc= proc, v= util.H)
            else:
                print('--target (-t) is required when performing a network scan (-ns)')
           
        elif args.recursive: 
            log('##### Starting Recursive Run #####', proc= proc, v= util.H)
            
            normal_run(
                target= args.host, 
                netmiko_platform= args.platform, 
                resume= args.resume,
                clean= args.clean,
                )
            log('##### Recursive Run Complete #####', proc= proc, v= util.H)
           
        else: 
            log('##### Starting Single Run #####', proc= proc, v= util.H)
            single_run(
                ip= args.host, 
                netmiko_platform= args.platform,
                resume= args.resume,
                clean= args.clean,
                )
            log('##### Single Run Complete #####', proc= proc, v= util.H)
        
    else:
        print('No arguments passed.')
       
       
     
    
    
    