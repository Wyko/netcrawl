import queue, multiprocessing, traceback, json
from time import sleep

from . import config, io_sql
from .device_dispatcher import create_instantiated_device
from .wylog import logging, log, logf
from netcrawl.util import cleanExit
from netcrawl.io_sql import device_db, main_db
from prettytable import PrettyTable


@logf
def recursive_scan(**kwargs):
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
        skip_named_duplicates (bool): If True, this will cause 
            netcrawl to skip neighbors which have the same
            hostname as a device that was previously visited.
            
            .. note:: While this can potentially save a lot of time when 
                scanning devices, if multiple different devices 
                share the same hostname, they will not be scanned!
                
        target (str): The IP address of a seed device to add to the pending
            devices database
        
        netmiko_platform (str): The Netmiko platform of the :code:`target`
            device, if one was given.
        
        processes (int): The number of worker processes to create,
            multiplied by the CPU count
            
    .. note:: If there are any remaining keyword arguments in :code:`**kwargs`, 
        they will be passed to :class:`netcrawl.io_sql.main_db` and 
        :class:`netcrawl.io_sql.device_db`
    '''
    
    proc = 'main.recursive_scan'
        
    # Handle keyboard interrupts        
    with cleanExit():
        log('Starting Recursive Scan', proc=proc, v=logging.H)
    
        # Connect to the databases
        m_db = io_sql.main_db(**kwargs)
        d_db = io_sql.device_db(**kwargs)
    
        # Add the seed device if a target was specified  
        if kwargs.get('target'): 
            _add_target_device(kwargs['target'], m_db,
                               kwargs.get('netmiko_platform', 'unknown'))
    
        # Set the number of sub-processes
        num_workers = multiprocessing.cpu_count() * kwargs.get('processes', 16)
            
        # Establish communication queues
        tasks = multiprocessing.JoinableQueue(num_workers * 2)
        results = multiprocessing.Queue()
        
        # Create workers and start them
        workers = [_worker(tasks, results) for i in range(num_workers)]
        for w in workers: w.start()
        
        '''Loop to run the program. When this loop exits, 
        the application exits'''
        while True: 
            # Take devices from the pending table and add them to the queue
            _add_devices_to_queue(tasks, m_db, **kwargs)
            
            # Process the results from the workers
            _process_results(results,  m_db, d_db)
                    
            # Poison Pill - Decide if we should kill the workers
            if m_db.count_pending() == 0 and tasks.empty():
                _kill_workers(tasks, workers)
                break
            #################################################################
            
            log('Main loop done.', proc=proc, v=logging.I)
            sleep(1)
        
        # Close the connections to the databases
        m_db.close()
        d_db.close() 
        
        # Prints a post-mortem
        print_report()
        
        log('Normal run complete. 0 devices pending.',
            proc=proc, v=logging.H)
        return True



def _add_target_device(target, m_db, platform= 'unknown'):
    '''Adds a seed device to the pending table and removes any references to it
    from the visited table so it will be processed again.'''
    
    # Remove the seed device from visited devices
    m_db.remove_visited_record(target)
    
    m_db.add_pending_device_d(
        ip_list=[target],
        netmiko_platform= platform)


def _process_results(results, m_db, d_db):
    '''Iterates over each item put on the :code:`results` queue and processes
    them, adding them into the inventory database.'''
    
    proc= 'core._process_results'
    
    while not results.empty():
        # Get the next result 
        result= results.get()
        
        # Record the device as being processed and save it
        log('Setting result [{}] as processed'.format(result['original']['ip']), proc=proc, v=logging.I)
        m_db.remove_pending_record(result['original']['pending_id'])
        
        log('Adding result [{}] to Visited'.format(result['original']['ip']), proc=proc, v=logging.I)
        m_db.add_visited_device_d(result['original'])
    
        if ((result['error'] is not None) or 
            (result['device'].failed)): continue 
            
        else: 
            # Add a successfully polled device to the database
            log('Adding result [{}] to Devices'.format(result['original']['ip']), proc=proc, v=logging.I)
            d_db.add_device_nd(result['device']) 
    
            # Save the device config and the device neighbors 
            log('Saving result [{}] Neighbors'.format(result['original']['ip']), proc=proc, v=logging.I)
            m_db.add_device_pending_neighbors(result['device'])
            result['device'].save_config()
            
            log('Successfully processed {}'.format(result['device'].device_name),
                proc=proc, v=logging.H)
        

def _add_devices_to_queue(tasks, m_db, **kwargs):
    '''Iterates over each pending device and adds it to the tasks queue until
    the tasks queue is full.
    
    Args:
        tasks (JoinableQueue): The queue to add the pending devices to

    Keyword Args:
        skip_named_duplicates (bool): If True, this will cause 
            netcrawl to skip neighbors which have the same
            hostname as a device that was previously visited.
            
            .. note:: While this can potentially save a lot of time when 
                scanning devices, if multiple different devices 
                share the same hostname, they will not be scanned!
    '''
    proc= 'core._add_device_to_queue'
    
    remaining = m_db.count_pending()
    while ((remaining >= 0) and (tasks.full() == False)): 
        
        # Get the next device
        device_d = m_db.get_next()
        if device_d is None: break
        
        # Skip devices which have already been visited
        if (kwargs.get('skip_named_duplicates') and 
            m_db.ip_name_exists(ip=device_d.get('ip'),
                                   name=device_d.get('device_name'),
                                   table='visited')): visited = True  
                                            
        elif m_db.ip_exists(ip=device_d.get('ip'),
                               table='visited'): visited = True
        else: visited = False
        
        if visited:
            log('- Device {1} at {0} has already been processed. Skipping.'.format(
                device_d.get('ip', None), device_d.get('device_name', None)),
                proc=proc, v=logging.N)
            m_db.remove_pending_record(device_d['pending_id'])
            continue
    
        log('---- Adding to queue: {name} at {ip} || {pending} devices pending ----'.format(
            ip=device_d.get('ip', None),
            name=(device_d.get('device_name') if device_d.get('device_name') is not None 
                   else '[Unknown Device]'),
            pending=m_db.count_pending()),
            proc=proc, v=logging.H)
        
        tasks.put(device_d)


def _kill_workers(task_queue, workers):
    '''
    Sends a NoneType poison pill to all active workers.
    
    Args:
        task_queue (JoinableQueue): The task queue upon which
            to put the poison pills
        workers (list): List of subprocesses
    '''
    proc= 'core._kill_workers'
    
    log('Killing workers', proc= proc, v= logging.N)
    
    # Clear the Queue
    while not task_queue.empty(): task_queue.get_nowait()
    
    # Send the poison pills
    for w in workers:
            log('[{}] is alive, poisoning now.'.format(w.name), 
                proc=proc, v=logging.I)
            task_queue.put('poison pill')
    
    # Wait for the workers to terminate
    for w in workers:
        if w.is_alive():
            log('[{}] joining.'.format(w.name), proc=proc, v=logging.I)
            w.join()
            log('[{}] joined.'.format(w.name), proc=proc, v=logging.I)
        else:
            log('[{}] is dead.'.format(w.name), proc=proc, v=logging.I)
    

def print_report():
    '''Prints a brief report of the state of the databases to the console'''
    proc= 'core.print_report'
    
    try:
        d_db= device_db()
        m_db= main_db()
        
        pt= PrettyTable(['Database', 'Attribute', 'Value'])
        
        pt.add_row(['Inventory', 'Devices', d_db.count('devices', distinct= False)])
        pt.add_row(['Inventory', 'Distinct Devices', d_db.count('devices', distinct= True)])
        pt.add_row(['Inventory', 'Interfaces', d_db.count('interfaces')])
        pt.add_row(['Inventory', 'Distinct Macs', d_db.count('mac', distinct= True)])
        
        pt.add_row(['Main', 'Pending', m_db.count('pending', distinct= False)])
        pt.add_row(['Main', 'Distinct Pending', m_db.count('pending', distinct= True)])
        pt.add_row(['Main', 'Visited', m_db.count('visited', distinct= False)])
        pt.add_row(['Main', 'Distinct Visited', m_db.count('visited', distinct= True)])
        
        print(pt)
    
    except Exception as e:
        print('Post Mortem Report failed: [{}]'.format(str(e)))
        return True

class _worker(multiprocessing.Process):
    '''Subprocess class which executes the recursive scan functionality.'''
    
    def __init__(self,
                 task_queue,
                 result_queue,
                 ):
        '''
        Initialize the worker process.
        
        Args:
            task_queue (multiprocessing.JoinableQueue): Stores the pending tasks
            result_queue (multiprocessing.Queue): Stores the polling results
        '''
        multiprocessing.Process.__init__(self)
        self.result_queue = result_queue
        self.task_queue = task_queue
        self.cc = config.cc
    
    def run(self):
        with cleanExit():
            proc = '{}.run'.format(self.name)
            
            # Reset global variables since subprocesses may not
            # inherit parent runstates
            config.cc= self.cc

            while True:
                log('{}: Awaiting task. Queue size: [{}]'.format(
                                                    self.name,
                                                    self.task_queue.qsize()),
                                                    v=logging.I,
                                                    proc=proc)
                
                # Get the next device in the queue
                try: next_device = self.task_queue.get(timeout= 5)
                except queue.Empty: continue
                
                # Poison pill means shutdown
                if next_device == 'poison pill':
                    log('{}: Got poison pill. Walking into the light...'.format(
                        self.name, self.task_queue.qsize()), v=logging.N, proc=proc)
                    
                    self.task_queue.task_done()
                    break
                
                log('{}: Got IP [{}], Name [{}] Platform [{}]'.format(self.name,
                                                          next_device.get('ip', 'Unknown IP'),
                                                          next_device.get('device_name', 'Unknown Name'),
                                                          next_device.get('netmiko_platform', 'Unknown Platform'),
                                                          ),
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
                
            log('Process returning', proc=proc, v= logging.I)
            return True
            
def _scan_host(h, nm):
    '''
    Scans one host using Nmap
    
    Args:
        h (str): Host address
        nm (nmap.PortScanner): A PortScanner instance to use to scan the host
    
    Returns:
        dict:
        
            .. code-block:: python
                
                {
                'netmiko_platform' (str): 'unknown'
                'raw_cdp' (str): A JSON dump of the nmap output
                'ip_list' (list): Contains h as one element of a list
                }
        
    '''
    
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

@logf
def nmap_scan(target, **kwargs):
    '''
    Ping each host in a given range one at a time. When a live host
    is found, add it to the pending hosts database.
    
    Args:
        target (str): An Nmap compatible target specifier as outlined
            `in the Nmap 
            documentation <https://nmap.org/book/
            man-target-specification.html>`_
            
    Keyword Args:
        **kwargs: Arguments to pass to :class:`netcrawl.io_sql.main_db`
    ''' 
    proc = 'main.nmap_scan'
     
    
    try: import nmap
    except ImportError:
        log('Nmap not installed', proc= proc, v= logging.C)
        return False
    
    # Handle Keyboard Interrupts
    with cleanExit():
        log('Starting host scan on target ' + target, proc=proc, v=logging.H)
        
        nm = nmap.PortScanner()
        main_db = io_sql.main_db(**kwargs)
        
        # Use NMAP's nice target specification feature
        # to get a list of all the hosts to scan
        hosts = nm.listscan(target)
        
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

@logf
def single_scan(target, netmiko_platform= 'unknown'):
    '''
    Starts a **Single Scan** (-sS) run. This scan polls a single device and
    presents information about the device to the console. Useful for testing 
    a connection, as well as getting a quick overview of the target.

    Keyword Args:
        target (str): The network address of the device to scan
        
        netmiko_platform (str): The Netmiko platform of the :code:`target`
            device. If one is not given, it will attempt to autodetect the
            device type.
    '''
    proc = 'main.single_scan'
    
    log('Processing connection to {}'.format(target), proc=proc, v=logging.H)
    
    # Handle keyboard interrupts
    with cleanExit():
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
    
    
        
       
       
     
    
    
    
