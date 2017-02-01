import os
current_file_path = __file__
current_file_dir = os.path.dirname(__file__)

DB_PATH = current_file_dir + '/database/' 

# Define the timestamp format
TIME_FORMAT = '%Y-%m-%d %H:%M:%S'


# When a device fails to connect, try again with this much delay
DELAY_INCREASE = 0.3

# The delay factor s
BASE_DELAY = 1