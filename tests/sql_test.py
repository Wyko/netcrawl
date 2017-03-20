'''
Created on Mar 20, 2017

@author: Wyko
'''
import unittest
from netcrawl import io_sql, config
from faker import Faker


class sqlTest(unittest.TestCase):


    def setUp(self):
        config.parse_config()
        self.dbName = 'pytestdb'


    def tearDown(self):
        pass

    
    def test_Create_and_Destroy_Database(self):
        '''Tests the creation of a new database'''
        fake = Faker()
        db_name= '_'.join(['fakedb',
                           fake.word(),
                           fake.word(),
                           fake.word(),
                          ])
        
        _db= io_sql.sql_database()
        
        
        _db.create_database(db_name)
        assert _db.database_exists(db_name)
        
        _db.delete_database(db_name)
        assert not _db.database_exists(db_name)
        
        


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()