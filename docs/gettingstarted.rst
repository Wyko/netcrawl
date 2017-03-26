===============
Getting Started
===============

These instructions will get you a copy of the project up and running on your local machine.

Dependencies
============
* *[Netmiko](https://github.com/ktbyers/netmiko)* - Any version that has the autodetect functionality.
* *psycopg2* - PostgreSQL package
* *[cryptography](https://cryptography.io)*
* *[keyring](https://pypi.python.org/pypi/keyring)*
  * [Running `keyring` on linux](https://pypi.python.org/pypi/keyring#using-keyring-on-ubuntu-16-04)

### Manual Install
* *[PostgreSQL](https://www.postgresql.org/)*

### Optional - Nmap
Without installing this, you will not be able to use the -sN function.

* *[Nmap](https://nmap.org)* - Manually download and install
* *[python-nmap](http://xael.org/pages/python-nmap-en.html)* - for scanning function


### Testing

`pip install Faker pytest`

## Installation

1. Run `pip install -U netcrawl`
2. Install Postgresql and set up the **main** and **inventory** databases. If these are not created netcrawl will attempt to create them automatically.
3. Follow any additional directions as needed to install `keyring` on your platform
4. Add device and database credentials using `netcrawl -m`

Usage
=====

.. argparse::
   :module: netcrawl.core
   :func: make_parser
   :prog: NetCrawl
   :nodefault:
   
   

Add new credentials
+++++++++++++++++++

.. code-block:: console

    netcrawl -m

Recursive Scan
++++++++++++++++

This will inventory all devices from a seed device, skipping any neighbors who's 
CDP hostname matches that of a previously attempted (successful or not) device.

.. code-block:: console

    netcrawl -sR --skip-named-duplicates -t 10.1.1.1

Discover a network segment using Nmap
+++++++++++++++++++++++++++++++++++++++

.. code-block:: console

    netcrawl -sN -t 10.0-10.0-254.1    