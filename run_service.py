"""
Main module for a test Flask-based web application.
"""
import app
from app import app_object
import argparse

parser = argparse.ArgumentParser(prog="Running the server side of VyPR")
parser.add_argument("--db", type=str, help="name of the database containing verdicts", required=False)
args = parser.parse_args()

if args.db:
    app.database_string = args.db

if __name__ == "__main__":

    # run the application
    app_object.run(host="0.0.0.0", debug=True, port=9002)
