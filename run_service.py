"""
Main module for a test Flask-based web application.
"""
import app
from app import app_object
import argparse

parser = argparse.ArgumentParser(prog="Running the server side of VyPR")
parser.add_argument("--db", type=str, help="name of the database containing verdicts", required=False)
parser.add_argument("--events-db", type=str, help="name of the database containing events", required=False)
parser.add_argument("--path", type=str, help="path to the source code of monitored service", required=False)
parser.add_argument("--port", type=int, help="the port to server on")
args = parser.parse_args()

if args.db:
    app.database_string = args.db

if args.events_db:
    app.events_database_string = args.events_db

if args.path:
    app.monitored_service_path = args.path

if args.port:
    port = args.port
else:
    port = 8080

if __name__ == "__main__":

    # run the application
    app_object.run(host="0.0.0.0", debug=True, port=port)
