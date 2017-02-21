'''
Created on Feb 19, 2017

@author: Wyko
'''

from Devices.cisco_device import cisco_device
from util import log
import re, util
from Devices.base_device import interface

class ios_device(cisco_device):
   
    def get_interfaces(self):

        log('Starting ios interface parsing.', proc="parse_ios_interfaces", v= util.N)
        
        interfaces = []
        # If no device config was passed, return
        if not self.config: 
            log('No configuration passed. Returning.', proc = 'parse_ios_interfaces', v= util.A)
            return interfaces
        
        # Split out the interfaces from the raw config
        raw_interfaces = re.findall(r'\n(^interface[\s\S]+?)\n!', self.config, (re.MULTILINE|re.IGNORECASE))
        
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
            raise ValueError('parse_nxos_interfaces: No interfaces found.')               
        
        self.merge_interfaces(interfaces)  