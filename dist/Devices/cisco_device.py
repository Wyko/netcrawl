'''
Created on Feb 19, 2017

@author: Wyko
'''

from Devices.base_device import network_device, interface
from wylog import log, logging
from util import parse_ip
from time import sleep
import re, gvars, util

class cisco_device(network_device):
        
    def _parse_hostname(self, attempts=5):
        proc = 'cisco_device._parse_hostname'
        log('Parsing hostname', proc=proc, v=logging.I)
        
        output = re.search('^hostname (.+)\n', self.config, re.MULTILINE)
        if output and output.group(1): 
            log('Hostname from regex: {}'.format(output.group(1)), proc=proc, v=logging.N)
            self.device_name = output.group(1)
            return True
        
        else: log('Regex parsing failed, trying prompt parsing.', proc=proc, v=logging.D)
        
        if not self.connection: 
            log('No self.connection object available. Method failed', proc=proc, v=logging.C)
            raise ValueError(proc + ': No self.connection object available')
        
        # If the hostname couldn't be parsed, get it from the prompt    
        for i in range(attempts):
            try:
                output = self.connection.find_prompt()
            except ValueError:
                self.connection.global_delay_factor += gvars.DELAY_INCREASE
                log('Failed to find the prompt during attempt %s. Increasing delay to %s'  
                    % (str(i + 1), self.connection.global_delay_factor),
                    proc=proc, v=logging.A)
                sleep(2 + i)
                continue
                        
            if '#' in output: 
                self.device_name = output.split('#')[0]
                log('Hostname from prompt: ' + self.device_name, proc=proc, v=logging.N)
                return True
            
            else: sleep(2 + 1)
        
        # Last case scenario, return nothing
        log('Failed. No hostname found.', proc=proc, v=logging.C)
        raise ValueError('_parse_hostname failed. No hostname found.')

    
    def _get_serials(self):
        proc = 'cisco_device._get_serials'
        
        log('Starting to get serials', proc=proc, v=logging.I)
        
        # Poll the device for the serials
        raw_output = self._attempt('show inventory',
                     proc=proc,
                     fn_check=lambda x: bool(re.search(r'''
                                        ^Name.*?["](.+?)["][\s\S]*?
                                        Desc.*?["](.+?)["][\s\S]*?
                                        SN:[ ]?(\w+)''',
                                        x, re.X | re.M | re.I)))
        
        # Parse each serial number
        output = re.findall(r'''
                            ^Name.*?["](.+?)["][\s\S]*?
                            Desc.*?["](.+?)["][\s\S]*?
                            SN:[ ]?(\w+)''',
                            raw_output, re.X | re.M | re.I)
        
        # Raise error if no results were produced.
        if not (output and output[0]):
            log('Failed to get serials. Re.Findall produced no results. ' + 
                'Raw_output[:20] was: {}'.format(raw_output[:20]),
                ip=self.connection.ip, proc=proc, v=logging.A)
            raise ValueError(proc + ': Failed to get serials. Re.Findall produced no results ' + 
                'Raw_output was: {}'''.format(raw_output))
                
        # Add the found serials to the parent device        
        serials = []
        for i in output:
            serials.append({
                'name': i[0],
                'desc': i[1],
                'serialnum': i[2]
                })
        log('Serials found: {}'.format(len(serials)), proc=proc, v=logging.N)
        self.serial_numbers.extend(serials)
        return True
        
    
    def split_interface_name(self, interface_name):
        '''Returns a tuple containing (interface_type, interface_number)'''
        
        try: output = re.search(r'''
                ([A-Za-z\-]{2,})   # An interface name, consisting of at least 2 letters
                ([\d\/\.]+)        # The interface number, with potential backslashes
            ''', interface_name, re.I | re.X | re.M) 
        except: 
            return None
        else:
            if output and output.re.groups == 2: 
                return (
                    output.group(1),
                    output.group(2),
                    )
            else: 
                return None
    
    
    
    
    def _get_mac_address_table(self, attempts=3):
        '''Populates self.mac_address_table from the remote device.
        
        Returns:
            Boolean: True if the command was successful
            
        Raises:
            Exception: ValueError if no result was found.
        '''
        proc = 'cisco_device._get_mac_address_table'

        log('Getting MAC address table', proc=proc, v=logging.I)
        
        # Try the two command formats
        try: self.raw_mac_address_table = self._attempt('show mac address-table',
                         proc=proc,
                         fn_check=util.contains_mac_address,
                         alert=False)
        except: 
            try: self.raw_mac_address_table = self._attempt('show mac-address-table',
                         proc=proc,
                         fn_check=util.contains_mac_address,
                         alert=False)
            except:
                log('No MAC addresses found.', proc=proc, v=logging.A)
                return False
        
        # Parse the table
        output = re.finditer(# #### MAC Regex ####
            r'''            
            (?P<mac_address>         # MAC capture group
                (?:[0-9A-F]{2,4}[\:\-\.]){2,7}[0-9A-F]{2,4}
            )                    
            .*?                      # Skip all characters up to the interface
            (?P<interface_name>      # Interface capture group
                (?P<interface_type>
                    [A-Za-z\-]{2,}     # At least two letters
                )
                (?P<interface_number>
                    [\d\/]+          # Any combination of numbers and
                )    
            )
            \s*?$                    # Match if interface is at the end of the line
            ''',
            self.raw_mac_address_table, flags=(re.X | re.I | re.M))

        # Return a dictionary containing the MAC's and interfaces
        self.mac_address_table = [m.groupdict() for m in output]
        
        count = 0
        for mac in self.mac_address_table:
            # Ignore blank mac addresses
            if mac['mac_address'] == 'ffff.ffff.ffff': continue
            
            count += 1 
            
            # Get the associated parent interface
            interf = self.match_partial_to_full_interface(mac['interface_name'])
           
            # If no match was found, create a new interface for it and append it to the list
            if not interf:
                interf = interface()
                interf.interface_description = '**** Matched from MAC Address, not interface list'
                interf.interface_name = mac['interface_name']
                self.interfaces.append(interf)
            
            # Normalize the MAC
            mac['mac_address'] = self._normalize_mac_address(mac['mac_address'])
            
            # Add the MAC to the interface
            interf.mac_address_table.append(mac['mac_address'])
        
        log('MAC entries found: {}'.format(count), proc=proc, v=logging.N)
        return True


    def _get_config(self, attempts=5):
        proc = 'cisco_device._get_config'
        
        log('Beginning config download from %s' % self.connection.ip, proc=proc, v=logging.I)

        self.config = self._attempt('show run',
                             proc=proc,
                             fn_check=lambda x: bool(len(x) > 250),
                             check_msg='Config seems too short.',
                             attempts=attempts,
                             )
        
        log('Config download successful.', ip=self.connection.ip, proc=proc, v=logging.N)
    
    
    def _get_other_ips(self):
        proc = 'cisco_device._get_other_ips'
        output = re.findall(r'(?:glbp|hsrp|standby).*?(\d{1,3}(?:\.\d{1,3}){3})', self.config, re.I)
        log('{} non-standard (virtual) ips found on the device'.format(len(output)), proc=proc, v=logging.D)
        self.other_ips.extend(output)
        
    
    def _get_cdp_neighbors(self, attempts=3):
        proc = 'cisco_device._get_cdp_neighbors'

        log('Getting CDP neighbors', proc=proc, v=logging.I)
        
        for i in range(attempts):
            # Get the CDP neighbors for the device 
            raw_cdp = self._attempt('show cdp neighbor detail',
                         proc=proc,
                         attempts=attempts,
                         fn_check=lambda x: bool(x))
            
            # Check whether CDP is enabled at all
            if re.search(r'not enabled', raw_cdp, re.I): 
                log('CDP not enabled on %s' % self.connection.ip, proc=proc, v=logging.C)
                raise ValueError(proc + ': CDP not enabled on %s' % self.connection.ip)
            
            # Split the full 'sh cdp [...]' output into non-empty individual neighbors
            cdp_output = list(filter(None, re.split(r'-{4,}', raw_cdp)))
            
            # Parse each neighbor's CDP data
            cdp_neighbor_list = []
            neighbor_count = 0
            for entry in cdp_output:
                try: cdp_neighbor = self.parse_neighbor(entry)
                except: continue
                else:
                    if not cdp_neighbor: continue
                    neighbor_count += 1
                    
                    # Match a neighbor to a full neighbor entry
                    interf = self.match_partial_to_full_interface(cdp_neighbor['source_interface'])
                    if interf: interf.neighbors.append(cdp_neighbor)
                    
                    # Or else add it to the list of unmatched neighbors
                    else: cdp_neighbor_list.append(cdp_neighbor)
            
            # If no neighbors were found, try again
            if not neighbor_count > 0:
                log('Attempt {}: No CDP neighbors found. raw_cdp[20] was: {}'.format(
                    str(i + 1), raw_cdp[:20]), proc=proc, v=logging.A)
                if i >= attempts: raise ValueError(proc + ': Command successful but no neighbors found from %s' % self.connection.ip)
                continue
            else:
                log('CDP neighbors found: {}'.format(neighbor_count), proc=proc, v=logging.N)
                
            self.neighbors = cdp_neighbor_list
            self.raw_cdp = raw_cdp
            return True

    
    def match_partial_to_full_interface(self, partial):
        '''Given a partial MAC address, iterate through all of this device's
        interfaces and match the address to an interface. Return the 
        interface.
        
        1. Split the partial interface by name and number
        2. For each interface, check if the interface name starts with the partial name
        3. If so, check if the interface number matches the partial interface number
        4. Return the full interface name
        '''
        proc = 'cisco_device.match_partial_to_full_interface'
        
        if not partial: return None
        # Split the MAC
        output = self.split_interface_name(partial)
        
        # Returns none if no matches were found (such as when the interface is "Switch"
        if not output: return None
        
        # Escape any problematic strings (like Gig0/0.100)
        output = [re.escape(x) for x in output]
        
        # Match expanded interface names
        p = re.compile('^' + output[0] + '.*?' + output[1], re.I)
        
        # Check if the mac's interface name matches an interface
        for interf in self.interfaces:
            if bool(p.match(interf.interface_name)):
                log('Partial interface {} matched interface {}'.format(
                    partial, interf.interface_name),
                    v=logging.D, proc=proc, ip=self.ip)
                
                return interf 
        
        # If no match was found return false
        self.alert('No interface match for {}'.format(partial), proc=proc, failed=False, ip=self.ip)
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
            'ip_list': None,
            }
        
        # Get each IP address
        output['ip_list'] = parse_ip(cdp_input)
        
        output['netmiko_platform'] = self.parse_netmiko_platform(cdp_input)
        
        # Parse the system platform
        system_platform = re.search(r'Platform: ?(.+?),', cdp_input, flags=re.I)
        if system_platform: output['system_platform'] = system_platform.group(1)
        
        # Parse the source interface
        source_interface = re.search(r'^interface:[ ]?(.*?)[,\n]', cdp_input, flags=(re.I | re.M))
        if source_interface: output['source_interface'] = source_interface.group(1)
    
        # Parse the neighbor interface
        neighbor_interface = re.search(r'^interface:.*?:[ ](.*?)[,\n ]', cdp_input, flags=(re.I | re.M))
        if neighbor_interface: output['neighbor_interface'] = neighbor_interface.group(1)
        
        # Get the device name
        device_name = re.findall(r'(?:System Name|Device ID): ?(.*?)(?:\(|\n)', cdp_input, flags=re.I)
        if len(device_name) > 1: output['device_name'] = device_name[1]  # Returns the more readable Device name if present
        elif output: output['device_name'] = device_name[0]  # Returns the device ID otherwise
        if "." in output['device_name']: output['device_name'] = output['device_name'].split(".")[0]
        
        return output

