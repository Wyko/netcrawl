'''
Created on Mar 20, 2017

@author: Wyko
'''
from netcrawl import io_sql, config
from netcrawl.io_sql import device_db
from faker import Faker
from tests import helpers
from netcrawl.devices.base import NetworkDevice
from time import sleep
import psycopg2

from netcrawl.config import cc
from tests.helpers import fakeDevice, populated_cisco_network_device



def test_update_device():
    
    with fakeDevice() as f:
        db= io_sql.device_db()
        
        record= db.get_device_record('device_id', f['index'])
        assert f['device'].device_name == record['device_name']
        
        # Change the device name
        f['device'].device_name= 'something'
        
        db.update_device_entry(f['device'], device_id= f['index'])
        
        record= db.get_device_record('device_id', f['index'])
        assert f['device'].device_name == 'something'
        

def test_set_dependents_as_updated():
    with fakeDevice() as f:
        db= io_sql.device_db()
        
        record= db.get_device_record('device_id', f['index'])
        oldtime= record['updated']
        print(type(oldtime))
        print(oldtime)
        del(db)
        
        sleep(.5)
        config.cc.debug= True
        config.cc.verbosity= 6
        
        db= io_sql.device_db()
        db.set_dependents_as_updated(device_id= f['index'])
        newrecord= db.get_device_record('device_id', f['index'])
        
        
        print(type(newrecord['updated']))
        print(newrecord['updated'])
        
        assert oldtime != newrecord['updated']
        

def test_time_in_sql():
    with fakeDevice() as f:
        db= io_sql.device_db()
        record= db.get_device_record('device_id', f['index'])
        oldtime= record['updated']
        print(oldtime)
        del(db)
        
        sleep(.5)
        db= io_sql.device_db()
        db.execute_sql('''
            UPDATE devices
            SET updated = now()
            where device_id = %s;
        ''', (f['index'], ), fetch= False)
        
        record2= db.get_device_record('device_id', f['index'])
        print('Index: ', f['index'])
        print('New Time: ', record2['updated'])
        
        assert oldtime != record2['updated']

def test_inventory_fixture_works():
    assert config.cc.inventory.name is not None
    print('Inventory Name: ', config.cc.inventory.name)
    
    # For the heck of it, because for some reason importing 
    # the specific variable doesn't work like the whole instance
    assert cc is None
    
    
def test_fake_device():
    '''Purely tests whether the helper function works'''
    
    # Create a fake device
    with fakeDevice() as f:
        assert isinstance(f['index'], int)
        assert isinstance(f['device'], NetworkDevice)
        

def test_devicedb_exists_functions():
    db= io_sql.device_db()
    
    device= helpers.populated_cisco_network_device()
    
    assert not db.exists(unique_name= device.unique_name, 
                         device_name= device.device_name)
    index= db.add_device_nd(device)
    
    # Test the different types of exists statements
    assert db.exists(device_id= index)
    assert db.exists(device_name= device.device_name)
    assert db.exists(unique_name= device.unique_name)
    
    db.delete_device_record(index)
    
    # Test the different types of exists statements
    assert not db.exists(device_id= index)
    assert not db.exists(device_name= device.device_name)
    assert not db.exists(unique_name= device.unique_name)
    

def test_devicedb_get_record():
    '''The SQL database columns should match up with the names of 
    attributes in the base network device_class'''
    
    db= device_db()
    
    # Create a fake device and add it to the database
    with fakeDevice() as f:
        
        record= db.get_device_record('device_id', f['index'])
        
        assert isinstance(record, psycopg2.extras.DictRow) , 'Record is type [{}]'.format(type(record))
        
        print('Database Columns:\n', [k for k in record.keys()])
        print('Class Attributes:\n', [item for item in dir(f['device']) if not item.startswith("__")])
        
        # Make sure that the records in the database have a matching class variable
        # and that the values are the same
        for k, v in record.items():
            
            # We dont care about 'updated'
            if k == 'updated': continue
            
            assert hasattr(f['device'], k)
            assert getattr(f['device'], k) == v
