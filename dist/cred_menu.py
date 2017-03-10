import getpass, textwrap, config
from cmd import Cmd
from wylog import logging
import sys


class UserPrompt(Cmd):

    
    prompt = 'netcrawl > '

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
    
    
class MainMenu(UserPrompt):
    intro = textwrap.dedent('''\
        Modify device credentials database service accounts.
        Type help or ? to list commands.
        Choose from the following:
        1) List current device credentials
        2) Modify device credentials
        3) Modify database credentials
        Q) Exit
        ''')

    def do_1(self, args):
        '''List current device usernames and a hash of their passwords'''
        print(config.get_vault_data())

    def do_2(self, args):
        ModifyDevice().cmdloop()
    
    def do_3(self, args):
        pass

    def do_4(self, args):
        pass

        

class ModifyDevice(UserPrompt):
    intro = textwrap.dedent('''\
    
        Modify device credentials
        
        Choose from the following:
        1) Delete device credential
        2) Add device credential
        3) Return to main menu 
        Q) Exit
        ''')
    

    def do_1(self, args):
        pass
    
    def do_2(self, args):
        """Add a device credential to secure storage"""
        print()
        cred={'username': input('Username: '),
              'password': getpass.getpass('Password: '),
              'type': input('Credential Type: ')
             }
        
        creds= config.get_vault_data()
        print(creds)
        creds.append(cred)
        print(creds)
        config.write_vault_data(creds)
        
    
def start():
    logging.VERBOSITY= 0
    MainMenu().cmdloop()