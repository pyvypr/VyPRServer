# VyPR Verdict Server

A Flask-based server acting as a central repository and analysis tool for data collected
by the VyPR framework.

## Components

The server consists of:
- An *insertion API*, used by VyPR during instrumentation and monitoring to store data.
- An *analysis API*, used by VyPR's Python analysis library.
- A *web tool*, for use by developers to explore data collected by VyPR.

## Setup

#### Installing Dependencies

Since the verdict server is written in Python, we encourage the use of a virtual environment so the dependencies for it can be separated from other projects.

To initialise a virtual environment, you will need `virtualenv` to run
```
virtualenv venv --python=python2.7
```
in the server's root directory.  To activate the virtual environment, run
```
source venv/bin/activate
```
After this is done, run
```
pip install -r requirements.txt
```
to install all dependencies.

#### Creating the Database

The verdict server attaches to a database, which is currently assumed to be SQLite.  You can attach any database with the schema found in `verdict-schema.sql`.
If starting with a blank database, we recommend running
```
sqlite3 verdicts.db < verdict-schema.sql
```

## Launching the Server

The server can be launched by running
```
python run_service.py --port <port number> --db <database> --path <service path>
```
where all arguments are optional but `--db` defines the database to attach to and `--path` defines the location of the source code of the service that VyPR is being used to monitor.

Once the server is running:
- VyPR can be directed to it, in which case the relevant part of the server's API will be accessed.
- You can access the analysis web tool by navigating to the web server's URL in you browser.

### Licence

(C) Copyright 2018 CERN and University of Manchester.
This software is distributed under the terms of the GNU General Public Licence version 3 (GPL Version 3), copied verbatim in the file "COPYING".
In applying this licence, CERN does not waive the privileges and immunities granted to it by virtue of its status as an Intergovernmental Organization or submit itself to any jurisdiction.

Author: Joshua Dawes - CERN, University of Manchester
