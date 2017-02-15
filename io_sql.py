from datetime import datetime
from global_vars import RUN_PATH, TIME_FORMAT, TIME_FORMAT_FILE
from util import log

import sqlite3
import util



class sql_writer():
    def __init__(self, dbname):
        self.db = sqlite3.connect(dbname)  # @UndefinedVariable
        self.db.row_factory = sqlite3.Row  # @UndefinedVariable
        self.cur = self.db.cursor()
#         self.cur.execute('''PRAGMA foreign_keys = ON;''')
    
    def close(self):
        if self.db: self.db.close()


    def ip_exists(self, ip, table):
        '''Check if a given IP exists in the database'''
        
        self.cur.execute('''select exists 
            (select * from {} where ip='{}' limit 1);'''.format(table, ip))
        output = self.cur.fetchone()
        
        if output and output[0] == 1: return True
        else: return False
        
        
    def count(self, table):
        '''Counts the number of rows in the table'''

        self.cur.execute('SELECT count(id) from {};'.format(table) )
        return self.cur.fetchone()[0]



class neighbor_db(sql_writer):
    TABLE_NAME = 'Neighbor'
    
    def __init__(self, dbname, drop= True):
        sql_writer.__init__(self, dbname)
        self.create_table(drop)
    
    def __len__(self):
        return sql_writer.count(self, self.TABLE_NAME)
    
    def ip_exists(self, ip):
        return sql_writer.ip_exists(self, ip, self.TABLE_NAME)
    
    def count_pending(self):
        '''Counts the number of rows in the table'''
        self.cur.execute('SELECT count(id) from Neighbor WHERE pending=1;')
        return self.cur.fetchone()[0]
    
    def get_next(self):
        self.cur.execute('SELECT * FROM Neighbor WHERE pending=1 ORDER BY id ASC LIMIT 1')
        output = self.cur.fetchone()
        
        if output:
            self.cur.execute('UPDATE Neighbor SET pending=0 WHERE id=?', (output['id'],))
            self.db.commit()
            return dict(output)
        
        else:
            return None
    
    def add_device_d(self, device_d= None, **kwargs):
        
        # Neighbor dict template
        _device_d = {
            'name': '',
            'ip': '',
            'management_ip': '',
            'netmiko_platform': '',
            'system_platform': '',
            'source_interface': '',
            'neighbor_interface': '',
            'software': '',
            'raw_cdp': '',
            }
        
        # If a dict was supplied, add values from it into the template
        if device_d:
            for key, value in device_d.items():
                _device_d[key] = value 
        
        # If the function was passed with keyword args instead
        elif kwargs:
            # Template for the seed device
            for key, value in kwargs.items():
                _device_d[key] = value
        
        else: return False
        
        # Break if no IP address was supplied
        if not _device_d['ip']: return False
        
        # If the device is an unvisited recognized device, mark it as pending
        if _device_d['netmiko_platform'] and not sql_writer.ip_exists(
            self, ip= _device_d['ip'], table= 'Visited'): 
            
            pending = 1
        else: pending = 0
        
        try:
            self.cur.execute('''
                INSERT INTO Neighbor  
                    (
                    working,
                    ip,
                    name,
                    pending,
                    netmiko_platform,
                    system_platform,
                    source_interface,
                    neighbor_interface,
                    software,
                    raw_cdp,
                    updated
                    )
                VALUES 
                    (0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ;''',
                (
                _device_d['ip'],
                _device_d['name'],
                pending,
                _device_d['netmiko_platform'],
                _device_d['system_platform'],
                _device_d['source_interface'],
                _device_d['neighbor_interface'],
                _device_d['software'],
                _device_d['raw_cdp'],
                datetime.now().strftime(TIME_FORMAT),  
                ))
            
        except sqlite3.IntegrityError as e:  # @UndefinedVariable
            log('Duplicate IP rejected: {}'.format(_device_d['ip']), 
                proc= 'neighbor_db.add_device_d', error= e, 
                v= util.D)
            return False
        
        else:
            log('Device added to Neighbor table: {}'.format(_device_d['ip']), 
                proc= 'neighbor_db.add_device_d', 
                v= util.D)
            self.db.commit()
    
    
    def add_device_neighbors(self, _device= None, _list= None):
        """Appends a device or a list of devices to the database
        
        Optional Args:
            _device (network_device): A single device 
            _list (List): List of devices
            
        Returns:
            Boolean: True if write was successful, False otherwise.
        """
        if not _list: _list= []
        
        log('Starting to add devices to database', proc= 'neighbor_db.add_device_neighbors',
            v= util.N)
        
        # If a single device was passed, add it to the list
        if _device: _list.append(_device)
        
        # Return an error if no data was passed
        if not _list: 
            log('No devices to add', proc= 'neighbor_db.add_device_neighbors', v= util.A)
            return False
        
        
        for device in _list:
            for neighbor in device.neighbors:           
                
                # Check if the ip is a known address.
                # If not, add it to the list of ips to check
                if not sql_writer.ip_exists(self, ip= neighbor['ip'], table= 'Visited'):
                    self.add_device_d(neighbor)
                    
                    
        self.db.commit()
        return True

    
    
    def create_table(self, drop= True):
        
        if drop: self.db.execute('DROP TABLE IF EXISTS Neighbor;')
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS Neighbor(
            id                 INTEGER PRIMARY KEY, 
            ip                 TEXT NOT NULL,
            pending            INTEGER NOT NULL,
            working            INTEGER NOT NULL,
            name               TEXT,
            netmiko_platform   TEXT,
            system_platform    TEXT,
            source_interface   TEXT,
            neighbor_interface TEXT,
            software           TEXT,
            raw_cdp            TEXT,
            updated            TEXT
            );
            ''')



        

class visited_db(sql_writer):
    
    def __init__(self, dbname, drop= True):
        sql_writer.__init__(self, dbname)
        self.create_table(drop)
    
    def __len__(self):
        return sql_writer.count(self, 'Visited')
    
    def ip_exists(self, ip):
        return sql_writer.ip_exists(self, ip, 'Visited')
    
    
    def add_device_d(self, device_d= None, **kwargs):
        
        _device_d = {
            'name': '',
            'ip': '',
            'serial': '',
            }
     
        # If a dict was supplied, add values from it into the template
        if device_d:
            for key, value in device_d.items():
                _device_d[key] = value 
        
        # If the function was passed with keyword args instead
        elif kwargs:
            # Template for the seed device
            for key, value in kwargs.items():
                _device_d[key] = value
        
        else: return False
        
        try:
            self.db.execute('''
                INSERT INTO Visited  
                    (
                    ip,
                    name,
                    serial,
                    updated
                    )
                VALUES 
                    (
                    '{ip}',
                    '{name}',
                    '{serial}',
                    '{updated}'
                    );
            '''.format(
                    ip= _device_d['ip'],
                    name= _device_d['name'],
                    serial= _device_d['serial'],
                    updated = datetime.now().strftime(TIME_FORMAT),  
                ))
            
        except sqlite3.IntegrityError:  # @UndefinedVariable
            log('Duplicate IP rejected: {}'.format(_device_d['ip']), 
                proc= 'visited_db.add_device_d', 
                v= util.D)
        else:
            log('Device added to Visited table: {}'.format(_device_d['ip']), 
                proc= 'visited_db.add_device_d', 
                v= util.D)
            self.db.commit()
    
    
    
    def add_device_nd(self, _device= None, _list= None):
        """Appends a device or a list of devices to the database
        
        Optional Args:
            _device (network_device): A single network_device
            _list (List): List of network_device objects
            
        Returns:
            Boolean: True if write was successful, False otherwise.
        """ 
        if not _list: _list= []
        
        log('Starting to add devices to visited list', proc= 'visited_db.add_device_nd',
            v= util.N)
        
        # If a single device was passed, add it to the list so that we can
        # simplify the code later on
        if _device: _list.append(_device)
        
        # Return an error if no data was passed
        if not _list: 
            log('No devices to add', proc= 'visited_db.add_device_nd',
                v= util.A)
            return False
        
        # Process each device
        for _device in _list:
            
            # Get the IP's from the device 
            ip_list = _device.get_ips()
            log('{} has {} ip(s)'.format(_device.device_name, len(ip_list)), 
                proc='visited_db.add_device_nd', v= util.N)
            
            for ip in ip_list:
                
                try:
                    self.cur.execute('''
                        INSERT INTO Visited  
                            (
                            ip,
                            name,
                            serial,
                            updated
                            )
                        VALUES 
                            (
                            '{ip}',
                            '{name}',
                            '{serial}',
                            '{updated}'
                            );
                    '''.format(
                            ip= ip,
                            name= _device.device_name,
                            serial= _device.first_serial(),
                            updated= datetime.now().strftime(TIME_FORMAT)
                        ))
                except sqlite3.IntegrityError:  # @UndefinedVariable
                    log('Duplicate IP rejected: {}'.format(ip), 
                        proc= 'visited_db.add_device_nd', 
                        v= util.D)
                    continue
                
        
        self.db.commit()
        log('Added {} devices to visited table'.format(len(_list)), 
            proc= 'visited_db.add_device_nd',
            v= util.N)
        return True
    
    
    def count_unique(self):
        '''Counts the number of unique devices in the database'''
        self.cur.execute('''SELECT count(distinct Serial) from Visited''')
        return self.cur.fetchone()[0]
    
    
    def create_table(self, drop= True):
        
        if drop: self.db.execute('DROP TABLE IF EXISTS Visited;')
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS Visited(
            id         INTEGER PRIMARY KEY, 
            ip         TEXT NOT NULL UNIQUE,
            name       TEXT,
            serial     TEXT,
            updated    TEXT
            );
            ''')
            

    