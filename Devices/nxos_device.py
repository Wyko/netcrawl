'''
Created on Feb 18, 2017

@author: Wyko
'''

from util import log
from datetime import datetime
from gvars import DEVICE_PATH, TIME_FORMAT_FILE
from time import sleep
import re, hashlib, util, os
import gvars
from Devices.base_device import interface
from Devices.cisco_device import cisco_device

class nxos_device(cisco_device):
    '''
    classdocs
    '''

    
    def get_mac_address_table(self):
        pass
        
    
    def parse_mac_address_table(self, raw_address_table):
        output= re.finditer(              # #### NX-OS MAC Regex ####
            '''            
            (?<MAC>              # Name of MAC capture group
            (?:[0-9A-F]{2,4}[\:\-\.]){2,7}[0-9A-F]{2,4}
            )                    # End of MAC Address
            .*?                  # Skip all characters up to the interface
            (?<Interface>        # Name of the interface capture group
            [A-Z0-9\/]+    
            )                    # End of the Interface
            $                    # Match if interface is at the end of the line
            ''', (re.X | re.I | re.M) )
        
        self.mac_address_table = output
        
        
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