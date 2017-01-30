import xml.etree.ElementTree as ET


def open_tree(destination):
    """Opens an XML file and returns a tree object. If the database does not
    exist, create a databse with that name and return the tree object
    associated with it.
    
    Args:
        destination (string): The database name to write to.
    """



def write_device(device, destination='main', update=True, error_code=''):
    """Write a device to the main database.
    
    Args:
        device (network_device): The network_device class object to write.
        update (Boolean): If True, search for and update an existing copy
            of the device in the database. If none is found, create a new
            entry anyway. If False, create a new entry.
        destination (string): The database name to write to. Defaults to the
            'main' database.
        error_code (string): An optional error field to include.
    """

    
