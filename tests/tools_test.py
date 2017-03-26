'''
Created on Mar 18, 2017

@author: Wyko
'''

from netcrawl.tools import find_unknown_switches, locate
from netcrawl import config, io_sql

from faker import Faker
from tests.helpers import fakeDevice

def setup_module(module):
    config.parse_config()

def test_find_unknown_switches_runs_without_errors():
    find_unknown_switches.run_find_unknown_switches()
    
   
def test_locate_mac_runs_without_error():
    fake = Faker()
    
    for i in range(10):
        locate(fake.mac_address())
        
def test_fake_device():
    db= io_sql.device_db()
    
    with fakeDevice() as f:
        assert db.exists(device_id= f['index'])
    
    assert not db.exists(device_id= f['index'])
        
