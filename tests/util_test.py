'''
Created on Mar 13, 2017

@author: Wyko
'''

from faker import Factory
from pytest import raises
from netcrawl import util

import pytest


@pytest.mark.parametrize("ip, mask, expected", [
    ('169.98.102.209', '255.255.255.0', '169.98.102.0'),
    ('207.17.208.94', '255.255.0.0', '207.17.0.0'),
    ('50.204.211.184', '255.0.0.0', '50.0.0.0'),
    ('116.219.191.68', '255.255.254.0', '116.219.190.0'),
    ('102.168.167.157', '0.0.0.0', '0.0.0.0'),
    ('40.187.188.120', '255.255.255.128', '40.187.188.0'),
    ])    
def test_get_network_ip(ip, mask, expected):
    net_ip= util.network_ip(ip, mask) 
    print('Network IP was: ', net_ip)
    assert net_ip == expected
    
    
def test_is_ip_returns_true_on_valid_ips():
    fake= Factory.create()
    for i in range(100):
        assert util.is_ip(fake.ipv4()) is True
    
def test_is_ip_returns_false_on_bs():
    fake= Factory.create()
    for i in range(100):
        assert util.is_ip(fake.bs()) is False
        