import queue, multiprocessing, traceback, json
import sys
from time import sleep

from . import config, io_sql
from .tools import mac_audit
from .credentials import menu
from .device_dispatcher import create_instantiated_device
from .wylog import logging, log, logf


# @logf
def normal_run(**kwargs):
    '''
    Starts a **Recursive Scan** (-sR) run. This is the main scanning 
    method for netcrawl.
    
    1. If a :code:`target` kwarg is given, add that seed device to
    the list of pending deivces, even if it was already
    visited.
     
    2. Create workers (subprocesses) to perform the scanning 
    work, up to 16 per CPU core, or up to the :code:`processes` 
    kwarg per core if that kwarg was given.
    
    3. Query the Pending table in the Main database for 
    pending devices.
    
    4. Autodetect the Netmiko platform for each device 
    if needed.
    
    5. Inventory the device using 
    :py:func:`netcrawl.devices.base.NetworkDevice.process_device`
    
    6. Add each discovered device to the Inventory database
    
    Keyword Args:
        target (str): The IP address of a target (seed) device
        
        netmiko_platform (str): The Netmiko platform of the seed
            device, if one was given. Used with :code:`target`
        
        processes (int): The number of worker processes to create,
            multiplied by the CPU count
            
        skip_named_duplicates (bool): If True, this will cause 
            netcrawl to skip neighbors which have the same
            hostname as a device that was previously visited.
            
            .. note:: While this can potentially save a lot of time when 
                scanning devices, if multiple different devices 
                share the same hostname, they will not be scanned!
            
        clean (bool): If True, this causes all database tables to 
            be dropped in order to start with a clean database.
            
            .. warning:: Obviously, this is really dangerous.
    '''
    
    proc = 'main.normal_run'
    log('Starting Normal Run', proc=proc, v=logging.H)

    # Connect to the databases
    main_db = io_sql.main_db(**kwargs)
    device_db = io_sql.device_db(**kwargs)

    # Add the seed device if a target was specified  
    if ('target' in kwargs) and (kwargs['target'] is not None):
        
        # Remove the seed device from visited devices
        main_db.remove_visited_record(kwargs['target'])
        
        main_db.add_pending_device_d(
            ip_list=[kwargs['target']],
            netmiko_platform=kwargs.get('netmiko_platform', 'unknown'))

    # Set the number of sub-processes
    num_workers = multiprocessing.cpu_count() * kwargs.get('processes', 16)
        
    # Establish communication queues
    tasks = multiprocessing.JoinableQueue(num_workers * 2)
    results = multiprocessing.Queue()
    
    # Create workers and start them
    workers = [worker(tasks, results) for i in range(num_workers)]
    for w in workers: w.start()
    
    try:
        while True: 
    
            #################### Add Devices To Queue #######################
            # While there are pending neighbors, process each one
            remaining = main_db.count_pending()
            while ((remaining >= 0) and (tasks.full() == False)): 
                
                # Get the next device
                device_d = main_db.get_next()
                if device_d is None: break
                
                # Skip devices which have already been visited
                if (kwargs.get('skip_named_duplicates') and 
                    main_db.ip_name_exists(ip=device_d.get('ip'),
                                           name=device_d.get('device_name'),
                                           table='visited')): visited = True  
                                                    
                elif main_db.ip_exists(ip=device_d.get('ip'),
                                       table='visited'): visited = True
                else: visited = False
                
                if visited:
                    log('- Device {1} at {0} has already been processed. Skipping.'.format(
                        device_d.get('ip', None), device_d.get('device_name', None)),
                        proc=proc, v=logging.N)
                    main_db.remove_pending_record(device_d['pending_id'])
                    continue
            
                log('---- Adding to queue: {name} at {ip} || {pending} devices pending ----'.format(
                    ip=device_d.get('ip', None),
                    name=(device_d.get('device_name') if device_d.get('device_name') is not None 
                           else '[Unknown Device]'),
                    pending=main_db.count_pending()),
                    proc=proc, v=logging.H)
                
                tasks.put(device_d)
            
            ################### Get results from the queue ###################
            results_pool = []
            while not results.empty(): 
                log('Getting subprocess results', proc=proc, v=logging.D)
                try: results_pool.append(results.get_nowait())
                except queue.Empty: 
                    log('Queue Empty', proc=proc, v=logging.D)
                    break
                else: log('Got a result', proc=proc, v=logging.D)
            
            log('Got [{}] subprocess results'.format(
                    len(results_pool)), proc=proc, v=logging.I)
            
            ############# Insert Processed Devices Into Database #############
            for result in results_pool:
                # Record the device as being processed and save it
                log('Setting result [{}] as processed'.format(result['original']['ip']), proc=proc, v=logging.I)
                main_db.remove_pending_record(result['original']['pending_id'])
                
                log('Adding result [{}] to Visited'.format(result['original']['ip']), proc=proc, v=logging.I)
                main_db.add_visited_device_d(result['original'])
            
                if ((result['error'] is not None) or 
                    (result['device'].failed)): continue 
                    
                else: 
                    # Add a successfully polled device to the database
                    log('Adding result [{}] to Devices'.format(result['original']['ip']), proc=proc, v=logging.I)
                    device_db.add_device_nd(result['device']) 
        
                    # Save the device config and the device neighbors 
                    log('Saving result [{}] Neighbors'.format(result['original']['ip']), proc=proc, v=logging.I)
                    main_db.add_device_pending_neighbors(result['device'])
                    result['device'].save_config()
                    
                    log('Successfully processed {}'.format(result['device'].device_name),
                        proc=proc, v=logging.H)
    
                    
            #################### POISION PILL ###############################
            if (remaining is 0) and tasks.empty():
                _kill_workers(tasks, num_workers)
                break
            
            sleep(1)
            log('Main loop done.', proc=proc, v=logging.I)
    
    except (KeyboardInterrupt, SystemExit):
        log('Run execution cancelled', proc=proc, v= logging.C)
    
    else:
        log('Normal run complete. 0 devices pending.',
            proc=proc, v=logging.H)
    
    finally:
        # Stop the workers
        _kill_workers(tasks, num_workers)   
        # Close the connections to the databases
        main_db.close()
        device_db.close() 
    



def _kill_workers(task_queue, num_workers):
    '''
    Sends a NoneType poision pill to all active workers.
    
    Args:
        task_queue (JoinableQueue): The task queue upon which
            to put the poision pills
        num_workers (int): The number of workers, which translates
            to the number of poision pills to put in the queue
    '''

    for w in range(num_workers): task_queue.put(None)
    

class worker(multiprocessing.Process):
    
    def __init__(self,
                 task_queue,
                 result_queue,
                 ):
        
        multiprocessing.Process.__init__(self)
        self.result_queue = result_queue
        self.task_queue = task_queue
        self.cc = config.cc
    
    def run(self):
        proc = '{}.run'.format(self.name)
        
        # Reset global variables since subprocesses may not
        # inherit parent runstates
        config.cc= self.cc
        
        try:
            while True:
                
                log('{}: Awaiting task. Queue size: [{}]'.format(
                                                    self.name,
                                                    self.task_queue.qsize()),
                                                    v=logging.I,
                                                    proc=proc)
                # Get the next device in the queue
                next_device = self.task_queue.get()
                
                # Poison pill means shutdown
                if next_device is None:
                    log('{}: Got poision pill. Walking into the light...'.format(
                        self.name, self.task_queue.qsize()), v=logging.N, proc=proc)
                    
                    self.task_queue.task_done()
                    break
                
                log('{}: Got IP [{}], Device [{}]'.format(self.name,
                                                          next_device.get('ip', 'Unknown IP'),
                                                          next_device),
                                                          v=logging.N, proc=proc,
                                                          ip=next_device.get('ip', 'Unknown IP'))
                
                # Prepare the result set to pass back to the main proccess
                result = {
                    'device': None,
                    'log': None,
                    'error': None,
                    'original': next_device,
                    }
                
                # Create an inherited device class object
                try: result['device'] = create_instantiated_device(**next_device)
                except Exception as e:
                    log('Device [{}] could not be instantiated: [{}]'.format(
                        next_device.get('ip'), str(e)),
                        v=logging.C, proc=proc)
                    result['log'] = 'Device could not be instantiated.\n'
                    result['error'] = e 
                    self.task_queue.task_done()
                    self.result_queue.put(result)
                    
                    if config.cc.raise_exceptions: raise
                    else: 
                        traceback.print_exc()
                        continue
                    
                # Poll the device
                try: result['device'].process_device()
                except Exception as e:
                    log('Connection to {} failed: {}'.format(
                        result['device'].ip, str(e)),
                        v=logging.C, proc=proc)
                    result['log'] = 'Connection to {} failed: {}'.format(result['device'].ip, str(e))
                    result['error'] = e   
                    
                    # Set the connection to None in order to allow Pickling
                    result['device'].connection = None
                    
                    # Put the result on the device queue and signal done
                    self.task_queue.task_done()
                    self.result_queue.put(result) 
                        
                    # Ignore CLI errors, raise the rest
                    if (config.cc.raise_exceptions and 
                        ('CLI connection' not in str(e))): 
                        raise
                    else: 
    #                     traceback.print_exc()
                        continue                                            
                
                # Set the connection to None in order to allow Pickling
                result['device'].connection = None
                
                # Put the result on the device queue and signal done
                self.task_queue.task_done()
                self.result_queue.put(result)
        
        except (KeyboardInterrupt, SystemExit):
            try: self.terminate()
            except: pass
        
        return
            
def _scan_host(h, nm):
        
        # Scan the host
        nm.scan(h, '22, 23', '-sV -T5')
        
        # Continue loop if the host is down
        if not nm.has_host(h): 
            return h + ' is down'
        
        # Add newly discovered devices to the database
        if (
            (nm[h].has_tcp(22) and nm[h].tcp(22).get('state') == 'open') or
            (nm[h].has_tcp(23) and nm[h].tcp(23).get('state') == 'open')
            ):
            return {
                    'netmiko_platform': 'unknown',
                    'raw_cdp': json.dumps(nm[h], sort_keys=True, indent=4),
                    'ip_list': [h],
                    }

def scan_range(_target, **kwargs):
    '''Ping each host in a given range one at a time. When a live host
    is found, add it to the pending hosts list and run the normal_scan
    method.''' 
    proc = 'main.scan_range'
     
    log('Starting host scan on target ' + _target, proc=proc, v=logging.H)
    
    try: import nmap
    except ImportError:
        log('Nmap not installed', proc= proc, v= logging.C)
        return False
    
    nm = nmap.PortScanner()
    main_db = io_sql.main_db(**kwargs)
    
    # Use NMAP's nice target specification feature
    # to get a list of all the hosts to scan
    hosts = nm.listscan(_target)
    
    pool = multiprocessing.Pool(processes=multiprocessing.cpu_count() * 4)
    
    results = [pool.apply_async(_scan_host, args=(h, nm,)) for h in hosts if 
               not((main_db.ip_exists(h, 'visited')) or
                   (main_db.ip_exists(h, 'pending')))]
    
    for r in results:
        result = r.get()
        
        if isinstance(result, dict):
            log('Got result [{}]'.format(result), proc=proc, v=logging.N)
            main_db.add_pending_device_d(result)
        else:
            log('Host down. Result [{}]'.format(result), proc=proc, v=logging.N)
        
    log('Finished scanning hosts', proc=proc, v=logging.H)


def single_run(target, netmiko_platform= 'unknown'):
    proc = 'main.single_run'
    
    log('Processing connection to {}'.format(target), proc=proc, v=logging.H)
    
    try: device = create_instantiated_device(ip=target, netmiko_platform=netmiko_platform)
    except Exception as e: 
        log('Connection to [{}] failed: {}'.format(
            target, str(e)), proc=proc, v= logging.C)
        raise
    
    
    # Process the device
    try: device.process_device()
    except Exception as e:
        device.alert(msg='Connection to {} failed: {}'.format(device.ip, str(e)), proc=proc)
        print('Device processing failed')
        if config.cc.raise_exceptions: raise
        return False
        
    # Output the device info to console
    print('\n' + str(device) + '\n')
    print(device.neighbor_table())
    
    
        
       
       
     
    
    
    
