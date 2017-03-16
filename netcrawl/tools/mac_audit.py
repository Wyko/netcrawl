import csv, os

from netcrawl import io_sql, util, config
import sys


def _open_csv(_path):
    '''File must have headers, and it must include the following:
        : 'mac' - Contains the MAC's to check
        : 'ip' - Ip address of the network
        : 'subnet' - Mask for the network
         
    The csv will be parsed for mac addresses that resemble those 
    in the report'''
    
    if not os.path.isfile(_path):
        raise IOError('File does not exist [{}]'.format(_path))
    
    with open(_path) as csvfile:
        cr= csv.DictReader(csvfile)
        
        entries= []
        # Iterate over the csv 
        for row in cr:
            assert 'ip' in row, 'CSV had no IP'
            assert 'mac' in row, 'CSV had no MAC'
            
            # Make sure it has the right headers
            if all (k in row for k in ('ip', 'mac', 'subnet')):
                
                # Sanitize the input
                row['ip'] = util.clean_ip(row['ip'])
                row['subnet'] = util.clean_ip(row['subnet'])
                row['mac'] = util.ucase_letters(row['mac'])
                
                row['network_ip']= util.network_ip(
                    row['ip'], 
                    row['subnet'])
                
                entries.append(row) 
        return entries


def run_audit(csv_path):
    '''Iterate over each row in the the csv and output a new csv with 
    any matching MAC's listed by confidence (number of matching
    characters, starting from the OUI.'''
    
    if config.cc['modified'] is False:
        config.parse_config()
    
    with open(os.path.join(config.run_path(), 'mac_audit.txt'), 'w'): pass
    
    # Open the input CSV
    entries= _open_csv(csv_path)
    csv_subnets= sort_csv_by_subnet(entries)
    print ('CSV Len: ', len(csv_subnets))
    
    device_db = io_sql.device_db()

    subnets= device_db.device_subnets()
    subnets.sort(key=lambda x: x[0])
    print ('Subnet Len: ', len(subnets))
    
    
    for net, id in subnets:
        if net in csv_subnets:
            results=[]
            # Get all the macs seen on that subnet 
            device_macs= device_db.device_macs(id)
            
            # Reduce from list of tuples
            device_macs= [x[0] for x in device_macs]
            
            # Deduplicate them
            device_macs= sorted(set(device_macs))
            
            print(len(device_macs), 'macs seen on', net)
            
            for mac in device_macs:
                for csv_mac in csv_subnets[net]:
                    x= evaluate_mac(mac, csv_mac['mac'])
                    if x > 50:
                        results.append({'confidence': x,
                                        'wired_mac': mac,
                                        'csv_mac': csv_mac,
                                        })
                        
            results= sorted(results, key=lambda x: x['confidence'])            
            with open(os.path.join(config.run_path(), 'mac_audit.txt'), 'a') as outfile:
                for x in results:
                    outfile.write(str(x) + '\n')
                    
    
def sort_csv_by_subnet(csv_rows):
    '''Takes a list of dicts with 'network_ip' and 'mac' 
    as keys, then produces a dict of lists containing 
    subnets and the mac addresses associated with them'''
    
    subnets={}
    for row in csv_rows:
        if row['network_ip'] not in subnets:
            subnets[row['network_ip']] = []
        
        subnets[row['network_ip']].append(row)
                
    return subnets


def evaluate_mac(mac1, mac2):
    
    if any([mac1 is None,
           mac2 is None]):
        return 0

    # Strip all non-letter characters
    mac1= util.ucase_letters(mac1)
    mac2= util.ucase_letters(mac2)
    
    if len(mac1) != len(mac2):
        return 0
    
    count=0
    for i in range(len(mac1)):
        if mac1[i] == mac2[i]: count+=1
        
        # Break at the first bad match
        else: break
        
    #===========================================================================
    # # Use this to return the exact number of characters matched 
    # return count
    #===========================================================================
    
    # Returns a percentage match
    if count==0: return 0    
    return int((count / len(mac1)) * 100)
        
        
     
if __name__ == '__main__':
    run_audit(r"E:\rogue_joined.csv")
        
        
        
        
        
    
    