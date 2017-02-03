import re
from time import sleep
from device_classes import interface, network_device
from cdp import get_cdp_neighbors
from cli import start_cli_session
from io_file import log, log_failed_device
from global_vars import DELAY_INCREASE 


def parse_hostname(raw_config, ssh_connection=''):
    log('# Starting', proc='parse_hostname')
    
    output = re.search('^hostname (.+)\n', raw_config, re.MULTILINE)
    if output: 
        log('# Regex parsing the config found {}'.format(output.group(1)), proc='parse_hostname')
        return output.group(1)
    
    if ssh_connection == '': 
        log('! parse_hostname: No ssh_connection received')
        return ''
    
    # If the hostname couldn't be parsed, get it from the prompt    
    for i in range(5):
        try:
            output = ssh_connection.find_prompt()
        except ValueError:
            ssh_connection.global_delay_factor += DELAY_INCREASE
            log('! parse_hostname: Failed to find the prompt during attempt %s. Increasing delay to %s'  % (str(i+1), ssh_connection.global_delay_factor))
            sleep(1)
            continue
                    
        if '#' in output: 
            log('# Prompt parsing found ' + output, proc='parse_hostname')
            return output.split('#')[0]
        else: sleep(1)
    
    # Last case scenario, return nothing
    log('! parse_hostname: No hostname found.')
    return ''


def parse_nxos_interfaces(raw_config=''):
    
    log('# Starting', proc='parse_nxos_interfaces')
    
    # If no device config was passed, return it now
    if raw_config == '': return
    
    # Split out the interfaces from the raw config
    raw_interfaces = re.findall(r'(^interface[\s\S]+?)\n\s*\n', raw_config, re.MULTILINE)
    
    interfaces = []
    
    # For each interface parsed from the raw config, parse it into structured data
    for interf in raw_interfaces:
        i = interface()
        
        try: i.interface_name = re.search(r'^interface[ ]?(.+)$', interf, re.IGNORECASE | re.MULTILINE).group(1)
        except: continue
        else: i.interface_type = re.split(r'\d', i.interface_name)[0]
        
        # Description
        try: i.interface_description = re.search(r'description[ ]+(.+)$', interf, re.IGNORECASE | re.MULTILINE).group(1)
        except: pass
        
        # IP and Subnet (Matches both octets and CIDR)
        ip_info = re.search(r'ip address.*?(\d{1,3}(?:\.\d{1,3}){3})[ ]?((?:\/\d+)|(?:\d{1,3}(?:\.\d{1,3}){3}))', interf, re.IGNORECASE | re.MULTILINE)
        if ip_info and ip_info.group(1): i.interface_ip = ip_info.group(1)
        if ip_info and ip_info.group(2): i.interface_subnet = ip_info.group(2)    
        
        # Add the new interface to the list of interfaces
        interfaces.append(i)
                
    return interfaces            



def get_ios_int_br(ssh_connection):
    # Try three times to get the output, waiting longer each time 
    for i in range(2):
        try: raw_output = ssh_connection.send_command_expect('sh ip int br')
        except: 
            ssh_connection.global_delay_factor += DELAY_INCREASE
            log('? parse_ios_interfaces: Show ip interface brief attempt %s failed. New delay: %s' % (str(i+1), ssh_connection.global_delay_factor))
        
    interfaces = []
    
    # Process the interfaces
    for line in raw_output.split('\n'):
        if 'nterface' in line: continue

        try:        
            # Create a new network_device object to house the data we find
            interf = interface()
            output = re.split(r'\s+', line)
            
            # Remove empty strings
            for i, line in enumerate(output): 
                if line == '': output.pop(i)
            
            # Process the first ip interface entry
            interf.interface_name = output[0]
            interf.interface_type = re.split(r'\d', output[0])[0]
            
            # process the second entry
            interf.interface_ip = output[1]
            
            if len(output) > 3:
                if 'dministrativel' in output[4]: 
                    interf.interface_status = '%s %s/%s' % (output[4], output[5], output[6])
                else: interf.interface_status = '%s/%s' % (output[4], output[5])  
            
            interfaces.append(interf)
        except Exception as e: 
            log('! Sh ip int br failed with error: ' + str(e), proc = 'parse_ios_interfaces')
            continue
    
    return interfaces
        
     


def parse_ios_interfaces(raw_config=''):
    
    log('# Starting ios interface parsing.', proc="parse_ios_interfaces")
    interfaces = []
    # If no device config was passed, return
    if not raw_config: 
        log('# No configuration passed. Returning.', proc = 'parse_ios_interfaces')
        return interfaces
    
    # Split out the interfaces from the raw config
    raw_interfaces = re.findall(r'\n(^interface[\s\S]+?)\n!', raw_config, (re.MULTILINE|re.IGNORECASE))
    
    # For each interface parsed from the raw config, create a new interface 
    # object and parse it into structured data
    for interf in raw_interfaces:
        
        temp_interf = interface()
        
        # Parse the interface name from the raw data. If that isn't possible, continue
        try: temp_interf.interface_name = re.search(r'^interface[ ]?(.+)$', interf, re.IGNORECASE | re.MULTILINE).group(1)
        except: 
            log('! Raw config parsing failed to find interface name. Skipping interface', proc='parse_ios_interfaces')
            continue
        
        # Description
        try: temp_interf.interface_description = re.search(r'description[ ]+(.+)$', interf, re.IGNORECASE | re.MULTILINE).group(1)
        except: pass
        
        try:
            # IP and Subnet (Matches both octets and CIDR)
            ip_info = re.search(r'ip address.*?(\d{1,3}(?:\.\d{1,3}){3})[ ]?((?:\/\d+)|(?:\d{1,3}(?:\.\d{1,3}){3}))', interf, re.IGNORECASE | re.MULTILINE)
            if ip_info and ip_info.group(1): temp_interf.interface_ip = ip_info.group(1)
            if ip_info and ip_info.group(2): temp_interf.interface_subnet = ip_info.group(2)    
        except Exception as e:
            log('! Exception while parsing IP and Subnet: {}'.format(str(e)),
                proc = 'parse_ios_interfaces')
            pass
        
        interfaces.append(temp_interf)
                
    return interfaces            


def get_serials(ssh_connection):
    # Try three times to get the output, waiting longer each time 
    for i in range(2):
        try: raw_output = ssh_connection.send_command_expect('sh inv')
        except: 
            log('! get_serials: Show inventory attempt %s failed.' % str(i+1))
            continue
        else: break
    
    # Get each serial number
    output = re.findall(r'^Name.*?["](.+?)["][\s\S]*?Desc.*?["](.+?)["][\s\S]*?SN:[ ]?(\w+)', raw_output, re.MULTILINE | re.IGNORECASE)
    
    if len(output[0]) != 3:
        log('! get_serials: Output of %s is not normal. Len: %s, Output: %s' % 
            (ssh_connection.ip, len(output[0]), output[0]), ssh_connection.ip)
        return ''
    
    serials = []
    
    for i in output:
        serials.append({
            'name': i[0],
            'description': i[1],
            'serial': i[2]
            })
    
    return serials
    


def get_device(ip, platform='cisco_ios', global_delay_factor=1):
    '''Main method which returns a fully populated network_device object'''
   
    # Open a connection to the device and return a session object
    # that we can reuse in multiple functions
    try: ssh_connection = start_cli_session(ip, platform, global_delay_factor)
    except:
        log('! Failed getting %s device %s' % (ip, platform), ip, proc='get_device')
        raise
    
    device = network_device()
    
    device.management_ip = ssh_connection.ip
    device.serial_numbers = get_serials(ssh_connection)
    device.config = get_config(ssh_connection)
    device.device_name = parse_hostname(device.config, ssh_connection)
    device.neighbors = get_cdp_neighbors(ssh_connection)
    
    try:
        if 'ios' in platform:
            device.merge_interfaces(get_ios_int_br(ssh_connection))
            device.merge_interfaces(parse_ios_interfaces(device.config))
        elif 'nx' in platform:
            device.interfaces = parse_nxos_interfaces(device.config)
    except:
        log('! Failed to retrieve interfaces from {}'.format(ip), proc='get_device')
        raise
    
    ssh_connection.disconnect()
    
    return device
    
    
def get_config(ssh_connection):
    log('# Beginning config download from %s' % ssh_connection.ip, proc='get_config')
    raw_config = ''
    
    # enter enable mode
    for i in range(2):
        try: ssh_connection.enable()
        except Exception as e: 
            log('! get_config: Enable failed on attempt %s. Current delay: %s' % (str(i+1), ssh_connection.global_delay_factor), ssh_connection.ip)
            ssh_connection.global_delay_factor += DELAY_INCREASE
            sleep(1)
            continue
        else: 
            log('# Enable successful on attempt %s. Current delay: %s' % (str(i+1), ssh_connection.global_delay_factor), ssh_connection.ip, proc='get_config')
            sleep(2)
            break
    
    # Try three times to get the output, waiting longer each time 
    for i in range(2):
        try: raw_config = ssh_connection.send_command_expect('sh run')
        except Exception as e: 
            log('! get_config: Config download failed on attempt %s. Current delay: %s' % (str(i+1), ssh_connection.global_delay_factor), ssh_connection.ip)
            ssh_connection.global_delay_factor += DELAY_INCREASE
            sleep(2)
            continue
        else:
            log('# Config download successful on attempt %s. Current delay: %s' % (str(i+1), ssh_connection.global_delay_factor), ssh_connection.ip, proc='get_config')
            sleep(1)
            break
    
    
    
    return raw_config

 
    