import os

from .credentials.manage import get_device_creds, get_database_cred
import textwrap


cc = {
    
    # Whether or not the config has been updated,
    # like after it has been parsed from settings.ini
    'modified': False,
    
    # The global verbosity level for logging
    'verbosity': 3,
    
    # Whether or not to process debug messages
    'debug': False,
    
    # Raise errors encountered during device processing
    'raise_exceptions': False,
    
    'working_dir': None,
    
    'time': {
        'format': {
            'pretty': '%Y-%m-%d %H:%M:%S',
            'file': '%Y%m%d_%H%M%S',
        },
    },
                  
    'delay': {
        # The starting delay factor in cli connections
        'base_delay': 1,

        # The amount the delay increases on failed attempts
        'delay_increase': 0.3,
    },
        
    'file': {
        
#         'root_path': os.path.abspath(os.sep),
        'root_path': os.path.join(os.path.expanduser('~')),
        
        'log': {
            'name': 'log.txt',
            'full_path': None,
        },
        
        'run': {
            'folder': 'netcrawl',
            'full_path': None,
        },
             
        'devices': {
            'folder': 'devices',
            'full_path': None,
        },
        
    },
    
    # User credentials to log in to devices
    'credentials': [
#         {
#             'username': None,
#             'password': None,
#             'type': None,
#         },
    ],
        
    'database': {
        'main': {
            'username': None,
            'password': None,
            'dbname': 'main',
            'server': 'localhost',
            'port': 5432,
        },
        
        'inventory': {
            'username': None,
            'password': None,
            'dbname': 'inventory',
            'server': 'localhost',
            'port': 5432,
        },
    }
}

def set_database_cred(username, password):
    cc['database']['main']['username']= username
    cc['database']['main']['password']= password
    cc['database']['inventory']['username']= username
    cc['database']['inventory']['password']= password

def is_modified():
    '''Convenience function to find out whether the the 
    config has been modified (i.e, after it has been
    parsed from config.ini'''
    return cc['modified']

def raise_exceptions():
    return cc['raise_exceptions']

def postgres_args():
    '''This just uses the main_db credentials'''
    return {'dbname': 'postgres',
            'user': cc['database']['main']['username'],
            'password': cc['database']['main']['password'],
            'host': cc['database']['main']['server'],
            'port': cc['database']['main']['port'],
            }

def main_args():
    return {'dbname': cc['database']['main']['dbname'],
            'user': cc['database']['main']['username'],
            'password': cc['database']['main']['password'],
            'host': cc['database']['main']['server'],
            'port': cc['database']['main']['port'],
            }
    
def inventory_args():
    return {'dbname': cc['database']['inventory']['dbname'],
            'user': cc['database']['inventory']['username'],
            'password': cc['database']['inventory']['password'],
            'host': cc['database']['inventory']['server'],
            'port': cc['database']['inventory']['port'],
            }

def pretty_time():
    return cc['time']['format']['pretty']

def file_time():
    return cc['time']['format']['file']

def run_path():
    return cc['file']['run']['full_path']

def creds():
    return cc['credentials']

def log_path():
    return cc['file']['log']['full_path']

def root_path():
    return cc['file']['root_path']

def device_path():
    return cc['file']['devices']['full_path']

def vault_path():
    return os.path.join(cc['file']['run']['full_path'], 'vault')

def working_dir():
    return cc['working_dir']

def set_working_dir():
    cc['working_dir']= os.path.dirname(os.path.abspath(__file__))

def setting_path():
    return os.path.join(working_dir(), 'settings.ini')


def parse_config():
    proc= 'config.parse_config'
    
    cc['modified']= True
    set_working_dir()
    
    # Parse and make the runtime folders
    cc['file']['run']['full_path']= os.path.join(cc['file']['root_path'], cc['file']['run']['folder'])    
    cc['file']['devices']['full_path']= os.path.join(cc['file']['run']['full_path'], cc['file']['devices']['folder'])
    # Get the log path
    cc['file']['log']['full_path'] = os.path.join(cc['file']['run']['full_path'],
                                                  cc['file']['log']['name'])

    os.makedirs(device_path(), exist_ok= True)
    
    if not os.path.isdir(device_path()):
        raise IOError('Filepath could not be created: [{}]'.format(device_path()))
    
    
    # Populate credentials
    cc['credentials']= get_device_creds()
    
    _cred= get_database_cred()
    set_database_cred(_cred['username'], _cred['password'])
    

def check_credentials():
    if (cc['credentials'] is None or
        len(cc['credentials']) == 0):
        raise IOError('There are no device credentials. Add one with -m') 
    
    if (cc['database']['main']['username'] is None
        or cc['database']['main']['password'] is None):
        raise IOError('There are no database credentials. Add one with -m') 










