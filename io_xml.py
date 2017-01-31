from lxml import etree as ET
from device_classes import network_device
import os.path


def open_tree(destination='main', create=True):
    """Opens an XML file and returns a tree object. If the database does not
    exist, create a databse with that name and return the tree object
    associated with it.
    
    Args:
        destination (string): The database name to open (or create).
        create (Boolean): (Optional) If True, allows the creation of a new file
            if the database doesn't exist yet.

    Returns:
        ElementTree: The tree object corresponding with the opened database
        Boolean: False if no tree was opened or created.
    """
	
	destination = destination + '.xml'
	
    # Break early if the file doesn't exist and we aren't allowed to make
    # a new one.
    exists = os.path.isfile(destination)
    if create == False and exists == False: return False

    # Make the new tree
    if exists:
        tree = ET.ElementTree(file=destination)
    else:
        tree = ET.ElementTree()
    
    if tree: return tree
    else: return False



def print_tree(tree):
    """Prints an ElementTree to the console."""
    for elem in tree.iter():
        print (elem.tag, elem.attrib)



def entry_exists(device, tree):
    for elem in tree.find('network_device[serials/serial'):
            break
    pass
        

def write_device(device, destination='main', update=True, error_code=''):
    """Write a network_device to an XML database.
    
    Args:
        device (network_device): The network_device class object to write. Can
            accept both a single device or a list of devices.
        update (Boolean): If True, search for and update an existing copy
            of the device in the database. If none is found, create a new
            entry anyway.
            If False, create a new entry.
        destination (string): The database name to write to. Defaults to the
            'main' database.
        error_code (string): An optional error field to include.

    Returns:
        Boolean: True if the write was successful, False if not.

    Raises:
        IOError: If write was unsuccessful.
    """

    # Open the database
    tree = open_tree(destination + '.xml')
    if not tree or tree == False:
        raise IOError('!!! File ' + destination + ' could not be opened for writing device.')
        return False

    root = tree.getroot()

    # If a single device was passed, convert it to a single element list.
    if type(device) is network_device: device = [device]

    device_element = ''
    # Check to see if the device already exists, if we need to update it
    if update and device.serial[0]['serial'] and device.serial[0]['serial'] != '':

        # Compare the device's serial against the database
        elem = root.xpath("network_device[serials/serial/@serial='XYZ1234567890']")

        # If a result was found (result list not empty)
        if elem:
            device_element = elem[0]
        else:
            # Otherwise create a new element and add it to the database
            device_element = ET.Element("network_device")
            root.append(device_element)
            



    
    
