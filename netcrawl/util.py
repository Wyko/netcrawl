from contextlib import closing
from netaddr import IPNetwork
import socket, re, time
from functools import wraps


def getCreds():
    """
    Get stored credentials using a the credentials module. Requests credentials 
    via prompt otherwise.
    
    Returns:
        List of Dicts: **[{username, password, cred_type}, ]** 
        
        If the username and password had to be requested, the 
        list will only have one entry.
    """
    
    try: from credentials import credList
    except ImportError: pass
    else: 
        if len(credList) > 0: return credList
    
    # If no credentials could be acquired the other way, get them this way.
    import getpass
    username = input("Username: ")
    password = getpass.getpass("Password: ")
    return [{'username': username, 'password': password, 'cred_type': 'User Entered'}]  


def ucase_letters(raw_input):
    '''Returns the input string stripped of everything but letters, numbers, and
    underscores.''' 
    
    return ''.join([x.upper() for x in raw_input if re.match(r'\w', x)])


def contains_mac_address(mac):
    '''Simple boolean operator to determine if a string contains a mac anywhere
    within it.'''
    return bool(re.search(r'''
        (?:
            [0-9A-F]{2,4}  # Match 2-4 Hex characters
            [\:\-\.]       # Seperated by :, -, or .
        ){2,7}             # match it between 2 and 7 times
            [0-9A-F]{2,4}  # Followed by one last set of Hex
        ''',
        mac, re.I | re.X))


class cleanExit:
    '''Context manager who's only purpose is to cleanly exit when the code
    execution is interrupted by the user'''
    
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, exc_tb):
        if exc_type is KeyboardInterrupt:
            print('Exiting due to keyboard interrupt.')
            return True
        return exc_type is None
    

def network_ip(ip, subnet):
    '''Returns the network IP address calculated from the given `ip` and
    `subnet`.
    '''  
    
    
    if not is_ip(ip): 
        raise TypeError('IP [{}] is not a valid ip'.format(ip))
    
    # Handle CIDR
    if not is_ip(subnet):
        try: subnet= cidr_to_netmask(subnet)
        except ValueError:
            raise TypeError(
                'Subnet [{}] is not a valid ip or CIDR'.format(subnet))
    
    return str(IPNetwork( '{}/{}'.format(
            ip, subnet)).network)


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
    '''Returns true if the given string is an IPv4 address'''
    if not isinstance(raw_input, str):
        raise TypeError('[{}] is not a string'.format(
            raw_input))
    
    match= re.match(r'''
        (?:
            (?:
                25[0-5]|          # Match 250-255
                2[0-4][0-9]|      # Match 200-249
                [01]?[0-9][0-9]?  # Match 0-199
            )
            (?:\.|\b)             # Followed by a . or a word boundry
        ){4}                      # Repeat that four times
        ''', raw_input, re.X)
    
    return bool(match)

def netmask_to_cidr(netmask):
    '''
    Translates a netmask to a CIDR format
    
    Args:
        netmask (str): A netmask in four octet ip address format
        
    Returns:
        int: The CIDR representation of the netmask
    '''
    
    return sum([bin(int(x)).count("1") for x in netmask.split(".")])
    
    
def cidr_to_netmask(cidr):
    '''Changes CIDR notation to subnet masks. 
    I honestly have no idea how this works. I
    just added some error checking.'''
    
    # Strip any non digit characters
    if isinstance(cidr, str): 
        cidr = int(re.sub(r'\D', '', str(cidr)))
    
    try: cidr = int(cidr)
    except Exception as e: 
        raise ValueError('Input CIDR [{}] not a valid netmask. '
                         'Error [{}]'.format(cidr, str(e)))
    
    if not (0 <= cidr <= 32):
        raise ValueError('Input CIDR [{}] not a valid '
                         'netmask.'.format(cidr))
     
    return '.'.join([str((0xffffffff << (32 - cidr) >> i) & 0xff)
                    for i in [24, 16, 8, 0]])


def clean_ip(ip):
    '''Removes all non-digit or period characters from
    the source string'''
    
    return ''.join([x for x in ip if re.match(r'[\d\.]', x)])
        

def timeit(method):
    '''Decorator method which times the wrapped method and prints the result to 
    the console'''
    
    @wraps(method)
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        print('Function', method.__name__, 'time:', round((te - ts) * 1000, 1), 'ms')
        print()
        
        return result
    return timed


class benchmark(object):
    '''Context manager which times the surrounded code and prints the results 
    to the console'''
    
    def __init__(self, name):
        self.name = name
    def __enter__(self):
        self.start = time.time()
    def __exit__(self, ty, val, tb):
        end = time.time()
        print("%s : %0.5f seconds" % (self.name, end - self.start))
        return False    


def port_is_open(port, address, timeout=5):
    """
    Checks a socket to see if the specified `port` is open.
    
    Args:
        port (int): The numbered TCP port to check
        address (str): The address of the host to check
        
    Keyword Args:
        timeout (int): The number of seconds to wait before timing out. 
            Defaults to 5 seconds. Zero seconds disables timeout
    
    Returns: 
        bool: True if the port is open
    """
    
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as conn:
            conn.settimeout(timeout)
            if conn.connect_ex((address, port)) == 0:
                    return True
            else:
                    return False 
    return False
