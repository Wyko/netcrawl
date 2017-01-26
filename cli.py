from netmiko import ConnectHandler
from netmiko import NetMikoAuthenticationException
from netmiko import NetMikoTimeoutException

from credentials import credList



def start_cli_session(ip, platform):
    """
    Starts a CLI session with a remote device. Will attempt to use
    SSH first, and if it fails it will try a terminal session.
    
    :param ip: IP address of the device
    :param username: username used for the authentication
    :param password: password used for the authentication
    :param enable_secret: enable secret
    :param platform: One of the following:
        cisco_ios
        cisco_asa
        cisco_nxos
    :return: a Netmiko ConnectHandler object opened to the enable prompt 
    """
    
    print('# Connecting to %s device %s' % (platform, ip))
    
    # Try logging in with each credential we have
    for username, password in credList:
        try:
            # establish a connection to the device
            ssh_connection = ConnectHandler(
                device_type=platform,
                ip=ip,
                username=username,
                password=password,
                secret=password
            )
            print('# Successful ssh auth to %s' % (ip))
            return ssh_connection
        except NetMikoAuthenticationException:
            print ('# SSH auth error to %s using %s / %s' % (ip, username, password))
            continue
        except NetMikoTimeoutException:
            print('# SSH to %s timed out.' % ip)
            # If the device is unavailable, don't try any other credentials
            break
    
    if (not 'ssh_connection' in locals()) and (platform=='cisco_ios'):
        for username, password in credList:
            try:
                # establish a connection to the device using telnet
                ssh_connection = ConnectHandler(
                    device_type='cisco_ios_telnet',
                    ip=ip,
                    username=username,
                    password=password,
                    secret=password
                )
                print('# Successful telnet auth to %s' % (ip))
                return ssh_connection
            except NetMikoAuthenticationException:
                print ('# Telnet auth error to %s using %s / %s' % (ip, username, password))
                continue
            except:
                print('# Telnet to %s timed out.' % ip)
                # If the device is unavailable, don't try any other credentials
                break
    
    raise IOError('# No connection could be established to %s.' % ip)

