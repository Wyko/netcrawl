'''
Created on Feb 19, 2017

@author: Wyko
'''

from util import log
from datetime import datetime
from gvars import DEVICE_PATH, TIME_FORMAT_FILE
from time import sleep
import re, hashlib, util, os
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
            return output.group(1)
        else: log('Regex parsing failed, trying prompt parsing.', proc='parse_hostname', v= util.N)
        
        if not self.ssh_connection: 
            log('No self.ssh_connection object passed, function failed', proc= 'parse_hostname', v= util.C)
            return None
        
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
                return output.split('#')[0]
            else: sleep(2 + 1)
        
        # Last case scenario, return nothing
        log('Failed. No hostname found.', proc= 'parse_hostname', v= util.C)
        return None


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