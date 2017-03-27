==========================
Dependencies
==========================

-----------------
netmiko_
-----------------

- Provides core SSH and Telnet connection functionality
- **Minimum Version Required**: 1.3.0


----------------------------
psycopg2_
----------------------------

- A package to interact with the PostgreSQL backend

--------------------
cryptography_
--------------------

- Encrypts the database and device logon credentials

-------------------
keyring_
-------------------

- Stores the encryption key

.. note::

    Linux users may have to install keyring with added consideration.
    Please see `Running keyring on Linux`_.
    To ease this you can install the `keyrings.alt`_ package, but that
    has possible security implications. Use at your discretion.
    
- python-nmap
- netaddr
- prettytable    
    
.. _psycopg2: http://initd.org/psycopg/docs/index.html    
.. _`keyrings.alt`: https://pypi.python.org/pypi/keyrings.alt
.. _netmiko: https://github.com/ktbyers/netmiko
.. _cryptography: https://cryptography.io
.. _keyring: https://pypi.python`Running keyring on linux`_
.. _`Running keyring on linux`: https://pypi.python.org/pypi/keyring#using-keyring-on-headless-linux-systems