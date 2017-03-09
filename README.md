# netcrawl

This package is designed to facilitate crawling a network for information on connected devices.

This package is still in development.

## Usage

```
usage: NetCrawl [-h] [-v LEVEL] [-i] [-u] [-d] [-c] [-sd] [-sR | -sS | -sN]
                [-t TARGET] [-p PLATFORM]

Netcrawl is a network discovery tool designed to poll one or
more devices, inventory them in a SQL database, and then
continue the process through the device's neighbors. It offers
integration with Nmap to discover un-connected hosts.

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
```

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

### Required
* *[Netmiko](https://github.com/ktbyers/netmiko)* - Any version that has the autodetect functionality.
* *psycopg2* - PostgreSQL package
* *[keyring](https://pypi.python.org/pypi/keyring)*
** [Running `keyring` on linux](https://pypi.python.org/pypi/keyring#using-keyring-on-ubuntu-16-04)

`pip install keyring psycopg2 git+git://github.com/ktbyers/netmiko.git@1bdde6bee64d596209be9e0ed0b189d8b58a0711`

### Optional
* *[Nmap](https://nmap.org)* - Manually download and install
* *[python-nmap](http://xael.org/pages/python-nmap-en.html)* - for scanning function

`pip install python-nmap`


## Overview


### File Structure

#### log.txt

This is the operational log.
* Timestamp
* Process
* Log Message
* IP Address

```
2017-02-02 23:05:27, get_raw_cdp_output       , # Enable successful on attempt 1. Current delay: 1, 10.1.103.3
```


## Built With

* [Netmiko](https://github.com/ktbyers/netmiko) - SSH and Telnet connection manager

## Authors

* **Wyko ter Haar** - *Initial work* - [Wyko](https://github.com/Wyko)
