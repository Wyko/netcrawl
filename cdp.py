import re
from io_file import log, log_failed_device
from global_vars import DELAY_INCREASE
from time import sleep

def get_cdp_neighbors(ssh_connection):
    # Get the layer two neighbors for the device 
    try: cdp_output = get_raw_cdp_output(ssh_connection)
    except:
        log('# get_cdp_neighbors: No CDP output retrieved from %s' % ssh_connection.ip)
        
    if not cdp_output: 
        return
    
    # Parse out the CDP data and return a list of entries
    cdp_neighbor_list = []
    for entry in cdp_output:
        cdp_neighbor = parse_neighbor(entry)
    
        if not is_empty(cdp_neighbor): cdp_neighbor_list.append(cdp_neighbor)
    return cdp_neighbor_list



def get_raw_cdp_output(ssh_connection):
    """Get the CDP neighbor detail from the given device using SSH
    
    Returns:
        List of Strings: The raw CDP output, split into individual entries.
    """
    
    log('# get_raw_cdp_output: Starting, device %s' % ssh_connection.ip)
    
    # enter enable mode
    for i in range(2):
        try: ssh_connection.enable()
        except Exception as e: 
            log('# get_raw_cdp_output: Enable failed on attempt %s. Current delay: %s' % (str(i+1), ssh_connection.global_delay_factor), ssh_connection.ip)
            ssh_connection.global_delay_factor += DELAY_INCREASE
            continue
        else: 
            log('# get_raw_cdp_output: Enable successful on attempt %s. Current delay: %s' % (str(i+1), ssh_connection.global_delay_factor), ssh_connection.ip)
            break
            
    
    # execute the show cdp neighbor detail command
    # we increase the delay_factor for this command, because it take some time if many devices are seen by CDP
    result = ''
    for i in range(2):
        try: result = ssh_connection.send_command_expect("show cdp neighbor detail")
        except Exception as e:
            log('# get_raw_cdp_output: Sh cdp n det failed on attempt %s. Current delay: %s' % (str(i+1), ssh_connection.global_delay_factor), ssh_connection.ip)
            ssh_connection.global_delay_factor += DELAY_INCREASE
            sleep(1)
            continue
        else: 
            log('# get_raw_cdp_output: Sh cdp n det successful on attempt %s. Current delay: %s' % (str(i+1), ssh_connection.global_delay_factor), ssh_connection.ip)
            break
 
    # Split the raw output by the common '---' separator and return a list of 
    # CDP entries
    return re.split(r'-{4,}', result)

def parse_system_name(cdp_input):
    output = re.findall(r'(?:System Name|Device ID): ?(.*?)(?:\(|\n)', cdp_input, flags=re.I)
    if len(output)>1: return output[1] # Returns the more readable Device name if present
    elif output: return output[0] # Returns the device ID otherwise
    else: return ''
    
def parse_ip(cdp_input):
    output = re.search(r"(1[0-9]{1,3}(?:\.\d{1,3}){3})", cdp_input, flags=re.I)
    if output: return output.group(1)
    else: return ''

    
def parse_netmiko_platform(cdp_input):
    ios_strings = [
        'Internetwork Operating System Software',
        'IOS Software',
        'IOS (tm)'
        ]
    
    if 'NX-OS' in cdp_input: 
        return "cisco_nxos"
    elif any(ext in cdp_input for ext in ios_strings): 
        return "cisco_ios"
    else: return ''

    
def parse_system_platform(cdp_input):
    output = re.search(r'Platform: ?(.+?),', cdp_input)
    if output: return output.group(1)
    else: return ''
    

def parse_neighbor(cdp_input):
    output = {
        'name': '',
        'ip': '',
        #'management_ip': '',
        'netmiko_platform': '',
        'system_platform': ''
        }
    
    output['name'] = parse_system_name(cdp_input) 
    output['ip'] = parse_ip(cdp_input)
    output['netmiko_platform'] = parse_netmiko_platform(cdp_input)
    output['system_platform'] = parse_system_platform(cdp_input)
    
    return output


def is_empty(cdp_neighbor):
    for item in cdp_neighbor.values():
        if not item == '': return False
    return True
