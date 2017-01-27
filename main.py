import cdp
import sys
from cli import start_cli_session

def main():
    # ip = input('IP of Host: ')
    ip = '10.0.255.44'
    
    # Open a connection to the device and return a session object
    # that we can reuse in multiple functions
    try:
        ssh_connection = start_cli_session(ip, 'cisco_ios')
    except IOError as e:
        print(e)
        return
    
    print ('# Connection established to %s' % ssh_connection.ip)
    
    
    

if __name__ == "__main__":
    main()