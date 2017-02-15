import re, hashlib, util, datetime
from util import log
from global_vars import RUN_PATH, TIME_FORMAT_FILE, TIME_FORMAT


class interface():
    '''Generic network device interface'''
    def __init__(self):
        self.interface_name=''
        self.interface_ip=''
        self.interface_subnet=''
        self.interface_description=''
        self.interface_status=''
        self.tunnel_destination_ip=''
        self.remote_interface=''
        self.tunnel_status=''
        self.interface_type=''
                 
    
    def __str__(self):
            
        output = []
        for var, value in vars(self).items(): output.append(var + ': ' + str(value))
        return '\n'.join(str(x) for x in sorted(output))
    


class network_device():
    '''Generic network device'''
    def __init__(self):
        self.device_name = ''
        self.interfaces = []
        self.neighbors = []
        self.config = ''
        self.management_ip = ''
        self.serial_numbers = []
        self.other_ips=[]
        self.netmiko_platform= ''
        self.system_platform= ''
    
    def add_ip(self, ip):
        """Adds an IP address to the list of other IPs
        
        Args:
            ip (string): An IP address
        """
        if not ip in self.other_ips:
            self.other_ips.append(ip)
 
 
    def save_config(self):
        log('Saving config.', proc='save_config', v= util.N)
        
        filename = self.unique_name()
        path = RUN_PATH + filename + '/' 
        filename = filename + '_' + datetime.now().strftime(TIME_FORMAT_FILE) + '.cfg'  # @UndefinedVariable
        
        with open(path + filename, 'a') as outfile:       
            outfile.write('\n'.join([
                datetime.now().strftime(TIME_FORMAT),  # @UndefinedVariable
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
            if sh_name: entry += '{name:30.29}, '.format(name = n['name'])
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
                    for key in vars(new_interf).keys():
                        vars(old_interf)[key] = vars(new_interf)[key] 
            
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
    
        if name and self.device_name: 
            if len(self.device_name) > 12:
                output.append(self.device_name[-12:])
            else:
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
    
                
    def __str__(self):
        return '\n'.join([
            'Device Name:     ' + self.device_name,
            'Unique Name:     ' + self.unique_name(),
            'Management IP:   ' + self.management_ip,
            'First Serial:    ' + str(self.serial_numbers[0]),
            'Serial Count:    ' + str(len(self.serial_numbers)),
            'Interface Count: ' + str(len(self.interfaces)),
            'Neighbor Count:  ' + str(len(self.neighbors)),
            'Config Size:     ' + str(len(self.config))
            ])
        
    