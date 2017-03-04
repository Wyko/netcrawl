from datetime import datetime
from contextlib import closing
from multiprocessing import Lock

import socket, os, re, time



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


def netmask_to_cidr(netmask):
    return sum([bin(int(x)).count("1") for x in netmask.split(".")])
    
    
def cidr_to_netmask(cidr):
    '''Changes CIDR notation to subnet masks. 
    I honestly have no idea how this works. I
    just added some error checking.'''
    
    # Strip any non digit characters
    if type(cidr) == str: 
        cidr= int(re.sub(r'\D', '', str(cidr)))
    else: cidr= int(cidr)
    
    if not (0 <= cidr <= 32):
        raise ValueError('Input CIDR not recognized as a valid netmask')
     
    return '.'.join([str((0xffffffff << (32 - cidr) >> i) & 0xff)
                    for i in [24, 16, 8, 0]])


def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        print('Function', method.__name__, 'time:', round((te -ts)*1000,1), 'ms')
        print()
        return result
    return timed

        
class benchmark(object):
    def __init__(self,name):
        self.name = name
    def __enter__(self):
        self.start = time.time()
    def __exit__(self,ty,val,tb):
        end = time.time()
        print("%s : %0.5f seconds" % (self.name, end-self.start))
        return False    


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