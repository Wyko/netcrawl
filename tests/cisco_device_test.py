'''
Created on Mar 15, 2017

@author: Wyko
'''

import os, pytest
from tests import helpers
from netcrawl.devices import CiscoDevice

@pytest.fixture(params=helpers.get_example_dir('ios_show_inv'))
def next_example(request):
    return request.param
                        
def test_cisco_parse_serials(next_example):
    cd = CiscoDevice()
    helpers.populate_network_device(cd)

    for f in helpers.get_example_dir('ios_show_inv'):
        parse= cd._parse_serials(next_example)
         
        assert len(parse) > 0 
        assert isinstance(parse, list)                        
                        
#===============================================================================
# def test_cisco_parse_serials():
#     cd = CiscoDevice()
#     helpers.populate_network_device(cd)
# 
#     for f in helpers.get_example_dir('ios_show_inv'):
#         parse= cd._parse_serials(f)
#          
#         assert len(parse) > 0 
#         assert isinstance(parse, list)
#===============================================================================
