from netmiko import ConnectHandler
from netmiko import NetMikoAuthenticationException
from netmiko import NetMikoTimeoutException
from util import log, port_is_open

from time import sleep

import util

def getCreds():
    """Get stored credentials using a the credentials module. 
    Requests credentials via prompt otherwise.
    
    Returns:
        List of Dicts: {username, password, type} If the username and password 
            had to be requested, the list will only have one entry.
    """
    
    try: from credentials import credList
    except ImportError: pass
    else: 
        if len(credList) > 0: return credList
    
    # If no credentials could be acquired the other way, get them this way.
    import getpass
    username = input("Username: ")
    password = getpass.getpass("Password: ")
    return [{'user': username, 'password': password, 'type': 'User Entered'}]  
        



        
def start_cli_session(ip, platform, global_delay_factor = 1):
    """
    Starts a CLI session with a remote device. Will attempt to use
    SSH first, and if it fails it will try a terminal session.
    
    Args:
        ip (string): IP address of the device
        username (string): Username used for the authentication
        password (string): Password used for the authentication
        enable_secret (string): The enable password
        platform (string): One of the following netmiko platforms:
            cisco_ios
            cisco_asa
            cisco_nxos
    
    Optional Args: 
        global_delay_factor (float): A number by which timeouts are multiplied
    
    Returns: 
        Dict: 
            'ssh_connection': Netmiko ConnectHandler object opened to the enable prompt 
            'TCP_22': True if port 22 is open
            'TCP_23': True if port 23 is open
            'cred': The first successful credential dict 
    """
    
    log('Connecting to %s device %s' % (platform, ip), ip, proc='start_cli_session', v= util.N)
    
    # Get the username and password
    credList = getCreds()
    
    sleep(1)
    t22 = port_is_open(22, ip)
    sleep(1)
    t23 = port_is_open(23, ip)
    
    result_set= {
        'ssh_connection': None,
        'TCP_22': t22,
        'TCP_23': t23,
        'cred': None,
        }
    
    # Check to see if SSH (port 22) is open
    if not result_set['TCP_22']:
        log('Port 22 is closed on %s' % ip, ip, proc='start_cli_session', v= util.A)
    else: 
        # Try logging in with each credential we have
        for _cred in credList:
            cred= dict(_cred)
            try:
                # Establish a connection to the device
                ssh_connection = ConnectHandler(
                    device_type=platform,
                    ip=ip,
                    username= cred['user'],
                    password= cred['password'],
                    secret= cred['password'],
                    global_delay_factor=global_delay_factor
                )
                log('Successful ssh auth to %s using %s, %s' % (ip, cred['user'], cred['password'][:2]), proc='start_cli_session', v= util.N)
                
                # Trim the password in the output for some semblance of security
                cred['password']= cred['password'][:2]
                result_set.update({
                    'cred': cred,
                    'ssh_connection': ssh_connection
                    })

                return result_set
    
            except NetMikoAuthenticationException:
                log ('SSH auth error to %s using %s, %s' % (ip, cred['user'], cred['password'][:2]), proc='start_cli_session', v= util.A)
                continue
            except NetMikoTimeoutException:
                log('SSH to %s timed out.' % ip, proc='start_cli_session', v= util.A)
                # If the device is unavailable, don't try any other credentials
                break
    
    # Check to see if port 23 (telnet) is open
    if not result_set['TCP_23']:
        log('Port 23 is closed on %s' % ip, ip, proc='start_cli_session', v= util.A)
    else:
        for cred in credList:
            try:
                # Establish a connection to the device using telnet
                ssh_connection = ConnectHandler(
                    device_type=platform + '_telnet',
                    ip=ip,
                    username=cred['user'],
                    password=cred['password'],
                    secret=cred['password']
                )
                log('Successful telnet auth to %s using %s, %s' % (ip, cred['user'], cred['password'][:2]), proc='start_cli_session', v= util.N)
                
                
                # Trim the password in the output for some semblance of security
                cred['password']= cred['password'][:2]
                result_set.update({
                    'cred': cred,
                    'ssh_connection': ssh_connection
                    })

                return result_set
            
            except NetMikoAuthenticationException:
                log('Telnet auth error to %s using %s, %s' % 
                    (ip, cred['user'], cred['password'][:2]), v= util.A, proc= 'start_cli_session')
                continue
            except:
                log('Telnet to %s timed out.' % ip, proc='start_cli_session', v= util.A)
                # If the device is unavailable, don't try any other credentials
                break
    
    return result_set
