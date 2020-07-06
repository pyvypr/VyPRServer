"""
Module to handle operations on events database for visualisation.
"""
import sqlite3
import datetime
import traceback
import dateutil
import json

import app


def connect():
    """
    Get a connection to the events database, currently sqlite.
    :return: sqlite connection
    """
    connection = sqlite3.connect(app.events_database_string)
    return connection


def get_events(type, start_time=None):
    """
    Get all events that currently exist for the given type.
    :return: List of event dictionaries created by instrumentation.
    """
    con = connect()
    con.row_factory = sqlite3.Row
    cursor = con.cursor()

    if not start_time:
        # set the start time to long ago enough to capture all events
        start_time = datetime.datetime.now() - datetime.timedelta(minutes=10000)

    # fix a time up to which we are taking events, so we know from
    # which time to start the next time we poll for events
    end_time = datetime.datetime.now()
    events = cursor.execute(
        "select * from event where type = ? and time_added > ? and time_added <= ?",
        [type, start_time, end_time]
    ).fetchall()
    events = map(dict, events)
    for n in range(len(events)):
        events[n]["data"] = json.loads(events[n]["data"])
    # we return the end time so that next time we can get events after this point
    return events, end_time


def get_function_name_to_code_map():
    """
    Go through all instrumentation events and construct a map from function names to source code
    to be used in visualisation of monitoring.
    :return: a dictionary mapping from function names to lists of lines of their source code.
    """
    con = connect()
    cursor = con.cursor()

    instrumentation_events = cursor.execute("select data from event where "
                                            "action_to_perform = 'begin_function_processing'").fetchall()
    function_to_code = {}
    for event in instrumentation_events:
        function_name = json.loads(event[0])["function_name"]
        if function_name not in function_to_code:
            function_to_code[function_name] = json.loads(event[0])["code"]

    return function_to_code



def insert_instrumentation_event(action, data, time):
    """
    Given an action, some data and an event time, create a new row in the event table.
    :param action:
    :param data:
    :param time:
    :return: Success or failure
    """
    con = connect()
    cursor = con.cursor()

    try:
        cursor.execute("insert into event (type, action_to_perform, data, time_added) values(?, ?, ?, ?)",
                       ["instrumentation", action, data, dateutil.parser.isoparse(time)])
        con.commit()
        return True
    except:
        traceback.print_exc()
        return False

def insert_monitoring_event(action, data, time):
    """
    Given an action, some data and an event time, create a new row in the event table.
    :param action:
    :param data:
    :param time:
    :return: Success or failure
    """
    con = connect()
    cursor = con.cursor()

    try:
        cursor.execute("insert into event (type, action_to_perform, data, time_added) values(?, ?, ?, ?)",
                       ["monitoring", action, data, dateutil.parser.isoparse(time)])
        con.commit()
        return True
    except:
        traceback.print_exc()
        return False
