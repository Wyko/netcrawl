===============
Installation
===============

These instructions will help install Netcrawl in your environment.


Netcrawl
=============

.. code-block:: console

    pip install -U netcrawl


PostgreSQL
==============

1. Download and install `PostgreSQL <https://www.postgresql.org/>`_
2. Set up the :code:`main` and :code:`inventory` databases. If these are not created netcrawl will attempt to create them automatically.


Credentials
===============

Add device and database credentials to the credential vault using :code:`netcrawl -m`
   

Nmap
========

Installing this will permit you to be able to use the -sN function.

- `Nmap <https://nmap.org>`_ - Manually download and install
- `python-nmap <http://xael.org/pages/python-nmap-en.html>`_ - Python insterface for Nmap


Testing
==========

.. code-block:: console
    
    pip install Faker pytest
