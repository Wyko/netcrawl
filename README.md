# netcrawl

This package is designed to facilitate crawling a network for information on connected devices.

This package is still in development and no part is ready for production use.


## Overview


### File Structure

#### index.db

The index is a list of **all known neighbors.** It is a comma separated, table-formatted document containing the following:
* IP Address of the neighbor (Multiple entries if a neighbor has multiple IPs)
* Connected interface of the neighbor:Hostname of the neighbor
* IP Address of the source device
* Connected interface of the source device:Hostname of the source device
* Timestamp

```
10.0.255.49, FastEthernet0/23:oh-mas-core-rt1, 10.0.255.50, FastEthernet0/1:oh-mas-dist-sw4, 2017-02-02 23:05:30
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


## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

What things you need to install the software and how to install them

```
Give examples
```

### Installing

A step by step series of examples that tell you have to get a development env running

Say what the step will be

```
Give the example
```

And repeat

```
until finished
```

End with an example of getting some data out of the system or using it for a little demo

## Running the tests

Explain how to run the automated tests for this system

### Break down into end to end tests

Explain what these tests test and why

```
Give an example
```

### And coding style tests

Explain what these tests test and why

```
Give an example
```

## Deployment

Add additional notes about how to deploy this on a live system

## Built With

* [Dropwizard](http://www.dropwizard.io/1.0.2/docs/) - The web framework used
* [Maven](https://maven.apache.org/) - Dependency Management
* [ROME](https://rometools.github.io/rome/) - Used to generate RSS Feeds

## Contributing

Please read [CONTRIBUTING.md](https://gist.github.com/PurpleBooth/b24679402957c63ec426) for details on our code of conduct, and the process for submitting pull requests to us.

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/your/project/tags). 

## Authors

* **Billie Thompson** - *Initial work* - [PurpleBooth](https://github.com/PurpleBooth)

See also the list of [contributors](https://github.com/your/project/contributors) who participated in this project.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

* Hat tip to anyone who's code was used
* Inspiration
* etc
