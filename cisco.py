import re
from device_classes import interface
from device_classes import network_device

def parse_cisco_device_config(raw_config):
    device = network_device()
    
    device.device_name = parse_hostname(raw_config)
    
    return device


def parse_hostname(raw_config):
    output = re.search('hostname (.+)\n', raw_config)
    if output: return output.group(1)
    else: return ''

    
def get_config(ssh_connection):
    print ('# Beginning config download from %s' % ssh_connection.ip)
    
    # enter enable mode
    ssh_connection.enable()
    
    # Try three times to get the output, waiting longer each time 
    for i in range(2):
        raw_config = ssh_connection.send_command_expect('sh run', max_loops=((i+1)*100))
        if raw_config: break
        else: print('# Download attempt %s failed.' % i+1)
    
    return parse_cisco_device_config(raw_config)
    
    