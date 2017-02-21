from datetime import datetime
from contextlib import closing

import socket, os, re

# Stores current global verbosity level
VERBOSITY = 4

# Variables for logging
CRITICAL = 1
C = 1
ALERT = 2
A = 2
HIGH = 3
H = 3
NORMAL = 4
N = 4
DEBUG = 5
D = 5


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


def parse_ip(raw_input):
    """Returns a list of strings containing each IP address 
    matched in the input string."""
    return re.findall(r'''
        \b                        # Start at a word boundry
        (?:
            (?:
                25[0-5]|          # Match 250-255
                2[0-4][0-9]|      # Match 200-249
                [01]?[0-9][0-9]?  # Match 0-199
            )
            (?:\.|\b)             # Followed by a . or a word boundry
        ){4}                      # Repeat that four times
        \b                        # End at a word boundry
        ''', raw_input, re.X)


def is_ip(raw_input):
    output = re.search(r"(^1[0-9]{1,3}(?:\.\d{1,3}){3}$)", raw_input)
    
    if output and output.group(1):
        return True
    else:
        return False
    

def log(msg, 
        ip='', 
        print_out=True, 
        proc='', 
        log_path = os.path.dirname(__file__) + '/runtime/',
        v = 4,
        error= ''
        ):
    """Writes a message to the log.
    
    Args:
        msg (string): The message to write.
        
    Optional Args:
        ip (string): The IP address.
        proc (string): The process which caused the log entry
        log_path (string): Where to save the file
        print_out (Boolean): If True, copies the message to console
        v (Integer): Verbosity level. Logs with verbosity above the global 
            verbosity level will not be printed out.  
            v= 1: Critical alerts
            v= 2: Non-critical alerts
            v= 3: High level info
            v= 4: Common info
            v= 5: Debug level info
            
        error (Exception): 
        
    Returns:
        Boolean: True if write was successful, False otherwise.
    """ 
    
    time_format = '%Y-%m-%d %H:%M:%S'

    # Set the prefix for the log entry
    if v >=3: info_str = '#' + str(v)
    if v ==2: info_str = '? '
    if v ==1: info_str = '! '

    msg = info_str + ' ' + msg
    
    output = '{_time}, {_proc:<25}, {_msg:60}, {_ip}, {_error}'.format(
                _time= datetime.now().strftime(time_format),
                _proc= proc,
                _msg = msg.replace(',', ';'),
                _ip = ip,
                _error = str(error)
                )
    
    # Print the message to console            
    if v <= VERBOSITY and print_out: print('{:<25.25}: {}'.format(proc, msg))
    
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    
    # Open the error log
    f = open(log_path + 'log.txt','a')
    
    if f and not f.closed:
        f.write(output + '\n')
        f.close()
        return True
    
    else: return False
    

def port_is_open(port, address, timeout=5):
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
    return False