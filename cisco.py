import re
from time import sleep
from device_classes import interface
from device_classes import network_device
from cdp import get_cdp_neighbors
from cli import start_cli_session


def parse_hostname(raw_config, ssh_connection=''):
    output = re.search('^hostname (.+)\n', raw_config, re.MULTILINE)
    if output: return output.group(1)
    
    if ssh_connection == '': return ''
    
    # If the hostname couldn't be parsed, get it from the prompt    
    for i in range(5):
        try:
            output = ssh_connection.find_prompt()
        except ValueError:
            print('# Encountered an error trying to find the prompt during attempt %s' % (i+1))
                    
        if '#' in output: return output.split('#')[0]
        else: sleep(1)
    
    # Last case scenario, return nothing
    return ''


def get_interfaces(ssh_connection, raw_config=''):
    # Try three times to get the output, waiting longer each time 
    for i in range(2):
        try: raw_output = ssh_connection.send_command_expect('sh ip int br', max_loops=((i+1)*30))
        except: 
            print('# Show ip int br attempt %s failed.' % str(i+1))
            continue
        else: break
    
    interfaces = []
    
    # Process the interfaces
    for line in raw_output.split('\n'):
        if 'nterface' in line: continue
        
        # Create a new network_device object to house the data we find
        interf = interface()
        output = re.split(r'\s+', line)
        
        interf.interface_name = output[0]
        interf.interface_type = re.split(r'\d', output[0])[0]
        
        interf.interface_ip = output[1]
        if 'dministrativel' in output[4]: 
            interf.interface_status = '%s %s/%s' % (output[4], output[5], output[6])
        else: interf.interface_status = '%s/%s' % (output[4], output[5])  
        
        interfaces.append(interf)
        
        #print ('---------\n' + str(interf))
        
    # If no device config was passed, return it now
    if raw_config == '': return interfaces
    
    # Split out the interfaces from the raw config
    raw_interfaces = re.findall(r'\n(^interface[\s\S]+?)\n!', raw_config, re.MULTILINE)
    
    # For each interface parsed from the raw config, match it to an existing 
    # interface and parse it into structured data
    for interf in raw_interfaces:
        i_name = re.search(r'^interface[ ]?(.+)$', interf, re.IGNORECASE | re.MULTILINE).group(1)
        for i in interfaces:
            # If the config-parsed interface name matches the saved name
            if i_name in i.interface_name: 
                i.interface_description = re.search(r'description[ ]+(.+)$', interf, re.IGNORECASE | re.MULTILINE).group(1)
                
                
    


def get_device(ip, platform='cisco_ios'):
    '''Main method which returns a fully populated network_device object'''
    
        # Open a connection to the device and return a session object
    # that we can reuse in multiple functions
    try: ssh_connection = start_cli_session(ip, platform)
    except IOError as e:
        print(e)
        raise
        return
    
    device = network_device()
    
    device.config = get_config(ssh_connection)
    device.device_name = parse_hostname(device.config, ssh_connection)
    device.neighbors = get_cdp_neighbors(ssh_connection)
    device.interfaces = get_interfaces(ssh_connection, device.config)
    
    ssh_connection.disconnect()
    
    return device
    
    
def get_config(ssh_connection):
    print ('# Beginning config download from %s' % ssh_connection.ip)
    raw_config = ''
    
    # enter enable mode
    ssh_connection.enable()
    
    # Try three times to get the output, waiting longer each time 
    for i in range(2):
        try: raw_config = ssh_connection.send_command_expect('sh run', max_loops=((i+1)*50))
        except: 
            print('# Config download attempt %s failed.' % str(i+1))
            continue
        else: break
    
    
    
    return raw_config

 
    