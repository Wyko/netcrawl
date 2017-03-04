from datetime import datetime
from gvars import TIME_FORMAT
from wylog import log
from retrying import retry

import sqlite3, util

class sql_database():
    def __init__(self, dbname, **kwargs):
        self.db = sqlite3.connect(dbname, timeout=15)  # @UndefinedVariable
        self.db.row_factory = sqlite3.Row  # @UndefinedVariable
        self.cur = self.db.cursor()
        
#         self.cur.execute('PRAGMA journal_mode=wal')
        
        # Create the tables in each database, overwriting if needed
        clean= kwargs.get('clean', False)
        self.create_table(drop_tables= clean)
        
    
    def close(self):
        if self.db: self.db.close()
        
    


    def ip_exists(self, ip, table):
        '''Check if a given IP exists in the database'''
        if ip is None or table is None:
            raise ValueError('IP[{}] or Table[{]] missing'.format(
                ip, table))
        
        self.cur.execute('''
            select exists 
            (select * from {} where ip='{}' limit 1);'''.format(table, ip))
        output = self.cur.fetchone()
        
        if output and output[0] == 1: return True
        else: return False
        
        
    def ip_name_exists(self, ip, name, table):
        '''Check if a given IP OR Name exists in the database'''
        
        self.cur.execute('''
            select exists 
                (select * from {} 
                where 
                    ip='{}' 
                    OR 
                    device_name='{}'
                limit 1);'''.format(table, ip, name))
        output = self.cur.fetchone()
        
        if output and output[0] == 1: return True
        else: return False    
        
    
    def count(self, table):
        '''Counts the number of rows in the table'''
        proc= 'io_sql.count'
        self.cur.execute('SELECT count(id) from {};'.format(table) )
        return self.cur.fetchone()[0]


    def last_id(self, table):
        '''Get the next entry ID in the table. Make sure a valid ID was 
        returned and then increment by one.
        '''
        proc= 'io_sql.sql_database.last_id'
        # Get the last row number in the table
        self.cur.execute('select seq from sqlite_sequence where name="{}";'.format(table))
        _id = self.cur.fetchone()
        
        # If it was returned, increment by one
        if _id and _id[0]: 
            log('Last entry placed at id {} in {}'.format(_id[0], table),
                proc= proc, v= log.D)
            return int(_id[0])
        else: 
            log('No valid ID returned in table: {}'.format(table), 
                proc= proc, v= log.C)
            return None
        


class neighbor_db(sql_database):
    TABLE_NAME = 'Neighbor'
    
    retry_args= {'stop_max_delay': 60000, # Stop after 60 seconds
                 'wait_exponential_multiplier': 100, # Exponential backoff
                 'wait_exponential_max': 10000,
                 'retry_on_exception': ( # Only retry on this exception
                     lambda x: isinstance(x, sqlite3.OperationalError)
                     )
                 }
    
    def __init__(self, dbname, **kwargs):
        sql_database.__init__(self, dbname, **kwargs)
        proc= 'neighbor_db.__init__'
        
        self.resume = kwargs.get('resume', True)

        # If resuming, then set everything as not working
        if self.resume:
            self.cur.execute('''
                UPDATE Neighbor 
                SET
                    working= 0
            ''')
        else:
            # Otherwise, reset the working and pending tag
            self.cur.execute('''
                UPDATE Neighbor 
                SET
                    pending= 0,
                    working= 0
            ''')
        self.db.commit()

    
    def __len__(self):
        return sql_database.count(self, self.TABLE_NAME)
    
    def ip_exists(self, ip):
        return sql_database.ip_exists(self, ip, self.TABLE_NAME)
    
    def count_pending(self):
        '''Counts the number of rows in the table'''
        self.cur.execute('SELECT count(device_id) from Neighbor WHERE pending=1;')
        return self.cur.fetchone()[0]
    
    
    @retry(**retry_args)
    def set_processed(self, _id):
        proc= 'io_sql.set_processed'
        
        # Error checking
        assert isinstance(_id, int), (
            proc+ ': _id [{}] is not int'.format(type(_id)))
        
        # Set the entry as not being worked on and not pending
        result= self.cur.execute('''
            UPDATE Neighbor SET 
                pending= 0,
                working= 0
            WHERE
                device_id = ?
            ''', (_id, ))
        self.db.commit()
        
        
        
    @retry(**retry_args)
    def get_next(self):
        '''Returns the next pending neighbor entry as
        an appropriately inherited network_device.
        '''
        proc= 'neighbor_db.get_next'
        
        self.cur.execute('''
            SELECT * FROM 
                Neighbor 
            WHERE 
                pending= 1 AND
                working= 0 
            ORDER BY device_id ASC LIMIT 1
            ''')
            
        output = self.cur.fetchone()
        
        if output:
            
            # Mark the new entry as being worked on 
            self.cur.execute('UPDATE Neighbor SET working=1 WHERE device_id=?', (output['device_id'],))
            self.db.commit()
            output = dict(output)
            return output
        
        else: return None
    
    
    def add_device_d(self, device_d= None, **kwargs):
        proc= 'io_sql.neighbor_db.add_device_d'
        
        # Neighbor dict template
        _device_d = {
            'device_name': None,
            'ip': None,
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
        if _device_d['netmiko_platform'] and not sql_database.ip_exists(
                        self, ip= _device_d['ip'], table= 'Visited'): 
            pending = 1
        else: pending = 0
        
        try:
            self.cur.execute('''
                INSERT INTO Neighbor  
                    (
                    working,
                    ip,
                    device_name,
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
                    (0, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                ''',
                (
                _device_d['ip'],
                _device_d['device_name'],
                pending,
                _device_d['netmiko_platform'],
                _device_d['system_platform'],
                _device_d['source_interface'],
                _device_d['neighbor_interface'],
                _device_d['software'],
                _device_d['raw_cdp'],
                datetime.now().strftime(TIME_FORMAT),  
                ))
            self.db.commit()
            
        except sqlite3.IntegrityError as e:  # @UndefinedVariable
            log('Duplicate IP rejected: {}'.format(_device_d['ip']), 
                proc= proc, error= e, 
                v= log.D)
            return False
        
        else:
            log('Device added to Neighbor table: {}'.format(_device_d['ip']), 
                proc= proc, 
                v= log.D)
    
    
    def add_device_neighbors(self, _device= None, _list= None):
        """Appends a device or a list of devices to the database
        
        Optional Args:
            _device (network_device): A single device 
            _list (List): List of devices
            
        Returns:
            Boolean: True if write was successful, False otherwise.
        """
        proc= 'io_sql.neighbor_db.add_device_neighbors'
        if not _list: _list= []
        
        log('Adding neighbors to Neighbor table', proc= proc,
            v= log.N)
        
        # If a single device was passed, add it to the list
        if _device: _list.append(_device)
        
        # Return an error if no data was passed
        if not _list: 
            log('No devices to add', proc= proc, v= log.A)
            return False
        
        
        for device in _list:
            for neighbor in device.all_neighbors():           
                
                if (('ip' in neighbor) and 
                    (isinstance(neighbor['ip'], str))):
                
                    # Check if the ip is a known address.
                    # If not, add it to the list of ips to check
                    if not sql_database.ip_exists(self, ip= neighbor['ip'], table= 'Visited'):
                        self.add_device_d(neighbor)
                else:
                    log('Neighbor does not have a valid ip. Neighbor: [{}]'.format(
                        neighbor), proc= proc, v= log.A)
                    
        self.db.commit()
        return True


    
    def create_table(self, drop_tables= True):
        proc= 'neighbor_db.create_table'
        
        if drop_tables: self.db.execute('DROP TABLE IF EXISTS Neighbor;')
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS Neighbor(
            device_id          INTEGER PRIMARY KEY AUTOINCREMENT, 
            ip                 TEXT NOT NULL,
            pending            INTEGER NOT NULL,
            working            INTEGER NOT NULL,
            device_name        TEXT,
            netmiko_platform   TEXT,
            system_platform    TEXT,
            source_interface   TEXT,
            neighbor_interface TEXT,
            software           TEXT,
            raw_cdp            TEXT,
            updated            TEXT
            );
            ''')
        self.db.commit()


        

class visited_db(sql_database):
    TABLE_NAME= 'Visited'
    
    def __init__(self, dbname, **kwargs):
        sql_database.__init__(self, dbname, **kwargs)
    
    def __len__(self):
        return sql_database.count(self, self.TABLE_NAME)
    
    def ip_exists(self, ip):
        return sql_database.ip_exists(self, ip, self.TABLE_NAME)
    
    def ip_name_exists(self, ip, name):
        return sql_database.ip_name_exists(self, ip, name, self.TABLE_NAME)
    
    def add_device_d(self, device_d= None, **kwargs):
        proc= 'visited_db.add_device_d'
        
        _device_d = {
            'device_name': None,
            'ip': None,
            'serialnum': None,
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
        
        # Error check to make sure we at least have an IP address to add
        assert (('ip' in _device_d) and
                (_device_d['ip'] is not None)), proc+ 'No IP in [{}]'.format(_device_d)
        
        try:
            self.db.execute('''
                INSERT INTO Visited  
                    (
                    ip,
                    device_name,
                    serial,
                    updated
                    )
                VALUES 
                    (
                    '{ip}',
                    '{device_name}',
                    '{serial}',
                    '{updated}'
                    );
            '''.format(
                    ip= _device_d['ip'], # Must have an IP
                    device_name= _device_d.get('device_name', None),
                    serial= _device_d.get('serialnum', None),
                    updated = datetime.now().strftime(TIME_FORMAT),  
                ))
            self.db.commit()
        except sqlite3.IntegrityError:  # @UndefinedVariable
            log('Duplicate IP rejected: {}'.format(_device_d['ip']), 
                proc= 'visited_db.add_device_d', 
                v= log.D)
        else:
            log('Device added to Visited table: {}'.format(_device_d['ip']), 
                proc= 'visited_db.add_device_d', 
                v= log.D)
    
    
    
    def add_device_nd(self, _device= None, _list= None):
        """Appends a device or a list of devices to the database
        
        Optional Args:
            _device (network_device): A single network_device
            _list (List): List of network_device objects
            
        Returns:
            Boolean: True if write was successful, False otherwise.
        """ 
        if not _list: _list= []
        
        log('Adding device(s) to {} table.'.format(self.TABLE_NAME), 
            proc= 'visited_db.add_device_nd', v= log.N)
        
        # If a single device was passed, add it to the list so that we can
        # simplify the code later on
        if _device: _list.append(_device)
        
        # Return an error if no data was passed
        if not _list: 
            log('No devices to add', proc= 'visited_db.add_device_nd',
                v= log.A)
            return False
        
        # Process each device
        for _device in _list:
            
            # Get the IP's from the device 
            ip_list = _device.get_ips()
            log('{} has {} ip(s)'.format(_device.device_name, len(ip_list)), 
                proc='visited_db.add_device_nd', v= log.I)
            
            # For failed devices which couldn't be fully polled:
            if len(ip_list) ==0:
                self.cur.execute('''
                    INSERT INTO Visited  
                        (
                        device_name,
                        updated
                        )
                    VALUES 
                        (?, ?);
                    ''',
                    (_device.device_name,
                     datetime.now().strftime(TIME_FORMAT)
                    ))
            for ip in ip_list:
                
                try:
                    self.cur.execute('''
                        INSERT INTO Visited  
                            (
                            ip,
                            device_name,
                            serial,
                            updated
                            )
                        VALUES 
                            (
                            '{ip}',
                            '{device_name}',
                            '{serial}',
                            '{updated}'
                            );
                    '''.format(
                            ip= ip,
                            device_name= _device.device_name,
                            serial= _device.first_serial(),
                            updated= datetime.now().strftime(TIME_FORMAT)
                        ))
                except sqlite3.IntegrityError:  # @UndefinedVariable
                    log('Duplicate IP rejected: {}'.format(ip), 
                        proc= 'visited_db.add_device_nd', v= log.D)
                    continue
                
        
        self.db.commit()
        log('Added {} devices to visited table'.format(len(_list)), 
            proc= 'visited_db.add_device_nd', v= log.I)
        return True
    
    
    def count_unique(self):
        '''Counts the number of unique devices in the database'''
        self.cur.execute('''SELECT count(distinct Serial) from Visited''')
        return self.cur.fetchone()[0]
    
    
    def create_table(self, drop_tables= True):
        
        if drop_tables: self.db.execute('DROP TABLE IF EXISTS Visited;')
        self.db.execute('''
            CREATE TABLE IF NOT EXISTS Visited(
            id             INTEGER PRIMARY KEY AUTOINCREMENT, 
            ip             TEXT UNIQUE,
            device_name    TEXT,
            serial         TEXT,
            updated        TEXT
            );
            ''')
        self.db.commit()

    

class device_db(sql_database):
    TABLE_NAME = 'Devices'
    
    def __init__(self, dbname, **kwargs):
        sql_database.__init__(self, dbname, **kwargs)
        self.cur.execute('PRAGMA foreign_keys = ON;')
        self.db.commit()
        
        
    
    def __len__(self):
        return sql_database.count(self, self.TABLE_NAME)
    
    def ip_exists(self, ip):
        return sql_database.ip_exists(self, ip, self.TABLE_NAME)
    
    def add_device_nd(self, _device= None, _list= None):
        """Appends a device or a list of devices to the database
        
        Optional Args:
            _device (network_device): A single network_device
            _list (List): List of network_device objects
            
        Returns:
            Boolean: True if write was successful, False otherwise.
        """ 
        proc= 'io_sql.device_db.add_device_nd'
        
        # Return an error if no data was passed    
        if not (_list or _device): 
            log('No devices to add', proc= proc, v= log.A)
            return False
        
        if not _list: _list= []
        
        log('Adding device(s) to {} table'.format(self.TABLE_NAME), proc= proc, v= log.N)
        
        # If a single device was passed, add it for group processing
        if _device: _list.append(_device)
        
        # Process each device
        for _device in _list:
            device_id= self.insert_device_entry(_device)
            
            # Add all the device's serials
            for serial in _device.serial_numbers:
                self.insert_serial_entry(device_id, serial)
            
            # Add all of the device's interfaces            
            for interf in _device.interfaces:
                interface_id= self.insert_interface_entry(device_id, interf)
                
                # Add all the interface's mac addresses
                for mac_address in interf.mac_address_table:
                    mac_id= self.insert_mac_entry(device_id, interface_id, mac_address)
                
                # Add each neighbor that was matched to an interface
                for neighbor in interf.neighbors:
                    neighbor_id= self.insert_neighbor_entry(device_id, interface_id, neighbor)
                
            # Add each neighbor not matched to an interface
            for neighbor in _device.neighbors:
                neighbor_id= self.insert_neighbor_entry(device_id, None, neighbor)
                
        self.db.commit()
        return True
    
    
    def insert_device_entry(self, _device):
        # Trim the password
        _password= _device.credentials.get('password', None)
        if _password: _password= _password[:2]
       
        # Add the device into the database
        self.cur.execute('''
            INSERT INTO Devices (
                device_name,
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
                username,
                password,
                cred_type,
                updated
                )
            VALUES (
                :device_name,
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
                :username,
                :password,
                :cred_type,
                :updated
                );''',
            {
                'device_name': _device.device_name,
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
                'username': _device.credentials.get('user', None),
                'password': _password,
                'cred_type': _device.credentials.get('type', None),
                'updated': datetime.now().strftime(TIME_FORMAT)
                
            })
        self.db.commit()
        return sql_database.last_id(self, 'Devices')
    
    
    def insert_interface_entry(self, device_id, interf):
        self.cur.execute('''
            INSERT INTO Interfaces (
                device_id,
                interface_name,
                interface_type,
                interface_number,
                ip,
                subnet,
                virtual_ip,
                description,
                raw_interface,
                updated
                )
            VALUES (
                :device_id,
                :interface_name,
                :interface_type,
                :interface_number,
                :ip,
                :subnet,
                :virtual_ip,
                :description,
                :raw_interface,
                :updated
                );''',
            {
            'device_id': device_id,
            'interface_name': interf.interface_name,
            'interface_type': interf.interface_type,
            'interface_number': interf.interface_number,
            'ip': interf.interface_ip,
            'subnet': interf.interface_subnet,
            'virtual_ip': interf.virtual_ip,
            'description': interf.interface_description,
            'raw_interface': interf.raw_interface,
            'updated': datetime.now().strftime(TIME_FORMAT)
            })
        self.db.commit()
        return sql_database.last_id(self, 'Interfaces')
    
    
    def insert_serial_entry(self, device_id, serial):
        self.cur.execute('''
            INSERT INTO Serials (
                device_id,
                serialnum,
                name,
                description,
                productid,
                vendorid,
                updated
                )
            VALUES (
                :device_id,
                :serialnum,
                :name,
                :description,
                :productid,
                :vendorid,
                :updated
                );''',
            {
            'device_id': device_id,
            'serialnum': serial.get('serialnum', None),
            'name': serial.get('name', None),
            'description': serial.get('desc', None),
            'productid': serial.get('productid', None),
            'vendorid': serial.get('vendorid', None),
            'updated': datetime.now().strftime(TIME_FORMAT)
            })
        self.db.commit()
        return sql_database.last_id(self, 'Serials')
    
    
    def insert_neighbor_ip_entry(self, neighbor_id, ip):
        self.cur.execute('''
            INSERT INTO Neighbor_IPs
            (
                neighbor_id,
                ip,
                updated
            )
            VALUES
            (
                :neighbor_id,
                :ip,
                :updated
            );''',
            {
            'parent': neighbor_id,
            'ip': ip,
            'updated': datetime.now().strftime(TIME_FORMAT)
            })
        self.db.commit()
        return sql_database.last_id(self, 'Neighbor_IPs')
    
    
    def insert_neighbor_entry(self, device_id, interface_id, neighbor):
        self.cur.execute('''
            INSERT INTO Neighbors
            (
                device_id,
                interface_id,
                device_name,
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
                :device_id,
                :interface_id,
                :device_name,
                :netmiko_platform,
                :system_platform,
                :source_interface,
                :neighbor_interface,
                :software,
                :raw_cdp,
                :updated
            );''',
            {
            'device_id': device_id,
            'interface_id': interface_id,
            'device_name': neighbor.get('device_name', None),
            'netmiko_platform': neighbor.get('netmiko_platform', None),
            'system_platform': neighbor.get('system_platform', None),
            'source_interface': neighbor.get('source_interface', None),
            'neighbor_interface': neighbor.get('neighbor_interface', None),
            'software': neighbor.get('software', None),
            'raw_cdp': neighbor.get('raw_cdp', None),
            'updated': datetime.now().strftime(TIME_FORMAT)
            })
        return sql_database.last_id(self, 'Neighbors')
     
    
    def insert_mac_entry(self, device_id, interface_id, mac_address):
        self.cur.execute('''
            INSERT INTO MAC
            (
                device_id,
                interface_id,
                mac_address,
                updated
            )
            VALUES
            (
                :device_id,
                :interface_id,
                :mac_address,
                :updated
            );''',
            {
            'device_id': device_id,
            'interface_id': interface_id,
            'mac_address': mac_address,
            'updated': datetime.now().strftime(TIME_FORMAT)
            })
        self.db.commit()
        return sql_database.last_id(self, 'MAC')
        
    
    
    def create_table(self, drop_tables= True):
        
        if drop_tables: self.db.executescript('''
            DROP TABLE IF EXISTS Neighbor_IPs;
            DROP TABLE IF EXISTS MAC;
            DROP TABLE IF EXISTS Interfaces;
            DROP TABLE IF EXISTS Serials;
            DROP TABLE IF EXISTS Neighbors;
            DROP TABLE IF EXISTS Devices;
            ''')

        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS Devices(
                device_id          INTEGER PRIMARY KEY AUTOINCREMENT, 
                device_name        TEXT,
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
                username           TEXT,
                password           TEXT,
                cred_type          TEXT,
                updated            TEXT
            );
            
            CREATE TABLE IF NOT EXISTS Interfaces(
                interface_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id          INTEGER NOT NULL,
                interface_name     TEXT NOT NULL,
                interface_number   TEXT,
                interface_type     TEXT,
                ip                 TEXT,
                subnet             TEXT,
                virtual_ip         TEXT,
                description        TEXT,
                raw_interface      TEXT,
                updated            TEXT,
                FOREIGN KEY(device_id) REFERENCES Devices(device_id) 
                    ON DELETE CASCADE ON UPDATE CASCADE
            );

            CREATE TABLE IF NOT EXISTS MAC(
                mac_id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id              INTEGER NOT NULL,
                interface_id           INTEGER NOT NULL,
                mac_address            TEXT NOT NULL,
                updated                TEXT,
                FOREIGN KEY(interface_id) REFERENCES Interfaces(interface_id) 
                    ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY(device_id) REFERENCES Devices(device_id) 
                    ON DELETE CASCADE ON UPDATE CASCADE
                
            );
            
             CREATE TABLE IF NOT EXISTS Serials(
                serial_id          INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id          INTEGER NOT NULL,
                serialnum          TEXT NOT NULL,
                name               TEXT,
                description        TEXT,
                productid          TEXT,
                vendorid           TEXT,
                updated            TEXT,
                FOREIGN KEY(device_id) REFERENCES Devices(device_id) 
                    ON DELETE CASCADE ON UPDATE CASCADE
            );
            
            CREATE TABLE IF NOT EXISTS Neighbors(
                neighbor_id        INTEGER PRIMARY KEY AUTOINCREMENT, 
                device_id          INTEGER NOT NULL,
                interface_id       INTEGER,
                device_name        TEXT,
                netmiko_platform   TEXT,
                system_platform    TEXT,
                source_interface   TEXT,
                neighbor_interface TEXT,
                software           TEXT,
                raw_cdp            TEXT,
                pending            INTEGER,
                working            INTEGER,
                failed             INTEGER,
                failed_msg         TEXT,
                updated            TEXT,
                FOREIGN KEY(device_id) REFERENCES Devices(device_id) 
                    ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY(interface_id) REFERENCES Interfaces(interface_id) 
                    ON DELETE CASCADE ON UPDATE CASCADE
            );  
            
            CREATE TABLE IF NOT EXISTS Neighbor_IPs(
                neighbor_ip_id     INTEGER PRIMARY KEY AUTOINCREMENT, 
                neighbor_id        INTEGER NOT NULL,
                ip                 TEXT NOT NULL,
                type               TEXT,
                updated            TEXT,
                FOREIGN KEY(neighbor_id) REFERENCES Neighbors(neighbor_id) 
                    ON DELETE CASCADE ON UPDATE CASCADE
            );  
            ''')


