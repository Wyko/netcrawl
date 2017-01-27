from cdp import get_cdp_neighbors
from cli import start_cli_session
from cisco import get_config

def main():
    # ip = input('IP of Host: ')
    ip = '10.1.120.1'
    
    # Open a connection to the device and return a session object
    # that we can reuse in multiple functions
    try:
        ssh_connection = start_cli_session(ip, 'cisco_ios')
    except IOError as e:
        print(e)
        return
    
    # Get the CDP neighbors of the device
    #for n in get_cdp_neighbors(ssh_connection): print(n)
    
    # Get the config
    print(get_config(ssh_connection))
    
    ssh_connection.disconnect()
    
    

if __name__ == "__main__":
    main()