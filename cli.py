from netmiko import ConnectHandler
from netmiko import NetMikoAuthenticationException
from netmiko import NetMikoTimeoutException
from uti import log, port_is_open

import uti

def getCreds():
    """Get stored credentials using a the credentials module. 
    Requests credentials via prompt otherwise.
    
    Returns:
        List of Tuples: (username, password) If the username and password had to be requests, the list will only have one entry.
    """
    
    try: from credentials import credList
    except ImportError: pass
    else: 
        if len(credList) > 0: return credList
    
    # If no credentials could be acquired the other way, get them this way.
    import getpass
    username = input("Username: ")
    password = getpass.getpass("Password: ")
    return [(username, password)]  
        



        
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
        ConnectHandler: Netmiko ConnectHandler object opened to the enable prompt 
    """
    
    log('Connecting to %s device %s' % (platform, ip), ip, proc='start_cli_session', v= uti.N)
    
    # Get the username and password
    credList = getCreds()
    
    # Check to see if SSH (port 22) is open
    if not port_is_open(22, ip):
        log('Port 22 is closed on %s' % ip, ip, proc='start_cli_session', v= uti.A)
    else: 
        # Try logging in with each credential we have
        for username, password in credList:
            try:
                # Establish a connection to the device
                ssh_connection = ConnectHandler(
                    device_type=platform,
                    ip=ip,
                    username=username,
                    password=password,
                    secret=password,
                    global_delay_factor=global_delay_factor
                )
                log('Successful ssh auth to %s using %s, %s' % (ip, username, password[:2]), proc='start_cli_session', v= uti.N)
                return ssh_connection
    
            except NetMikoAuthenticationException:
                log ('SSH auth error to %s using %s, %s' % (ip, username, password[:2]), proc='start_cli_session', v= uti.A)
                continue
            except NetMikoTimeoutException:
                log('SSH to %s timed out.' % ip, proc='start_cli_session', v= uti.A)
                # If the device is unavailable, don't try any other credentials
                break
    
    
    # Check to see if port 23 (telnet) is open
    if not port_is_open(23, ip):
        log('Port 23 is closed on %s' % ip, ip, proc='start_cli_session', v= uti.A)
    else:
        for username, password in credList:
            try:
                # Establish a connection to the device using telnet
                ssh_connection = ConnectHandler(
                    device_type=platform + '_telnet',
                    ip=ip,
                    username=username,
                    password=password,
                    secret=password
                )
                log('Successful telnet auth to %s using %s, %s' % (ip, username, password[:2]), proc='start_cli_session', v= uti.N)
                return ssh_connection
            
            except NetMikoAuthenticationException:
                log('start_cli_session: Telnet auth error to %s using %s, %s' % (ip, username, password[:2]), v= uti.A)
                continue
            except:
                log('Telnet to %s timed out.' % ip, proc='start_cli_session', v= uti.A)
                # If the device is unavailable, don't try any other credentials
                break
    
    raise OSError('start_cli_session: No connection could be established to %s.' % ip)
