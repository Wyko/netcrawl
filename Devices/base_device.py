from util import log, port_is_open, getCreds
from datetime import datetime
from gvars import DEVICE_PATH, TIME_FORMAT_FILE
from time import sleep
from netmiko import ConnectHandler, NetMikoAuthenticationException
from netmiko import NetMikoTimeoutException

import re, hashlib, util, os, gvars

class interface():
    '''Generic network device interface'''
    def __init__(self):
        
        self.interface_name= None
        self.interface_ip= None
        self.interface_subnet= None
        self.interface_description= None
        self.interface_status= None
        self.tunnel_destination_ip= None
        self.remote_interface= None
        self.tunnel_status= None
        self.interface_type= None
        self.virtual_ip= None
    
    
    def type(self):
        return re.split(r'\d', self.interface_name)[0]
               
    
    def __str__(self):
            
        output = []
        for var, value in vars(self).items(): output.append(var + ': ' + str(value))
        return '\n'.join(str(x) for x in sorted(output))
    


class network_device():
    '''Generic network device'''
    def __init__(self, **kwargs):
        # Immutable arguments
        self.raw_mac_address_table= kwargs.pop('raw_mac_address_table', None)
        self.netmiko_platform= kwargs.pop('netmiko_platform', None)
        self.system_platform= kwargs.pop('system_platform', None)
        self.ssh_connection= kwargs.pop('ssh_connection', None)
        self.neighbor_id= kwargs.pop('neighbor_id', None)        
        self.device_name= kwargs.pop('device_name', None)
        self.credentials= kwargs.pop('credentials', None)
        self.AD_enabled= kwargs.pop('AD_enabled', None)
        self.software= kwargs.pop('software', None)
        self.raw_cdp= kwargs.pop('raw_cdp', None)
        self.config= kwargs.pop('config', None)
        self.TCP_22= kwargs.pop('TCP_22', None)
        self.TCP_23= kwargs.pop('TCP_23', None)
        self.device_id= kwargs.pop('id', None)
        self.ip= kwargs.pop('ip', None)
        
        # Mutable arguments
        self.serial_numbers= []
        self.interfaces = []
        self.neighbors = []
        self.other_ips= []
        self.mac_address_table= []
        
        # Other Args
        self.failed = False
        self.failed_msg = ''
        

    def __str__(self):
        return '\n'.join([
            'Device Name:     ' + str(self.device_name),
            'Unique Name:     ' + str(self.unique_name()),
            'Management IP:   ' + str(self.ip),
            'First Serial:    ' + str(self.serial_numbers[0]),
            'Serial Count:    ' + str(len(self.serial_numbers)),
            'Interface Count: ' + str(len(self.interfaces)),
            'Neighbor Count:  ' + str(len(self.neighbors)),
            'Config Size:     ' + str(len(self.config))
            ])
    
    def alert(self, msg, proc):
        '''Populates the failed messages variable for the device'''
        self.failed = True
        self.failed_msg += proc + ': ' + msg + ' | '
        log(msg= msg, proc= proc, v= util.A)
    
    
    def get_serials(self):
        self.alert('No inherited method replaced this method.', 'base_device.get_serials')
        
    def get_config(self):
        self.alert('No inherited method replaced this method.', 'base_device.get_config')
                
    def parse_hostname(self):
        self.alert('No inherited method replaced this method.', 'base_device.parse_hostname')
                
    def get_cdp_neighbors(self):
        self.alert('No inherited method replaced this method.', 'base_device.get_cdp_neighbors')
            
    def get_interfaces(self):
        self.alert('No inherited method replaced this method.', 'base_device.get_interfaces')
            
    def get_other_ips(self):
        self.alert('No inherited method replaced this method.', 'base_device.get_other_ips')
        
    def get_mac_address_table(self):
        self.alert('No inherited method replaced this method.', 'base_device.get_mac_address_table')       
    
    
    def add_ip(self, ip):
        """Adds an IP address to the list of other IPs
        
        Args:
            ip (string): An IP address
        """
        if not ip in self.other_ips:
            self.other_ips.append(ip)
 
 
    def save_config(self):
        log('Saving config.', proc='save_config', v= util.N)
        
        path = DEVICE_PATH + self.unique_name() + '/' 
        filename = datetime.now().strftime(TIME_FORMAT_FILE) + '.cfg'
        
        if not os.path.exists(path):
            os.makedirs(path)
        
        with open(path + filename, 'a') as outfile:       
            outfile.write('\n'.join([
                datetime.now().strftime(TIME_FORMAT_FILE),
                self.config,
                '\n']))
                
        log('Finished saving config.', proc='save_config', v= util.N)
    
 
    def neighbor_table(self, sh_src= True, sh_name= True, sh_ip = True, sh_platform = True ):
        """Returns a formatted table of neighbors.
        
        Optional Args:
            sh_src (Boolean): When true, show the source interface for each entry
            sh_name (Boolean): When true, show the hostname for each entry
            sh_ip (Boolean): When true, show the IP address for each entry
            sh_platform (Boolean): When true, show the system platform for each entry
            
        """ 
        
        output= ''
        
        entries = []
        
        # Add the table header
        entry = ''
        if sh_name: entry += '     {name:^30}  '.format(name = 'Neighbor Name')
        if sh_ip: entry += '{ip:^15} '.format(ip = 'IP')
        if sh_src: entry += '{src:^25} '.format(src = 'Source Interface')
        if sh_platform: entry += '  Platform'
        entries.append(entry)
        
        # Populate the table
        for n in self.neighbors:
            entry = '-- '
            if sh_name: entry += '{name:30.29}, '.format(name = n['device_name'])
            if sh_ip: entry += '{ip:15}, '.format(ip = n['ip'])
            if sh_src: entry += '{src:25}, '.format(src = n['source_interface'])
            if sh_platform: entry += '{platform}'.format(platform = n['system_platform'])
            entries.append(entry)
        
        output += '\n'.join(entries)
        
        return output
        
    
    def merge_interfaces(self, new_interfaces):
        """Merges a list of interfaces with the ones currently in the device.
        If the interface name matches, then the new interface will overwrite 
        any old data it has new entries for.
        
        Args:
            new_interfaces (List of interface objects): One or more interface objects
        """
         
        for new_interf in new_interfaces:
            match = False
            for old_interf in self.interfaces:
                # If the new interface name matches the saved name
                if new_interf.interface_name == old_interf.interface_name:
                    match = True
                    log('Interface {} merged with old interface'.
                        format(new_interf.interface_name), 
                        proc='merge_interfaces',
                        v = util.D)
                    # For each variable in the interface class, compare and overwrite new ones.
                    for key in gvars(new_interf).keys():
                        gvars(old_interf)[key] = gvars(new_interf)[key] 
            
            if not match: self.interfaces.append(new_interf)
    
    
    def interfaces_to_string(self):
        output = '\n----------\n'.join(str(interf) for interf in self.interfaces)           
        return output
            
    
    def get_ips(self):
        """Returns a list of IP addresses aggregated from interfaces."""
        
        output = []
        for interf in self.interfaces:
            
            # if the interface exists and if it matches an IP address
            if (interf.interface_ip and 
                re.search(r"(1[0-9]{1,3}(?:\.\d{1,3}){3})", interf.interface_ip, flags=re.I)):
                output.append(interf.interface_ip) 
        
        for ip in self.other_ips: output.append(ip)
            
        return output


    def unique_name(self, name= True, serials= True):
        """Returns a unique identifier for this device"""
        
        output = []
        
        if not (self.device_name or self.serial_numbers):
            return None
        
        if name and self.device_name: 
#             if len(self.device_name) > 16:
#                 output.append(self.device_name[-16:])
#             else:
            output.append(self.device_name)
        
        # Make a hash of the serials        
        if serials and len(self.serial_numbers) > 0:
            h = hashlib.md5()
            for x in sorted(self.serial_numbers, key= lambda k: k['serial']):
                h.update(x['serial'].encode())
            output.append(h.hexdigest()[:5])
        
        return '_'.join(output)
        
    
    def first_serial(self):
        if len(self.serial_numbers) == 0: return ''
        else: return self.serial_numbers[0]['serial']
    
    
    def enable(self, attempts= 3):
        '''Enter enable mode.
        
        Returns:
            Boolean: True if enable mode successful.
        '''
        
        for i in range(attempts):
            
            # Attempt to enter enable mode
            try: self.ssh_connection.enable()
            except Exception as e: 
                log('Enable failed on attempt %s. Current delay: %s' % (str(i+1), 
                    self.ssh_connection.global_delay_factor), 
                    ip= self.ssh_connection.ip, proc= 'enable', v= util.A, error= e)
                
                # At the final try, return the failed device.
                if i >= attempts-1: 
                    raise ValueError('Enable failed after {} attempts'.format(i))
                
                # Otherwise rest for one second longer each time and then try again
                self.ssh_connection.global_delay_factor += gvars.DELAY_INCREASE
                sleep(i+2)
                continue
            else: 
                log('Enable successful on attempt %s. Current delay: %s' % 
                    (str(i+1), self.ssh_connection.global_delay_factor), 
                    ip= self.ssh_connection.ip, proc= 'enable', v= util.D)
                
                return True
    
    
    def process_device(self):
        '''Main method which fully populates the network_device'''
       
        self.start_cli_session()
        self.enable()
       
        for fn in (
            self.get_serials(),
            self.get_config(),
            self.parse_hostname(),
            self.get_cdp_neighbors(),
            self.get_interfaces(),
            self.get_other_ips(),
            self.get_mac_address_table()
            ):
            try: 
                fn
            except Exception as e:
                self.alert('Error: ' + str(e), 'main.process_device')
                if not gvars.SUPPRESS_ERRORS: raise
               
        
        log('Finished getting {}'.format(self.unique_name()), proc='process_device', v= util.H)
        self.ssh_connection.disconnect()
        return True
    
    
    def start_cli_session(self, global_delay_factor = 1):
        """
        Starts a CLI session with a remote device. Will attempt to use
        SSH first, and if it fails it will try a terminal session.
        
        Optional Args: 
            global_delay_factor (float): A number by which timeouts are multiplied
        
        Returns: 
            Dict: 
                'ssh_connection': Netmiko ConnectHandler object opened to the enable prompt 
                'TCP_22': True if port 22 is open
                'TCP_23': True if port 23 is open
                'cred': The first successful credential dict 
        """
        
        log('Connecting to %s device %s' % (self.netmiko_platform, self.ip), self.ip, proc='start_cli_session', v= util.N)
        
        # Get the username and password
        credList = getCreds()
        
        self.ssh_connection= None
        self.credentials= None
        self.failed= True
        self.TCP_22= port_is_open(22, self.ip)
        self.TCP_23= port_is_open(23, self.ip)
        
        # Check to see if SSH (port 22) is open
        if not self.TCP_22:
            log('Port 22 is closed on %s' % self.ip, self.ip, proc='start_cli_session', v= util.A)
        else: 
            # Try logging in with each credential we have
            for cred in credList:
                try:
                    # Establish a connection to the device
                    ssh_connection = ConnectHandler(
                        device_type=self.netmiko_platform,
                        ip=  self.ip,
                        username= cred['user'],
                        password= cred['password'],
                        secret= cred['password'],
                        global_delay_factor= global_delay_factor
                    )
                    log('Successful ssh auth to %s using %s, %s' % (self.ip, cred['user'], cred['password'][:2]), proc='start_cli_session', v= util.N)
                    
                    self.credentials = cred
                    self.ssh_connection= ssh_connection
                    self.failed= False
                    return True
        
                except NetMikoAuthenticationException:
                    log ('SSH auth error to %s using %s, %s' % (self.ip, cred['user'], cred['password'][:2]), proc='start_cli_session', v= util.A)
                    continue
                except NetMikoTimeoutException:
                    log('SSH to %s timed out.' % self.ip, proc='start_cli_session', v= util.A)
                    # If the device is unavailable, don't try any other credentials
                    break
        
        # Check to see if port 23 (telnet) is open
        if not self.TCP_23:
            log('Port 23 is closed on %s' % self.ip, self.ip, proc='start_cli_session', v= util.A)
        else:
            for cred in credList:
                try:
                    # Establish a connection to the device using telnet
                    ssh_connection = ConnectHandler(
                        device_type=self.netmiko_platform + '_telnet',
                        ip= self.ip,
                        username=cred['user'],
                        password=cred['password'],
                        secret=cred['password']
                    )
                    log('Successful telnet auth to %s using %s, %s' % (self.ip, cred['user'], cred['password'][:2]), proc='start_cli_session', v= util.N)
                    
                    self.credentials = cred
                    self.ssh_connection= ssh_connection
                    self.failed= False
                    return True
                
                except NetMikoAuthenticationException:
                    log('Telnet auth error to %s using %s, %s' % 
                        (self.ip, cred['user'], cred['password'][:2]), v= util.A, proc= 'start_cli_session')
                    continue
                except:
                    log('Telnet to %s timed out.' % self.ip, proc='start_cli_session', v= util.A)
                    # If the device is unavailable, don't try any other credentials
                    break
        
        raise ValueError('No CLI connection could be established')
        
            