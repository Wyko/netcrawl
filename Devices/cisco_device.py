'''
Created on Feb 19, 2017

@author: Wyko
'''

from util import log, parse_ip
from time import sleep
import re, util
import gvars
from Devices.base_device import network_device

class cisco_device(network_device):
    '''
    classdocs
    '''
        
    def parse_hostname(self, attempts=5):
        log('Starting', proc='parse_hostname', v= util.N)
        
        output = re.search('^hostname (.+)\n', self.config, re.MULTILINE)
        if output and output.group(1): 
            log('Regex parsing the config found {}'.format(output.group(1)), proc='parse_hostname', v= util.N)
            self.device_name= output.group(1)
            return True
        
        else: log('Regex parsing failed, trying prompt parsing.', proc='parse_hostname', v= util.N)
        
        if not self.ssh_connection: 
            log('No self.ssh_connection object passed, function failed', proc= 'parse_hostname', v= util.C)
            raise ValueError('parse_hostname: No ssh_connection object passed')
        
        # If the hostname couldn't be parsed, get it from the prompt    
        for i in range(attempts):
            try:
                output = self.ssh_connection.find_prompt()
            except ValueError:
                self.ssh_connection.global_delay_factor += gvars.DELAY_INCREASE
                log('Failed to find the prompt during attempt %s. Increasing delay to %s'  
                    % (str(i+1), self.ssh_connection.global_delay_factor), 
                    proc= 'parse_hostname', v= util.A)
                sleep(2 + i)
                continue
                        
            if '#' in output: 
                log('Prompt parsing found ' + output, proc='parse_hostname', v= util.N)
                self.device_name= output.split('#')[0]
                return True
            
            else: sleep(2 + 1)
        
        # Last case scenario, return nothing
        log('Failed. No hostname found.', proc= 'parse_hostname', v= util.C)
        raise ValueError('parse_hostname failed. No hostname found.')


    def get_serials(self):
        log('Starting to get serials', proc= 'get_serials', v= util.N)
        sleep(3)
        # Try three times to get the output, waiting longer each time 
        limit= 3
        for i in range(limit):
            try: raw_output = self.ssh_connection.send_command_expect('sh inv')
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
                    ip= self.ssh_connection.ip, proc= 'get_serials', v= util.A)
                
                # Continue if we haven't tried enough times yet, otherwise error out
                if i < limit: continue
                else:
                    raise ValueError('''get_serials: Finally failed to get serials \
    on attempt {}. Re.Findall produced no results. \
    Raw_output was: {}'''.format(str(i+1), raw_output))
                
                
        # Add the found serials to the parent device        
        serials = []
        for i in output:
            serials.append({
                'name': i[0],
                'description': i[1],
                'serial': i[2]
                })
        log('Finished. Got {} serials.'.format(len(serials)), proc= 'get_serials', v= util.N)
        self.serial_numbers.extend(serials)
        return True
        
        
    def get_config(self, attempts=5):
        log('Beginning config download from %s' % self.ssh_connection.ip, proc='get_config', v= util.N)
        raw_config = ''
        
        sleep(2)
        # Try five times to get the output, waiting longer each time 
        for i in range(4):
            try: raw_config = self.ssh_connection.send_command_expect('sh run')
            except Exception as e: 
                log('Config download failed on attempt %s. Current delay: %s' % (str(i+1), 
                    self.ssh_connection.global_delay_factor), self.ssh_connection.ip, proc= 'get_config', v= util.A, error= e)
                self.ssh_connection.global_delay_factor += gvars.DELAY_INCREASE
                sleep(2)
                continue
            
            if len(raw_config) < 250:
                log('Config download completed, but seems too short. Attempt: {} Current delay: {} Config[:30]: {})'.format(
                    str(i+1), self.ssh_connection.global_delay_factor, str(raw_config)[:30]), 
                    self.ssh_connection.ip, proc= 'get_config', 
                    v= util.C
                    )
                self.ssh_connection.global_delay_factor += gvars.DELAY_INCREASE
                sleep(2)
                continue       
            
            log('Config download successful on attempt %s. Current delay: %s' % (str(i+1), self.ssh_connection.global_delay_factor), self.ssh_connection.ip, proc='get_config', v= util.N)
            sleep(2+i)
            break
    
        self.config = raw_config
    
    
    def get_other_ips(self):
        output = re.findall(r'(?:glbp|hsrp|standby).*?(\d{1,3}(?:\.\d{1,3}){3})', self.config, re.I)
        log('{} non-standard (virtual) ips found on the device'.format(len(output)), proc= 'get_other_ips', v= util.D)
        self.other_ips.extend(output)
        
    
    def get_cdp_neighbors(self, attempts= 3):
    
        for i in range(attempts):
            
            # Get the CDP neighbors for the device 
            try: raw_cdp = self.get_raw_cdp_output()
            except:
                log('No CDP output retrieved from %s' % self.ssh_connection.ip, proc='get_cdp_neighbors', v= util.C)
                if i >= attempts: raise ValueError('get_cdp_neighbors: No CDP output retrieved from %s' % self.ssh_connection.ip)
            else:
                
                # Check if we got actual output    
                if not raw_cdp: 
                    log('Attempt {}: Command successful but no CDP output retrieved from {}'.format(str(i), self.ssh_connection.ip), proc='get_cdp_neighbors', v= util.C)
                    if i >= attempts: raise ValueError('get_cdp_neighbors: Command successful but no CDP output retrieved from %s' % self.ssh_connection.ip)
                    continue
                
                # Check whether CDP is enabled at all
                if re.search(r'not enabled', raw_cdp, re.I): 
                    log('CDP not enabled on %s' % self.ssh_connection.ip, proc='get_cdp_neighbors', v= util.C)
                    raise ValueError('get_cdp_neighbors: CDP not enabled on %s' % self.ssh_connection.ip)
                
                # Split the full 'sh cdp [...]' output into non-empty individual neighbors
                cdp_output= list(filter(None, re.split(r'-{4,}', raw_cdp)))
                
                # Parse each neighbor's CDP data
                cdp_neighbor_list = []
                for entry in cdp_output:
                    try: cdp_neighbor = self.parse_neighbor(entry)
                    except: continue
                    else:
                        if cdp_neighbor: cdp_neighbor_list.append(cdp_neighbor)
                
                # If no neighbors were found, try again
                if not len(cdp_neighbor_list) > 0:
                    log('Attempt {}: No CDP neighbors found. raw_cdp[20] was: {}'.format(
                        str(i+1), raw_cdp[:20]), proc='get_cdp_neighbors', v= util.A)
                    if i >= attempts: raise ValueError('get_cdp_neighbors: Command successful but no CDP output retrieved from %s' % self.ssh_connection.ip)
                    continue
                else:
                    log('{} CDP neighbors found from {}.'.format(len(cdp_neighbor_list), self.ssh_connection.ip), proc='get_cdp_neighbors', v= util.NORMAL)
                    
                self.neighbors= cdp_neighbor_list
                self.raw_cdp = raw_cdp
                return True


    def get_raw_cdp_output(self, attempts= 3):
        """Get the CDP neighbor detail from the given device using SSH
        
        Returns:
            String: The raw CDP output.
        """
        
        log('Starting, device %s' % self.ssh_connection.ip, proc='get_raw_cdp_output', v= util.N)
        
        # Show cdp neighbor detail
        for i in range(attempts):
            try: result = self.ssh_connection.send_command_expect("show cdp neighbor detail")
            except Exception as e:
                log('Sh cdp n det failed on attempt %s. Current delay: %s' % 
                    (str(i+1), self.ssh_connection.global_delay_factor), 
                    ip= self.ssh_connection.ip, proc= 'get_raw_cdp_output', v= util.A,
                    error= e)
                
                self.ssh_connection.global_delay_factor += gvars.DELAY_INCREASE
                sleep(1)
                continue
            else: 
                log('Sh cdp n det produced output on attempt {}'.format
                    (str(i+1), self.ssh_connection.global_delay_factor), 
                    self.ssh_connection.ip, proc='get_raw_cdp_output', v= util.NORMAL)
                break
     
        # Split the raw output by the common '---' separator and return a list of 
        # CDP entries
        if result: return result
        else: return None
    
        
    def parse_netmiko_platform(self, cdp_input):
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
    
    
    def parse_neighbor(self, cdp_input):
        '''Accepts a single CDP neighbor entry and parses it into
        a dictionary.
        '''
        
        output = {
            'device_name': None,
            'netmiko_platform': None,
            'system_platform': None,
            'source_interface': None,
            'neighbor_interface': None,
            'software': None,
            'raw_cdp': cdp_input,
            'ip': None,
            'other_ips': []
            }
        
        # Get each IP address
        ip_list = parse_ip(cdp_input)
        
        for i, ip in enumerate(ip_list):
            if i==0: output['ip'] = ip
            else: output['other_ips'].append(ip)
        
        output['netmiko_platform'] = self.parse_netmiko_platform(cdp_input)
        
        # Parse the system platform
        system_platform = re.search(r'Platform: ?(.+?),', cdp_input, flags=re.I)
        if system_platform: output['system_platform'] = system_platform.group(1)
        
        # Parse the source interface
        source_interface = re.search(r'^interface:[ ]?(.*?)[,\n]', cdp_input, flags=(re.I|re.M))
        if source_interface: output['source_interface']= source_interface.group(1)
    
        # Parse the neighbor interface
        neighbor_interface = re.search(r'^interface:.*?:[ ](.*?)[,\n ]', cdp_input, flags=(re.I|re.M))
        if neighbor_interface: output['neighbor_interface']= neighbor_interface.group(1)
        
        # Get the device name
        device_name = re.findall(r'(?:System Name|Device ID): ?(.*?)(?:\(|\n)', cdp_input, flags=re.I)
        if len(device_name)>1: output['device_name'] = device_name[1] # Returns the more readable Device name if present
        elif output: output['device_name'] = device_name[0] # Returns the device ID otherwise
        if "." in output['device_name']: output['device_name'] = output['device_name'].split(".")[0]
        
        return output

