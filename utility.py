from datetime import datetime
from contextlib import closing

import socket
import os
import re


def parse_ip(raw_input):
    """Returns the first IP address matched in the input string. None if 
    nothing matched.
    """
    return re.findall(r"(1[0-9]{1,3}(?:\.\d{1,3}){3})", raw_input)
    

def log(msg, 
        ip='', 
        print_out=True, 
        proc='', 
        log_path = os.path.dirname(__file__) + '/runtime/'
        ):
    """Writes a message to the log.
    
    Args:
        msg (string): The message to write.
        
    Optional Args:
        ip (string): The IP address.
        print_out (Boolean): If True, copies the message to console
        proc (string): The process which caused the log entry
        log_path (string): Where to save the file
        
    Returns:
        Boolean: True if write was successful, False otherwise.
    """ 
    
    time_format = '%Y-%m-%d %H:%M:%S'

    output = '{}, {:<25}, {:45}, {}'.format(
                datetime.now().strftime(time_format),
                proc,
                msg.replace(',', ';'),
                ip
                )
                
    if print_out: print('{:<25.25}: {}'.format(proc, msg))
    
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    
    # Open the error log
    f = open(log_path + 'log.db','a')
    
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