'''
Created on Mar 17, 2017

@author: Wyko
'''

from netcrawl.io_sql import device_db
from prettytable import PrettyTable
import os


def run_find_unknown_switches():
    db = device_db()
    results = db.execute_sql_gen('''
        -- Get all interfaces which have more than one MAC address attached to it but no CDP Neighbors
        SELECT 
            devices.device_name, 
            interfaces.interface_id,
            interface_name, 
            count(mac_address) as macs
        FROM 
            interfaces 
        JOIN mac on interfaces.interface_id = mac.interface_id
        JOIN devices on devices.device_id=mac.device_id
        LEFT JOIN neighbors on neighbors.interface_id=mac.interface_id
        
        WHERE 
            interface_name not like '%ort%' AND
            interface_name not like '%lan%'
        GROUP BY 
            devices.device_name, 
            interface_name,
            interfaces.interface_id
        HAVING 
            -- Select only interfaces with more than 3 MACs and no CDP neighbors
            count(mac_address) > 3 AND 
            count(neighbors) = 0 AND
            
            -- Remove some common false positives
            devices.device_name not like '%ven%' AND
            interfaces.interface_name not like '%sup%'
        ORDER BY devices.device_name, macs DESC;
        ''')
    
    t= _generate_table(results)
    print(t)
    _write_table(t)
    
    
def _write_table(t):
    path = os.path.join(config.run_path(),
                        'unknown_switches.txt')
    with open(path, 'w') as outfile:
        outfile.write(str(t))
        
    print ('Finished writing table to [{}]'.format(path))
            
    
def _generate_table(results):
    t = PrettyTable(['Device Name', 'Interface ID', 'Interface', 'MAC Count'])
    t.align = 'l'
    for r in results: t.add_row(r)
    return t


if __name__ == '__main__':
    from netcrawl import config
    config.parse_config()
    
    run_find_unknown_switches()
    
    
    
    
    
    