'''
Created on Feb 18, 2017

@author: Wyko
'''

import re

from . import Interface, CiscoDevice
from ..wylog import log, logging


class NxosDevice(CiscoDevice):
    
    
    def get_serials(self):
        '''Returns serials based on XML output'''
        proc = 'NxosDevice.get_serials'
        
        log('Starting to get serials', proc=proc, v=logging.I)
        
        output = self._attempt('show inv | xml | sec <ROW_inv>',
             proc=proc,
             fn_check=lambda x: bool(re.search(r'ROW_inv', x, re.I)))
        
        # Split the output into a list of dicts
        self.serial_numbers = [{x: y for (x, y) in re.findall(r'<(.+?)>(.*?)<\/\1>', entry, re.I)} 
                    for entry in re.split(r'<RoW_inv>', output, flags=(re.I | re.M)) if entry.strip()]
        
        log('Serials found: {}.'.format(len(self.serial_numbers)), proc=proc, v=logging.N)

    
    def _get_interfaces(self):
        '''Tries the two ways to parse NXOS'''
        proc = 'NxosDevice._get_interfaces'
        
        try: self.get_interfaces_xml()
        except: 
            log('XML parsing failed. Attempting config parsing.',
                proc=proc, v=logging.I)
            self.get_interfaces_config()
        
        
    def get_interfaces_xml(self):
        proc = 'NxosDevice.get_interfaces_xml'
        
        log('Getting XML interface data', proc=proc, v=logging.I)
        
        # Poll the device for interfaces
        output = self._attempt('show interface | xml | sec ROW_interface',
                 proc=proc, fn_check=lambda x: '<ROW_interface>' in x)
        
        # Split the results into individual interfaces
        output = [x for x in output.strip().split('<ROW_interface>') if not x.strip() == '']
        
        # Parse each interface into variables
        re_comp = re.compile(r'<(.+?)>(.*?)<\/\1>')
        interfaces = []
        for interf in output:
            
            # Parse the interface data
            entries = dict(re_comp.findall(interf))
            i = Interface()
            
            i.raw_interface = interf
            
            # Set the interface variables based on the results
            i.interface_name = entries.pop('interface', None)
            if not i.interface_name: continue
            
            x = self.split_interface_name(i.interface_name)
            if x: 
                i.interface_type = x[0]
                i.interface_number = x[1]
            
            i.interface_ip = next((v for k, v in entries.items() 
                                if k == 'svi_ip_addr' or k == 'eth_ip_addr'), None) 
            
            i.interface_description = next((v for k, v in entries.items() 
                                if k == 'svi_desc' or k == 'desc'), None)
            
            i.interface_subnet = entries.pop('svi_ip_mask', None)
            
            i.parent_interface_name = entries.pop('eth_bundle', None)
            
            interfaces.append(i)
        
        
        if len(interfaces) > 0:
            log('Interfaces found: {}.'.format(
                len(interfaces)), proc=proc, v=logging.N)  
            
        else:
            log('No interfaces found', proc=proc, v=logging.C)
            raise ValueError(proc + ': No interfaces found.')     
            
        self.merge_interfaces(interfaces)
        
        
    
    
    def get_interfaces_config(self):
        proc = 'NxosDevice.get_interfaces_config'
        
        log('Getting config interface data', proc=proc, v=logging.I)
        
        # If no device config was passed, return it now
        if self.config == '': return
        
        # Split out the interfaces from the raw config
        raw_interfaces = re.findall(r'(^interface[\s\S]+?)\n\s*\n', self.config, re.M)
        
        interfaces = []
        
        # For each interface parsed from the raw config, parse it into structured data
        for interf in raw_interfaces:
            i = Interface()
            i.raw_interface = interf
            
            try: output = re.search(r'''
                ^\s*?            # Beginning of a line, with whitespace
                interf.*?        # The word interface, followed by some characters
                \b               # A word boundry
                (                # The full interface name capture group
                ([A-Za-z\-]{2,}) # An interface name, consisting of at least 2 letters
                ([\d\/\.]+)        # The interface number, with potential backslashes and .'s
                )$
            ''', interf, re.I | re.X | re.M) 
            except: continue
            else:
                if output and output.re.groups == 3: 
                    i.interface_name = output.group(1)
                    i.interface_type = output.group(2)
                    i.interface_number = output.group(3)
                else: continue
            
            # Description
            try: i.interface_description = re.search(r'description[ ]+(.+)$', interf, re.I | re.M).group(1)
            except: pass
            
            # IP and Subnet (Matches both octets and CIDR)
            ip_info = re.search(r'ip address.*?(\d{1,3}(?:\.\d{1,3}){3})[ ]?((?:\/\d+)|(?:\d{1,3}(?:\.\d{1,3}){3}))', interf, re.I | re.M)
            if ip_info and ip_info.group(1): i.interface_ip = ip_info.group(1)
            if ip_info and ip_info.group(2): i.interface_subnet = ip_info.group(2)    
            
            # Add the new interface to the list of interfaces
            interfaces.append(i)
    
        if len(interfaces) > 0:
            log('Interfaces found: {}'.format(
                len(interfaces)), proc=proc, v=logging.N)  
            
        else:
            log('No interfaces found. Raw_interfaces was: {}'.format(
                raw_interfaces), proc=proc, v=logging.C)
            raise ValueError(proc + ': No interfaces found.')                
        
        # Merge the interfaces into the device interfaces
        self.merge_interfaces(interfaces)  
        return True
