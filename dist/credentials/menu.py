from cmd import Cmd
import getpass, textwrap, config
import sys

from wylog import logging
from credentials import manage


class UserPrompt(Cmd):

    
    def emptyline(self):
        pass

    def precmd(self, line):
        '''Accepts lowervase or uppercase input''' 
        line = line.lower()
        return line

    def do_q(self, args):
        """Quits the program."""
        print ("Quitting.")
        sys.exit()
        
    def do_r(self, args):
        return True
    
    
class MainMenu(UserPrompt):
    intro = textwrap.dedent('''\
        Modify device credentials and database service accounts.
        Type help or ? to list commands.
        
        Choose from the following:
        1) List current device credentials
        2) Modify device credentials
        3) Update database credential
        Q) Exit
        ''')
    
    prompt = 'netcrawl> '

    def do_1(self, args):
        '''List current device usernames and a hash of their passwords'''
        print(manage.list_creds())

    def do_2(self, args):
        ModifyDevice().cmdloop()
        print(self.intro)
    
    def do_3(self, args):
        """Replace the current database login"""
        
        print('New database login credentials')
        _cred={'username': input('Username: '),
              'password': getpass.getpass('Password: '),
             }
        
        manage.write_database_cred(_cred)

    def do_r(self, args):
        pass



class ModifyDevice(UserPrompt):
    intro = textwrap.dedent('''\
    
        Modify device credentials
        
        Choose from the following:
        1) Add device credential
        2) Delete device credential
        R) Return to main menu 
        Q) Exit
        ''')
    
    prompt = 'netcrawl:devices> '

    def do_1(self, args):
        """Add a device credential to secure storage"""
        print()
        _cred={'username': input('Username: '),
              'password': getpass.getpass('Password: '),
              'type': input('Credential Type: ')
             }
        
        manage.add_device_cred(_cred)
        
    def do_2(self, args):
        '''Delete a credential'''
        if len(manage.get_device_creds()) == 0:
            print('No device credentials stored.')
        else:
            print()
            DeleteDeviceCred().cmdloop()
            print(self.intro)
        
    
class DeleteDeviceCred(UserPrompt):
    intro = textwrap.dedent('''\
    
        Delete a credential:
        1) By index
        2) Enter exact username and password
        R) Return to main menu 
        Q) Exit
        ''')    
    prompt = 'netcrawl:devices:delete> '
    
    def preloop(self):
        print(manage.list_device_creds())
    
    def do_1(self, args):
        """Delete by index"""
        print()
        try: 
            index= int(input('Index: '))
        except: 
            print('Invalid input')
        else:
            manage.delete_device_cred(index= index)
    
    def do_2(self, args):
        """Delete exact credential"""
        print()
        _cred={'username': input('Username: ').lower(),
              'password': getpass.getpass('Password: '),
             }
        
        manage.delete_device_cred(_cred= _cred)
        
    
def start():
    logging.VERBOSITY= 0
    MainMenu().cmdloop()