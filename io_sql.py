from datetime import datetime
from gvars import TIME_FORMAT
from util import log
import sqlite3
import util



class sql_writer():
    def __init__(self, dbname, **kwargs):
        self.db = sqlite3.connect(dbname)  # @UndefinedVariable
        self.db.row_factory = sqlite3.Row  # @UndefinedVariable
        self.cur = self.db.cursor()
        
        # Create the tables in each database, overwriting if needed
        if kwargs and ('clean' in kwargs) and kwargs['clean']:
            self.create_table(drop= kwargs['clean'])
        else: self.create_table()
        
    
    def close(self):
        if self.db: self.db.close()


    def ip_exists(self, ip, table):
        '''Check if a given IP exists in the database'''
        
        self.cur.execute('''
            select exists 
            (select * from {} where ip='{}' limit 1);'''.format(table, ip))
        output = self.cur.fetchone()
        
        if output and output[0] == 1: return True
        else: return False
        
        
    def count(self, table):
        '''Counts the number of rows in the table'''

        self.cur.execute('SELECT count(id) from {};'.format(table) )
        return self.cur.fetchone()[0]


    def last_id(self, table):
        '''Get the next entry ID in the table. Make sure a valid ID was 
        returned and then increment by one.
        '''
        
        # Get the last row number in the table
        self.cur.execute('select seq from sqlite_sequence where name="{}";'.format(table))
        _id = self.cur.fetchone()
        
        # If it was returned, increment by one
        if _id and _id[0]: 
            log('Last entry placed at id {} in {}'.format(_id[0], table),
                proc= 'sql_writer.last_id', v= util.D)
            return int(_id[0])
        else: 
            log('No valid ID returned in table: {}'.format(table), 
                proc= 'sql_writer.last_id', v= util.C)
            return None
        


class neighbor_db(sql_writer):
    TABLE_NAME = 'Neighbor'
    
    def __init__(self, dbname, **kwargs):
        sql_writer.__init__(self, dbname, **kwargs)
        
        # If not resuming, then set everything as not pending or working
        if kwargs and ('resume' in kwargs) and (kwargs['resume'] == False):
            self.cur.execute('''
                UPDATE Neighbor 
                SET
                    pending= 0,
                    working= 0
            ''')

    
    def __len__(self):
        return sql_writer.count(self, self.TABLE_NAME)
    
    def ip_exists(self, ip):
        return sql_writer.ip_exists(self, ip, self.TABLE_NAME)
    
    def count_pending(self):
        '''Counts the number of rows in the table'''
        self.cur.execute('SELECT count(id) from Neighbor WHERE pending=1;')
        return self.cur.fetchone()[0]
    
    
    def set_processed(self, _id):
        # Set the entry as not being worked on and not pending
        self.cur.execute('''
            UPDATE Neighbor SET 
                pending= 0,
                working= 0
            WHERE
                id = ?
            ''', (_id, ))
        self.db.commit()
        
    
    def get_next(self):
        self.cur.execute('''
            SELECT * FROM 
                Neighbor 
            WHERE 
                pending= 1 AND
                working= 0 
            ORDER BY id ASC LIMIT 1
            ''')
            
        output = self.cur.fetchone()
        
        if output:
            
            # Mark the new entry as being worked on 
            self.cur.execute('UPDATE Neighbor SET working=1 WHERE id=?', (output['id'],))
            self.db.commit()
            return dict(output)
        
        else:
            return None
    
    
    def add_device_d(self, device_d= None, **kwargs):
        
        # Neighbor dict template
        _device_d = {
            'name': None,
            'ip': None,
            'connect_ip': None,
            'netmiko_platform': None,
            'system_platform': None,
            'source_interface': None,
            'neighbor_interface': None,
            'software': None,
            'raw_cdp': None,
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
            id                 INTEGER PRIMARY KEY AUTOINCREMENT, 
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
    
    def __init__(self, dbname, **kwargs):
        sql_writer.__init__(self, dbname, **kwargs)
    
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
            id         INTEGER PRIMARY KEY AUTOINCREMENT, 
            ip         TEXT NOT NULL UNIQUE,
            name       TEXT,
            serial     TEXT,
            updated    TEXT
            );
            ''')
            

    

class device_db(sql_writer):
    TABLE_NAME = 'Devices'
    
    def __init__(self, dbname, **kwargs):
        sql_writer.__init__(self, dbname, **kwargs)
        self.cur.execute('PRAGMA foreign_keys = ON;')
        self.db.commit()
        
        
    
    def __len__(self):
        return sql_writer.count(self, self.TABLE_NAME)
    
    def ip_exists(self, ip):
        return sql_writer.ip_exists(self, ip, self.TABLE_NAME)
    
    def add_device_nd(self, _device= None, _list= None):
        """Appends a device or a list of devices to the database
        
        Optional Args:
            _device (network_device): A single network_device
            _list (List): List of network_device objects
            
        Returns:
            Boolean: True if write was successful, False otherwise.
        """ 
        
        # Return an error if no data was passed    
        if not (_list or _device): 
            log('No devices to add', proc= 'device_db.add_device_nd', v= util.A)
            return False
        
        if not _list: _list= []
        
        log('Starting to add device to table', proc= 'device_db.add_device_nd', v= util.N)
        
        # If a single device was passed, add it for group processing
        if _device: _list.append(_device)
        
        # Process each device
        for _device in _list:
            
            # Add the device into the database
            self.cur.execute('''
                INSERT INTO Devices (
                    name,
                    unique_name,
                    netmiko_platform,
                    system_platform,
                    software,
                    raw_cdp,
                    raw_config,
                    updated,
                    failed,
                    failed_msg,
                    TCP_22,
                    TCP_23,
                    AD_enabled,
                    accessible,
                    cred,
                    updated
                    )
                VALUES (
                    :name,
                    :unique_name,
                    :netmiko_platform,
                    :system_platform,
                    :software,
                    :raw_cdp,
                    :raw_config,
                    :updated,
                    :failed,
                    :failed_msg,
                    :TCP_22,
                    :TCP_23,
                    :AD_enabled,
                    :accessible,
                    :cred,
                    :updated
                    );''',
                {
                    'name': _device.device_name,
                    'unique_name': _device.unique_name(),
                    'netmiko_platform': _device.netmiko_platform,
                    'system_platform': _device.system_platform,
                    'software': _device.software,
                    'raw_cdp': _device.raw_cdp,
                    'raw_config': _device.config,
                    'failed': int(_device.failed),
                    'failed_msg': _device.failed_msg,
                    'TCP_22': _device.TCP_22,
                    'TCP_23': _device.TCP_23,
                    'AD_enabled': _device.AD_enabled,
                    'accessible': _device.accessible,
                    'cred': str(_device.cred),
                    'updated': datetime.now().strftime(TIME_FORMAT)
                    
                })
            device_id= sql_writer.last_id(self, 'Devices')
            
            for interf in _device.interfaces:
                
                self.cur.execute('''
                    INSERT INTO Interfaces (
                        parent,
                        name,
                        type,
                        ip,
                        subnet,
                        virtual_ip,
                        description
                        )
                    VALUES (
                        :parent,
                        :name,
                        :type,
                        :ip,
                        :subnet,
                        :virtual_ip,
                        :description
                        );''',
                    {
                    'parent': device_id,
                    'name': interf.interface_name,
                    'type': interf.type(),
                    'ip': interf.interface_ip,
                    'subnet': interf.interface_subnet,
                    'virtual_ip': interf.virtual_ip,
                    'description': interf.interface_description
                    })
                interf_id= sql_writer.last_id(self, 'Interfaces')
                    
                
        self.db.commit()
        return True
    
     
    
    
    def create_table(self, drop= True):
        
        if drop: self.db.executescript('''
            DROP TABLE IF EXISTS MAC;
            DROP TABLE IF EXISTS Interfaces;
            DROP TABLE IF EXISTS Serials;
            DROP TABLE IF EXISTS Neighbors;
            DROP TABLE IF EXISTS Devices;
            ''')

        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS Devices(
                id                 INTEGER PRIMARY KEY AUTOINCREMENT, 
                name               TEXT,
                unique_name        TEXT,
                netmiko_platform   TEXT,
                system_platform    TEXT,
                software           TEXT,
                raw_cdp            TEXT,
                raw_config         TEXT,
                failed             BOOLEAN,
                failed_msg         TEXT,
                TCP_22             BOOLEAN,
                TCP_23             BOOLEAN,
                AD_enabled         BOOLEAN,
                accessible         BOOLEAN,
                cred               TEXT,
                updated            TEXT
            );
            
            CREATE TABLE IF NOT EXISTS Interfaces(
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                parent             INTEGER NOT NULL,
                name               TEXT NOT NULL,
                type               TEXT,
                ip                 TEXT,
                subnet             TEXT,
                virtual_ip         TEXT,
                description        TEXT,
                FOREIGN KEY(parent) REFERENCES Devices(id)
            );

            CREATE TABLE IF NOT EXISTS MAC(
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                interface          INTEGER NOT NULL,
                address            TEXT NOT NULL,
                FOREIGN KEY(interface) REFERENCES Interfaces(id)
            );
            
             CREATE TABLE IF NOT EXISTS Serials(
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                parent             INTEGER NOT NULL,
                serial             TEXT NOT NULL UNIQUE,
                name               TEXT,
                description        TEXT,
                FOREIGN KEY(parent) REFERENCES Devices(id)
            );
            
            CREATE TABLE IF NOT EXISTS Neighbors(
                id                 INTEGER PRIMARY KEY AUTOINCREMENT, 
                ip                 TEXT NOT NULL,
                parent             INTEGER NOT NULL,
                pending            INTEGER NOT NULL,
                working            INTEGER NOT NULL,
                name               TEXT,
                netmiko_platform   TEXT,
                system_platform    TEXT,
                source_interface   TEXT,
                neighbor_interface TEXT,
                software           TEXT,
                raw_cdp            TEXT,
                updated            TEXT,
                FOREIGN KEY(parent) REFERENCES Devices(id)
            );       
            ''')
        self.db.commit()


