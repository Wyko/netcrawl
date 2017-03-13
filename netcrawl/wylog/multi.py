'''
Created on Mar 4, 2017

@author: Wyko
'''

from multiprocessing import Lock

from . import log, logging


class logged_lock():
    '''This is a wrapper around the Multiprocessing Lock 
    class that includes some logging.'''
    
    def __call__(self, proc):
        self.proc= proc
        return self 
    
    def __init__(self, name):
        self.lock= Lock()
        self.name = name
        
    def __enter__(self):
        log('Acquiring lock [{}]'.format(self.name), proc= self.proc, v= logging.D)
        self.lock.acquire()
        log('Got lock [{}]'.format(self.name), proc= self.proc, v= logging.D)
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.lock.release()
        log('Released lock [{}]'.format(self.name), proc= self.proc, v= logging.D)