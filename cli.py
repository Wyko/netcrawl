from netmiko import ConnectHandler
from netmiko import NetMikoAuthenticationException
from netmiko import NetMikoTimeoutException
from contextlib import closing
import socket
from io_file import log

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
        

def port_is_open(port, address, timeout=4):
    """Checks a socket to see if the port is open.
    
    Args:
        port (int): The numbered TCP port to check
        address (string): The IP address of the host to check.
        
    Optional Args:
        timeout (int): The number of seconds to wait before timing out. 
            Defaults to 5 seconds. Zero seconds disables timeout.
    
    Returns: 
        bool: True if the port is open, False if closed.
    """
    
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as conn:
            conn.settimeout(timeout)
            if conn.connect_ex((address, port)) == 0:
                    return True
            else:
                    return False 

        
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
    
    log('# start_cli_session: Connecting to %s device %s' % (platform, ip), ip)
    
    # Get the username and password
    credList = getCreds()
    
    # Check to see if SSH (port 22) is open
    if port_is_open(22, ip):
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
                log('# start_cli_session: Successful ssh auth to %s using %s, %s' % (ip, username, password[:2]))
                return ssh_connection
    
            except NetMikoAuthenticationException:
                log ('# start_cli_session: SSH auth error to %s using %s, %s' % (ip, username, password[:2]))
                continue
            except NetMikoTimeoutException:
                log('# start_cli_session: SSH to %s timed out.' % ip)
                # If the device is unavailable, don't try any other credentials
                break
    else: log('# start_cli_session: Port 22 is closed on %s' % ip, ip)
    
    # Check to see if port 23 (telnet) is open
    if port_is_open(23, ip):
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
                log('# start_cli_session: Successful telnet auth to %s using %s, %s' % (ip, username, password[:2]))
                return ssh_connection
            
            except NetMikoAuthenticationException:
                log('# start_cli_session: Telnet auth error to %s using %s, %s' % (ip, username, password[:2]))
                continue
            except:
                log('# start_cli_session: Telnet to %s timed out.' % ip)
                # If the device is unavailable, don't try any other credentials
                break
    
    raise OSError('! start_cli_session: No connection could be established to %s.' % ip)
