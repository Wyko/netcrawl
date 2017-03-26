'''
Created on Feb 28, 2017

@author: Wyko
'''

from netmiko import NetMikoAuthenticationException
from netmiko import NetMikoTimeoutException

from netcrawl import config
from netcrawl.util import port_is_open
from netcrawl.wylog import log, logging


def connect(handler=None,
            netmiko_platform=None,
            ip=None,
            cred=None,
            port=None):
    """
    Starts a CLI session with a remote device. 
    
    Uses Netmiko to start a SSH or Telnet session with a target device. It will attempt 
    to use SSH first, and if it fails it will try Telnet. For each connection method, it
    will attempt each credential specified in the cred argument (if specified) or the 
    config.cc.credentials list otherwise.
    
    Keyword Args:
        cred (dict): If supplied, this method will only use the specified credential. 
            Uses the config.cc.credentials list otherwise. 
        port (int): If supplied, this method will connect only on this port 
        ip (str): The IP address to connect to
        netmiko_platform (str): The platform of the device, in the Netmiko format 
        handler (ConnectHandler): A Netmiko-type handler to use. Currently using
            one of Netmiko.ConnectHandler, Netmiko.ssh_autodetect.SSHDetect. 
            Uses Netmiko.ConnectHandler by default.
    
    Returns:
        dict: A dict containing:
            - **connection** (*ConnectHandler*): A Netmiko ConnectHandler object 
                with a successfully opened connection 
            - **tcp_22** (*bool*): True if port 22 is open
            - **tcp_23** (*bool*): True if port 23 is open
            - **username** (*str*): The first successful credential's username
            - **password** (*str*): The first successful credential's password
            - **cred_type** (*str*): The first successful credential's type 
            
    Raises:
        IOError: If a connection could not be established
        AssertionError: If error checking failed
    """
    proc = 'cli.connect'
    
    log('Connecting to %s device %s' % (netmiko_platform, ip), ip=ip, proc=proc, v=logging.I)
    
    assert isinstance(ip, str), proc + ': Ip [{}] is not a string.'.format(type(ip)) 
    
    result = {
            'tcp_22': port_is_open(22, ip),
            'tcp_23': port_is_open(23, ip),
            'connection': None,
            'username': None,
            'password': None,
            'cred_type': None,
            }
    
    # Error checking        
    if cred: # User supplied credentials
        assert isinstance(cred, dict), 'Cred is type [{}]. Should be dict.'.format(type(cred))
    else:
        assert len(config.cc.credentials) > 0, 'No credentials available'
    if port: assert port is 22 or port is 23, 'Invalid port number [{}]. Should be 22 or 23.'.format(str(port))


    # Switch between global creds or argument creds
    if cred: _credList = cred
    else: _credList = config.cc.credentials
    
    # Check to see if SSH (port 22) is open
    if not result['tcp_22']:
        log('Port 22 is closed on %s' % ip, ip=ip, proc=proc, v=logging.I)
    elif port is None or port is 22: 
        # Try wylog in with each credential we have
        for cred in _credList:
            try:
                # Establish a connection to the device
                result['connection'] = handler(
                    device_type=netmiko_platform,
                    ip=ip,
                    username=cred['username'],
                    password=cred['password'],
                    secret=cred['password'],
                )
                
                result['username'] = cred['username']
                result['password'] = cred['password']
                result['cred_type'] = cred['cred_type']
                
                log('Successful ssh auth to %s using %s, %s' % (ip, cred['username'], cred['password'][:2]), ip=ip, proc=proc, v=logging.N)
                
                return result
    
            except NetMikoAuthenticationException:
                log ('SSH auth error to %s using %s, %s' % (ip, cred['username'], cred['password'][:2]), ip=ip, proc=proc, v=logging.A)
                continue
            except NetMikoTimeoutException:
                log('SSH to %s timed out.' % ip, ip=ip, proc=proc, v=logging.A)
                # If the device is unavailable, don't try any other credentials
                break
            except Exception as e:
                log('SSH to [{}] failed due to [{}] error: [{}]'.format(ip, type(e).__name__, str(e)))
                break
    
    # Check to see if port 23 (telnet) is open
    if not result['tcp_23']:
        log('Port 23 is closed on %s' % ip, ip=ip, proc=proc, v=logging.I)
    elif port is None or port is 23:
        for cred in _credList:
            try:
                # Establish a connection to the device
                result['connection'] = handler(
                    device_type=netmiko_platform + '_telnet',
                    ip=ip,
                    username=cred['username'],
                    password=cred['password'],
                    secret=cred['password'],
                )
                
                result['username'] = cred['username']
                result['password'] = cred['password']
                result['cred_type'] = cred['cred_type']
                log('Successful ssh auth to %s using %s, %s' % (ip, cred['username'], cred['password'][:2]), ip=ip, proc=proc, v=logging.N)
                
                return result
            
            except NetMikoAuthenticationException:
                log('Telnet auth error to %s using %s, %s' % 
                    (ip, cred['username'], cred['password'][:2]), ip=ip, v=logging.A, proc=proc)
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
