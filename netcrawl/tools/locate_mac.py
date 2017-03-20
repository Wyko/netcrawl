'''
netcrawl.tools.mac_trace -- Lists the devices and ports that the specified MAC was seen on

@author:     Wyko ter Haar
@license:    MIT
@contact:    vegaswyko@gmail.com
'''

import sys
import os

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

from prettytable import PrettyTable

from netcrawl import config, util
from netcrawl.io_sql import device_db
from netcrawl.tools.manuf.manuf import MacParser
import textwrap

__version__ = 0.1
__date__ = '2017-03-20'
__updated__ = '2017-03-20'

DEBUG = 1


def locate(macs):
    ddb= device_db()
    mp = MacParser()
    
    # If just one mac was passed, make sure it works
    if not isinstance(macs, list):
        macs= [macs]
    
    for mac in macs:
        
        
        t = PrettyTable(['Device Name', 'Interface', 'CDP Neighbors'])
        t.align = 'l'
        
        print('MAC: ', mac)
        
        # Normalize the MAC
        mac = util.ucase_letters(mac)
        
        manuf= mp.get_manuf(mac)
        comment= mp.get_comment(mac)
        print('Manufacturer: ', manuf, ', ', comment)
        
        locations= ddb.locate_mac(mac)
        if len(locations) == 0:
            print('No matches found')
        else:
            for match in locations: t.add_row(match)
            print(t, '\n')
        
        
    


def main(argv=None): # IGNORE:C0111
    '''Command line options.'''
    
    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)
    
    config.parse_config()
    
    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = str(__updated__)
    program_version_message = '%%(prog)s %s (%s)' % (program_version, program_build_date)
    program_shortdesc = __import__('__main__').__doc__.split("\n")[1]
    program_license = textwrap.dedent('''\
            %s
            
            Created by Wyko ter Haar on %s.
            
            Licensed under the MIT License
            
            Distributed on an "AS IS" basis without warranties
            or conditions of any kind, either express or implied.
        ''' % (program_shortdesc, str(__date__)))

    try:
        # Setup argument parser
        parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-v", "--verbose", dest="verbose", action="count", help="set verbosity level [default: %(default)s]")
        parser.add_argument(dest="macs", help="MAC addresses to locate", metavar="MACs", nargs='+')

        # Process arguments
        args = parser.parse_args()

        config.set_verbosity(args.verbose)
        
        locate(args.macs)

    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
    except Exception as e:
        if DEBUG:
            raise(e)
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2

if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-v")
    sys.exit(main())