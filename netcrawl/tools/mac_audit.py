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
    
    for e in entries:
        macs = device_db.macs_at_subnet(e['network_ip'])

    
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
        
        
     
        
        
        
        
        
        
    
    