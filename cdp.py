import re
import util
from gvars import DELAY_INCREASE
from time import sleep
from util import parse_ip, log

def get_cdp_neighbors(ssh_connection):
    
    limit = 3
    for i in range(limit):
        # Get the layer two neighbors for the device 
        try: raw_cdp = get_raw_cdp_output(ssh_connection)
        except:
            log('No CDP output retrieved from %s' % ssh_connection.ip, proc='get_cdp_neighbors', v= util.C)
            if i >= limit: raise ValueError('get_cdp_neighbors: No CDP output retrieved from %s' % ssh_connection.ip)
        else:
            # Check if we got actual output    
            if not raw_cdp: 
                log('Command successful but no CDP output retrieved from %s' % ssh_connection.ip, proc='get_cdp_neighbors', v= util.C)
                if i >= limit: raise ValueError('get_cdp_neighbors: Command successful but no CDP output retrieved from %s' % ssh_connection.ip)
                continue
            
            # Check whether CDP is enabled at all
            if re.search(r'not enabled', raw_cdp, re.I): 
                log('CDP not enabled on %s' % ssh_connection.ip, proc='get_cdp_neighbors', v= util.C)
                raise ValueError('get_cdp_neighbors: CDP not enabled on %s' % ssh_connection.ip)
            
            cdp_output= re.split(r'-{4,}', raw_cdp)
            
            # Parse out the CDP data and return a list of entries
            cdp_neighbor_list = []
            for entry in cdp_output:
                cdp_neighbor = parse_neighbor(entry)
            
                if not is_empty(cdp_neighbor): cdp_neighbor_list.append(cdp_neighbor)
            
            # If no neighbors were found, try again
            if not len(cdp_neighbor_list) > 0:
                log('No CDP neighbors found on attempt {}. raw_cdp[20] was: {}'.format(
                    str(i+1), raw_cdp[:20]), proc='get_cdp_neighbors', v= util.A)
                if i >= limit: raise ValueError('get_cdp_neighbors: Command successful but no CDP output retrieved from %s' % ssh_connection.ip)
                continue
            else:
                log('{} CDP neighbors found from {}.'.format(len(cdp_neighbor_list), ssh_connection.ip), proc='get_cdp_neighbors', v= util.NORMAL)
        
            return (cdp_neighbor_list, raw_cdp)



def get_raw_cdp_output(ssh_connection):
    """Get the CDP neighbor detail from the given device using SSH
    
    Returns:
        List of Strings: The raw CDP output, split into individual entries.
    """
    
    log('Starting, device %s' % ssh_connection.ip, proc='get_raw_cdp_output', v= util.N)
    
    # enter enable mode
    for i in range(2):
        try: ssh_connection.enable()
        except Exception as e: 
            log('Enable failed on attempt %s. Current delay: %s' % (str(i+1), ssh_connection.global_delay_factor), ssh_connection.ip, proc='get_raw_cdp_output', v= util.A)
            ssh_connection.global_delay_factor += DELAY_INCREASE
            continue
        else: 
            log('Enable successful on attempt %s. Current delay: %s' % (str(i+1), ssh_connection.global_delay_factor), ssh_connection.ip, proc='get_raw_cdp_output', v= util.N)
            break
            
    
    # Show cdp neighbor detail
    limit = 3
    for i in range(limit):
        try: result = ssh_connection.send_command_expect("show cdp neighbor detail")
        except Exception as e:
            log('Sh cdp n det failed on attempt %s. Current delay: %s' % 
                (str(i+1), ssh_connection.global_delay_factor), 
                ip= ssh_connection.ip, proc= 'get_raw_cdp_output', v= util.A,
                error= e)
            
            ssh_connection.global_delay_factor += DELAY_INCREASE
            sleep(1)
            continue
        else: 
            log('Sh cdp n det produced output on attempt {}'.format
                (str(i+1), ssh_connection.global_delay_factor), 
                ssh_connection.ip, proc='get_raw_cdp_output', v= util.NORMAL)
            break
 
    # Split the raw output by the common '---' separator and return a list of 
    # CDP entries
    if result: return result
    else: return None

def parse_system_name(cdp_input):
    output = re.findall(r'(?:System Name|Device ID): ?(.*?)(?:\(|\n)', cdp_input, flags=re.I)
    
    if len(output)>1: _hostname = output[1] # Returns the more readable Device name if present
    elif output: _hostname = output[0] # Returns the device ID otherwise
    else: return ''

    if "." in _hostname: _hostname = _hostname.split(".")[0]
    return _hostname

    
def parse_netmiko_platform(cdp_input):
    blacklist = [
        'AIR',
        'IP Phone'
        ]
    
    ios_strings = [
        'Internetwork Operating System Software',
        'IOS Software',
        'IOS (tm)'
        ]
    
    if any(ext in cdp_input for ext in blacklist):
        return ''
    elif 'NX-OS' in cdp_input: 
        return "cisco_nxos"
    elif any(ext in cdp_input for ext in ios_strings): 
        return "cisco_ios"
    else: return None

    
def parse_system_platform(cdp_input):
    output = re.search(r'Platform: ?(.+?),', cdp_input, flags=re.I)
    if output: return output.group(1)
    else: return ''


def parse_source_interface(cdp_input):
    output = re.search(r'^interface:[ ]?(.*?)[,\n]', cdp_input, flags=(re.I|re.M))
    if output: return output.group(1)
    else: return ''


def parse_neighbor_interface(cdp_input):
    output = re.search(r'^interface:.*?:[ ](.*?)[,\n ]', cdp_input, flags=(re.I|re.M))
    if output: return output.group(1)
    else: return ''

def parse_neighbor(cdp_input):
    output = {
        'name': '',
        'ip': '',
        'connect_ip': '',
        'netmiko_platform': '',
        'system_platform': '',
        'source_interface': '',
        'neighbor_interface': '',
        'software': '',
        'raw_cdp': cdp_input,
        }
    
    # Get each IP address
    ip = parse_ip(cdp_input)
    if ip and len(ip) > 0: output['ip'] = ip[0]
    if ip and len(ip) > 1: output['connect_ip'] = ip[1]
    
    output['name'] = parse_system_name(cdp_input) 
    output['netmiko_platform'] = parse_netmiko_platform(cdp_input)
    output['system_platform'] = parse_system_platform(cdp_input)
    output['source_interface'] = parse_source_interface(cdp_input)
    output['neighbor_interface'] = parse_neighbor_interface(cdp_input)
    
    return output


def is_empty(cdp_neighbor):
    for item in cdp_neighbor.values():
        if not item == '': return False
    return True
