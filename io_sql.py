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
        
        self.cur.execute('''SELECT count(id) from {};'''.format(table))
        return self.cur.fetchone()[0]


class pending_db(sql_writer):
    
    def __init__(self, dbname, drop= True):
        sql_writer.__init__(self, dbname)
        self.create_table(drop)
    
    def __len__(self):
        return sql_writer.count(self, 'Pending')
    
    def ip_exists(self, ip):
        return sql_writer.ip_exists(self, ip, 'Pending')
    
    def add_device_d(self, device_d= None, **kwargs):
        
        # Pending dict template
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
        
        try:
            self.db.execute('''
                INSERT INTO Pending  
                    (
                    ip,
                    name,
                    netmiko_platform,
                    system_platform,
                    source_interface,
                    neighbor_interface,
                    software,
                    raw_cdp,
                    updated
                    )
                VALUES 
                    (
                    '{ip}',
                    '{name}',
                    '{netmiko_platform}',
                    '{system_platform}',
                    '{source_interface}',
                    '{neighbor_interface}',
                    '{software}',
                    '{raw_cdp}',
                    '{updated}'
                    );
            '''.format(
                    ip= _device_d['ip'],
                    name= _device_d['name'],
                    netmiko_platform= _device_d['netmiko_platform'],
                    system_platform= _device_d['system_platform'],
                    source_interface= _device_d['source_interface'],
                    neighbor_interface= _device_d['neighbor_interface'],
                    software= _device_d['software'],
                    raw_cdp= _device_d['raw_cdp'],
                    updated = datetime.now().strftime(TIME_FORMAT),  
                ))
        except sqlite3.IntegrityError:
            log('Duplicate IP rejected: {}'.format(_device_d['ip']), 
                proc= 'pending_db.add_device_d', 
                v= util.D)
        else:
            log('Device added to pending: {}'.format(_device_d['ip']), 
                proc= 'pending_db.add_device_d', 
                v= util.N)
            self.db.commit()
    
    
    def add_device_nd(self, _device= None, _list= []):
        """Appends a device or a list of devices to the database
        
        Optional Args:
            _device (network_device): A single device 
            _list (List): List of devices
            
        Returns:
            Boolean: True if write was successful, False otherwise.
        """
        
        log('Starting to add devices to database', proc= 'pending_db.add_device_nd',
            v= util.N)
        
        # If a single device was passed, add it to the list
        if _device: _list.append(_device)
        
        # Return an error if no data was passed
        if not _list: 
            log('No devices to add', proc= 'pending_db.add_device_nd', v= util.A)
            return False
        
        
        for device in _list:
            for neighbor in device.neighbors:           
                # Throw out all of the devices whose platform is not recognized  
                if not neighbor['netmiko_platform']: 
                    log('Neighbor %s:%s rejected due to platform.' % (
                        neighbor['ip'], 
                        neighbor['system_platform']), 
                        proc='process_pending_list',
                        print_out=False,
                        v= util.ALERT
                        ) 
                    continue
                
                # Check if the ip is a known address.
                # If not, add it to the list of ips to check
                if not self.ip_exists(neighbor['ip'], 'Visited'):
                    try:
                        self.cur.execute('''
                            INSERT INTO Pending  
                                (
                                ip,
                                name,
                                netmiko_platform,
                                system_platform,
                                source_interface,
                                neighbor_interface,
                                software,
                                raw_cdp,
                                updated
                                )
                            VALUES 
                                (
                                '{ip}',
                                '{name}',
                                '{netmiko_platform}',
                                '{system_platform}',
                                '{source_interface}',
                                '{neighbor_interface}',
                                '{software}',
                                '{raw_cdp}',
                                '{updated}'
                                );
                        '''.format(
                                ip= neighbor['ip'],
                                name= neighbor['name'],
                                netmiko_platform= neighbor['netmiko_platform'],
                                system_platform= neighbor['system_platform'],
                                source_interface= neighbor['source_interface'],
                                neighbor_interface= neighbor['neighbor_interface'],
                                software= neighbor['software'],
                                raw_cdp= neighbor['raw_cdp'],
                                updated = datetime.now().strftime(TIME_FORMAT),  
                            ))
                    except sqlite3.IntegrityError:
                        log('Duplicate IP rejected: {}'.format(ip), 
                            proc= 'pending_db.add_device_nd', 
                            v= util.D)
                        continue
                    
        self.db.commit()
        return True

    
    
    def create_table(self, drop= True):
        
        if drop: self.db.execute('DROP TABLE IF EXISTS Pending;')
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS Pending(
            id                 INTEGER PRIMARY KEY, 
            ip                 TEXT NOT NULL UNIQUE,
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


    def get_next(self):
        self.cur.execute('SELECT * FROM Pending ORDER BY id ASC LIMIT 1')
        output = self.cur.fetchone()
        
        if output:
            self.cur.execute('DELETE FROM Pending WHERE id=?', (output['id'],))
            self.db.commit()
           
        return dict(output)
        

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
            
        except sqlite3.IntegrityError:
            log('Duplicate IP rejected: {}'.format(_device_d['ip']), 
                proc= 'visited_db.add_device_d', 
                v= util.D)
        else:
            log('Device added to visiting: {}'.format(_device_d['ip']), 
                proc= 'visited_db.add_device_d', 
                v= util.N)
            self.db.commit()
    
    
    
    def add_device_nd(self, _device= None, _list= []):
        """Appends a device or a list of devices to the database
        
        Optional Args:
            _device (network_device): A single network_device
            _list (List): List of network_device objects
            
        Returns:
            Boolean: True if write was successful, False otherwise.
        """ 
        
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
                except sqlite3.IntegrityError:
                    log('Duplicate IP rejected: {}'.format(ip), 
                        proc= 'visited_db.add_device_nd', 
                        v= util.D)
                    continue
                
        
        self.db.commit()
        log('Added {} devices to visited table'.format(len(_list)), 
            proc= 'visited_db.add_device_nd',
            v= util.N)
        return True
    
    
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
            

    