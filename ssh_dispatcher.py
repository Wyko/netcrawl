"""Controls selection of proper class based on the device type.

Credit: Kirk Byers
"""
from Devices.ios_device import ios_device
from Devices.nxos_device import nxos_device

# The keys of this dictionary are the supported device_types
CLASS_MAPPER_BASE = {
    'cisco_ios': ios_device,
    'cisco_nxos': nxos_device,
}

# Also support keys that end in _ssh
new_mapper = {}
for k, v in CLASS_MAPPER_BASE.items():
    new_mapper[k] = v
    alt_key = k + u"_ssh"
    new_mapper[alt_key] = v
CLASS_MAPPER = new_mapper

# Add telnet drivers
CLASS_MAPPER['cisco_ios_telnet'] = ios_device

platforms = list(CLASS_MAPPER.keys())
platforms.sort()
platforms_base = list(CLASS_MAPPER_BASE.keys())
platforms_base.sort()
platforms_str = u"\n".join(platforms_base)
platforms_str = u"\n" + platforms_str


def ConnectHandler(*args, **kwargs):
    """Factory function selects the proper class and creates object based on device_type."""
    if kwargs['netmiko_platform'] not in platforms:
        raise ValueError('Unsupported device_type: '
                         'currently supported platforms are: {0}'.format(platforms_str))
    ConnectionClass = ssh_dispatcher(kwargs['netmiko_platform'])
    return ConnectionClass(*args, **kwargs)


def ssh_dispatcher(device_type):
    """Select the class to be instantiated based on vendor/platform."""
    return CLASS_MAPPER[device_type]
