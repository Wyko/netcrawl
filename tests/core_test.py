'''
Created on Mar 21, 2017

@author: Wyko
'''

from netcrawl import config, core, io_sql
from faker import Faker
from tests import helpers

def test_process_duplicate_device():
    
    # Connect to the database
    ddb = io_sql.device_db()
    
    # Create a fake device and make sure it doesn't exist 
    device= helpers.populated_cisco_network_device()
    assert not ddb.exists(unique_name= device.unique_name, 
                          device_name= device.device_name)
    
    ddb.add_device_nd(device)
    assert ddb.exists(unique_name= device.unique_name)
    
    duplicate= core.process_duplicate_device(device, ddb)
    
    assert duplicate
        
    
    
    