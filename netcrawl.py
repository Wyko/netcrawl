from gvars import MAIN_DB_PATH, RUN_PATH, DEVICE_DB_PATH
from device_dispatcher import create_instantiated_device
from time import sleep

from wylog import logging, log

import sys, argparse, textwrap, os, util, io_sql, gvars 
import queue, multiprocessing

def normal_run(**kwargs):
    proc= 'main.normal_run'
    log('Starting Normal Run', proc= proc, v= log.H)

    # Connect to the databases
    main_db = io_sql.main_db(**kwargs)
    device_db = io_sql.device_db(**kwargs)

    # Add the seed device if a target was specified  
    if 'target' in kwargs:
        nlist.add_device_d(ip= kwargs['target'], 
                           netmiko_platform= kwargs.get('netmiko_platform', 'unknown'))

    # Set the number of sub-processes
    num_workers = multiprocessing.cpu_count() * 16
        
    # Establish communication queues
    tasks = multiprocessing.JoinableQueue(num_workers*2)
    results = multiprocessing.Queue()
    
    # Create workers and start them
    workers= [worker(tasks, 
                     results, 
                     v= util.VERBOSITY,)
              for i in range(num_workers)]
    for w in workers: w.start()
    
    while True: 
        
        #################### Add Devices To Queue #######################
        # While there are pending neighbors, process each one
        while ((nlist.count_pending() >= 0) and
            (tasks.full() == False)): 
            
            # Get the next device
            device_d = nlist.get_next()
            if device_d is None: break
            
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
                    proc= proc, v= log.N)
                nlist.set_processed(device_d['device_id'])
                continue
        
            log('---- Adding to queue: {name} at {ip} || {pending} devices pending ----'.format(
                ip= device_d.get('ip', None), 
                name= (device_d.get('device_name') if device_d.get('device_name') is not None 
                       else '[Unknown Device]'), 
                pending= nlist.count_pending()), 
                proc= proc, v= log.H)
            
            tasks.put(device_d)

        
        ################### Get results from the queue ###################
        results_pool= []
        while not results.empty(): 
            log('Getting subprocess results', proc= proc, v= log.D)
            try: results_pool.append(results.get_nowait())
            except queue.Empty: 
                log('Queue Empty', proc= proc, v= log.D)
                break
            else: log('Got a result', proc= proc, v= log.D)
        
        log('Got [{}] subprocess results'.format(
                len(results_pool)), proc= proc, v= log.I)
        
        ############# Insert Processed Devices Into Database #############
        for result in results_pool:
            # Record the device as being processed and save it
            log('Setting result [{}] as processed'.format(result['original']['ip']), proc= proc, v= log.I)
            nlist.set_processed(result['original']['device_id'])
            
            log('Adding result [{}] to Visited'.format(result['original']['ip']), proc= proc, v= log.I)
            vlist.add_device_d(result['original'])
        
            if ((result['error'] is not None) or 
                (result['device'].failed)): continue 
                
            else: 
                # Add a successfully polled device to the database
                log('Adding result [{}] to Devices'.format(result['original']['ip']), proc= proc, v= log.I)
                dlist.add_device_nd(result['device']) 
    
                # Save the device config and the device neighbors 
                log('Saving result [{}] Neighbors'.format(result['original']['ip']), proc= proc, v= log.I)
                nlist.add_device_neighbors(result['device'])
                result['device'].save_config()
                
                log('Successfully processed {}'.format(result['device'].device_name), 
                    proc= proc, v= log.H)
        
        sleep(1)
        log('Main loop done.', proc= proc, v= log.I)
    
    # Close the connections to the databases
    main_db.close()
    device_db.close()    
    
    log('Normal run complete. {} devices pending.'.
            format(nlist.count_pending()), proc= proc, v= log.H)


class worker(multiprocessing.Process):
    
    def __init__(self, 
                 task_queue, 
                 result_queue,
                 v= 4, # Verbosity
                 ):
        
        multiprocessing.Process.__init__(self)
        self.result_queue = result_queue
        self.task_queue = task_queue
        self.v= v
    
    def run(self):
        util.VERBOSITY= self.v
        proc= '{}.run'.format(self.name)
        while True:
            
            log('{}: Awaiting task. Queue size: [{}]'.format(
                                                self.name,
                                                self.task_queue.qsize()),
                                                v= log.I,
                                                proc= proc)
            # Get the next device in the queue
            next_device = self.task_queue.get()
            
            # Poison pill means shutdown
            if next_device is None:
                log('{}: Got poision pill. Walking into the light...'.format(
                    self.name, self.task_queue.qsize()), v= log.N, proc= proc)
                
                self.task_queue.task_done()
                break
            
            log('{}: Got IP [{}], Device [{}]'.format(self.name, 
                                                      next_device.get('ip', 'Unknown IP'),
                                                      next_device),
                                                      v= log.N, proc= proc, 
                                                      ip= next_device.get('ip', 'Unknown IP'))
            
            # Prepare the result set to pass back to the main proccess
            result={
                'device': None,
                'log': None,
                'error': None,
                'original': next_device,
                }
            
            # Create an inherited device class object
            try: result['device']= create_instantiated_device(**next_device)
            except TypeError as e:
                result['log']= 'Device could not be instantiated.\n'
                result['error']= e 
                self.task_queue.task_done()
                self.result_queue.put(result)
                continue
                
            # Poll the device
            try: result['device'].process_device()
            except Exception as e:
                result['log']= 'Connection to {} failed: {}'.format(result['device'].ip, str(e))
                result['error']= e                                                    
            
            # Set the connection to None in order to allow Pickling
            result['device'].connection= None
            
            # Put the result on the device queue and signal done
            self.task_queue.task_done()
            self.result_queue.put(result)
        return
            


def scan_range(_target= '10.20.254.15', **kwargs):
    '''Ping each host in a given range one at a time. When a live host
    is found, add it to the pending hosts list and run the normal_scan
    method.''' 
    proc= 'main.scan_range'
     
    import nmap, json
    
    log('Starting host scan on target ' + _target, proc= proc, v= log.H)
    
    nm= nmap.PortScanner()
    vlist = io_sql.visited_db(MAIN_DB_PATH, **kwargs)
    nlist = io_sql.neighbor_db(MAIN_DB_PATH, **kwargs)
    
    # Use NMAP's nice target specification feature
    # to get a list of all the hosts to scan
    hosts= nm.listscan(_target)
    
    for h in hosts:
        
        # Skip hosts we've already discovered
        if vlist.ip_exists(h) or nlist.ip_exists(h): 
            log(h + ' already visited, skipping.', v= log.D, proc= proc)
            continue
        
        # Scan the host
        nm.scan(h, '22, 23', '-sV -T5')
        
        # Continue loop if the host is down
        if not nm.has_host(h): 
            log(h + ' is down', v= log.D, proc= proc)
            continue
        else:
            log(h + ' is ' + nm[h].state(), v= log.D, proc= proc)
        
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
                         proc= proc, v= log.N)
        
    log('Finished scanning hosts', proc= proc, v= log.H)

def single_run(ip, netmiko_platform, **kwargs):
    proc= 'main.single_run'
    
    log('Processing connection to {}'.format(ip), proc= proc, v= log.H)
    
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
        description=textwrap.dedent(
            '''\
            Netcrawl is a network discovery tool designed to poll one or 
            more devices, inventory them in a SQL database, and then 
            continue the process through the device's neighbors. It offers
            integration with Nmap to discover un-connected hosts.'''))
    
    polling = parser.add_argument_group('Options')
    scanning = parser.add_argument_group('Scan Type')
    scantype= scanning.add_mutually_exclusive_group()
    target= parser.add_argument_group('Target Specification')
    
    polling.add_argument(
        '-v',
        type= int,
        dest= 'v',
        default= logging.N,
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
        '-d',
        '--debug',
        action="store_true",
        dest= 'debug',
        help= textwrap.dedent(
        '''\
        Enables debug messages. If this is not specified, a Verbosity level
            of 5 or greater has no effect since those messages will be 
            ignored anyway. If Debug is enabled and V is less than 5, 
            debug messages will only be printed to the log file.
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
        help= 'Hostname or IP address of a starting device'
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
    
    # Parse CLI arguments
    if len(sys.argv[1:]) > 0: 
        args = parse_cli()
          
        # Set verbosity level for wylog
        util.VERBOSITY = args.v
        util.PRINT_DEBUG = args.debug
          
        # Create the directory to host the logs and other files
        if not os.path.exists(RUN_PATH):
            os.makedirs(RUN_PATH)
          
        if args.network_scan:
            if args.host: 
                log('##### Starting Scan #####', proc= proc, v= log.H)
                scan_range(args.host,
                           clean= args.clean)
                log('##### Scan Complete #####', proc= proc, v= log.H)
            else:
                print('--target (-t) is required when performing a network scan (-ns)')
           
        elif args.recursive: 
            log('##### Starting Recursive Run #####', proc= proc, v= log.H)
            
            normal_run(
                target= args.host, 
                netmiko_platform= args.platform, 
                resume= args.resume,
                clean= args.clean,
                )
            log('##### Recursive Run Complete #####', proc= proc, v= log.H)
           
        else: 
            log('##### Starting Single Run #####', proc= proc, v= log.H)
            single_run(
                ip= args.host, 
                netmiko_platform= args.platform,
                resume= args.resume,
                clean= args.clean,
                )
            log('##### Single Run Complete #####', proc= proc, v= log.H)
        
    else:
        print('No arguments passed.')
       
       
     
    
    
    