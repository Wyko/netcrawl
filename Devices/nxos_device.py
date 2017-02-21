'''
Created on Feb 18, 2017

@author: Wyko
'''

from util import log
import re, util
from Devices.base_device import interface
from Devices.cisco_device import cisco_device

class nxos_device(cisco_device):
    
    def get_mac_address_table(self, attempts= 3):
        '''Populates self.mac_address_table from the remote device.
        
        Returns:
            Boolean: True if the command was successful
            
        Raises:
            Exception: ValueError if no result was found.
        '''
        
        for i in range(attempts):
            output= self.ssh_connection.send_command_expect('show mac address-table')
            
            # Check if something that looks like a MAC was returned
            if bool(re.search(r'(?:[0-9A-F]{2,4}[\:\-\.]){2,7}[0-9A-F]{2,4}', output)):
                self.raw_mac_address_table = output
                log('Attempt {}: Got valid output.'.format(
                    str(i+1)), self.ip, proc= 'get_mac_address_table', v= util.N)
                
                # Parse the table
                self.parse_mac_address_table()                
                return True
            
            # Otherwise, continue the loop or break out
            elif i+1 >= attempts:
                log('Attempt Final {}: No valid output. Got[:20]: {}'.format(
                    str(i+1), output), self.ip, proc= 'get_mac_address_table', v= util.C)
                raise ValueError('get_mac_address_table: Attempt Final {}: ' +
                    'No valid output. Got[:20]: {}'.format(i, output))
            else:
                log('Attempt {}: No valid output. Got[:20]: {}'.format(
                    str(i+1), output), self.ip, proc= 'get_mac_address_table', v= util.D)
                continue
                
        
    
    def parse_mac_address_table(self):
        if not self.raw_mac_address_table:
            self.alert('Parse function called without having raw data.', 
                       proc= 'nxos_device.parse_mac_address_table')
            return False
        
        output= re.finditer(              # #### NX-OS MAC Regex ####
            r'''            
            (?P<mac>             # MAC capture group
            (?:[0-9A-F]{2,4}[\:\-\.]){2,7}[0-9A-F]{2,4}
            )                    
            .*?                  # Skip all characters up to the interface
            (?P<interface>      # Interface capture group
            [A-Z0-9\/]+    
            )
            $                    # Match if interface is at the end of the line
            ''', self.raw_mac_address_table, (re.X | re.I | re.M) )
        
        # Return a dictionary containing the MAC's and interfaces
        self.mac_address_table= [m.groupdict() for m in output]
        
    def get_interfaces(self):
        
        log('Starting', proc='parse_nxos_interfaces', v= util.N)
        
        # If no device config was passed, return it now
        if self.config == '': return
        
        # Split out the interfaces from the raw config
        raw_interfaces = re.findall(r'(^interface[\s\S]+?)\n\s*\n', self.config, re.MULTILINE)
        
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
            raise ValueError('parse_nxos_interfaces: No interfaces found.')                
        
        # Merge the interfaces into the device interfaces
        self.merge_interfaces(interfaces)  
        return True