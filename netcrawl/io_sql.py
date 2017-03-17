from psycopg2 import errorcodes
import psycopg2, time, traceback
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extras import RealDictCursor

from . import config
from .wylog import log, logf, logging


retry_args = {'stop_max_delay': 60000,  # Stop after 60 seconds
             'wait_exponential_multiplier': 100,  # Exponential backoff
             'wait_exponential_max': 10000,
             }

            
class sql_logger():
    '''Utility class to enable logging of SQL execute statements, 
    as well as handling specific errors'''
    
    def __init__(self, proc, ignore_duplicates=True):
        self.proc = proc
        
        # If a duplicate constraint is hit, ignore it.
        self.ignore_duplicates = ignore_duplicates
        
    def __enter__(self):
        log('Beginning execution in [{}]'.format(self.proc),
            proc=self.proc, v=logging.D)
        self.start = time.time()
        
    def __exit__(self, ty, val, tb):
        end = time.time()
        
        # Ignore the problem if we just added a duplicate
        if ty is None:
            log('SQL execution in [{}] completed without error. Duration: [{:.3f}]'.format(
                self.proc, end - self.start), proc=self.proc, v=logging.D)
        
        # Handle duplicate entry violations    
        elif (ty is psycopg2.IntegrityError) and self.ignore_duplicates:
            if (val.pgcode in (errorcodes.UNIQUE_VIOLATION,
                               errorcodes.NOT_NULL_VIOLATION,
                )):
                log('SQL execution in [{}] completed. Null or Unique constraint hit [{}]. Duration: [{:.3f}]'.format(
                    self.proc, val.pgerror, end - self.start), proc=self.proc, v=logging.I)
                return True
                
        else:
            log('Finished SQL execution in [{}] after [{:.3f}] seconds with [{}] error [{}]. Traceback: [{}]'.format(
                self.proc, end - self.start, ty.__name__, str(val), traceback.format_tb(tb)),
                proc=self.proc, v=logging.I)


class sql_database():
    def __init__(self, dbname, **kwargs):
        # Create the tables in each database, overwriting if needed
        clean = kwargs.get('clean', False)
        self.create_database(dbname)
        self.create_table(drop_tables=clean)
    
    """
    def delete_database(self, db_name, cur= None):
        '''Very much deletes a database'''
        proc= 'sql_database.delete_database'
        
        def _execute(db_name, cur):
            # Make sure the database exists
            cur.execute("SELECT 1 from pg_database WHERE datname= %s", (db_name, ))
            
            if not cur.fetchone(): 
                log('Database [{}] does not exist'.format(db_name), v=logging.I, proc= proc)
                return False 
            
            cur.execute('''
                -- Disallow new connections
                UPDATE pg_database SET datallowconn = 'false' WHERE datname = '{0}';
                ALTER DATABASE {0} CONNECTION LIMIT 1;
                
                -- Terminate existing connections
                SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{0}';
            '''.format(db_name))
            cur.commit()
            
            cur.execute('DROP DATABASE {0}'.format(db_name))
            return True
        
        if cur: 
            return _execute(db_name, cur)
        else:
            with psycopg2.connect(dbname='postgres', 
                                  user='wyko', 
                                  password='pass', 
                                  host='localhost') as conn:
                with conn.cursor() as cur, sql_logger(proc):
                    return _execute(db_name, cur)
    """            
    
    
    @logf
    def execute_sql(self, *args):
        with self.conn, self.conn.cursor() as cur:
            cur.execute(*args)
            return cur.fetchall()
            
    @logf
    def create_database(self, new_db):
        '''Creates a new database'''
        
        proc = 'sql_database.create_database'
        
        with psycopg2.connect(**config.postgres_args()) as conn:
            with conn.cursor() as cur, sql_logger(proc):
                cur.execute("SELECT 1 from pg_database WHERE datname= %s", (new_db,))
                exists = bool(cur.fetchone()) 
            
        if not exists:
            with psycopg2.connect(**config.postgres_args()) as conn:
                conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                with conn.cursor() as cur, sql_logger(proc):
                    cur.execute('CREATE DATABASE {};'.format(new_db))
                    return True
    
    def close(self):
        if not self.conn.closed: self.conn.close()
        

    def ip_exists(self, ip, table):
        '''Check if a given IP exists in the database'''
        proc = 'sql_database.ip_exists'
        
        if ip is None or table is None:
            raise ValueError(proc + ': IP[{}] or Table[{]] missing'.format(
                ip, table))
        
        with self.conn, self.conn.cursor() as cur:
            cur.execute('''
                select exists 
                (select * from {t} 
                where ip= %(ip)s 
                limit 1);
                '''.format(t=table),
                {'ip': ip}
                )
            return cur.fetchone()[0]  # Returns a (False,) tuple
        
        
    def ip_name_exists(self, ip, name, table, cur=None):
        '''Check if a given IP OR Name exists in the database'''
        proc = 'sql_database.ip_name_exists'
        
        if None in (ip,
                    table,
                    name):
            raise ValueError(proc + ': IP[{}], Name [{}] or Table[{]] missing'.format(
                ip, name, table))
        
        with self.conn, self.conn.cursor() as cur:
            cur.execute('''
                select exists 
                    (select * from %(table)s 
                    where 
                        ip= %(ip)s 
                        OR 
                        device_name= %(device)s
                    limit 1);''',
                {'table': table, 'ip': ip, 'device': name})
            return cur.fetchone()[0]  # Returns a (False,) tuple
        
    
    def count(self, table):
        '''Counts the number of rows in the table'''
        proc = 'io_sql.count'
        
        with self.conn, self.conn.cursor() as cur:
            cur.execute('SELECT count(*) as exact_count from {}'.format(table))
            return cur.fetchone()[0]


class main_db(sql_database):
    
    def __init__(self, **kwargs):
        proc = 'main_db.__init__'
        
        self.DB_NAME = 'main'
        
        self.conn = psycopg2.connect(**config.main_args())
        
        sql_database.__init__(self, self.DB_NAME, **kwargs)
        
        self.ignore_visited = kwargs.get('ignore_visited', True)
        
        with self.conn, self.conn.cursor() as cur, sql_logger(proc):

            # Delete everything in the visited table
            if self.ignore_visited: cur.execute('DELETE FROM visited')
            
            # Then set all pending entries as not working
            cur.execute('''
                UPDATE pending 
                SET working= FALSE
            ''')

    
    def __len__(self):
        return sql_database.count(self, self.DB_NAME)
    
    def count_pending(self):
        '''Counts the number of rows in the table'''
        return sql_database.count(self, 'pending')
    
    def count_unique_visited(self):
        '''Counts the number of unique devices in the database'''
        with self.conn, self.conn.cursor() as cur:
            cur.execute('''
                SELECT count(distinct device_name) 
                FROM visited;''')
        return cur.fetchone()[0]
    
    
    def remove_pending_record(self, _id):
        '''Removes a record from the pending table''' 
        proc = 'main_db.remove_processed'
        
        # Error checking
        assert isinstance(_id, int), (
            proc + ': _id [{}] is not int'.format(type(_id)))
        
        # Delete the processed entry
        with self.conn, self.conn.cursor() as cur:
            cur.execute('''
                DELETE FROM 
                    pending
                WHERE
                    pending_id = %s
                ''', (_id,))
            
    def remove_visited_record(self, ip):
        '''Removes a record from the pending table''' 
        proc = 'main_db.remove_processed'
        
        # Error checking
        assert isinstance(ip, str), (
            proc + ': ip [{}] is not str'.format(type(ip)))
        
        # Delete the processed entry
        with self.conn, self.conn.cursor() as cur:
            cur.execute('''
                DELETE FROM 
                    visited
                WHERE
                    ip = %s
                ''', (ip,))
        

    def get_next(self):
        '''Gets the next pending device.
        
        Returns: 
            Dict: The next pending device as a dictionary object
                with the names of the rows as keys.
        '''
        proc = 'main_db.get_next'
        
        # User a special cursor which returns results as dicts
        with self.conn, self.conn.cursor(cursor_factory=RealDictCursor) as cur:        
            cur.execute('''
                SELECT * FROM 
                    pending 
                WHERE 
                    working= FALSE
                ORDER BY pending_id ASC LIMIT 1
                ''')
            output = cur.fetchone()
        

            # Mark the new entry as being worked on 
            if output:
                cur.execute('''
                    UPDATE pending 
                    SET working= TRUE
                    WHERE pending_id= %s
                    ''',
                    (output['pending_id'],))
                
                # Return the next device
                output = dict(output)
                return output
            
            else: return None
    
    
    def add_pending_device_d(self, device_d=None, cur=None, **kwargs):
        proc = 'main_db.add_pending_device_d'
        
        # Pending dict template
        _device_d = {
            'device_name': None,
            'ip_list': None,
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
        
        # Break if no IP address or platform was supplied
        if ((_device_d['ip_list'] is None) or
            (len(_device_d['ip_list']) == 0 or
            (_device_d['netmiko_platform'] is None))): 
            return False
        
        with self.conn, self.conn.cursor() as cur:
            for ip in _device_d['ip_list']:
                if sql_database.ip_exists(self, ip, 'visited'):
                    log('[{}] already in visited table'.format(ip),
                        v=logging.I, proc=proc)
                
                if sql_database.ip_exists(self, ip, 'pending'):
                    log('[{}] already in pending table'.format(ip),
                        v=logging.I, proc=proc)
                    continue
                
                with sql_logger(proc):
                    cur.execute('''
                        INSERT INTO pending  
                            (
                            working,
                            ip,
                            device_name,
                            netmiko_platform,
                            system_platform,
                            source_interface,
                            neighbor_interface,
                            software,
                            raw_cdp
                            )
                        VALUES 
                            (FALSE, 
                            %(ip)s, 
                            %(device_name)s, 
                            %(netmiko_platform)s, 
                            %(system_platform)s, 
                            %(source_interface)s, 
                            %(neighbor_interface)s, 
                            %(software)s, 
                            %(raw_cdp)s 
                        );
                        ''',
                        {
                        'ip': ip,
                        'device_name': _device_d['device_name'],
                        'netmiko_platform': _device_d['netmiko_platform'],
                        'system_platform': _device_d['system_platform'],
                        'source_interface': _device_d['source_interface'],
                        'neighbor_interface': _device_d['neighbor_interface'],
                        'software': _device_d['software'],
                        'raw_cdp': _device_d['raw_cdp'],
                        })
        
    
    def add_device_pending_neighbors(self, _device=None, _list=None):
        """Appends a device or a list of devices to the database
        
        Optional Args:
            _device (network_device): A single device 
            _list (List): List of devices
            
        Returns:
            Boolean: True if write was successful, False otherwise.
        """
        proc = 'main_db.add_device_pending_neighbors'
        if not _list: _list = []
        
        log('Adding neighbors to pending table', proc=proc,
            v=logging.N)
        
        # If a single device was passed, add it to the list
        if _device: _list.append(_device)
        
        # Return an error if no data was passed
        if not _list: 
            log('No devices to add', proc=proc, v=logging.A)
            return False
        
        # Process each device in one transaction
        for device in _list:
            for neighbor in device.all_neighbors():           
                
                if not neighbor.get('netmiko_platform'):
                    log('Neighbor [{}] has no platform. Skipping'.format(
                        neighbor), v=logging.I, proc=proc)
                    continue
                    
                # Add it to the list of ips to check
                self.add_pending_device_d(neighbor)
                    
    def create_table(self, drop_tables=True):
        proc = 'main_db.create_table'
        log('Creating main.db tables',
            proc=proc, v=logging.I)
        
        with self.conn, self.conn.cursor() as cur:
            if drop_tables: 
                cur.execute('''
                    DROP TABLE IF EXISTS 
                        pending, 
                        visited 
                    CASCADE;
                    ''')
                
            cur.execute('''
                CREATE TABLE IF NOT EXISTS pending(
                pending_id         SERIAL PRIMARY KEY, 
                ip                 TEXT NOT NULL UNIQUE,
                working            BOOLEAN NOT NULL,
                device_name        TEXT,
                netmiko_platform   TEXT,
                system_platform    TEXT,
                source_interface   TEXT,
                neighbor_interface TEXT,
                software           TEXT,
                raw_cdp            TEXT,
                updated            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
                
                CREATE TABLE IF NOT EXISTS visited(
                visited_id     SERIAL PRIMARY KEY, 
                ip             TEXT UNIQUE,
                device_name    TEXT,
                updated        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                );
                ''')

    
    def add_visited_device_d(self, device_d=None, cur=None, **kwargs):
        proc = 'main_db.add_visited_device_d'
        
        _device_d = {
            'device_name': None,
            'ip': None,
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
        
        # Break if no IP addres was supplied
        if _device_d['ip'] is None: 
            raise ValueError(proc + ': No IP or platform was supplied in [{}]'.format(_device_d))
        
        def _execute(_device_d, cur):        
            with sql_logger(proc):    
                cur.execute('''
                    INSERT INTO visited  
                        (
                        ip,
                        device_name
                        )
                    VALUES 
                        (
                        %(ip)s, 
                        %(device_name)s
                        );
                    ''',
                    {
                    'ip': _device_d['ip'],  # Must have an IP
                    'device_name': _device_d['device_name'],
                    })
            
        # Create a cursor if none was passed
        if cur is None:
            with self.conn, self.conn.cursor() as cur:
                return _execute(_device_d, cur)
            
        # Otherwise use the passed cursor
        else: return _execute(_device_d, cur)
        
    
    
    def add_visited_device_nd(self, _device=None, _list=None, cur=None):
        """Appends a device or a list of devices to the database
        
        Optional Args:
            _device (network_device): A single network_device
            _list (List): List of network_device objects
            
        Returns:
            Boolean: True if write was successful, False otherwise.
        """ 
        proc = 'main_db.add_visited_device_nd'
        
        if not _list: _list = []
        
        log('Adding device(s) to  table.'.format(self.DB_NAME),
            proc=proc, v=logging.N)
        
        # If a single device was passed, add it to the list so that we can
        # simplify the code later on
        if _device: _list.append(_device)
        
        # Return an error if no data was passed
        if not _list: 
            log('No devices to add', proc=proc,
                v=logging.A)
            return False
        
        def _execute(_list, cur):
            # Process each device
            for _device in _list:
                
                # Get the IP's from the device 
                ip_list = _device.get_ips()
                log('{} has {} ip(s)'.format(_device.device_name, len(ip_list)),
                    proc=proc, v=logging.I)
                
                # For failed devices which couldn't be fully polled:
                with sql_logger(proc):    
                    cur.execute('''
                        INSERT INTO visited  
                            (
                            device_name,
                            ip
                            )
                        VALUES 
                            (%s, %s);
                        ''',
                        (_device.device_name,
                         _device.ip) 
                        )
                    
                for ip in ip_list:
                    with sql_logger(proc):
                        cur.execute('''
                        INSERT INTO visited  
                            (
                            device_name,
                            ip
                            )
                        VALUES 
                            (%s, %s);
                        ''',
                        (_device.device_name,
                        ip) 
                        )
        
        
        # Create a cursor if none was passed
        if cur is None:
            with self.conn, self.conn.cursor() as cur:
                return _execute(_list, cur)
            
        # Otherwise use the passed cursor
        else: return _execute(_list, cur)
        
        
        log('Added {} devices to visited table'.format(len(_list)),
            proc=proc, v=logging.I)
        return True
    
    
class device_db(sql_database):
    
    def __init__(self, **kwargs):
        proc = 'device_db.__init__'
        
        self.DB_NAME = 'inventory'
        sql_database.__init__(self,self.DB_NAME, **kwargs)
        
        self.conn = psycopg2.connect(**config.inventory_args())
    
    def __len__(self):
        'Returns the number of devices in the database'
        return sql_database.count(self, 'devices')
    
    def ip_exists(self, ip):
        return sql_database.ip_exists(self, ip, 'interfaces')
    
    
    def locate_mac(self, mac):
        with self.conn, self.conn.cursor() as cur:
            cur.execute('''
                SELECT distinct devices.device_name as device, interface_name as interface, neighbors.device_name as neighbor
                FROM mac
                JOIN devices ON mac.device_id=devices.device_id
                JOIN interfaces on mac.interface_id=interfaces.interface_id
                LEFT JOIN neighbors on mac.interface_id=neighbors.interface_id
                WHERE mac_address = %s;
                ''', (mac, ))
            return cur.fetchall()
    
    
    def devices_on_subnet(self, subnet):
        with self.conn, self.conn.cursor() as cur:
            cur.execute('''
                SELECT distinct interfaces.device_id
                FROM interfaces
                JOIN devices on interfaces.device_id=devices.device_id
                WHERE network_ip is %s;
                ''', (subnet, ))
            results= cur.fetchall()
        
        # Return a nicely formatted list of device ID's 
        results= [x[0] for x in results]
        return sorted(set(results))
    
    def macs_on_subnet(self, subnet):
        with self.conn, self.conn.cursor() as cur:
            cur.execute('''
                SELECT distinct mac_address
                FROM (SELECT distinct interface_id
                      FROM (SELECT distinct device_id
                            FROM interfaces
                            WHERE network_ip = %s) as foo
                      JOIN interfaces ON interfaces.device_id=foo.device_id) as bar
                JOIN mac on mac.interface_id = bar.interface_id;
                ''', (subnet, ))
            
            # Create a generator over the macs so that we don't 
            # get overwhelmed
            for mac in cur:
                if mac is None: return True
                
                else: yield mac[0]

        
        
    def device_macs(self, device_id):
        with self.conn, self.conn.cursor() as cur:
            cur.execute('''
                SELECT mac_address
                FROM mac
                JOIN interfaces on mac.interface_id=interfaces.interface_id
                WHERE interfaces.device_id = %s;
                ''', (device_id, ))
            return cur.fetchall()
    
    def unique_name_exists(self, name):
        '''Returns True if a given unique_name already exists'''
        proc = 'io_sql.unique_name_exists'
        
        with self.conn, self.conn.cursor() as cur:
            cur.execute('''
                select exists 
                (select * from devices 
                where unique_name = %s
                limit 1);
                ''',
                (name.upper(),))
            return cur.fetchone()[0]  # Returns a (False,) tuple)
    
    
    def add_device_nd(self, _device=None, _list=None):
        """Appends a device or a list of devices to the database
        
        Optional Args:
            _device (network_device): A single network_device
            _list (List): List of network_device objects
            
        Returns:
            Boolean: True if write was successful, False otherwise.
        """ 
        proc = 'device_db.add_device_nd'
        
        # Return an error if no data was passed    
        if not (_list or _device): 
            log('No devices to add', proc=proc, v=logging.A)
            return False
        
        if not _list: _list = []
        
        log('Adding device(s) to devices table'.format(self.DB_NAME), proc=proc, v=logging.N)
        
        # If a single device was passed, add it for group processing
        if _device: _list.append(_device)
        
        # Do everything in one transaction
        with self.conn, self.conn.cursor() as cur:
            
            # Process each device
            for _device in _list:
                device_id = self.insert_device_entry(_device, cur)
                
                # Add all the device's serials
                for serial in _device.serial_numbers:
                    self.insert_serial_entry(device_id, serial, cur)
                
                # Add all of the device's interfaces            
                for interf in _device.interfaces:
                    interface_id = self.insert_interface_entry(device_id, interf, cur)
                    
                    # Add all the interface's mac addresses
                    for mac_address in interf.mac_address_table:
                        mac_id = self.insert_mac_entry(device_id, interface_id, mac_address, cur)
                    
                    # Add each neighbor + ip that was matched to an interface
                    for neighbor in interf.neighbors:
                        neighbor_id = self.insert_neighbor_entry(device_id, interface_id, neighbor, cur)
                        for n_ip in neighbor: self.insert_neighbor_ip_entry(neighbor_id, n_ip, cur)
                    
                # Add each neighbor + ip not matched to an interface
                for neighbor in _device.neighbors:
                    neighbor_id = self.insert_neighbor_entry(device_id, None, neighbor, cur)
                    for n_ip in neighbor: self.insert_neighbor_ip_entry(neighbor_id, n_ip, cur)
                    
        self.conn.commit()
        return True
    
    
    def insert_device_entry(self, _device, cur):
        # Trim the password
        _password = _device.credentials.get('password', None)
        if _password: _password = _password[:2]
       
        # Add the device into the database
        cur.execute('''
            INSERT INTO devices (
                device_name,
                unique_name,
                netmiko_platform,
                system_platform,
                software,
                raw_cdp,
                raw_config,
                failed,
                error_log,
                processing_error,
                TCP_22,
                TCP_23,
                username,
                password,
                cred_type
                )
            VALUES (
                %(device_name)s,
                %(unique_name)s,
                %(netmiko_platform)s,
                %(system_platform)s,
                %(software)s,
                %(raw_cdp)s,
                %(raw_config)s,
                %(failed)s,
                %(error_log)s,
                %(processing_error)s,
                %(TCP_22)s,
                %(TCP_23)s,
                %(username)s,
                %(password)s,
                %(cred_type)s
                )
            RETURNING device_id;
            ''',
            {
                'device_name': _device.device_name,
                'unique_name': _device.unique_name(),
                'netmiko_platform': _device.netmiko_platform,
                'system_platform': _device.system_platform,
                'software': _device.software,
                'raw_cdp': _device.raw_cdp,
                'raw_config': _device.config,
                'failed': _device.failed,
                'error_log': _device.error_log,
                'processing_error': _device.processing_error,
                'TCP_22': _device.TCP_22,
                'TCP_23': _device.TCP_23,
                'username': _device.credentials.get('username', None),
                'password': _password,
                'cred_type': _device.credentials.get('type', None),
            })
        return cur.fetchone()[0]
    
    
    def insert_interface_entry(self, device_id, interf, cur):
        cur.execute('''
            INSERT INTO interfaces (
                device_id,
                interface_name,
                interface_type,
                interface_number,
                ip,
                subnet,
                virtual_ip,
                description,
                raw_interface,
                network_ip
                )
            VALUES (
                %(device_id)s,
                %(interface_name)s,
                %(interface_type)s,
                %(interface_number)s,
                %(ip)s,
                %(subnet)s,
                %(virtual_ip)s,
                %(description)s,
                %(raw_interface)s,
                %(network_ip)s
                )
            RETURNING interface_id;
            ''',
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
            'network_ip': interf.network_ip,
            })
        return cur.fetchone()[0]
    
    
    def insert_serial_entry(self, device_id, serial, cur):
        cur.execute('''
            INSERT INTO serials (
                device_id,
                serialnum,
                name,
                description,
                productid,
                vendorid
                )
            VALUES (
                %(device_id)s,
                %(serialnum)s,
                %(name)s,
                %(description)s,
                %(productid)s,
                %(vendorid)s
                )
            RETURNING serial_id;
            ''',
            {
            'device_id': device_id,
            'serialnum': serial.get('serialnum', None),
            'name': serial.get('name', None),
            'description': serial.get('desc', None),
            'productid': serial.get('productid', None),
            'vendorid': serial.get('vendorid', None),
            })
        return cur.fetchone()[0]
    
    
    def insert_neighbor_ip_entry(self, neighbor_id, ip, cur):
        cur.execute('''
            INSERT INTO neighbor_ips
            (
                neighbor_id,
                ip
            )
            VALUES
            (
                %(neighbor_id)s,
                %(ip)s
            )
            RETURNING neighbor_ip_id;
            ''',
            {
            'neighbor_id': neighbor_id,
            'ip': ip,
            })
        return cur.fetchone()[0]
    
    
    def insert_neighbor_entry(self, device_id, interface_id, neighbor, cur):
        cur.execute('''
            INSERT INTO neighbors
            (
                device_id,
                interface_id,
                device_name,
                netmiko_platform,
                system_platform,
                source_interface,
                neighbor_interface,
                software,
                raw_cdp
            )
            VALUES
            (
                %(device_id)s,
                %(interface_id)s,
                %(device_name)s,
                %(netmiko_platform)s,
                %(system_platform)s,
                %(source_interface)s,
                %(neighbor_interface)s,
                %(software)s,
                %(raw_cdp)s
            )
            RETURNING neighbor_id;
            ''',
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
            })
        return cur.fetchone()[0]
     
    
    def insert_mac_entry(self, device_id, interface_id, mac_address, cur):
        cur.execute('''
            INSERT INTO mac
            (
                device_id,
                interface_id,
                mac_address
            )
            VALUES
            (
                %(device_id)s,
                %(interface_id)s,
                %(mac_address)s
            )
            RETURNING mac_id;
            ''',
            {
            'device_id': device_id,
            'interface_id': interface_id,
            'mac_address': mac_address,
            })
        return cur.fetchone()[0]
        
    
    
    def create_table(self, drop_tables=True):
        proc = 'device_db.create_table'
        
        with self.conn, self.conn.cursor() as cur:
                if drop_tables: cur.execute('''
                    DROP TABLE IF EXISTS 
                        neighbor_IPs,
                        mac,
                        serials,
                        neighbors,
                        interfaces,
                        devices 
                    CASCADE;
                    ''')
        
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS devices(
                        device_id          SERIAL PRIMARY KEY , 
                        device_name        TEXT,
                        unique_name        TEXT,
                        netmiko_platform   TEXT,
                        system_platform    TEXT,
                        software           TEXT,
                        raw_cdp            TEXT,
                        raw_config         TEXT,
                        failed             BOOLEAN,
                        error_log          TEXT,
                        processing_error   BOOLEAN,
                        TCP_22             BOOLEAN,
                        TCP_23             BOOLEAN,
                        username           TEXT,
                        password           TEXT,
                        cred_type          TEXT,
                        updated            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                    );

                    CREATE TABLE IF NOT EXISTS Interfaces(
                        interface_id       BIGSERIAL PRIMARY KEY ,
                        device_id          INTEGER NOT NULL,
                        interface_name     TEXT NOT NULL,
                        interface_number   TEXT,
                        interface_type     TEXT,
                        ip                 TEXT,
                        subnet             TEXT,
                        virtual_ip         TEXT,
                        description        TEXT,
                        raw_interface      TEXT,
                        network_ip         TEXT,
                        updated            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        FOREIGN KEY(device_id) REFERENCES Devices(device_id) 
                            ON DELETE CASCADE ON UPDATE CASCADE
                    );
        
                    CREATE TABLE IF NOT EXISTS MAC(
                        mac_id                 BIGSERIAL PRIMARY KEY ,
                        device_id              INTEGER NOT NULL,
                        interface_id           INTEGER NOT NULL,
                        mac_address            TEXT NOT NULL,
                        updated                TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        FOREIGN KEY(interface_id) REFERENCES Interfaces(interface_id) 
                            ON DELETE CASCADE ON UPDATE CASCADE,
                        FOREIGN KEY(device_id) REFERENCES Devices(device_id) 
                            ON DELETE CASCADE ON UPDATE CASCADE
                        
                    );
                    
                     CREATE TABLE IF NOT EXISTS Serials(
                        serial_id          SERIAL PRIMARY KEY ,
                        device_id          INTEGER NOT NULL,
                        serialnum          TEXT NOT NULL,
                        name               TEXT,
                        description        TEXT,
                        productid          TEXT,
                        vendorid           TEXT,
                        updated            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        FOREIGN KEY(device_id) REFERENCES Devices(device_id) 
                            ON DELETE CASCADE ON UPDATE CASCADE
                    );
                    
                    CREATE TABLE IF NOT EXISTS Neighbors(
                        neighbor_id        BIGSERIAL PRIMARY KEY , 
                        device_id          INTEGER NOT NULL,
                        interface_id       INTEGER,
                        device_name        TEXT,
                        netmiko_platform   TEXT,
                        system_platform    TEXT,
                        source_interface   TEXT,
                        neighbor_interface TEXT,
                        software           TEXT,
                        raw_cdp            TEXT,
                        updated            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        FOREIGN KEY(device_id) REFERENCES Devices(device_id) 
                            ON DELETE CASCADE ON UPDATE CASCADE,
                        FOREIGN KEY(interface_id) REFERENCES Interfaces(interface_id) 
                            ON DELETE CASCADE ON UPDATE CASCADE
                    );  
                    
                    CREATE TABLE IF NOT EXISTS Neighbor_IPs(
                        neighbor_ip_id     BIGSERIAL PRIMARY KEY , 
                        neighbor_id        INTEGER NOT NULL,
                        ip                 TEXT NOT NULL,
                        type               TEXT,
                        updated            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        FOREIGN KEY(neighbor_id) REFERENCES Neighbors(neighbor_id) 
                            ON DELETE CASCADE ON UPDATE CASCADE
                    );  
                    ''')
        
        
