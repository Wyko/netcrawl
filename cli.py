'''
Created on Feb 28, 2017

@author: Wyko
'''

from netmiko import NetMikoAuthenticationException
from netmiko import NetMikoTimeoutException
from util import port_is_open, getCreds
from wylog import log, logging

import gvars

def start_cli_session(handler=None,
                      netmiko_platform=None,
                      ip=None,
                      cred=None,
                      port=None):
    """
    Starts a CLI session with a remote device. Will attempt to use
    SSH first, and if it fails it will try a terminal session.
    
    Optional Args:
        cred (Dict): If supplied. this method will only use the specified credential
        port (Integer): If supplied, this method will connect only on this port 
        ip (String): The IP address to connect to
        netmiko_platform (Object): The platform of the device 
        handler (Object): A Netmiko-type ConnectionHandler to use. Currently using
            one of Netmiko.ConnectHandler, Netmiko.ssh_autodetect.SSHDetect. 
            Uses Netmiko.ConnectHandler by default.
    
    Returns: 
        Dict: 
            'connection': Netmiko ConnectHandler object opened to the enable prompt 
            'TCP_22': True if port 22 is open
            'TCP_23': True if port 23 is open
            'cred': The first successful credential dict 
            
    Raises:
        IOError: If connection could not be established
        AssertionError: If error checking failed
    """
    proc = 'cli.start_cli_session'
    
    log('Connecting to %s device %s' % (netmiko_platform, ip), ip=ip, proc=proc, v=logging.I)
    
    assert isinstance(ip, str), proc + ': Ip [{}] is not a string.'.format(type(ip)) 
    
    result = {
            'TCP_22': port_is_open(22, ip),
            'TCP_23': port_is_open(23, ip),
            'connection': None,
            'cred': None,
            }
    
    # Get credentials if none were acquired yet
    if len(gvars.CRED_LIST) == 0: gvars.CRED_LIST = getCreds()
    
    # Error checking        
    assert len(gvars.CRED_LIST) > 0, 'No credentials available'
    if port: assert port is 22 or port is 23, 'Invalid port number [{}]. Should be 22 or 23.'.format(str(port))
    if cred: assert isinstance(cred, dict), 'Cred is type [{}]. Should be dict.'.format(type(cred))

    # Switch between global creds or argument creds
    if cred: _credList = cred
    else: _credList = gvars.CRED_LIST
    
    # Check to see if SSH (port 22) is open
    if not result['TCP_22']:
        log('Port 22 is closed on %s' % ip, ip=ip, proc=proc, v=logging.I)
    elif port is None or port is 22: 
        # Try wylog in with each credential we have
        for cred in _credList:
            try:
                # Establish a connection to the device
                result['connection'] = handler(
                    device_type=netmiko_platform,
                    ip=ip,
                    username=cred['user'],
                    password=cred['password'],
                    secret=cred['password'],
                )
                
                result['cred'] = cred
                log('Successful ssh auth to %s using %s, %s' % (ip, cred['user'], cred['password'][:2]), ip=ip, proc=proc, v=logging.N)
                
                return result
    
            except NetMikoAuthenticationException:
                log ('SSH auth error to %s using %s, %s' % (ip, cred['user'], cred['password'][:2]), ip=ip, proc=proc, v=logging.A)
                continue
            except NetMikoTimeoutException:
                log('SSH to %s timed out.' % ip, ip=ip, proc=proc, v=logging.A)
                # If the device is unavailable, don't try any other credentials
                break
            except Exception as e:
                log('SSH to [{}] failed due to [{}] error: [{}]'.format(ip, type(e).__name__, str(e)))
                break
    
    # Check to see if port 23 (telnet) is open
    if not result['TCP_23']:
        log('Port 23 is closed on %s' % ip, ip=ip, proc=proc, v=logging.I)
    elif port is None or port is 23:
        for cred in _credList:
            try:
                # Establish a connection to the device
                result['connection'] = handler(
                    device_type=netmiko_platform + '_telnet',
                    ip=ip,
                    username=cred['user'],
                    password=cred['password'],
                    secret=cred['password'],
                )
                
                result['cred'] = cred
                log('Successful ssh auth to %s using %s, %s' % (ip, cred['user'], cred['password'][:2]), ip=ip, proc=proc, v=logging.N)
                
                return result
            
            except NetMikoAuthenticationException:
                log('Telnet auth error to %s using %s, %s' % 
                    (ip, cred['user'], cred['password'][:2]), ip=ip, v=logging.A, proc=proc)
                continue
            except NetMikoTimeoutException:
                log('Telnet to %s timed out.' % ip, ip=ip, proc=proc, v=logging.A)
                # If the device is unavailable, don't try any other credentials
                break
            except Exception as e:
                log('Telnet to [{}] failed due to [{}] error: [{}]'.format(ip, type(e).__name__, str(e)),
                    ip=ip, proc=proc, v=logging.A)
                break
    
    raise IOError(proc + ': CLI connection to [{}] failed'.format(ip))
