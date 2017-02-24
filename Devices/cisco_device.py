'''
Created on Feb 19, 2017

@author: Wyko
'''

from util import log, parse_ip
from time import sleep
import re, util
import gvars
from Devices.base_device import network_device, interface

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
        
        else: log('Regex parsing failed, trying prompt parsing.', proc='parse_hostname', v= util.D)
        
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
        proc= 'cisco_device.get_serials'
        
        log('Starting to get serials', proc= proc, v= util.I)
        
        # Poll the device for the serials
        raw_output= self.attempt('show inventory', 
                     proc= proc, 
                     fn_check= lambda x: bool(re.search(r'''
                                        ^Name.*?["](.+?)["][\s\S]*?
                                        Desc.*?["](.+?)["][\s\S]*?
                                        SN:[ ]?(\w+)''',
                                        x, re.X|re.M|re.I)))
        
        # Parse each serial number
        output = re.findall(r'''
                            ^Name.*?["](.+?)["][\s\S]*?
                            Desc.*?["](.+?)["][\s\S]*?
                            SN:[ ]?(\w+)''',
                            raw_output, re.X|re.M|re.I)
        
        # Raise error if no results were produced.
        if not (output and output[0]):
            log('Failed to get serials. Re.Findall produced no results. ' + 
                'Raw_output[:20] was: {}'.format(raw_output[:20]), 
                ip= self.ssh_connection.ip, proc= proc, v= util.A)
            raise ValueError(proc+ ': Failed to get serials. Re.Findall produced no results '+
                'Raw_output was: {}'''.format(raw_output))
                
        # Add the found serials to the parent device        
        serials = []
        for i in output:
            serials.append({
                'name': i[0],
                'desc': i[1],
                'serialnum': i[2]
                })
        log('Serials found: {}'.format(len(serials)), proc= proc, v= util.N)
        self.serial_numbers.extend(serials)
        return True
        
    
    def split_interface_name(self, interface_name):
        '''Returns a tuple containing (interface_type, interface_number)'''
        
        try: output= re.search(r'''
                ([A-Za-z]{2,})   # An interface name, consisting of at least 2 letters
                ([\d\/]+)        # The interface number, with potential backslashes
            ''', interface_name, re.I | re.X | re.M) 
        except: 
            return None
        else:
            if output and output.re.groups==2: 
                return (
                    output.group(1),
                    output.group(2),
                    )
            else: 
                return None
    

    def get_mac_address_table(self, attempts= 3):
        '''Populates self.mac_address_table from the remote device.
        
        Returns:
            Boolean: True if the command was successful
            
        Raises:
            Exception: ValueError if no result was found.
        '''
        
        # Try the two command formats
        try: self.raw_mac_address_table = self.attempt('show mac address-table', 
                         proc= 'cisco_device.get_mac_address_table', 
                         fn_check= lambda x: bool(re.search(r'(?:[0-9A-F]{2,4}[\:\-\.]){2,7}[0-9A-F]{2,4}', x, re.I)),
                         alert= False)
        except: 
            try: self.raw_mac_address_table = self.attempt('show mac-address-table', 
                         proc= 'cisco_device.get_mac_address_table', 
                         fn_check= lambda x: bool(re.search(r'(?:[0-9A-F]{2,4}[\:\-\.]){2,7}[0-9A-F]{2,4}', x, re.I)),
                         alert= False)
            except:
                log('No MAC addresses found.', proc= 'cisco_device.get_mac_address_table', v=util.C)
                return False
        
        # Parse the table
        output= re.finditer(         # #### MAC Regex ####
            r'''            
            (?P<mac_address>         # MAC capture group
                (?:[0-9A-F]{2,4}[\:\-\.]){2,7}[0-9A-F]{2,4}
            )                    
            .*?                      # Skip all characters up to the interface
            (?P<interface_name>      # Interface capture group
                (?P<interface_type>
                    [A-Za-z]{2,}     # At least two letters
                )
                (?P<interface_number>
                    [\d\/]+          # Any combination of numbers and
                )    
            )
            \s*?$                    # Match if interface is at the end of the line
            ''', self.raw_mac_address_table, flags= (re.X | re.I | re.M) )

        # Return a dictionary containing the MAC's and interfaces
        self.mac_address_table= [m.groupdict() for m in output]
        
        for mac in self.mac_address_table:
            # Ignore blank mac addresses
            if mac == 'ffff.ffff.ffff': continue
            
            # Get the associated parent interface
            interf= self.match_partial_to_full_interface(mac['interface_name'])
           
            # If no match was found, create a new interface for it and append it to the list
            if not interf:
                interf= interface()
                interf.interface_description= '**** Matched from MAC Address, not interface list'
                interf.interface_name= mac['interface_name']
                self.interfaces.append(interf)
            
            # Add the MAC to the interface
            interf.mac_address_table.append(mac['mac_address'])
        return True


    def get_config(self, attempts=5):
        proc= 'cisco_device.get_config'
        log('Beginning config download from %s' % self.ssh_connection.ip, proc= proc, v= util.I)
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
            raw_cdp= self.attempt('show cdp neighbor detail', 
                         proc= 'cisco_device.get_cdp_neighbors', 
                         attempts= attempts,
                         fn_check= lambda x: bool(x))
            
            # Check whether CDP is enabled at all
            if re.search(r'not enabled', raw_cdp, re.I): 
                log('CDP not enabled on %s' % self.ssh_connection.ip, proc='get_cdp_neighbors', v= util.C)
                raise ValueError('get_cdp_neighbors: CDP not enabled on %s' % self.ssh_connection.ip)
            
            # Split the full 'sh cdp [...]' output into non-empty individual neighbors
            cdp_output= list(filter(None, re.split(r'-{4,}', raw_cdp)))
            
            # Parse each neighbor's CDP data
            cdp_neighbor_list = []
            neighbor_count= 0
            for entry in cdp_output:
                try: cdp_neighbor = self.parse_neighbor(entry)
                except: continue
                else:
                    if not cdp_neighbor: continue
                    neighbor_count +=1
                    
                    # Match a neighbor to a full neighbor entry
                    interf= self.match_partial_to_full_interface(cdp_neighbor['source_interface'])
                    if interf: interf.neighbors.append(cdp_neighbor)
                    
                    # Or else add it to the list of unmatched neighbors
                    else: cdp_neighbor_list.append(cdp_neighbor)
            
            # If no neighbors were found, try again
            if not neighbor_count > 0:
                log('Attempt {}: No CDP neighbors found. raw_cdp[20] was: {}'.format(
                    str(i+1), raw_cdp[:20]), proc='get_cdp_neighbors', v= util.A)
                if i >= attempts: raise ValueError('get_cdp_neighbors: Command successful but no CDP output retrieved from %s' % self.ssh_connection.ip)
                continue
            else:
                log('{} CDP neighbors found from {}.'.format(neighbor_count, self.ssh_connection.ip), proc='get_cdp_neighbors', v= util.NORMAL)
                
            self.neighbors= cdp_neighbor_list
            self.raw_cdp = raw_cdp
            return True

    
    def match_partial_to_full_interface(self, partial):
        '''Given a partial MAC address, iterate through all of this device's
        interfaces and match the address to an interface. Return the 
        interface.
        
        1. Split the MAC interface by name and number
        2. For each interface, check if the interface name starts with the MAC name
        3. If so, check if the interface number matches the MAC interface number
        4. Add the MAC to the interface MAC table
        '''
        if not partial: return None
        # Split the MAC
        output= self.split_interface_name(partial)
        
        # Returns none if no matches were found (such as when the interface is "Switch"
        if not output: return None
        
        # Match expanded interface names
        p = re.compile(r'^' + output[0] + r'.*?' + output[1], re.I)
        
        # Check if the mac's interface name matches an interface
        for interf in self.interfaces:
            if bool(p.match(interf.interface_name)):
                log('Partial interface {} matched interface {}'.format(
                    partial, interf.interface_name),
                    v= util.D, proc= 'cisco_device.match_mac_to_interface')
                
                return interf 
        
        # If no match was found return false
        self.alert('No interface match for {}'.format(partial), proc= 'cisco.match_mac_to_interface')
        return None
                    
        
    
        
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

