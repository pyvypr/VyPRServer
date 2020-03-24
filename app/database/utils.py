"""
Module to provide database utility functions.
"""
import sqlite3
import json
import app

#database_string = "verdicts.db"


def get_connection():
    # for now, let exceptions appear in the log
    #global database_string
    return sqlite3.connect(app.database_string)


def query_db_one(query_string, arg):
    connection = get_connection()
    connection.row_factory = sqlite3.Row
    # enables saving the rows as a dictionary with name of column as key
    cursor = connection.cursor()
    list1 = cursor.execute(query_string, arg)
    f = list1.fetchone()
    connection.close()
    if f == None: return ("None")
    return json.dumps(dict(f))


def query_db_all(query_string, arg):
    connection = get_connection()
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    results = cursor.execute(query_string, arg)
    results = results.fetchall()
    connection.close()
    if results == None: return ("None")
    return json.dumps([dict(r) for r in results])
