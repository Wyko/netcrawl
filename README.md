# netcrawl

This package is designed to facilitate crawling a network for information on connected devices.

This package is still in development and no part is ready for production use.


## Overview


### File Structure

#### neighborhood.db

The index is a list of **all known neighbors.** It is a comma separated, table-formatted document containing the following:
* IP Address of the neighbor (Multiple entries if a neighbor has multiple IPs)
* Connected interface of the neighbor:Hostname of the neighbor
* IP Address of the source device
* Connected interface of the source device:Hostname of the source device
* Timestamp

```
10.0.255.49, FastEthernet0/23:oh-mas-core-rt1, 10.0.255.50, FastEthernet0/1:oh-mas-dist-sw4, 2017-02-02 23:05:30
```

#### visited.db

The index is a list of **all visited devices.** For each device a seperate entry is made for each IP address it has. Each entry looks like:
* One of the IP addresses of the device
* Hostname of the device
* Serial
* Timestamp

```
10.0.255.49, oh-mas-core-rt1, ABCD12345678, 2017-02-02 23:05:30
```

#### pending.db

The index is a list of **all unvisited devices.** For each device one entry is made. Each entry looks like:
* One of the IP addresses of the device
* Hostname of the device

```
10.0.255.49, oh-mas-core-rt1
```

#### failed.db

This is a list of the devices which were not able to be scanned for one reason or another.
* IP Address of the failed device
* Hostname (if known)
* Process which detected the failure
* Failure Reason
* Timestamp

```
10.0.255.49, oh-mas-core-rt1, start_cli_session, All known credentials failed, 2017-02-02 23:05:30
```

#### log.db

This is the operational log.
* Timestamp
* Process
* Log Message
* IP Address

```
2017-02-02 23:05:27, get_raw_cdp_output       , # Enable successful on attempt 1. Current delay: 1, 10.1.103.3
```
