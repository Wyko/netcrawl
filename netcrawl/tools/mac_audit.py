import csv, os

from .. import io_sql, util, config


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
    
    device_db = io_sql.device_db()
    
    # Open the input CSV
    entries= _open_csv(csv_path)
    
    csv_by_subnet(entries)
    
    macs = device_db.macs_at_subnet(e['network_ip'])

    
def sort_csv_by_subnet(csv_rows):
    '''Takes a list of dicts with 'network_ip' and 'mac' 
    as keys, then produces a dict of lists containing 
    subnets and the mac addresses associated with them'''
    #===========================================================================
    # example= {
    #     '10.1.120.0/255.255.255.0': [
    #         '52:18:67:1f:34:80'
    #         '71:ed:11:af:bc:02'
    #         '3c:ca:53:9c:c9:71'
    #         ],
    #     '10.2.0.0/255.255.0.0': [
    #         'df:90:31:22:0e:87'
    #         '9f:7f:4a:d2:61:fd'
    #         '64:62:0e:dc:26:d4'
    #         ]
    #     }
    #===========================================================================
    
    subnets={}
    for row in csv_rows:
        if row['network_ip'] not in subnets:
            subnets[row['network_ip']] = []
        
        subnets[row['network_ip']].append(row['mac'])
                
    return subnets


def evaluate_mac(mac1, mac2):
    
    if any([mac1 is None,
           mac2 is None]):
        return 0
    
    if len(mac1) != len(mac2):
        return 0
    
    count=0
    for i in range(len(mac1)):
        if mac1[i] == mac2[i]: count+=1
        
    print(mac1)
    print('^' * count)
        
    return (len(mac1) / count) * 100
        
        
     
        
        
        
        
        
        
    
    