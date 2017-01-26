import cdp
import fileio
import sys

def main():
    # ip = input('IP of Host: ')
    ip = '10.1.120.1
    '
    output = cdp.get_neighbor_details(ip, 'cisco_ios')
    
    if not output: sys.exit()
    
    for entry in output: print(entry)
    
    for entry in output:
        cdp_neighbor = cdp.parse_neighbor(entry)    
        if not cdp.is_empty(cdp_neighbor):
            print(cdp_neighbor)
    
    pass

if __name__ == "__main__":
    main()