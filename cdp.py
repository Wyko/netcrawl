import re, uti
from global_vars import DELAY_INCREASE
from time import sleep
from uti import parse_ip, log

def get_cdp_neighbors(ssh_connection):
    # Get the layer two neighbors for the device 
    try: cdp_output = get_raw_cdp_output(ssh_connection)
    except:
        log('No CDP output retrieved from %s' % ssh_connection.ip, proc='get_cdp_neighbors', v= uti.C)
        raise ValueError('get_cdp_neighbors: No CDP output retrieved from %s' % ssh_connection.ip)
    
    # Check if we got actual output    
    if not cdp_output and cdp_output[0]: 
        log('Command successful but no CDP output retrieved from %s' % ssh_connection.ip, proc='get_cdp_neighbors', v= uti.C)
        raise ValueError('get_cdp_neighbors: Command successful but no CDP output retrieved from %s' % ssh_connection.ip)
    
    # Check whether CDP is enabled at all
    if re.search(r'not enabled', cdp_output[0], re.I): 
        log('CDP not enabled on %s' % ssh_connection.ip, proc='get_cdp_neighbors', v= uti.C)
        raise ValueError('get_cdp_neighbors: CDP not enabled on %s' % ssh_connection.ip)
    
    # Parse out the CDP data and return a list of entries
    cdp_neighbor_list = []
    for entry in cdp_output:
        cdp_neighbor = parse_neighbor(entry)
    
        if not is_empty(cdp_neighbor): cdp_neighbor_list.append(cdp_neighbor)
    
    if not len(cdp_neighbor_list) > 0:
        log('No CDP neighbors found from {}. CDP_output was: {}'.format(
            ssh_connection.ip, cdp_output), proc='get_cdp_neighbors', v= uti.C)
    else:
        log('{} CDP neighbors found from {}.'.format(len(cdp_neighbor_list), ssh_connection.ip), proc='get_cdp_neighbors', v= uti.NORMAL)

    return cdp_neighbor_list



def get_raw_cdp_output(ssh_connection):
    """Get the CDP neighbor detail from the given device using SSH
    
    Returns:
        List of Strings: The raw CDP output, split into individual entries.
    """
    
    log('Starting, device %s' % ssh_connection.ip, proc='get_raw_cdp_output', v= uti.N)
    
    # enter enable mode
    for i in range(2):
        try: ssh_connection.enable()
        except Exception as e: 
            log('Enable failed on attempt %s. Current delay: %s' % (str(i+1), ssh_connection.global_delay_factor), ssh_connection.ip, proc='get_raw_cdp_output', v= uti.A)
            ssh_connection.global_delay_factor += DELAY_INCREASE
            continue
        else: 
            log('Enable successful on attempt %s. Current delay: %s' % (str(i+1), ssh_connection.global_delay_factor), ssh_connection.ip, proc='get_raw_cdp_output', v= uti.N)
            break
            
    
    # execute the show cdp neighbor detail command
    # we increase the delay_factor for this command, because it take some time if many devices are seen by CDP
    result = ''
    for i in range(2):
        try: result = ssh_connection.send_command_expect("show cdp neighbor detail")
        except Exception as e:
            log('Sh cdp n det failed on attempt %s. Current delay: %s' % (str(i+1), ssh_connection.global_delay_factor), ssh_connection.ip, proc='get_raw_cdp_output', v= uti.A)
            ssh_connection.global_delay_factor += DELAY_INCREASE
            sleep(1)
            continue
        else: 
            log('Sh cdp n det successful on attempt %s. Current delay: %s' % 
                (str(i+1), ssh_connection.global_delay_factor), 
                ssh_connection.ip, proc='get_raw_cdp_output', v= uti.NORMAL)
            break
 
    # Split the raw output by the common '---' separator and return a list of 
    # CDP entries
    return re.split(r'-{4,}', result)

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
    else: return ''

    
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
        'management_ip': '',
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
    if ip and len(ip) > 1: output['management_ip'] = ip[1]
    
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
