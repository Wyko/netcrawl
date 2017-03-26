'''
Created on Mar 15, 2017

@author: Wyko
'''

from netcrawl.devices.base import NetworkDevice
from netcrawl import config
from faker import Faker
from tests.helpers import populated_cisco_network_device,\
    populated_cisco_interface
import os, glob


def test_interface_string():
    i= populated_cisco_interface()
    print(i)
    
    # This is probably pointless.
    assert isinstance(str(i), str)
    
    # Make sure something legible actually got printed
    assert len(str(i)) > 5
    
def test_config_save():
    '''Ensure that the device can save its config'''
    
    n= populated_cisco_network_device()
    n.save_config()
    
    path = os.path.join(config.cc.devices_path, 
                        n.unique_name)
    
    assert glob.glob(os.path.join(path, '*.cfg'))
    
    import shutil
    shutil.rmtree(path, ignore_errors=True)
    
    assert not glob.glob(os.path.join(path, '*.cfg'))
    
    
    
    
    