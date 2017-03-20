'''
Created on Mar 13, 2017

@author: Wyko
'''

from time import sleep

from netcrawl import config
from netcrawl.wylog import log, log_snip, logging


def setup_module(module):
    config.parse_config()
    

def test_log_is_in_running_directory():
    import os
    log('Pytest log entry', proc= 'test_log_is_in_running_directory')
    
    assert os.path.isfile(os.path.join(
        config.run_path(),
        'log.txt'))

def test_log_snip_actually_logs_something(capsys):
    config.set_verbosity(logging.NORMAL)
    
    with log_snip('test_log_snip_actually_logs_something', 
                  logging.NORMAL):
        sleep(0.1)
        
    out, err = capsys.readouterr()
    
    assert 'Finished snippet' in out
    
    
    
    
    
    
    
    