# netcrawl

This package is designed to facilitate crawling a network for information on connected devices.

This package is still in development.

## Usage

```
NetCrawl [-h] [-v LEVEL] [-r] [-c] [-sd] [-sR | -sS | -sN] [-t TARGET] [-p PLATFORM]

This package will process a specified host and pull information from it. 
If desired, it can then crawl the device's neighbors recursively and continue the process.

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
  -r, --resume          Resume the last scan, if one was interrupted midway. Omitting
                            this argument is not the same as using -c; Previous database
                            entries are maintained. Scan starts with the seed device. All
                            neighbor entries marked pending are reset.
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
                        Hostname or IP address of the starting device
  -p PLATFORM           The Netmiko platform for the device
```

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

Download [Netmiko](https://github.com/ktbyers/netmiko)

```pip3 install Netmiko```

Download and install [Nmap](https://nmap.org)

```pip install nmap```

Download and install [keyring](https://pypi.python.org/pypi/keyring). On Linux, additional packages are required ([see documentation here](https://github.com/mitya57/secretstorage))

``` pip install keyring```

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
