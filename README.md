# Presentation Gave at IBMSTU 2017 ( São Paulo )
## Purpose
This is a simple DEMO idea of how to use Linear Regression to estimate server grownth over time
It use nmon data to predict size over time
At current stage it predict:
* Estimated date to reach 100% of entitled capacity ( IBM POWER LPAR )
* Estimated date to reach 95% of CPU usage
* Amount of cores being used when 95% CPU is reached

## Requirements
* Pymongo ( >= 3.2 )
* TensorFlow ( >= 1.0 )
* Python ( >= 3.5 ) ( Should work with 2.7, but wasn't tested )

## Usage
The idea is composed by two scripts
### nmon_parser.py :
This script is responsible to parse all nmon files presented at one directory.
It will scan the directory for nmon files ( for a specific LPAR ) and parse them in parallel
The following fields are being considered during Parsing:
* AAA | Basic information
* BBBL | Lpar configuration
* ^PCPU_ALL$|^SCPU_ALL$|^CPU_ALL$|^LPAR$|^MEM$|^PROC$|^NET$|^NETPACKET$|^NETSIZE$|^NETERROR$|^IOADAPT  -> General Counters

The information about database connection and directory to be scanned are at the bottom of the script, bellow __main__ reference
For STU the following parameters were used:

	directory = "/home/pqueiroz/clientes/IBM/STU_2017/dset/nmon"
	mongodb_uri = 'mongodb://localhost:27017'
	mongodb_db = 'stu2017'
	paralel = 1

* directory : Control which directory the nmon files are stored
* mongodb_uri : uri to connect at the mongo database ( [standard from mongodb](https://docs.mongodb.com/manual/reference/connection-string/) )
* mongodb_db : Database name to be used
* paralel : Amount of connections in Parallel

### predict_size.py
With all Data inserted at rhe database, this script will predict the sizes and dates
All parametrization is at top of the script and those are the parameters used at STU:

	learn_rate = 0.001
	samples = 100000
	mongodb_uri = 'mongodb://localhost:27017'
	mongodb_db  = "stu2017"

## TODO
* Use argparse or getopt to avoid change the code
* Use pyplot for visualization 
* split the dataset to consider testing
