'''
Created on Mar 14, 2017

@author: Wyko
'''

from netcrawl import config
import os

def setup_module(module):
    config.parse_config()

def test_set_working_dir():
    print ('Working Dir: ', config.cc['working_dir'])
    print ('Working dir2: ', config.working_dir())
    print ('Setting path: ', config.setting_path())
    
    assert config.cc['working_dir'] is not None
    assert os.path.exists(config.cc['working_dir'])


def test_open_settings():
    settings= config.open_settings()
    
    assert 'options' in settings