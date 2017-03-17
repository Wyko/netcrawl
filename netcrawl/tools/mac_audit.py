import csv, os

from netcrawl import io_sql, util, config
import textwrap
from netcrawl.io_sql import device_db
from netcrawl.tools.manuf.manuf import MacParser


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
    '''
    Given a CSV of subnets and MAC addresses, search the database
    for all MACs on subnets which match those in the CSV. Compare 
    each MAC and output a new csv with any matching MAC's listed 
    by confidence (number of matching characters, starting from the 
    OUI.
    This can be used, for example, for a Wireless Rogue SSID audit,
    for which the MAC address of the radios is known and you want to
    find out which rogue AP's are physically connected to your network.
    '''
    
    if config.cc['modified'] is False:
        config.parse_config()
    
    # Open the input CSV
    entries= _open_csv(csv_path)
    csv_subnets= sort_csv_by_subnet(entries)
    
    print ('CSV Len: ', len(csv_subnets))
    
    device_db = io_sql.device_db()

    results=[]
    mp = MacParser(update=True)
    
    # Iterate over each subnet where a rogue was detected
    for subnet in sorted(csv_subnets):
        
        print('Subnet: ', subnet)
        
        # Iterate over each mac in the subnet
        for mac in device_db.macs_on_subnet(subnet):
            
            # Iterate over each mac in the CSV subnet and 
            # find matches
            for csv_row in csv_subnets[subnet]:
                x= evaluate_mac(mac, csv_row['mac'])
                if x > 50:
                    csv_row= dict(csv_row)
                    csv_row['confidence'] = x
                    csv_row['wired_mac'] = mac
                    csv_row['Manufacturer'] = mp.search(mac)

                    results.append(csv_row)
                        
            
    results= sorted(results, key=lambda x: x['confidence'], reverse=True)
    if len(results) == 0: return False
    
    write_csv(results)
    write_report(results)


def write_report(rows):
    from datetime import datetime
    
    ddb= device_db()
    
    with open(os.path.join(config.run_path(), 'mac_audit_report.txt'), 'w') as outfile:
        outfile.write(textwrap.dedent('''\
            Title:  Rogue Device Report
            Time:   {}
            
            Note: In the neighbor table for each match, the interface with no 
                    neighbor or a neighbor which is an obvious non-network 
                    device (such as a phone) is the most likely interface to be 
                    directly connected to the matched MAC.
            
            '''.format(datetime.now().strftime(config.pretty_time()))))
        
        for x in rows:
            # Get the neighbors
            located= ddb.locate_mac(x['wired_mac'])
            result= '-'*50 + '\n\n'
            
            result+= '{:12}: {}\n'.format('Matched Mac', x.pop('mac'))
            result+= '{:12}: {}\n'.format('Wired Mac', x.pop('wired_mac'))
            result+= '{:12}: {}\n'.format('Confidence', x.pop('confidence'))
            result+= '{:12}: {}\n'.format('Manufacturer', x.pop('Manufacturer'))

            result+= '\n'.join(['{:12}: {}'.format(k, v) for k, v in sorted(x.items())])
            result+= '\n\n{:^97}'.format('-- Where this MAC was seen --')
            result+= '\n{:^30} | {:^30} | {:^30} |\n'.format('Device', 'Interface', 'Neighbor')
            
            for loc in located:
                result+= '{:30} | {:30} | {:30} |\n'.format(str(loc[0]),
                                                            str(loc[1]),
                                                            str(loc[2]))
            result+= '\n'
                
            outfile.write(result)
    
                        
def write_csv(rows):
    with open(os.path.join(config.run_path(), 'mac_audit.csv'), 'w', newline='') as outfile:
        
        keys= [k for k, v in rows[0].items()]
                  
        writer = csv.DictWriter(outfile, fieldnames=keys)
        writer.writeheader()
        for x in rows:
            writer.writerow(x)
    
    
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
    import argparse
    from netcrawl import config
    config.parse_config()
    
    parser = argparse.ArgumentParser(description='Perform an audit of MACs on the network')
    parser.add_argument('csv', help='A csv file to audit.')
    args = parser.parse_args()
    
    run_audit(args.csv)
        
        
        
        
        
    
    