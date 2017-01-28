from cisco import get_device

def main():
    # ip = input('IP of Host: ')
    ip = '10.20.101.114'
    
    # Get the config
    print(get_device(ip, 'cisco_ios'))
    

if __name__ == "__main__":
    main()