import re
import util
from time import sleep
from device_classes import interface, network_device
from cdp import get_cdp_neighbors
from cli import start_cli_session
from global_vars import DELAY_INCREASE 
from util import log
from io_file import log_failed_device
from netmiko.ssh_exception import NetMikoTimeoutException


def parse_hostname(raw_config, ssh_connection=''):
    log('Starting', proc='parse_hostname', v= util.N)
    
    output = re.search('^hostname (.+)\n', raw_config, re.MULTILINE)
    if output and output.group(1): 
        log('Regex parsing the config found {}'.format(output.group(1)), proc='parse_hostname', v= util.N)
        return output.group(1)
    else: log('Regex parsing failed, trying prompt parsing.', proc='parse_hostname', v= util.N)
    
    if not ssh_connection: 
        log('No ssh_connection object passed, function failed', proc= 'parse_hostname', v= util.C)
        return None
    
    # If the hostname couldn't be parsed, get it from the prompt    
    for i in range(5):
        try:
            output = ssh_connection.find_prompt()
        except ValueError:
            ssh_connection.global_delay_factor += DELAY_INCREASE
            log('Failed to find the prompt during attempt %s. Increasing delay to %s'  
                % (str(i+1), ssh_connection.global_delay_factor), 
                proc= 'parse_hostname', v= util.A)
            sleep(1)
            continue
                    
        if '#' in output: 
            log('Prompt parsing found ' + output, proc='parse_hostname', v= util.N)
            return output.split('#')[0]
        else: sleep(1)
    
    # Last case scenario, return nothing
    log('Failed. No hostname found.', proc= 'parse_hostname', v= util.C)
    return None


def parse_nxos_interfaces(raw_config=''):
    
    log('Starting', proc='parse_nxos_interfaces', v= util.N)
    
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
        else: i.interface_type = str(re.split(r'\d', i.interface_name)[0])
        
        # Description
        try: i.interface_description = re.search(r'description[ ]+(.+)$', interf, re.IGNORECASE | re.MULTILINE).group(1)
        except: pass
        
        # IP and Subnet (Matches both octets and CIDR)
        ip_info = re.search(r'ip address.*?(\d{1,3}(?:\.\d{1,3}){3})[ ]?((?:\/\d+)|(?:\d{1,3}(?:\.\d{1,3}){3}))', interf, re.IGNORECASE | re.MULTILINE)
        if ip_info and ip_info.group(1): i.interface_ip = ip_info.group(1)
        if ip_info and ip_info.group(2): i.interface_subnet = ip_info.group(2)    
        
        # Add the new interface to the list of interfaces
        interfaces.append(i)

    if len(interfaces) > 0:
        log('{} interfaces found.'.format(
            len(interfaces)), proc= 'parse_nxos_interfaces', v= util.N)  
    else:
        log('No interfaces found. Raw_interfaces was: {}'.format(
            raw_interfaces), proc= 'parse_nxos_interfaces', v= util.C)                
    return interfaces            



def get_ios_int_br(ssh_connection):
    # Try three times to get the output, waiting longer each time 
    for i in range(2):
        try: raw_output = ssh_connection.send_command_expect('sh ip int br')
        except: 
            ssh_connection.global_delay_factor += DELAY_INCREASE
            log('Show ip interface brief attempt %s failed. New delay: %s' % (str(i+1), ssh_connection.global_delay_factor), proc='get_ios_int_br', v= util.A)
        
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
            log('Sh ip int br failed with error: ' + str(e), proc = 'get_ios_int_br', v= util.C)
            continue
    
    return interfaces
        
     


def parse_ios_interfaces(raw_config=''):
    
    log('Starting ios interface parsing.', proc="parse_ios_interfaces", v= util.N)
    interfaces = []
    # If no device config was passed, return
    if not raw_config: 
        log('No configuration passed. Returning.', proc = 'parse_ios_interfaces', v= util.A)
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
            log('Raw config parsing failed to find interface name. Skipping interface', proc='parse_ios_interfaces', v= util.C)
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
            log('Exception while parsing IP and Subnet: {}'.format(str(e)),
                proc = 'parse_ios_interfaces', v= util.C)
            pass
        
        interfaces.append(temp_interf)

    if len(interfaces) > 0:
        log('{} interfaces found.'.format(
            len(interfaces)), proc= 'parse_ios_interfaces', v= util.N)  
    else:
        log('No interfaces found. Raw_interfaces was: {}'.format(
            raw_interfaces), proc= 'parse_ios_interfaces', v= util.C)                 
    return interfaces            


def get_serials(ssh_connection):
    log('Starting to get serials', proc= 'get_serials', v= util.N)
    sleep(3)
    # Try three times to get the output, waiting longer each time 
    limit= 3
    for i in range(limit):
        try: raw_output = ssh_connection.send_command_expect('sh inv')
        except Exception as e: 
            log('Show inventory attempt %s failed.' % str(i+1), proc= 'get_serials', v= util.A)
            if i < limit: continue
            else:
                raise ValueError('''get_serials: Show inventory attempt \
finally failed on attempt {} with error: {}.'''.format(str(i+1), str(e))) 
    
        # Get each serial number
        output = re.findall(r'^Name.*?["](.+?)["][\s\S]*?Desc.*?["](.+?)["][\s\S]*?SN:[ ]?(\w+)', raw_output, re.MULTILINE | re.IGNORECASE)
        
        # See if valid results were produced.
        if not (output and output[0]):
            log('''Failed to get serials on attempt {}. Re.Findall produced no \
results. Raw_output[:20] was: {}'''.format(str(i+1), raw_output[:20]), 
                ip= ssh_connection.ip, proc= 'get_serials', v= util.A)
            
            # Continue if we haven't tried enough times yet, otherwise error out
            if i < limit: continue
            else:
                raise ValueError('''get_serials: Finally failed to get serials \
on attempt {}. Re.Findall produced no results. \
Raw_output was: {}'''.format(str(i+1), raw_output))
            
    
    serials = []
    
    for i in output:
        serials.append({
            'name': i[0],
            'description': i[1],
            'serial': i[2]
            })
    
    log('Finished. Got {} serials.'.format(len(serials)), proc= 'get_serials', v= util.N)
    return serials
    


def get_device(ip, platform='cisco_ios', global_delay_factor=1, name= None, debug= True):
    '''Main method which returns a fully populated network_device object'''
   
    # Open a connection to the device and return a session object
    # that we can reuse in multiple functions
    try: cli_results = start_cli_session(ip, platform, global_delay_factor)
    except Exception as e:
        raise ValueError('Error starting CLI session. No result set returned. ' +
                         'Error: ' + str(e))
   
    device = network_device()
    device.management_ip = ip
    device.netmiko_platform = platform
    device.device_name = name
    device.TCP_22 = cli_results['TCP_22']
    device.TCP_23 = cli_results['TCP_23']
    device.cred = cli_results['cred']

    if cli_results['ssh_connection']:
        ssh_connection = cli_results['ssh_connection']
        device.accessible = True
    else:
        device.accessible = False
        return device
            
    
    # enter enable mode
    limit = 3
    for i in range(limit):
        try: ssh_connection.enable()
        except Exception as e: 
            log('Enable failed on attempt %s. Current delay: %s' % (str(i+1), 
                ssh_connection.global_delay_factor), 
                ip= ssh_connection.ip, proc= 'get_device', v= util.A, error= e)
            
            # At the final try, return the failed device.
            if i == limit-1: 
                device.failed_msg= 'get_device: Could not enable.'
                return device
            
            # Otherwise rest for one second and then try again
            ssh_connection.global_delay_factor += DELAY_INCREASE
            sleep(1)
            continue
        else: 
            log('Enable successful on attempt %s. Current delay: %s' % 
                (str(i+1), ssh_connection.global_delay_factor), 
                ip= ssh_connection.ip, proc= 'get_device', v= util.N)
            sleep(2)
            break
    
    try: device.serial_numbers = get_serials(ssh_connection)
    except Exception as e:
        log('Exception occurred getting serial numbers: {}.'.format(str(e)), proc='get_device', v= util.C)
        device.failed_msg= 'get_device: Exception occurred getting serial numbers: {}.'.format(str(e))
        return device
    
    try: device.config = get_config(ssh_connection)
    except Exception as e:
        log('Exception occurred getting device config: {}'.format(str(e)), proc='get_device', v= util.C)
        device.failed_msg= 'get_device: Failed to get device config. Error: ' + str(e)
        return device
    
    try: device.device_name = parse_hostname(device.config, ssh_connection)
    except Exception as e:
        log('Exception occurred getting device name: {}'.format(str(e)), proc='get_device', v= util.C)
        device.failed_msg= 'get_device: Failed to get device name. Error: ' + str(e)
        return device
    
    try: device.neighbors, device.raw_cdp = get_cdp_neighbors(ssh_connection)
    except Exception as e:
        log('Exception occurred getting neighbor info: {}'.format(str(e)), proc='get_device', v= util.C)
        device.failed_msg= 'get_device: Failed to get neighbor info. Error: ' + str(e)
        return device    
        
    try:
        if 'ios' in platform:
            device.merge_interfaces(get_ios_int_br(ssh_connection))
            device.merge_interfaces(parse_ios_interfaces(device.config))
        elif 'nx' in platform:
            device.merge_interfaces(parse_nxos_interfaces(device.config))
    except Exception as e:
        log('Failed to retrieve interfaces from {} with error: {}'.format(ip, str(e)), proc='get_device', v= util.C)
        device.failed_msg= 'get_device: Failed to retrieve interfaces from {} with error: {}'.format(ip, str(e))
        return device
    
    try: device.other_ips = get_other_ips(device.config)
    except: 
        log('{} non-standard (virtual) ips found on the device'.format(len(device.other_ips)), proc= 'get_device', v= util.N)
        pass
    
    ssh_connection.disconnect()
    device.failed = False
    
    log('Finished getting {}'.format(device.unique_name()), proc='get_device', v= util.H)
    return device
    

def get_other_ips(raw_config):
    output = re.findall(r'(?:glbp|hsrp|standby).*?(\d{1,3}(?:\.\d{1,3}){3})', raw_config, re.I)
    log('{} non-standard (virtual) ips found on the device'.format(len(output)), proc= 'get_other_ips', v= util.D)
    return output

def get_config(ssh_connection):
    log('Beginning config download from %s' % ssh_connection.ip, proc='get_config', v= util.N)
    raw_config = ''
    
    sleep(2)
    # Try five times to get the output, waiting longer each time 
    for i in range(4):
        try: raw_config = ssh_connection.send_command_expect('sh run')
        except Exception as e: 
            log('Config download failed on attempt %s. Current delay: %s' % (str(i+1), ssh_connection.global_delay_factor), ssh_connection.ip, proc= 'get_config', v= util.A)
            ssh_connection.global_delay_factor += DELAY_INCREASE
            sleep(2)
            continue
        
        if len(raw_config) < 200:

            log('Config download completed, but seems too short. Attempt: {} Current delay: {} Config: {})'.format(
                str(i+1), ssh_connection.global_delay_factor, str(raw_config)), 
                ssh_connection.ip, proc= 'get_config', 
                v= util.C
                )
            ssh_connection.global_delay_factor += DELAY_INCREASE
            sleep(2)
            continue       
        
        log('Config download successful on attempt %s. Current delay: %s' % (str(i+1), ssh_connection.global_delay_factor), ssh_connection.ip, proc='get_config', v= util.N)
        sleep(1)
        break

    
    return raw_config

 
    