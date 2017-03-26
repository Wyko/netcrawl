|Build Status| |Coverage Status| |Documentation Status|

netcrawl
========

Netcrawl is a tool designed to discover and poll one or more devices,
inventory them, and then provide useful data on the processed devices.

This package is still in development.

Features
--------

-  Switchport Tracing: Discover which devices and interfaces have seen a
   particular MAC
-  Wireless Audit: Discovers likely matches for rogue wireless devices
   among physically connected devices on a subnet
-  MAC Audit: Discover potential unauthorized switches on your network
-  Automatically backs up device configurations
-  Stores a neighbor database to find layer two connection mappings
-  Multiple ways to auto-detect system type of newly discovered devices
-  Works with Nmap to allow for discovery of both neighboring and
   seperated devices
-  Securely stores credentials using `keyring`_ and `cryptography`_
-  Can use multiple credentials in case the first fails
-  Stores device inventory using a PostgreSQL database
-  Offers a single device scan to quickly get data on one device
-  Concurrently runs multiple subprocesses to quickly scan devices
-  Multiple ``netcrawl`` top-level processes can run concurrently to
   scan different network segments (do not use ``-c`` while doing this),
   or to run an Nmap scan and inventory hosts as they are discovered.

Usage
-----
::
	usage: NetCrawl [-h] [-v LEVEL] [-m] [-i] [-u] [-d] [-c] [-sd] [-sR] [-sS]
	                [-sN] [-t TARGET] [-p PLATFORM]
	
	optional arguments:
	  -h, --help            show this help message and exit
	
	Options:
	  -v LEVEL              Verbosity level. Logs with less importance than
	                            the global verbosity level will not be processed.
	                            1: Critical alerts
	                            2: Non-critical alerts
	                            3: High level info
	                            4: Normal level
	                            5: Informational level
	                            6: Debug level info (All info)
	  -i, --ignore          Do not resume the last scan if one was interrupted midway. Omitting
	                            this argument is not the same as using -c; Previous device database
	                            entries are maintained, but all visited entries are removed.
	  -u, --update          Iterates through all previously-found devices and scans them again.
	                            This implies the --ignore flag in that it also removes previous
	                            visited entries.
	  -d, --debug           Enables debug messages. If this is not specified, a Verbosity level
	                            of 5 or greater has no effect since those messages will be
	                            ignored anyway. If Debug is enabled and V is less than 5,
	                            debug messages will only be printed to the log file.
	  -c, --clean           Delete all existing database entries and rebuild the databases.
	  -sd, --skip-named-duplicates
	                        If a CDP entry has the same host name as a previously visited device, ignore it.
	
	Scan Type:
	  -m                    Credential management. Use as only argument.
	  -sR, --recursive      Recursively scan neighbors for info. --target is not required,
	                            but if it is supplied then the device will be added as a
	                            scan target. Target will accept a single IP or hostname.
	  -sS, --single         Scan one seed device for info. --target is required.
	                            Target will accept a single IP or hostname.
	  -sN, --scan-network   Performs an NMAP scan against a specified target.
	                            --target is required. Target will accept a
	                            Nmap-compatible target identifier. Examples:
	                            10.1.1.1
	                            192.168.0-255.1
	
	Target Specification:
	  -t TARGET, --target TARGET
	                        Hostname or IP address of a starting device
	  -p PLATFORM           The Netmiko platform for the device

.. _keyring: https://pypi.python.org/pypi/keyring
.. _cryptography: https://cryptography.io

.. |Build Status| image:: https://travis-ci.org/Wyko/netcrawl.svg?branch=development
   :target: https://travis-ci.org/Wyko/netcrawl
.. |Coverage Status| image:: https://coveralls.io/repos/github/Wyko/netcrawl/badge.svg?branch=development
   :target: https://coveralls.io/github/Wyko/netcrawl?branch=development
.. |Documentation Status| image:: https://readthedocs.org/projects/netcrawl/badge/?version=latest
   :target: http://netcrawl.readthedocs.io/en/latest/?badge=latest