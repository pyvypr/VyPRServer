"""
Module to provide database utility functions.
"""
import sqlite3

database_string = "verdicts.db"


def get_connection():
    # for now, let exceptions appear in the log
    global database_string
    return sqlite3.connect(database_string)