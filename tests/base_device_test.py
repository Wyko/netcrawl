'''
Created on Mar 15, 2017

@author: Wyko
'''

from netcrawl.devices.base import NetworkDevice
from netcrawl import config
from faker import Faker
from tests.helpers import populated_cisco_network_device
import os, glob


def build_network_device():
    fake= Faker()

def test_interface_string():
    n= NetworkDevice()
    
def test_config_save():
    n= populated_cisco_network_device()
    n.save_config()
    
    path = os.path.join(config.cc.devices_path, 
                        n.unique_name)
    
    assert glob.glob(os.path.join(path, '*.cfg'))
    
    import shutil
    shutil.rmtree(path, ignore_errors=True)
    
    assert not glob.glob(os.path.join(path, '*.cfg'))
    
    
    
    
    