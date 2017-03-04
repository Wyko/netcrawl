"""Controls selection of proper class based on the device type.

Credit: Kirk Byers
"""
from Devices.base_device import network_device
from netmiko.ssh_autodetect import SSHDetect
from Devices.nxos_device import nxos_device
from Devices.ios_device import ios_device
from wylog import log

import gvars, cli, util

# The keys of this dictionary are the supported device_types
CLASS_MAPPER_BASE = {
    'cisco_ios': ios_device,
    'cisco_nxos': nxos_device,
}

# Also support keys that end in _ssh
new_mapper = {}
for k, v in CLASS_MAPPER_BASE.items():
    new_mapper[k] = v
    alt_key = k + u"_ssh"
    new_mapper[alt_key] = v
CLASS_MAPPER = new_mapper

# Add telnet drivers
CLASS_MAPPER['cisco_ios_telnet'] = ios_device

platforms = list(CLASS_MAPPER.keys())
platforms.sort()
platforms_base = list(CLASS_MAPPER_BASE.keys())
platforms_base.sort()
platforms_str = u"\n".join(platforms_base)
platforms_str = u"\n" + platforms_str


def create_instantiated_device(*args, **kwargs):
    """Factory function selects the proper network device class 
    and creates the object based on netmiko_platform."""
    proc= 'device_dispatcher.create_instantiated_device'
    
    log('Instantiating ' + kwargs['ip'], v= log.I, proc= proc)
    
    # In case of an unknown platform, autodetect
    if kwargs.get('netmiko_platform') not in platforms:
        ad= autodetect(kwargs['ip'])

        if ad not in platforms:
            raise TypeError('Appropriate device class could '+
                            'not be determined.')
        else:
            ConnectionClass = CLASS_MAPPER[ad]
            kwargs['netmiko_platform']= ad
            
    else:
        # Select the network device class to be 
        # instantiated based on vendor/platform.
        ConnectionClass = CLASS_MAPPER[kwargs['netmiko_platform']]
        
    log('Instantiated ' + kwargs['ip'], v= log.I, proc= proc)
    return ConnectionClass(*args, **kwargs)
    

    
def autodetect(target):
        '''This method invokes Netmiko's autodetect functionality
        to determine the correct device class, then returns that 
        class as a netmiko_platform.
        
        Args:
            target (String): The hostname or IP address to connect to
        
        Raises:
            TypeError: Could not find an appropriate class to inherit
            IOError: Could not connect to the device
            
        Returns:
            String: The netmiko_platform representation of the proper
                    device class.
        '''
        proc= 'base_device.find_device_type'
        
        log('Autodetecting unknown device type', proc= proc, v= log.I)
        
        # Error check
        assert type(target) is str, proc+ ': Target [{}] is not a string'.format(type(target))
        
        # Connect using the SSH autodetect system
        try: connection= cli.start_cli_session(ip= target,
                                               handler= SSHDetect,
                                               netmiko_platform= 'terminal_server'
                                               )['connection']
        except IOError as e:
            log('Autodetect connection failed.', proc= proc, v= log.A)
            raise IOError(proc+ 
                ': Autodetect connection failed with error [{}]'.format(str(e)))
        
        # Use the resulting connection object to perform the autodetection        
        ad= connection.autodetect()
        
        if ad is None: raise TypeError('Autodetection produced no result')
        else: 
            log('Autodetection determined a device type of [{}]'.format(ad), 
                proc= proc, v= log.N)
            return ad