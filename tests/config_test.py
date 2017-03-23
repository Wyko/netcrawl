'''
Created on Mar 14, 2017

@author: Wyko
'''

from netcrawl import config
import os

def setup_module(module):
    config.parse_config()
    

def test_set_working_dir():
    print ('Working Dir: ', config.cc.working_dir)
    
    assert config.cc.working_dir is not None
    assert os.path.exists(config.cc.working_dir)


