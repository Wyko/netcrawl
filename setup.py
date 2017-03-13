import os

from setuptools import setup


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "netcrawl",
    version = "0.3.0-beta",
    author = "Wyko ter Haar",
    author_email = "vegaswyko@gmail.com",
    description = ("Netcrawl is a network discovery tool designed to poll one or more devices, inventory them, and then continue the process through the device's neighbors."),
    license = "MIT",
    keywords = "cisco cdp network",
    url = "https://github.com/Wyko/wylog",
    packages=['netcrawl',
              'netcrawl.credentials',
              'netcrawl.devices',
              'netcrawl.tools',
              'tests'
			 ],
    long_description= read('README'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
    ],
)