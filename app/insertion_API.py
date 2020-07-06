"""
Verdict storage end points for use by the VyPR monitoring machinery.
"""
from app import app_object
from flask import request, jsonify, render_template
from . import database
import json


@app_object.route("/register_verdicts/", methods=["post"])
def register_verdicts():
    """
    Receives a verdict from a monitored service, and stores it
    """

    verdict_data = json.loads(request.data)

    database.insert_verdicts(verdict_data)

    return "success"


@app_object.route("/insert_function_call_data/", methods=["post"])
def insert_function_call_data():
    """
    Receives a json list of condition ids that make up the program path for a given function run.
    This is inserted into the database so that mapping observations
    to the appropriate previous condition is straightforward
    (we just have to follow the chain for the correct number of steps).
    """
    call_data = json.loads(request.data)
    insertion_result = database.insert_function_call_data(call_data)
    return json.dumps(insertion_result)


@app_object.route("/store_property/", methods=["post"])
def store_property():
    """
    Receives a serialised property and stores it, with its hash.
    Note: the hash stored must be the same as the one given to the instruments in the
    monitored code.
    """
    property_data = json.loads(request.data)

    atom_index_to_db_index, function_id = database.insert_property(property_data)

    return json.dumps({"atom_index_to_db_index": atom_index_to_db_index, "function_id": function_id})


@app_object.route("/store_binding/", methods=["post"])
def store_binding():
    """
    Receives a serialised binding and stores it.
    """
    binding_data = json.loads(request.data)
    new_id = database.insert_binding(binding_data)

    return str(new_id)


@app_object.route("/store_instrumentation_point/", methods=["post"])
def store_instrumentation_point():
    """
    Receives a serialised instrumentation point, with branch condition sequence and path length data,
    and stores it.
    Note: this returns an ID which instrumentation then attaches to an instrument
    so we can determine which instrumentation point in the SCFG generated observations at runtime.
    """
    instrumentation_point_data = json.loads(request.data)
    new_id = database.insert_instrumentation_point(instrumentation_point_data)

    return str(new_id)


@app_object.route("/store_branching_condition/", methods=["post"])
def store_branching_condition():
    """
    Receives a serialised branching condition.
    Note: this returns an ID which instrumentation then attaches to branch recording instruments.
    """
    branching_condition_data = json.loads(request.data)
    new_id = database.insert_branching_condition(branching_condition_data)

    return str(new_id)


@app_object.route("/get_property_from_hash/<hash>/", methods=["get"])
def get_property_from_hash(hash):
    """
    Given a property hash, get the property data.  We need the property index in this case.
    :param: hash
    :return: String of serialised property.
    """
    return database.get_property_byhash(hash)


@app_object.route("/insert_test_data/", methods=["post"])
def insert_test_data():
    """
    Insert test result data in the case that VyPR is being used in a test suite.
    :return: String of insertion result.
    """
    test_data = json.loads(request.data)
    insertion_result = database.insert_test_call_data(test_data)
    return json.dumps(insertion_result)
