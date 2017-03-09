'''
Created on Feb 19, 2017

@author: Wyko
'''

from Devices.cisco_device import cisco_device
from Devices.base_device import interface
from wylog import log, logging

import re


class ios_device(cisco_device):
   
    def _get_interfaces(self):
        proc= 'ios_device.parse_ios_interfaces'
        log('Starting ios interface parsing.', proc= proc, v= logging.I)
        
        interfaces = []
        # If no device config was passed, return
        if not self.config: 
            log('Error: No data in self.config.', proc= proc, v= logging.A)
            raise ValueError(proc+ ': No data in self.config.')
        
        # Split out the interfaces from the raw config
        raw_interfaces = re.findall(r'\n(^interface[\s\S]+?)\n!', self.config, (re.M|re.I))
        
        # For each interface parsed from the raw config, create a new interface 
        # object and parse it into structured data
        for interf in raw_interfaces:
            i = interface()
            
            # Add the raw config data to the interface
            i.raw_interface = interf
            
            try: output= re.search(r'''
                ^\s*?            # Beginning of a line, with whitespace
                interf.*?        # The word interface, followed by some characters
                \b               # A word boundry
                (                # The full interface name capture group
                ([A-Za-z\-]{2,})   # An interface name, consisting of at least 2 letters
                ([\d\/\.]+)        # The interface number, with potential backslashes and .'s
                )$
            ''', interf, re.I | re.X | re.M) 
            except: continue
            else:
                if output and output.re.groups==3: 
                    i.interface_name = output.group(1)
                    i.interface_type = output.group(2)
                    i.interface_number = output.group(3)
                else: continue
            
            # Parse description
            try: i.interface_description = re.search(r'description[ ]+(.+)$', interf, re.I|re.M).group(1)
            except: pass
            
            try:
                # IP and Subnet (Matches both octets and CIDR)
                ip_info = re.search(r'ip address.*?(\d{1,3}(?:\.\d{1,3}){3})[ ]?((?:\/\d+)|(?:\d{1,3}(?:\.\d{1,3}){3}))', interf, re.IGNORECASE | re.MULTILINE)
                if ip_info and ip_info.group(1): i.interface_ip = ip_info.group(1)
                if ip_info and ip_info.group(2): i.interface_subnet = ip_info.group(2)    
            except Exception as e:
                log('Exception while parsing IP and Subnet: {}'.format(str(e)),
                    proc = proc, v= logging.C)
                pass
            
            interfaces.append(i)
    
        if len(interfaces) > 0:
            log('Interfaces found: {}'.format(
                len(interfaces)), proc= proc, v= logging.N)  
        else:
            log('Error: No interfaces found. Raw_interfaces was: {}'.format(
                raw_interfaces), proc= proc, v= logging.C)  
            raise ValueError(proc+ ': No interfaces found.')               
        
        self.merge_interfaces(interfaces)  