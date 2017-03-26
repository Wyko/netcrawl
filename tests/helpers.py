'''
Created on Mar 15, 2017

@author: Wyko
'''

from faker.providers import BaseProvider
from faker import Factory, Faker
from netcrawl.devices import CiscoDevice, Interface
from netcrawl import io_sql
from contextlib import contextmanager

import os


@contextmanager
def fakeDevice():
    ''' Helper function to create a fake device and add 
    it to the database, then clean it up afterwards'''
    
    db= io_sql.device_db()
    device= populated_cisco_network_device()
    
    assert not db.exists(unique_name= device.unique_name, 
                         device_name= device.device_name)
    
    index=  db.add_device_nd(device)
    
    # Make sure the device was created
    assert db.exists(device_id= index)
    assert device.device_id == index
    
    # Close the connection to prevent too many connections accumulating
    db.conn.commit()
    del(db)
    
    yield {'index': index,
           'device': device
           }
        
    # After we're done with it, delete it
    db= io_sql.device_db()
    db.delete_device_record(index)
    

def example(file):
    '''Returns the data from a given example file as a string'''
    
    _file= os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'examples',
        file)
    
    assert os.path.isfile(_file), '[{}] is not a valid file'.format(
        _file)  
    
    return _file


def get_example_dir(dir_name):
    '''Returns all files in the specified examples subdirectory 
    as a generator yielding a new file each time'''
    
    directory= os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'examples',
            dir_name)
    
    for filename in os.listdir(directory):
        if filename.endswith('.txt'):
            with open(os.path.join(directory, filename), 'r') as infile:
                yield infile.read() 
            

def prepare_test_config():
    pass


def populated_cisco_network_device():
    fake= Faker()
    fake.add_provider(Cisco)
    
    nd = CiscoDevice()
    nd.device_name= '_'.join(['fakedevice',
                           fake.word(),
                           fake.word(),
                           fake.word(),
                          ])
    
    for i in range(1, fake.random_int(1, 10)):
        nd.serial_numbers.append(fake.ios_serial())
    
    nd.config= fake.text(max_nb_chars=fake.random_int(min=5))
    
    return nd
            

def populated_cisco_interface():
    fake = Factory.create()
    
    # then add new provider to faker instance
    fake.add_provider(Cisco)
    
    i = Interface()
 
    addr, mask = fake.ipv4(network=True).split('/')
     
    i.interface_ip= addr 
    i.interface_subnet= mask
     
    i.interface_description= fake.sentence(nb_words=6, variable_nb_words=True)
     
    i.interface_type= fake.interfaceType() 
    i.interface_number= fake.interfaceNumber()
    i.interface_name= i.interface_type + i.interface_number
    
    i.get_network_ip()
    
    return i

            
# first, import a similar Provider or use the default one
# create new provider class
class Cisco(BaseProvider):
    
    interface_types= ['port-channel',
                    'Multilink',
                    'TenGigabitEthernet',
                    'Ethernet',
                    'Cellular',
                    'loopback',
                    'Tunnel',
                    'FastEthernet',
                    'Vlan',
                    'Port-channel',
                    'POS',
                    'Loopback',
                    'Embedded-Service-Engine',
                    'Service-Engine',
                    'Serial',
                    'GigabitEthernet',
                    'Async',
                    'ISM',
                    'mgmt',
                    'MFR',]
    
    def interfaceType(self):
        return self.random_element(self.interface_types)
    
    
    def interfaceNumber(self):
        '''Generates a fake interface number'''
        
        name= str(self.random_digit())
        
        for x in range(self.random_int(0, 3)):
            name += '/' + str(self.random_digit())
        
        # Add a sub interface    
        if self.random_digit() < 3:
            name+= '.' + str(self.random_int(1, 999))
            
        return name
    
    def ios_serial(self):
        fake = Factory.create()
        
        return {'name': '_'.join(['fakeserial',
                           fake.word(),
                           fake.word()]),
                 
                'desc': '_'.join(['fakedesc',
                           fake.word(),
                           fake.word()]),
                 
                'pid': fake.uuid4(),
                'vid': fake.uuid4(),
                'serialnum': fake.uuid4()
                }
        












                