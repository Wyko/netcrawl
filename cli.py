from netmiko import ConnectHandler
from netmiko import NetMikoAuthenticationException
from netmiko import NetMikoTimeoutException

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
        

def port_is_open(port, address=127.0.0.1):
	"""Checks a local (by default) or remote socket to see if the port is open.
	
	Args:
		port (int): The numbered TCP port to check
		address (string): The IP address of the host to check. Localhost by default.
	
	Returns: 
		bool: True if the port is open, False if closed.
	"""
	
	with closing(socket.socket(socket.AF_INET,socket.SOCK_STREAM)) as conn:
			if conn.connect_ex((address, port)) == 0:
					return True
			else:
					return False 

		
def start_cli_session(ip, platform):
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
		
    Returns: 
		ConnectHandler: Netmiko ConnectHandler object opened to the enable prompt 
    """
    
    print('# Connecting to %s device %s' % (platform, ip))
    
	# Get the username and password
    credList = getCreds()
    
	# Check to see if SSH (port 22) is open
	if port_is_open(ip, 22):
		# Try logging in with each credential we have
		for username, password in credList:
			try:
				# Establish a connection to the device
				ssh_connection = ConnectHandler(
					device_type=platform,
					ip=ip,
					username=username,
					password=password,
					secret=password
				)
				print('# Successful ssh auth to %s' % (ip))
				return ssh_connection
	
			except NetMikoAuthenticationException:
				print ('# SSH auth error to %s using %s / %s' % (ip, username, password))
				continue
			except NetMikoTimeoutException:
				print('# SSH to %s timed out.' % ip)
				# If the device is unavailable, don't try any other credentials
				break
    
	# Check to see if port 23 (telnet) is open
	if port_is_open(ip, 23)
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
                print('# Successful telnet auth to %s' % (ip))
                return ssh_connection
            
			except NetMikoAuthenticationException:
                print ('# Telnet auth error to %s using %s / %s' % (ip, username, password))
                continue
            except:
                print('# Telnet to %s timed out.' % ip)
                # If the device is unavailable, don't try any other credentials
                break
    
    raise IOError('!!! No connection could be established to %s.' % ip)

