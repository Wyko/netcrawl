|Build Status| |Coverage Status| |Documentation Status|

========
NetCrawl
========
---------------------------------------
Network Information Gathering Made Easy
---------------------------------------


Netcrawl is a tool designed to discover and poll one or more devices,
inventory them, and then provide useful data on the processed devices.

The full documentation can be found in the `NetCrawl ReadTheDocs`_ site


Features
--------

-  **Switchport Tracing**: Discover which devices and interfaces have seen a
   particular MAC
-  **Wireless Audit**: Discovers likely matches for rogue wireless devices
   among physically connected devices on a subnet
-  **MAC Audit**: Discover potential unauthorized switches on your network
-  SSH and Telnet connections to network devices
-  Automatically backs up device configurations
-  Stores a neighbor database to find layer two connection mappings
-  Auto-detect system type of newly discovered devices
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

Example
--------


Scan one host with no logging output
+++++++++++++++++++++++++++++++++++++

.. code-block:: console

    C:\netcrawl>run.py -sS -t 10.1.120.1 -v0

    Device Name:       my-device-dist-1
    Unique Name:       MY-DEVICE-DIST-1_EC032
    Management IP:     10.1.120.1
    First Serial:      Name: [Switch System], Desc: [WS-C4500X-32], Serialnum: [JAE14350G30]
    Serial Count:      28
    Dynamic MAC Count: 920
    Interface Count:   88
    Neighbor Count:    22
    Config Size:       26573

    +---------------------------+------------------------+----------------------+-------------+
    | Neighbor Name             | Source Interface       | Platform             | IP Address  |
    +---------------------------+------------------------+----------------------+-------------+
    | DVCOPS-MIS-1              | TenGigabitEthernet1/1  | cisco WS-C3750-48P   | 10.1.220.11 |
    | DVCOPS-MIS-2              | TenGigabitEthernet1/2  | cisco WS-C3750-48P   | 10.1.220.10 |
    | DVCOPS-sceast-sc01        | TenGigabitEthernet1/3  | cisco WS-C3850-48P   | 10.1.139.12 |
    | DVCOPS-sccent-sc01        | TenGigabitEthernet1/4  | cisco WS-C3850-48P   | 10.1.139.11 |
    | DVCOPS-dcgsc-sc01         | TenGigabitEthernet1/16 | cisco WS-C3850-48P   | 10.1.139.26 |
    | DVCOPS-wlcprm-vd01        | TenGigabitEthernet1/17 | AIR-CT5520-K9        | 10.1.139.51 |
    +---------------------------+------------------------+----------------------+-------------+


Locate a device on the network
+++++++++++++++++++++++++++++++    
 
.. code-block:: console
 
    C:\netcrawl>locate_mac.py 00FEC89232B0

    MAC:  00FEC89232B0
    Manufacturer:  Cisco ,  Cisco Systems, Inc
    +-----------------------+---------------------+-----------------------+
    | Device Name           | Interface           | CDP Neighbors         |
    +-----------------------+---------------------+-----------------------+
    | DVCOPSDS01            | Ethernet2/24        | DVCOPSMGT1            |
    | DVCOPSMGT1            | GigabitEthernet0/23 | None                  |
    | DVCOPS-mgmt-sd01      | FastEthernet1/0/39  | DVCOPSDS01            |
    +-----------------------+---------------------+-----------------------+
    
    
Built With
-----------

* Netmiko_ - SSH and Telnet connection manager
* Manuf_ - OUI lookup


Authors
--------

* **Wyko ter Haar** - *Initial work* - Wyko_
   

.. _`NetCrawl ReadTheDocs`: http://netcrawl.readthedocs.io/en/latest/
.. _Wyko: https://github.com/Wyko   
.. _Manuf: https://github.com/coolbho3k/manuf
.. _Netmiko: https://github.com/ktbyers/netmiko
.. _keyring: https://pypi.python.org/pypi/keyring
.. _cryptography: https://cryptography.io

.. |Build Status| image:: https://travis-ci.org/Wyko/netcrawl.svg?branch=development
   :target: https://travis-ci.org/Wyko/netcrawl
.. |Coverage Status| image:: https://coveralls.io/repos/github/Wyko/netcrawl/badge.svg?branch=development
   :target: https://coveralls.io/github/Wyko/netcrawl?branch=development
.. |Documentation Status| image:: https://readthedocs.org/projects/netcrawl/badge/?version=latest
   :target: http://netcrawl.readthedocs.io/en/latest/?badge=latest    
    

   
