'''
Created on Mar 21, 2017

@author: Wyko
'''

from netcrawl import config, core, io_sql
from faker import Faker
from tests import helpers

db_name= 'netcrawl_pytest_core_db'

def setUp(self):
    config.parse_config()
    fake = Faker()
    
    # Create the database
    ddb= io_sql.sql_database()
    ddb.create_database(db_name)
    assert ddb.database_exists(db_name)
    
    
def tearDown(self):
    ddb= io_sql.sql_database()
    ddb.delete_database(db_name)
    assert not ddb.database_exists(db_name)
    
    
def test_process_duplicate_device():
    ddb= io_sql.device_db()
    device= helpers.populated_cisco_network_device()
    
    assert not ddb.exists(unique_name= device.unique_name(), 
                         device_name= device.device_name)
    
    ddb.add_device_nd(device)
    assert ddb.exists(unique_name= device.unique_name())
    
    core.process_duplicate_device(device, ddb)