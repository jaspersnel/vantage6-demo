# Simple setup script for Vantage6 demos

This repository contains script to very easily set up a Vantage6 demo infrastructure. It is meant to be used to set up both a Vantage6 server and (multiple) node(s) on one machine. Currently, the infrastructure as it is set up should not be used in a production environment as encryption is disabled and Vantage6 currently only supports the importing of superusers.

## Usage

A few python packages are necessary for this demo to run - PyYAML and vantage6. To easily install these non-globally, run the initialization script (this does require Python3):

```bash
source initialize.sh
```

In the future, to deactivate this environment with the necessary requirements, use the following command:
```bash
deactivate
```

The `setupdemo.py` script can now be used to set up a demo infrastructure. The easiest way to set things up is to simply put a number of database files in a `databases` directory. The script will set up an organization with a corresponding vantage6 node for each database file:

```bash
python setupdemo.py
```

This will setup the necessary files and output the command needed to run the infrastructure. Simply copy and paste the last few lines of commands to the command line and run them to start the infrastructure. A username/password for any of the organizations provided in the output can be used to now run things on the infrastructure.

Additionally, a file called `v6-demo-infra.yaml` will be created in the root directory. This contains all the information on the infrastructure that was initialized. Whenever the script is run again, it will first look if this file exists and use it as input. This is helpful to re-output things like run commands without having to change any credentials. To generate a new infrastructure instead, use the `-c` flag.

### re-using databases

One alternative to the above is to manually specify organization names, this allows for the re-using of one or more databases. E.g. if three names are provided while only two databases exist, the first two organizations will use the databases as expected, the third organization will loop back to use database 1. This can be done as follows:

```bash
python setupdemo.py -N UMCG VUMC MUMC
```

### Other options

If you want to use a different location for the databases, use the `-d` option. Any further commands can be inspected using the `--help` flag.