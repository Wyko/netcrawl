'''
Created on Mar 16, 2017

@author: Wyko
'''

from netcrawl.credentials import manage
from cryptography import fernet
from faker import Faker
import keyring

def setup_module(module):
    from netcrawl import config
    config.parse_config()

def test_get_Fernet_returns_a_key():
    fake = Faker()
    appname= '_'.join(['test_a_netcrawl_', fake.word(), fake.word()])
    username= '_'.join(['test_u_netcrawl_', fake.word(), fake.word()])
    
    key= manage._get_fernet_key(appname, username)
    
    assert isinstance(key, fernet.Fernet), 'Key [{}] is wrong type'.format(
        type(key))
    
    assert keyring.get_password(appname, username) is not None
    
    keyring.delete_password(appname, username)
    
    assert keyring.get_password(appname, username) is None
    
    