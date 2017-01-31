from cisco import get_device
from io_file import log
from io_file import load_index
from io_file import in_index


if __name__ == "__main__":
    log('# ----- Starting new run -----')
    
    index = load_index()
    
    # for i in index: print (i)
    
    
    # ip = input('IP of Host: ')
    ip = '10.0.255.40'
    
    # Get the config
    device = get_device(ip, 'cisco_nxos')
    
    
    print (device)
    print(device.interfaces_to_string())
    
    #print ('IP Addresses: ' + str(device.get_ips()))
    
    #print(in_index(index, device))
    
    
    
    log('# ----- Finishing run -----')