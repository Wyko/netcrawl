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
                 tunnel_status=''
                 interface_type=''
                 ):
                     
        self.interface_name = interface_name # Interface label, I.E: FastEthernet0/42
        self.interface_ip = interface_ip # Interface IP address
        self.interface_subnet = interface_subnet # Interface interface_subnet mask 
        self.interface_description = interface_description # Interface interface_description
        self.interface_status = status # 
        self.interface_type = interface_type # I.E: GigabitEthernet, Tunnel, Loopback
        self.remote_interface = remote_interface # An interface object representing the interface this one is connected to
        self.tunnel_status = tunnel_status # Online, Offline, or a custom status
        self.tunnel_destination_ip = tunnel_destination_ip # The globally routable IP address used to reach the far tunnel
        
    def __str__(self):
        pass


class network_device():
    '''Generic network device'''
    def __init__(self,
                device_name = '',
                management_ip = '',
                interfaces = [],
                neighbors = [],
        
        self.device_name = device_name
        self.management_ip = management_ip
        self.interfaces = interfaces # A list of interface objects
        self.neighbors = neighbors # A list of neighbor entries, as in CDP or LLDP
                
    def __str__(self):
        return device_name

