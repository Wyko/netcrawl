import re

def get_cdp_neighbors(ssh_connection):
    # Get the layer two neighbors for the device 
    cdp_output = get_raw_cdp_output(ssh_connection)
    if not cdp_output: 
        print ('# No CDP output retrieved from %s' % ssh_connection.ip)
        raise IOError('No CDP output retrieved' % ssh_connection.ip)
        return
    
    # Parse out the CDP data and return a list of entries
    cdp_neighbor_list = []
    for entry in cdp_output:
        cdp_neighbor = parse_neighbor(entry)
    
        if not is_empty(cdp_neighbor): cdp_neighbor_list.append(cdp_neighbor)
    return cdp_neighbor_list



def get_raw_cdp_output(ssh_connection):
    """
    get the CDP neighbor detail from the given device using SSH
     
    :return:
    """
 
    # enter enable mode
    ssh_connection.enable()
 
    # prepend the command prompt to the result (used to identify the local host)
    result = ssh_connection.find_prompt() + "\n"
 
    # execute the show cdp neighbor detail command
    # we increase the delay_factor for this command, because it take some time if many devices are seen by CDP
    result += ssh_connection.send_command("show cdp neighbor detail", delay_factor=2)
 
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
