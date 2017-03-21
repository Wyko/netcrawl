'''
Created on Mar 20, 2017

@author: Wyko
'''
import unittest
from netcrawl import io_sql, config
from faker import Faker
from tests import helpers


class sqlTest(unittest.TestCase):


    def setUp(self):
        config.parse_config()
        
        fake = Faker()
        self.db_name= '_'.join(['fakedb',
                           fake.word(),
                           fake.word(),
                           fake.word(),
                          ])
        
        # Create the database
        db= io_sql.sql_database()
        db.create_database(self.db_name)
        assert db.database_exists(self.db_name)

    #===========================================================================
    # def pytest_generate_tests(metafunc):
    #===========================================================================

    def test_add_and_delete_device_from_devicedb(self):
        db= io_sql.device_db()
        device= helpers.populated_cisco_network_device()
        
        assert not db.exists(unique_name= device.unique_name(), 
                             device_name= device.device_name)
        index= db.add_device_nd(device)
        
        # Test the different types of exists statements
        assert db.exists(device_id= index)
        assert db.exists(device_name= device.device_name)
        assert db.exists(unique_name= device.unique_name())
        
        db.delete_device_record(index)
        
        # Test the different types of exists statements
        assert not db.exists(device_id= index)
        assert not db.exists(device_name= device.device_name)
        assert not db.exists(unique_name= device.unique_name())
        
    
        
        
    def tearDown(self):
        db= io_sql.sql_database()
        db.delete_database(self.db_name)
        assert not db.database_exists(self.db_name)
        
        


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()