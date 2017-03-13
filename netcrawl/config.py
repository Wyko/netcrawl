import configparser
import os

from .credentials.manage import get_device_creds, get_database_cred


cc = {
    
    # Whether or not the config has been updated,
    # like after it has been parsed from settings.ini
    'modified': False,
    
    # The global verbosity level for logging
    'verbosity': 3,
    
    # Whether or not to process debug messages
    'debug': False,
    
    # Raise errors encountered during device processing
    'raise_exceptions': True,
    
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
        
        'root_path': None,
        
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
            'dbname': None,
            'username': None,
            'password': None,
            'server': None,
            'port': None,
        },
        
        'inventory': {
            'dbname': None,
            'username': None,
            'password': None,
            'server': None,
            'port': None,
        },
    }
}

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

def device_path():
    return cc['file']['devices']['full_path']

def vault_path():
    return os.path.join(cc['file']['run']['full_path'], 'vault')

def set_working_dir():
    cc['working_dir']= os.path.dirname(os.path.realpath(__file__))

def parse_config():
    proc= 'config.parse_config'
    
    cc['modified']= True
    set_working_dir()
    
    # Read the settings file
    settings = configparser.RawConfigParser()
    settings.read(os.path.join(cc['working_dir'], 'settings.ini'))
    
    # Parse the settings file
    cc['debug']= settings['options'].getboolean('debug', False)
    cc['verbosity']= settings['options'].getint('verbosity', 3)
    
    cc['database']['main']['dbname']= settings['main_database'].get('database_name', 'main')
    cc['database']['main']['server']= settings['main_database'].get('server', 'localhost')
    cc['database']['main']['port']= settings['main_database'].getint('port', 5432)

    cc['database']['inventory']['dbname']= settings['inventory_database'].get('database_name', 'inventory')
    cc['database']['inventory']['server']= settings['inventory_database'].get('server', 'localhost')
    cc['database']['inventory']['port']= settings['inventory_database'].getint('port', 5432)
    
    cc['time']['format']['pretty']= settings['time_formats'].get('pretty', '%Y-%m-%d %H:%M:%S')
    cc['time']['format']['file']= settings['time_formats'].get('file', '%Y%m%d_%H%M%S')
    
    
    # Set the root path
    
    # If settings root_path is blank, use OS root
    if settings['filepaths'].get('root_path', None) == '':
        cc['file']['root_path']= os.path.abspath(os.sep)
        
    else: cc['file']['root_path']= settings['filepaths'].get('root_path', os.path.abspath(os.sep))
    
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
    if (cc['credentials'] is None or
        len(cc['credentials']) == 0):
        raise IOError('There are no device credentials. Add one with -m') 
    
    _cred= get_database_cred()
    if _cred is None:
        raise IOError('There are no database credentials. Add one with -m') 

    else:
        cc['database']['main']['username']= _cred['username']
        cc['database']['main']['password']= _cred['password']
        cc['database']['inventory']['username']= _cred['username']
        cc['database']['inventory']['password']= _cred['password']
    


