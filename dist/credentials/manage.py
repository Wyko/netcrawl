'''
Created on Mar 11, 2017

@author: Wyko
'''

import cryptography, hashlib
from cryptography.fernet import Fernet
import keyring, os, config, ast
from wylog import logging, log


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


def _write_vault_data(data):
    '''Overwrites all stored data with the new data'''
    proc= 'config.write_vault_data'
    
    f= _get_fernet_key()
    
    with open(config.vault_path(), 'w+b') as outfile:
        outfile.write(f.encrypt(bytes(str(data), encoding='utf-8')))
        
    
def _get_vault_data():
    proc= 'config.get_vault_data'
    
    # Create the vault if needed
    if not os.path.isfile(config.vault_path()):
        log('Creating Vault', 
            proc=proc, v=logging.I)
        with open(config.vault_path(), 'w+b'): pass
    
    with open(config.vault_path(), 'r+b') as outfile:
        raw_vault= outfile.read()
    
    # Check for an empty dictionary
    if len(raw_vault) <= 1:
        log('Vault empty. Returning None', 
            proc=proc, v=logging.I)
        return _validate_vault(None)
        
    f= _get_fernet_key()
    
    try: output= f.decrypt(raw_vault)
    except cryptography.fernet.InvalidToken: 
        log('Vault data invalid.', 
            proc=proc, v=logging.A)
        return _validate_vault(None)
    else:
        # Translate the decrypted text into a dict, then
        # validate it and return it
        return _validate_vault(
            ast.literal_eval(
                str(output, encoding='utf-8')))    
    finally:
        del(f)


def get_device_creds():
    _vault= _get_vault_data()
    if not _vault or ('device_creds' not in _vault): 
        return None
    
    return _vault['device_creds'] 

def get_database_cred():
    _vault= _get_vault_data()
    if not _vault or ('database' not in _vault): 
        return None
    
    return _vault['database'] 


def delete_device_cred(_cred=None, index= None):
    _vault= _get_vault_data()
    if not _vault or ('device_creds' not in _vault): 
        return False
    
    if index is not None: 
        print('Removed ' + _vault['device_creds'][index]['username'])
        del _vault['device_creds'][index]
    
    elif _cred is not None:
        for x in _vault['device_creds']:
            if all((_cred['username'].lower() == x['username'].lower()),
                   (_cred['password'] == x['password'])):
                _vault['device_creds'].remove(x)
                print('Removed ' + _cred['username'])
    
    _write_device_creds(_vault['device_creds'])
                

def list_creds():
    '''Lists the device credentials in secure form'''
    output= _get_vault_data()
    if output is None: return ''
    
    if any([output['database']['password'] is None,
           output['database']['username'] is None]):
        f_output= 'No Database credentials stored.\n'
    else:
        output['database']['password']= hashlib.md5(output['database']['password'].encode()).hexdigest()[:8]
        f_output= '>> Database Username: {}\n   Hashed Password: {}\n\n'.format(
            output['database']['username'], output['database']['password'])
    
    if len(output['device_creds']) == 0:
        f_output+=('No device credentials stored.\n')
    else:
        for i, c in enumerate(output['device_creds']):
            # Hash the password and trim to 8 characters
            c['password']= hashlib.md5(c['password'].encode()).hexdigest()[:8]
            f_output+= '{}) Username: {}\n   Hashed Password: {}\n   Type: {}\n'.format(
                i, c['username'], c['password'], c['type'])
        
    return f_output
        
        
        
def _write_device_creds(_creds):
    _vault= _get_vault_data()
    _vault['device_creds']= _creds
    _write_vault_data(_vault)
    
    
def add_device_cred(_cred):
    if (isinstance(_cred, dict) and
        all (k in _cred for k in ('username',
                                  'password',
                                  'type',))):
    
        _vault= _get_vault_data()
        _vault['device_creds'].append(_cred)
        _write_vault_data(_vault)
    
    
def write_database_cred(_cred):
    _vault= _get_vault_data()
    _vault['database']= _cred
    _write_vault_data(_vault)
    

def _validate_vault(_vault):
    '''Superficially validates the vault data by making
    sure it conforms to the expected data types.'''
    proc= 'credentials.manage._validate_vault'
     
    if not isinstance(_vault, dict):
        log("Whole vault was malformed", 
            proc=proc, v=logging.I)
        return {
                'device_creds': [],
                'database': {'username': None,
                             'password': None},
                }
        
    if (('device_creds' not in _vault) or 
        (not isinstance(_vault['device_creds'], list))):
        log("'device_creds' was malformed", 
            proc=proc, v=logging.I)
        _vault['device_creds']= []
    
    if (('database' not in _vault) or 
        (not isinstance(_vault['database'], dict))):
        log("'database' was malformed", 
            proc=proc, v=logging.I)
        _vault['database']= {'username': None,
                             'password': None}

    return _vault
        
        
        
        
        
        