from cisco import get_device

def main():
    # ip = input('IP of Host: ')
    ip = '10.1.120.1'
    
    # Get the config
    print(get_device(ip))
    

if __name__ == "__main__":
    main()