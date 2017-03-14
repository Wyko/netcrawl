import os, re

from faker import Factory
from pytest import raises

from netcrawl.tools import mac_audit
from netcrawl import config
import csv

def setup_module(module):
    config.parse_config()

def _example(file):
    '''Returns the data from a given example file as a string'''
    
    
    _file= os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'examples',
        file)
    
    assert os.path.isfile(_file), '[{}] is not a valid file'.format(
        _file)  
    
    return _file


def test_disallows_bad_files():
    '''Don't permit bad filepaths'''
    with raises(IOError): 
        mac_audit._open_csv('C:\_Something_Awfully_Wrong')
        
        
def test_can_open_csv():
    _path= _example('ap_rogue_report.csv')
    
    print('Example path is [{}]'.format(_path))
    c= mac_audit._open_csv(_path)
    
    assert isinstance(c, list)
    assert len(c) > 2 


#===============================================================================
# def test_audit_runs_without_error():
#     _path= _example('ap_rogue_report.csv')
#     mac_audit.run_audit(_path)
#===============================================================================

def _strip_mac(mac):
    return ''.join([x.upper() for x in mac if re.match(r'\w', x)])


def test_bad_mac_doesnt_evaluate():
    fake= Factory().create()
    assert mac_audit.evaluate_mac(
        _strip_mac(fake.mac_address()),
        None
    ) == 0
    
    assert mac_audit.evaluate_mac(
        None,
        None
    ) == 0
    
    assert mac_audit.evaluate_mac(
        None,
        _strip_mac(fake.mac_address()),
    ) == 0


def test_perfect_mac_match_scores_100():
    fake= Factory().create()
    x= _strip_mac(fake.mac_address())
               
    assert mac_audit.evaluate_mac(x, x) == 100

# def test_eval_returns_valid_response():
#     response= mac_audit.evaluate_mac('001422012345')
#     
#     assert isinstance(response, dict), 'Response was [{}]'.format(
#         type(response))
#     
#     # Check to make sure a valid confidence was returned
#     assert all (k in response for k in ('matched',
#                                         'confidence',
#                                         'best_mac',
#                                         'mac_id',)
#                 ), 'No valid response found in [{}]'.format(response)
#     
