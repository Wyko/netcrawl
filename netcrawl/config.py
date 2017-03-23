import os

from .credentials.manage import get_device_creds, get_database_cred
import textwrap



class Database:
    def __init__(self, dbname):
        self.name= dbname
        self.username= None
        self.password= None
        self.server= 'localhost'
        self.port= 5432
    
    @property    
    def args(self):
        '''Returns a dict used to populate a psycopg2 connection'''
        
        return {'dbname': self.name,
                'user': self.username,
                'password': self.password,
                'host': self.server,
                'port': self.port,
                }


class Config:
    def __init__(self):
        
        # Whether or not the config has been updated,
        # like after it has been parsed from settings.ini
        self.modified= False
        
        # The global verbosity level for logging
        self.verbosity= 3
        
        # Whether or not to process debug messages
        self.debug= False
        
        # Raise errors encountered during device processing
        self.raise_exceptions= False
        
        self.working_dir= os.path.dirname(os.path.abspath(__file__))
        
        self.pretty_time= '%Y-%m-%d %H:%M:%S'
        self.file_time= '%Y%m%d_%H%M%S'
        
        # The starting delay factor in cli connections              
        self.base_delay= 1

        # The amount the delay increases on failed attempts
        self.delay_increase= 0.3
    
        self.root_path= os.path.join(os.path.expanduser('~'))
            
        self.run_folder= 'netcrawl'
        self.run_path= os.path.join(self.root_path, self.run_folder)
        
        self.devices_path= os.path.join(self.run_path, 'devices')
        
        self.log_path= os.path.join(self.run_path, 'log.txt')
        
        self.vault_path= os.path.join(self.run_path, 'vault')
        
        # Make the running directories
        os.makedirs(self.devices_path, exist_ok= True)
        
        # Check if everything worked
        if not os.path.isdir(self.devices_path):
            raise IOError('Filepath could not be created: [{}]'.format(self.devices_path))
        
        
        self.postgres= Database('postgres')
        self.main= Database('main')
        self.inventory = Database('inventory')

        # User credentials to log in to devices
        #=======================================================================
        # self.credentials= [
        #     {
        #         'username': None,
        #         'password': None,
        #         'type': None,
        #     },
        # ]
        #=======================================================================
        
        

    def set_all_database_creds(self, username, password):
        for db in (self.postgres,
                   self.main,
                   self.inventory):
            db.username= username
            db.password= password
            
    def check_credentials(self):
        if (self.credentials is None or
            len(self.credentials) == 0):
            raise IOError('There are no device credentials. Add one with -m')


# Stores the global config
####################
cc= None
####################


def parse_config():
    proc= 'config.parse_config'
    
    global cc
    if not cc: cc= Config()
    
    cc.credentials= get_device_creds()
        
    cc.set_all_database_creds(**get_database_cred())
    

    








