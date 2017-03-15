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


def _fake_csv_output():
    #===========================================================================
    # example= [
    #     {'mac': 'dc:a8:b0:ae:29:5f', 'network_ip': '168.237.85.0/25'}
    #     {'mac': '53:3a:83:c4:5c:1e', 'network_ip': '0.0.0.0/1'}]
    #===========================================================================

    # Generate a fake CSV output
    from random import shuffle
    fake= Factory.create()
    x= []
    previous_ips= []
    for i in range (10):
        
        # Generate a unique IP to make sure we 
        # have exactly 10 unique subnets 
        while True:
            ip= fake.ipv4(network= True)
            if ip not in previous_ips:
                previous_ips.append(ip)
                break
        
        for i in range (10):
            x.append({'mac': fake.mac_address(), 
                     'network_ip': ip})
        shuffle(x)
    return x


def test_sort_csv_by_subnet_returns_proper_number_of_results():
    
    result= mac_audit.sort_csv_by_subnet(_fake_csv_output())
    
    assert len(result)==10


def test_disallows_bad_files():
    '''Don't permit bad filepaths'''
    with raises(IOError): 
        mac_audit._open_csv('C:\_Something_Awfully_Wrong')
        
        
def test_can_open_csv():
    _path= _example('ip_subnet_mac.csv')
    
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
