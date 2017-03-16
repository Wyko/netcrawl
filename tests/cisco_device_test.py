'''
Created on Mar 15, 2017

@author: Wyko
'''

import os
from tests import helpers
from netcrawl.devices import CiscoDevice
from tests.helpers import Cisco


def test_cisco_parse_serials():
    cd = CiscoDevice()
    
    for f in helpers.get_example_dir('ios_show_inv'):
        parse= cd._parse_serials(f)
        
        assert len(parse) > 0 
        assert isinstance(parse, list)