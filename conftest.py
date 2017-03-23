'''
Created on Mar 22, 2017

@author: Wyko
'''

import pytest
from faker import Faker
from netcrawl import io_sql, config
from contextlib import contextmanager
from tests import helpers



@pytest.fixture(autouse=True, scope="session")
def inventory_db():
    """Sets up a test inventory database and returns the
    database name"""
    
    config.parse_config()
    
    fake = Faker()
    dbname= '_'.join(['fakedb',
                   fake.word(),
                   fake.word(),
                   fake.word(),
                  ])
    
    config.cc.inventory.name = dbname
    
    # Create the database
    db= io_sql.sql_database()
    db.create_database(dbname)
    assert db.database_exists(dbname)
    del(db)
    
    print('Inventroy_db: ', dbname)
    
    # Pass the database to the test functions
    yield
    
    print('Done with inventory_db: ', dbname)
    
    # Delete the database after use
    db= io_sql.sql_database()
    db.delete_database(dbname)
    assert not db.database_exists(dbname)