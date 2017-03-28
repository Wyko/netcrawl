'''
Created on Mar 27, 2017

@author: Wyko
'''

import argparse, textwrap, sys
from netcrawl.wylog import logging, log
from netcrawl.credentials import menu
from netcrawl.core import recursive_scan, single_scan, nmap_scan
from netcrawl import config

def make_parser() -> argparse.ArgumentParser:
    '''
    Uses argparse to create a CLI parser fully populated with the arguments for 
    Netcrawl. Creation of the parser and its execution were separated in order 
    to ensure compatibility with Sphinx's CLI auto-documentation. 
    
    Returns:
        argparse.ArgumentParser: A parser object ready for use in parsing a 
        CLI command
    '''
    
    parser = argparse.ArgumentParser(
        prog='NetCrawl',
        formatter_class=argparse.RawTextHelpFormatter,
        description=textwrap.dedent(
            '''\
            Netcrawl is a network discovery tool designed to poll one or 
            more devices, inventory them in a SQL database, and then 
            continue the process through the device's neighbors. It offers
            integration with Nmap to discover un-connected hosts.'''))
    
    polling = parser.add_argument_group('Options')
    scanning = parser.add_argument_group('Run Type')
    action = scanning.add_mutually_exclusive_group(required=True)
    target = parser.add_argument_group('Target Specification')
    
    polling.add_argument(
        '-v',
        type=int,
        dest='v',
        default=logging.N,
        choices=range(7),
        metavar='LEVEL',
        help=textwrap.dedent(
            '''\
            Verbosity level. Logs with less importance than 
                the global verbosity level will not be processed.
                1: Critical alerts
                2: Non-critical alerts 
                3: High level info
                4: Normal level
                5: Informational level
                6: Debug level info (All info)''')
        )
    
    
    action.add_argument(
        '-m',
        action="store_true",
        dest='manage_creds',
        help=textwrap.dedent(
        '''\
        Credential management. Use as only argument.
        '''),
        )
    

    polling.add_argument(
        '-i',
        '--ignore',
        action="store_true",
        dest='ignore_visited',
        help=textwrap.dedent(
        '''\
        Do not resume the last scan if one was interrupted midway. Omitting
            this argument is not the same as using -c; Previous device database
            entries are maintained, but all visited entries are removed. 
        '''),
        )
    
    polling.add_argument(
        '-u',
        '--update',
        action="store_true",
        dest='update',
        help=textwrap.dedent(
        '''\
        Iterates through all previously-found devices and scans them again. 
            This implies the --ignore flag in that it also removes previous 
            visited entries.
        '''),
        )
    
    polling.add_argument(
        '-d',
        '--debug',
        action="store_true",
        dest='debug',
        help=textwrap.dedent(
        '''\
        Enables debug messages. If this is not specified, a Verbosity level
            of 5 or greater has no effect since those messages will be 
            ignored anyway. If Debug is enabled and V is less than 5, 
            debug messages will only be printed to the log file.
        '''),
        )
    
    polling.add_argument(
        '-c',
        '--clean',
        action="store_true",
        dest='clean',
        help='Delete all existing database entries and rebuild the databases.',
        )
    
    polling.add_argument(
        '-sd',
        '--skip-named-duplicates',
        action="store_true",
        dest='skip_named_duplicates',
        help='If a CDP entry has the same host name as a previously visited device,'
        ' ignore it.',
        default=False
        )
    
    action.add_argument(
        '-sR',
        '--recursive',
        action="store_true",
        dest='recursive',
        help=textwrap.dedent(
        '''\
        Recursively scan neighbors for info. --target is not required,
            but if it is supplied then the device will be added as a 
            scan target. Target will accept a single IP or hostname.
        '''),
        )
    
    action.add_argument(
        '-sS',
        '--single',
        action="store_true",
        dest='single',
        help=textwrap.dedent(
        '''\
        Scan one seed device for info. --target is required.
            Target will accept a single IP or hostname.
        '''),
        )
    
    action.add_argument(
        '-sN',
        '--scan-network',
        action="store_true",
        dest='network_scan',
        help=textwrap.dedent(
        '''\
        Performs an NMAP scan against a specified target. 
            --target is required. Target will accept a 
            Nmap-compatible target identifier. Examples:
            10.1.1.1
            192.168.0-255.1
        '''),
        )
    
    target.add_argument(
        '-t',
        '--target',
        action='store',
        dest='host',
        metavar='TARGET',
#         default= None,
        help='Hostname or IP address of a starting device'
        )
    
    target.add_argument(
        '-p',
        dest='platform',
        metavar='PLATFORM',
        help='The Netmiko platform for the device',
        default='unknown'
        )
    
    return parser
    
    


def parse_cli():
    '''
    Creates an argparse CLI parser and parses the CLI options.
    
    Returns:
        argparse.Namespace: A simple class used to hold the 
        attributes parsed from the command line.
    '''
    
    parser= make_parser()
    args = parser.parse_args()
     
    if args.update: args.ignore_visited = True
     
    return args



def main(args=None):
    '''
    This is the main method for NetCrawl, containing 
    the code which executes the rest of the 
    application.
    '''
    
    proc = 'main.__main__'
    
    # Process the settings file
    config.parse_config()
    
    # Parse CLI arguments
    if len(sys.argv[1:]) > 0: 
        args = parse_cli()
    else:
        print('No arguments passed.')
        sys.exit()

    # Set verbosity level for wylog
    config.cc.verbosity= args.v
    
    log('Start new run', 
        new_log=True,
        v= logging.HIGH,
        proc= proc)
    
    logging.PRINT_DEBUG = args.debug
    if args.debug: config.cc.debug= True 
    

    if args.manage_creds:
        menu.start()
    
    if len(config.cc.credentials) == 0:
        print('There are no stored credentials. You must first add them with -m')
        log('There are no stored credentials. You must first add them with -m',
            v= logging.C, proc= proc)
        sys.exit()
    
      
    if args.network_scan:
        if args.host: 
            log('##### Starting Scan #####', proc=proc, v=logging.H)
            nmap_scan(args.host,
                       clean=args.clean)
            log('##### Scan Complete #####', proc=proc, v=logging.H)
        else:
            print('--target (-t) is required when performing a network scan (-ns)')
       
    elif args.recursive: 
        log('##### Starting Recursive Run #####', proc=proc, v=logging.H)
        
        recursive_scan(
            target=args.host,
            netmiko_platform=args.platform,
            ignore_visited=args.ignore_visited,
            clean=args.clean,
            )
        log('##### Recursive Run Complete #####', proc=proc, v=logging.H)
       
    elif args.single: 
        log('##### Starting Single Run #####', proc=proc, v=logging.H)
        single_scan(
            target= args.host,
            netmiko_platform=args.platform,
            )
        log('##### Single Run Complete #####', proc=proc, v=logging.H)
    

if __name__ == '__main__':
    main()