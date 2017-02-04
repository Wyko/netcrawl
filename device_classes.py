import re 
from utility import log

class interface():
    '''Generic network device interface'''
    def __init__(self, 
                 interface_name='', 
                 interface_ip='', 
                 interface_subnet='', 
                 interface_description='', 
                 interface_status='', 
                 tunnel_destination_ip='', 
                 remote_interface='', 
                 tunnel_status='',
                 interface_type=''
                 ):
                     
        self.interface_name = interface_name # Interface label, I.E: FastEthernet0/42
        self.interface_ip = interface_ip # Interface IP address
        self.interface_subnet = interface_subnet # Interface interface_subnet mask 
        self.interface_description = interface_description # Interface interface_description
        self.interface_status = interface_status # 
        self.interface_type = interface_type # I.E: GigabitEthernet, Tunnel, Loopback
        self.remote_interface = remote_interface # An interface object representing the interface this one is connected to
        self.tunnel_status = tunnel_status # Online, Offline, or a custom status
        self.tunnel_destination_ip = tunnel_destination_ip # The globally routable IP address used to reach the far tunnel
        
    
    def __str__(self):
            
        output = []
        for var, value in vars(self).items(): output.append(var + ': ' + str(value))
        return '\n'.join(str(x) for x in sorted(output))
    


class network_device():
    '''Generic network device'''
    def __init__(self,
                device_name = '',
                interfaces = [],
                neighbors = [],
                config = '',
                management_ip = '',
                serial_numbers = [],
                other_ips=[],
                netmiko_platform= '',
                system_platform= '',
                ):
        
        self.device_name = device_name
        self.interfaces = interfaces # A list of interface objects
        self.neighbors = neighbors # A list of neighbor entries, as in CDP or LLDP
        self.config = config # The full configuration of the device
        self.management_ip = management_ip
        self.serial_numbers = serial_numbers
        self.other_ips = other_ips # A list of other interesting IPs (HSRP, GLBP, etc)
        self.netmiko_platform = netmiko_platform
        self.system_platform= system_platform
                
    
    def add_ip(self, ip):
        """Adds an IP address to the list of other IPs
        
        Args:
            ip (string): An IP address
        """
        if not ip in self.other_ips:
            self.other_ips.append(ip)
 
        
    
    def merge_interfaces(self, interfaces):
        """Merges a list of interfaces with the ones currently in the device.
        If the interface name matches, then the new interface will overwrite 
        any old data it has new entries for.
        
        Args:
            interfaces (List of interface objects): One or more interface objects
        """
         
        for new_interf in interfaces:
            match = False
            for old_interf in self.interfaces:
                # If the new interface name matches the saved name
                if new_interf.interface_name == old_interf.interface_name:
                    match = True
                    log('# Interface {} merged with old interface'.
                        format(new_interf.interface_name), 
                        proc='merge_interfaces',
                        print_out=False)
                    # For each variable in the interface class, compare and overwrite new ones.
                    for key in vars(new_interf).keys():
                        vars(old_interf)[key] = vars(new_interf)[key] 
            
            if not match: self.interfaces.append(new_interf)
    
    def interfaces_to_string(self):
        output = ''
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
        
        return output
    
    
    def unique_name(self):
        """Returns a unique identifier for this device"""
        
        output = []
        trim_char = 5
        
        if self.management_ip and self.management_ip != '':
            output.append(self.management_ip)
        else: trim_char = 10
        
        if self.device_name and self.device_name != '':
            if len(self.device_name) > trim_char:
                output.append(self.device_name[(-1 * trim_char):])
            else:
                output.append(self.device_name)
        
        
        if len(self.serial_numbers) == 0:
            pass
        elif len(self.serial_numbers[0]['serial']) > trim_char:
            output.append(self.serial_numbers[0]['serial'][(-1 * trim_char):])
        elif len(self.serial_numbers[0]['serial']) > 1:
            output.append(self.serial_numbers[0]['serial'])
        
        return '_'.join(output)
        
    
    def first_serial(self):
        if len(self.serial_numbers) == 0: return ''
        else: return self.serial_numbers[0]['serial']
    
                
    def __str__(self):
        return '\n'.join([
            'Device Name: ' + self.device_name,
            'Unique Name: ' + self.unique_name(),
            'Management IP: ' + self.management_ip,
            'First Serial: ' + str(self.serial_numbers[0]),
            'Serial Count: ' + str(len(self.serial_numbers)),
            'Interface Count: ' + str(len(self.interfaces)),
            'Neighbor Count: ' + str(len(self.neighbors)),
            'Config Size: ' + str(len(self.config))
            ])
        
    