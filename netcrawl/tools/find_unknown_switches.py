'''
Created on Mar 17, 2017

@author: Wyko
'''

import os
from netcrawl.wylog import logf
from netcrawl import config
from netcrawl.io_sql import device_db
from netcrawl.tools import MacParser
from prettytable import PrettyTable


def run_find_unknown_switches(filter_device_name= [],
                              filter_interface_name= [],
                              filter_manufacturer= [],
                              min_macs= 3):
    
    db = device_db()
    
    where_clause=''
    for x in filter_device_name:
        where_clause+= " AND devices.device_name not like '%{}%' ".format(x)
    
    for x in filter_interface_name:
        where_clause+= " AND interface_name not like '%{}%' ".format(x)
    
    results = db.execute_sql('''
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
        FULL OUTER JOIN neighbors on neighbors.interface_id=mac.interface_id
        
        WHERE 
            -- Remove some common false positives
            devices.device_name not like '%ven%' AND
            interface_name not like '%sup%' AND
            interface_name not like '%ort%' AND
            interface_name not like '%lan%' 
            {}
        GROUP BY 
            devices.device_name, 
            interface_name,
            interfaces.interface_id
        HAVING 
            -- Select only interfaces with more than 3 MACs and no CDP neighbors
            count(mac_address) >= {} AND 
            count(neighbors) = 0
            
        ORDER BY devices.device_name, macs DESC;
        '''.format(where_clause, min_macs) )
    
    output= _generate_table(results)
    print(output)

    for interf in results:

        manufs= _get_entry_manufacturers(interf,
                                         filter_manufacturer,
                                         db)
        if manufs is None: continue
        
        output += '\n\n Device Report: {} - {}\n'.format(
            interf[0], interf[2])
        
        output += manufs 
    
    _write_report(output)
    
@logf
def _get_entry_manufacturers(interf, filter, db):
    mp = MacParser()
    
    # Error checking
    assert interf is not None
    assert len(interf) == 4
    assert interf[1] is not None
    
    mac_table= PrettyTable(['MAC', 'Manufacturer', 'Comment'])
    
    # Get the mac addresses on each interface
    for mac in db.execute_sql_gen('''
        SELECT distinct mac_address
        FROM mac
        WHERE interface_id = %s
    ''',
    (interf[1], ), proc='switches._get_entry_manufacturers'):
        
        if mac is None: break
        assert isinstance(mac, tuple)
        mac= mac[0]
        
        # Get the manufacturer of the device
        manuf= mp.get_manuf(mac)
        comment= mp.get_comment(mac)
        
        if manuf is None: manuf= ''
        if comment is None: comment= ''        
        
        # Remove all filtered matches
        found= False
        for x in filter:
            x= x.lower()
            if (x in manuf.lower() or
                x in comment.lower()): 
                found= True
                break
        
        if found: break
        
        mac_table.add_row([mac, manuf, comment])
    
    # Return none if the table wasn't populated
    if len(mac_table._rows)== 0: return None
    
    return str(mac_table)
            
    
    
def _write_report(t):
    path = os.path.join(config.run_path(),
                        'unknown_switches.txt')
    with open(path, 'w') as outfile:
        outfile.write(str(t))
        
    print ('Finished writing table to [{}]'.format(path))
            
    
def _generate_table(results):
    t = PrettyTable(['Device Name', 'Interface ID', 'Interface', 'MAC Count'])
    t.align = 'l'
    for r in results: t.add_row(r)
    return str(t)


if __name__ == '__main__':
    config.parse_config()
    
    run_find_unknown_switches(
        filter_device_name=['idmz', 'oh-mas', 'CNMAS'],
        min_macs=2,
        #=======================================================================
        # filter_manufacturer=['INTERME',
        #                      'HewlettP',
        #                      'KyushuMa',
        #                      'Cisco Systems',
        #                      'Intel',
        #                      'ADVANTECH',
        #                      
        #                      ],
        #=======================================================================
        )
    
    
    
    
    
    