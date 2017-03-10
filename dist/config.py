import keyring, os, config, ast, sys
import configparser, cryptography

from cryptography.fernet import Fernet
from cmd import Cmd
from wylog import logging, log

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
        
        'root_path': None,
        
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

def pretty_time():
    return cc['time']['format']['pretty']

def file_time():
    return cc['time']['format']['file']

def run_path():
    return cc['file']['run']['full_path']

def creds():
    return cc['credentials']

def device_path():
    return cc['file']['devices']['full_path']

def vault_path():
    return os.path.join(cc['file']['run']['full_path'], 'vault')

def set_working_dir():
    cc['working_dir']= os.path.dirname(os.path.realpath(__file__))

def parse_config():
    proc= 'config.parse_config'
    set_working_dir()
    
    # Read the settings file
    settings = configparser.RawConfigParser()
    settings.read(os.path.join(cc['working_dir'], 'settings.ini'))
    
    # Parse the settings file
    cc['debug']= settings['options'].getboolean('debug', False)
    cc['verbosity']= settings['options'].getint('verbosity', 3)
    
    cc['database']['main']['dbname']= settings['main_database'].get('database_name', 'main')
    cc['database']['main']['username']= settings['main_database'].get('username', 'svc_netmiko_main')
    cc['database']['main']['server']= settings['main_database'].get('server', 'localhost')
    cc['database']['main']['port']= settings['main_database'].getint('port', 5432)

    cc['database']['inventory']['dbname']= settings['inventory_database'].get('database_name', 'inventory')
    cc['database']['inventory']['username']= settings['inventory_database'].get('username', 'svc_netmiko_inventory')
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
    os.makedirs(device_path(), exist_ok= True)
    
    if not os.path.isdir(device_path()):
        raise IOError('Filepath could not be created: [{}]'.format(device_path()))
    
    # Populate credentials
    cc['credentials']= get_vault_data()
    


def _get_fernet_key():
    proc= 'config._get_fernet_key'
    
    # Retrieve the encryption key from storage or generate one
    key= keyring.get_password('netcrawl', 'netcrawl')
    if key is None:
        log('Creating encryption key', v= logging.N, proc= proc)
        key = Fernet.generate_key()
        keyring.set_password('netcrawl', 'netcrawl', str(key, encoding='utf-8'))
    else:
        key= bytes(key, encoding='utf-8')
        
    # Create a Fernet key from the base key
    return Fernet(key)
    del(key)


def write_vault_data(data):
    '''Overwrites all stored data with the new data'''
    proc= 'config.write_vault_data'
    
    f= _get_fernet_key()
    
    with open(config.vault_path(), 'w+b') as outfile:
        outfile.write(f.encrypt(bytes(str(data), encoding='utf-8')))
        
    
def get_vault_data():
    proc= 'config.get_vault_data'
    
    # Create the vault if needed
    if not os.path.isfile(config.vault_path()):
        log('Creating Vault', 
            proc=proc, v=logging.I)
        with open(config.vault_path(), 'w+b'): pass
    
    with open(config.vault_path(), 'r+b') as outfile:
        raw_vault= outfile.read()
    
    if len(raw_vault) <= 1:
        log('Vault empty. Returning empty list', 
            proc=proc, v=logging.I)
        return []
        
    f= _get_fernet_key()
    
    try: output= f.decrypt(raw_vault)
    except cryptography.fernet.InvalidToken: 
        log('Vault data invalid. Returning empty list', 
            proc=proc, v=logging.A)
        return []
    else:
        return ast.literal_eval(str(output, encoding='utf-8'))    
    finally:
        del(f)




